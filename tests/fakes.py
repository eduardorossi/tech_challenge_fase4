import numpy as np
from langchain_core.documents import Document

from voc_rag.config import Settings
from voc_rag.schemas import ReviewFilters

TEST_SETTINGS = Settings(min_similarity=0.5, fetch_k=10, lexical_k=10, rerank_k=10, top_k=4, overview_top_k=6)


class FakeEmbeddings:
    def __init__(self, vectors: dict[str, list[float]]):
        self.vectors = vectors

    def embed_query(self, text: str) -> list[float]:
        return self.vectors[text]


class FakeVectorStore:
    # Imita a parte da API do langchain_chroma.Chroma usada pelo retriever.
    def __init__(self, records: list[dict], query_vectors: dict[str, list[float]]):
        self.records = {record["id"]: record for record in records}
        self.embeddings = FakeEmbeddings(query_vectors)
        self.filters = []

    def similarity_search_by_vector_with_relevance_scores(self, embedding, k, filter=None):
        self.filters.append(filter)
        query = np.array(embedding)
        scored = []
        for record in self.records.values():
            vector = np.array(record["vector"]) / np.linalg.norm(record["vector"])
            scored.append((Document(id=record["id"], page_content=record["text"], metadata=record["metadata"]), 1 - float(vector @ query)))
        return sorted(scored, key=lambda pair: pair[1])[:k]

    def get(self, ids=None, include=None):
        records = [self.records[doc_id] for doc_id in ids if doc_id in self.records]
        return {
            "ids": [record["id"] for record in records],
            "documents": [record["text"] for record in records],
            "metadatas": [record["metadata"] for record in records],
            "embeddings": [record["vector"] for record in records],
        }


class FakeLexical:
    def __init__(self, results: dict[str, list[str]]):
        self.results = results

    def search(self, query: str, filters: ReviewFilters, k: int) -> list[str]:
        return self.results.get(query, [])[:k]


class FakeReranker:
    def __init__(self, grades: dict[str, int]):
        self.grades = grades
        self.calls = []

    def grade(self, question, filters, queries, texts):
        self.calls.append((question, filters, queries))
        return [[self.grades.get(text, 0) for text in candidates] for candidates in texts]


def record(doc_id: str, text: str, vector: list[float], **metadata) -> dict:
    return {"id": doc_id, "text": text, "vector": vector, "metadata": {"review_id": doc_id, **metadata}}
