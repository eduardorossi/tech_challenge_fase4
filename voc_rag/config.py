import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_EMBEDDING_MODELS = {
    "local": "intfloat/multilingual-e5-small",
    "openai": "text-embedding-3-small",
    "google": "gemini-embedding-2-preview",
}
# O E5 concentra as similaridades em uma faixa alta; o corte precisa acompanhar o modelo.
DEFAULT_MIN_SIMILARITY = {"local": 0.80, "openai": 0.40, "google": 0.40}
DEFAULT_CROSS_ENCODER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
VECTOR_STORES = {"faiss", "chroma"}
RERANKERS = {"cross_encoder", "llm"}


def env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "sim", "yes"}


def env_float(name: str, default: float | None = None) -> float | None:
    value = os.getenv(name, "").strip()
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    raw_dir: Path = ROOT / "data" / "raw"
    processed_dir: Path = ROOT / "data" / "processed"
    chroma_dir: Path = ROOT / "data" / "chroma"
    faiss_dir: Path = ROOT / "data" / "faiss"
    eval_dir: Path = ROOT / "data" / "eval"
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    chat_model: str = field(default_factory=lambda: os.getenv("CHAT_MODEL", "gpt-5.6-luna"))
    rerank_model: str = field(default_factory=lambda: os.getenv("RERANK_MODEL", ""))
    judge_provider: str = field(default_factory=lambda: os.getenv("JUDGE_PROVIDER", ""))
    judge_model: str = field(default_factory=lambda: os.getenv("JUDGE_MODEL", ""))
    temperature: float | None = field(default_factory=lambda: env_float("LLM_TEMPERATURE"))
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "local"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", ""))
    vector_store: str = field(default_factory=lambda: os.getenv("VECTOR_STORE", "faiss"))
    reranker: str = field(default_factory=lambda: os.getenv("RERANKER", "cross_encoder"))
    cross_encoder_model: str = field(default_factory=lambda: os.getenv("CROSS_ENCODER_MODEL", DEFAULT_CROSS_ENCODER))
    min_similarity: float | None = field(default_factory=lambda: env_float("MIN_SIMILARITY"))
    use_multi_query: bool = field(default_factory=lambda: env_flag("USE_MULTI_QUERY", True))
    use_bm25: bool = field(default_factory=lambda: env_flag("USE_BM25", True))
    use_rerank: bool = field(default_factory=lambda: env_flag("USE_RERANK", True))
    fetch_k: int = 40
    lexical_k: int = 40
    rerank_k: int = 30
    rrf_k: int = 60
    # Nota mínima do rerank por LLM (0 a 3) e logit mínimo do cross-encoder.
    min_relevance: int = 2
    # -1 calibrado no split dev: o corte 0 recusava recortes estreitos, como as 35 avaliações do Acre.
    min_rerank_score: float = field(default_factory=lambda: env_float("MIN_RERANK_SCORE", -1.0))
    mmr_lambda: float = 0.7
    top_k: int = 12
    overview_top_k: int = 20
    min_evidences: int = 3

    def __post_init__(self):
        if self.embedding_provider not in DEFAULT_EMBEDDING_MODELS:
            raise ValueError(f"EMBEDDING_PROVIDER desconhecido: {self.embedding_provider}. Use {', '.join(DEFAULT_EMBEDDING_MODELS)}.")
        if self.vector_store not in VECTOR_STORES:
            raise ValueError(f"VECTOR_STORE desconhecido: {self.vector_store}. Use {', '.join(sorted(VECTOR_STORES))}.")
        if self.reranker not in RERANKERS:
            raise ValueError(f"RERANKER desconhecido: {self.reranker}. Use {', '.join(sorted(RERANKERS))}.")
        # Campos vazios no .env herdam o modelo principal ou o padrão do provedor.
        if not self.embedding_model:
            object.__setattr__(self, "embedding_model", DEFAULT_EMBEDDING_MODELS[self.embedding_provider])
        if self.min_similarity is None:
            object.__setattr__(self, "min_similarity", DEFAULT_MIN_SIMILARITY[self.embedding_provider])
        if not self.rerank_model:
            object.__setattr__(self, "rerank_model", self.chat_model)
        if not self.judge_provider:
            object.__setattr__(self, "judge_provider", self.llm_provider)
        if not self.judge_model:
            object.__setattr__(self, "judge_model", self.chat_model)

    @property
    def collection_name(self) -> str:
        return "olist_reviews_" + re.sub(r"[^a-z0-9]+", "_", self.embedding_model.lower()).strip("_")

    @property
    def faiss_index_path(self) -> Path:
        return self.faiss_dir / f"{self.collection_name}.index"

    @property
    def faiss_ids_path(self) -> Path:
        return self.faiss_dir / f"{self.collection_name}.ids.parquet"

    @property
    def analytics_path(self) -> Path:
        return self.processed_dir / "reviews_analytics.parquet"

    @property
    def documents_path(self) -> Path:
        return self.processed_dir / "reviews_documents.parquet"
