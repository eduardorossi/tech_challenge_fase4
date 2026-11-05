import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_EMBEDDING_MODELS = {"openai": "text-embedding-3-small", "google": "gemini-embedding-2-preview"}


def env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "sim", "yes"}


def env_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    return float(value) if value else None


@dataclass(frozen=True)
class Settings:
    raw_dir: Path = ROOT / "data" / "raw"
    processed_dir: Path = ROOT / "data" / "processed"
    chroma_dir: Path = ROOT / "data" / "chroma"
    eval_dir: Path = ROOT / "data" / "eval"
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    chat_model: str = field(default_factory=lambda: os.getenv("CHAT_MODEL", "gpt-5.6-luna"))
    rerank_model: str = field(default_factory=lambda: os.getenv("RERANK_MODEL", ""))
    judge_provider: str = field(default_factory=lambda: os.getenv("JUDGE_PROVIDER", ""))
    judge_model: str = field(default_factory=lambda: os.getenv("JUDGE_MODEL", ""))
    temperature: float | None = field(default_factory=lambda: env_float("LLM_TEMPERATURE"))
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", ""))
    min_similarity: float = field(default_factory=lambda: float(os.getenv("MIN_SIMILARITY", "0.40")))
    use_multi_query: bool = field(default_factory=lambda: env_flag("USE_MULTI_QUERY", True))
    use_bm25: bool = field(default_factory=lambda: env_flag("USE_BM25", True))
    use_rerank: bool = field(default_factory=lambda: env_flag("USE_RERANK", True))
    fetch_k: int = 40
    lexical_k: int = 40
    rerank_k: int = 30
    rrf_k: int = 60
    min_relevance: int = 2
    mmr_lambda: float = 0.7
    top_k: int = 12
    overview_top_k: int = 20
    min_evidences: int = 3

    def __post_init__(self):
        # Campos vazios no .env herdam o modelo principal ou o padrão do provedor.
        if not self.embedding_model:
            object.__setattr__(self, "embedding_model", DEFAULT_EMBEDDING_MODELS[self.embedding_provider])
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
    def analytics_path(self) -> Path:
        return self.processed_dir / "reviews_analytics.parquet"

    @property
    def documents_path(self) -> Path:
        return self.processed_dir / "reviews_documents.parquet"
