import os

from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from voc_rag.config import Settings

LANGCHAIN_PROVIDERS = {"openai": "openai", "google": "google_genai"}
API_KEYS = {"openai": ["OPENAI_API_KEY"], "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"]}
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "


def require_api_key(provider: str) -> None:
    if provider not in API_KEYS:
        raise ValueError(f"Provedor desconhecido: {provider}. Use openai ou google.")
    if not any(os.getenv(name) for name in API_KEYS[provider]):
        raise RuntimeError(f"Defina {' ou '.join(API_KEYS[provider])} no arquivo .env para usar o provedor {provider}.")


def create_chat_model(provider: str, model: str, temperature: float | None = None) -> BaseChatModel:
    require_api_key(provider)
    # Modelos de raciocínio recusam temperature; o parâmetro só é enviado quando definido no .env.
    options = {} if temperature is None else {"temperature": temperature}
    return init_chat_model(model, model_provider=LANGCHAIN_PROVIDERS[provider], **options)


class E5Embeddings(Embeddings):
    """Embeddings locais da família E5, que exigem os prefixos "query: " e "passage: "."""

    def __init__(self, model: str, batch_size: int = 64, encoder=None):
        if encoder is None:
            from sentence_transformers import SentenceTransformer

            encoder = SentenceTransformer(model)
        self.model = encoder
        self.batch_size = batch_size
        # Os prefixos só valem para a família E5; outro modelo local recebe o texto puro.
        self.use_prefixes = "e5" in model.lower()

    def _encode(self, texts: list[str], prefix: str, show_progress: bool = False) -> list[list[float]]:
        texts = [prefix + text for text in texts] if self.use_prefixes else texts
        vectors = self.model.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=show_progress
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, E5_PASSAGE_PREFIX, show_progress=len(texts) > self.batch_size)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text], E5_QUERY_PREFIX)[0]


def create_embeddings(settings: Settings) -> Embeddings:
    if settings.embedding_provider == "local":
        return E5Embeddings(settings.embedding_model)
    require_api_key(settings.embedding_provider)
    if settings.embedding_provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.embedding_model)
