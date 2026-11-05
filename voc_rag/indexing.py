import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document

from voc_rag.config import Settings
from voc_rag.llm import create_embeddings

METADATA_COLUMNS = [
    "review_id", "score", "category", "delivery_status", "delay_days",
    "purchase_month", "purchase_month_num", "state",
]
BATCH_SIZE = 1000


def create_vector_store(settings: Settings) -> Chroma:
    # Cosseno explícito: nem todo provedor entrega vetores normalizados.
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=create_embeddings(settings),
        persist_directory=str(settings.chroma_dir),
        collection_metadata={"embedding_provider": settings.embedding_provider, "embedding_model": settings.embedding_model},
        collection_configuration={"hnsw": {"space": "cosine"}},
    )


def check_index(store: Chroma, settings: Settings) -> None:
    indexed = len(store.get(include=[])["ids"])
    expected = len(pd.read_parquet(settings.documents_path, columns=["review_id"]))
    if indexed != expected:
        raise RuntimeError(
            f"O índice {settings.collection_name} tem {indexed} documentos e a base preparada tem {expected}. "
            "Rode python -m voc_rag.cli index."
        )


class ReviewIndexer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self) -> int:
        rows = pd.read_parquet(self.settings.documents_path).to_dict("records")
        documents = [self._to_document(row) for row in rows]

        store = create_vector_store(self.settings)
        store.reset_collection()
        for start in range(0, len(documents), BATCH_SIZE):
            batch = documents[start:start + BATCH_SIZE]
            store.add_documents(batch, ids=[document.id for document in batch])
            print(f"{start + len(batch)}/{len(documents)} documentos indexados")
        return len(documents)

    @staticmethod
    def _to_document(row: dict) -> Document:
        metadata = {column: row[column] for column in METADATA_COLUMNS if not pd.isna(row[column])}
        return Document(id=row["review_id"], page_content=row["text"], metadata=metadata)
