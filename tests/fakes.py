import numpy as np

from voc_rag.config import Settings
from voc_rag.schemas import ReviewFilters

TEST_SETTINGS = Settings(min_similarity=0.5, fetch_k=10, lexical_k=10, rerank_k=10, top_k=4, overview_top_k=6)


class FakeEmbeddings:
    def __init__(self, vectors: dict[str, list[float]]):
        self.vectors = vectors

    def embed_query(self, text: str) -> list[float]:
        return self.vectors[text]


class FakeVectorStore:
    # Imita a interface de FaissReviewStore e ChromaReviewStore usada pelo retriever.
    def __init__(self, records: list[dict], query_vectors: dict[str, list[float]]):
        self.records = {record["id"]: record for record in records}
        self.embeddings = FakeEmbeddings(query_vectors)
        self.filters = []

    def count(self) -> int:
        return len(self.records)

    def search(self, query_vector, k, filters: ReviewFilters) -> list[str]:
        self.filters.append(filters)
        query = np.array(query_vector)
        scored = []
        for record in self.records.values():
            vector = np.array(record["vector"]) / np.linalg.norm(record["vector"])
            scored.append((record["id"], float(vector @ query)))
        return [doc_id for doc_id, _ in sorted(scored, key=lambda pair: -pair[1])[:k]]

    def fetch(self, ids):
        return {
            doc_id: (self.records[doc_id]["text"], self.records[doc_id]["metadata"], self.records[doc_id]["vector"])
            for doc_id in ids if doc_id in self.records
        }


class FakeLexical:
    def __init__(self, results: dict[str, list[str]]):
        self.results = results

    def search(self, query: str, filters: ReviewFilters, k: int) -> list[str]:
        return self.results.get(query, [])[:k]


class FakeReranker:
    # Mesma escala do LLMReranker: notas de 0 a 3 e corte em 2.
    name = "fake"
    model = "fake"
    min_score = 2

    def __init__(self, grades: dict[str, int]):
        self.grades = grades
        self.calls = []

    @staticmethod
    def score(relevance, similarity):
        return (relevance + similarity) / 4

    def grade(self, question, filters, queries, texts):
        self.calls.append((question, filters, queries))
        return [[self.grades.get(text, 0) for text in candidates] for candidates in texts]


def record(doc_id: str, text: str, vector: list[float], **metadata) -> dict:
    return {"id": doc_id, "text": text, "vector": vector, "metadata": {"review_id": doc_id, **metadata}}
