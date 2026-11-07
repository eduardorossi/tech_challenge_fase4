import numpy as np
import pandas as pd
from langchain_core.embeddings import Embeddings

from voc_rag.schemas import ReviewFilters
from voc_rag.stats import filter_mask

METADATA_COLUMNS = [
    "review_id", "score", "category", "delivery_status", "delay_days",
    "purchase_month", "purchase_month_num", "state",
]
CHROMA_OPERATORS = {">=": "$gte", "<=": "$lte", "==": "$eq", "in": "$in"}

# Texto, metadados e vetor de um documento do índice.
Record = tuple[str, dict, list[float]]


def to_chroma_filter(filters: ReviewFilters) -> dict | None:
    clauses = [{column: {CHROMA_OPERATORS[op]: value}} for column, op, value in filters.conditions()]
    if len(clauses) <= 1:
        return clauses[0] if clauses else None
    return {"$and": clauses}


def native(value):
    # Converte tipos do numpy para tipos do Python, aceitos como metadados.
    return value.item() if hasattr(value, "item") else value


def row_metadata(row: dict) -> dict:
    return {column: native(row[column]) for column in METADATA_COLUMNS if column in row and not pd.isna(row[column])}


class FaissReviewStore:
    """Índice exato (produto interno sobre vetores normalizados) com pré-filtro de metadados.

    O filtro vira uma máscara do pandas, e o IDSelectorBatch faz o FAISS comparar a consulta
    só com as avaliações do recorte. A busca continua exata em recortes pequenos, sem a perda
    de recall de aplicar o filtro depois da busca aproximada.
    """

    def __init__(self, index, documents: pd.DataFrame, embeddings: Embeddings):
        if index.ntotal != len(documents):
            raise RuntimeError(
                f"O índice FAISS tem {index.ntotal} vetores e a base preparada tem {len(documents)} documentos. "
                "Rode python -m voc_rag.cli index."
            )
        self.index = index
        self.documents = documents.reset_index(drop=True)
        self.embeddings = embeddings
        self.positions = {doc_id: position for position, doc_id in enumerate(self.documents["review_id"])}
        self.metadata = self.documents.to_dict("records")

    @classmethod
    def load(cls, settings, embeddings: Embeddings) -> "FaissReviewStore":
        import faiss

        if not settings.faiss_index_path.exists():
            raise RuntimeError(f"Índice {settings.faiss_index_path} não encontrado. Rode python -m voc_rag.cli index.")
        documents = pd.read_parquet(settings.documents_path)
        indexed_ids = pd.read_parquet(settings.faiss_ids_path)["review_id"]
        if not indexed_ids.equals(documents["review_id"]):
            raise RuntimeError("O índice FAISS foi gerado com outra versão da base preparada. Rode python -m voc_rag.cli index.")
        return cls(faiss.read_index(str(settings.faiss_index_path)), documents, embeddings)

    @staticmethod
    def build(settings, embeddings: Embeddings, documents: pd.DataFrame) -> int:
        import faiss

        vectors = np.asarray(embeddings.embed_documents(documents["text"].tolist()), dtype=np.float32)
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        settings.faiss_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(settings.faiss_index_path))
        documents[["review_id"]].to_parquet(settings.faiss_ids_path, index=False)
        return index.ntotal

    def count(self) -> int:
        return self.index.ntotal

    def search(self, query_vector: list[float], k: int, filters: ReviewFilters) -> list[str]:
        import faiss

        params = None
        if filters.conditions():
            allowed = np.flatnonzero(filter_mask(self.documents, filters).to_numpy()).astype(np.int64)
            if len(allowed) == 0:
                return []
            k = min(k, len(allowed))
            params = faiss.SearchParameters(sel=faiss.IDSelectorBatch(allowed))
        query = np.asarray([query_vector], dtype=np.float32)
        _, positions = self.index.search(query, min(k, self.index.ntotal), params=params)
        return [self.documents["review_id"].iat[position] for position in positions[0] if position >= 0]

    def fetch(self, ids: list[str]) -> dict[str, Record]:
        # Os vetores saem do próprio índice (reconstruct): o MMR não recalcula embeddings.
        found = {}
        for doc_id in ids:
            position = self.positions.get(doc_id)
            if position is None:
                continue
            row = self.metadata[position]
            found[doc_id] = (row["text"], row_metadata(row), self.index.reconstruct(position).tolist())
        return found


class ChromaReviewStore:
    """Adapta o langchain_chroma.Chroma à interface usada pelo retriever."""

    def __init__(self, chroma):
        self.chroma = chroma
        self.embeddings = chroma.embeddings

    @classmethod
    def create(cls, settings, embeddings: Embeddings) -> "ChromaReviewStore":
        from langchain_chroma import Chroma

        # Cosseno explícito: nem todo provedor entrega vetores normalizados.
        return cls(Chroma(
            collection_name=settings.collection_name,
            embedding_function=embeddings,
            persist_directory=str(settings.chroma_dir),
            collection_metadata={"embedding_provider": settings.embedding_provider, "embedding_model": settings.embedding_model},
            collection_configuration={"hnsw": {"space": "cosine"}},
        ))

    def build(self, documents: pd.DataFrame, batch_size: int = 1000) -> int:
        from langchain_core.documents import Document

        rows = documents.to_dict("records")
        self.chroma.reset_collection()
        for start in range(0, len(rows), batch_size):
            batch = [Document(id=row["review_id"], page_content=row["text"], metadata=row_metadata(row)) for row in rows[start:start + batch_size]]
            self.chroma.add_documents(batch, ids=[document.id for document in batch])
            print(f"{start + len(batch)}/{len(rows)} documentos indexados")
        return len(rows)

    def count(self) -> int:
        return len(self.chroma.get(include=[])["ids"])

    def search(self, query_vector: list[float], k: int, filters: ReviewFilters) -> list[str]:
        results = self.chroma.similarity_search_by_vector_with_relevance_scores(
            query_vector, k=k, filter=to_chroma_filter(filters)
        )
        return [document.id for document, _ in results]

    def fetch(self, ids: list[str]) -> dict[str, Record]:
        if not ids:
            return {}
        records = self.chroma.get(ids=ids, include=["documents", "metadatas", "embeddings"])
        return {
            doc_id: (text, metadata or {}, vector)
            for doc_id, text, metadata, vector in zip(
                records["ids"], records.get("documents", []), records.get("metadatas", []), records.get("embeddings", [])
            )
        }


def search_with_similarity(store, query: str, k: int, filters: ReviewFilters | None = None) -> list[tuple[str, dict, float]]:
    """Busca densa de um texto, com o cosseno de cada resultado. Usada nos notebooks e na calibração."""
    vector = np.asarray(store.embeddings.embed_query(query), dtype=float)
    vector = vector / (np.linalg.norm(vector) or 1)
    ids = store.search(vector.tolist(), k, filters or ReviewFilters.empty())
    found = store.fetch(ids)
    results = []
    for doc_id in ids:
        text, metadata, stored = found[doc_id]
        stored = np.asarray(stored, dtype=float)
        results.append((text, metadata, float(stored @ vector / (np.linalg.norm(stored) or 1))))
    return results
