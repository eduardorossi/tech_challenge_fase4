import pandas as pd

from voc_rag.config import Settings
from voc_rag.llm import create_embeddings
from voc_rag.vector_store import ChromaReviewStore, FaissReviewStore


def create_vector_store(settings: Settings):
    embeddings = create_embeddings(settings)
    if settings.vector_store == "faiss":
        return FaissReviewStore.load(settings, embeddings)
    return ChromaReviewStore.create(settings, embeddings)


def index_name(settings: Settings) -> str:
    return f"{settings.vector_store}:{settings.collection_name}"


def check_index(store, settings: Settings) -> None:
    indexed = store.count()
    expected = len(pd.read_parquet(settings.documents_path, columns=["review_id"]))
    if indexed != expected:
        raise RuntimeError(
            f"O índice {index_name(settings)} tem {indexed} documentos e a base preparada tem {expected}. "
            "Rode python -m voc_rag.cli index."
        )


class ReviewIndexer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self) -> int:
        documents = pd.read_parquet(self.settings.documents_path)
        embeddings = create_embeddings(self.settings)
        if self.settings.vector_store == "faiss":
            return FaissReviewStore.build(self.settings, embeddings, documents)
        return ChromaReviewStore.create(self.settings, embeddings).build(documents)
