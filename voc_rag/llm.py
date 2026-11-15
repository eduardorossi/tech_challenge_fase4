import os
import logging
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from pydantic import BaseModel

from voc_rag.config import Settings

logger = logging.getLogger(__name__)

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

def create_chat_model_pair(
    provider: str, model: str, temperature: float | None = None, fallback_model: str | None = None
) -> tuple[BaseChatModel | None, BaseChatModel | None]:
    primary = None
    fallback = None
    try:
        primary = create_chat_model(provider, model, temperature)
    except RuntimeError as error:
        logger.warning("Modelo principal indisponível: %s", error)

    if provider == "openai" and fallback_model:
        try:
            fallback = create_chat_model("google", fallback_model, temperature)
        except RuntimeError as error:
            logger.info("Fallback Google Gemini indisponível: %s", error)

    if primary is None:
        return fallback, None
    return primary, fallback


def structured_output_with_fallback(
    llm: BaseChatModel, schema: type[BaseModel], fallback_llm: BaseChatModel | None = None
) -> Runnable[Any, Any]:
    primary = llm.with_structured_output(schema)
    if fallback_llm is None:
        return primary
    fallback = fallback_llm.with_structured_output(schema)

    def invoke(input: Any, config: RunnableConfig | None = None) -> Any:
        try:
            return primary.invoke(input, config=config)
        except Exception as error:
            logger.warning(
                "A chamada ao modelo principal falhou (%s); tentando o Google Gemini.",
                type(error).__name__,
            )
            try:
                return fallback.invoke(input, config=config)
            except Exception:
                logger.exception("A chamada de fallback ao Google Gemini também falhou.")
                raise

    async def ainvoke(input: Any, config: RunnableConfig | None = None) -> Any:
        try:
            return await primary.ainvoke(input, config=config)
        except Exception as error:
            logger.warning(
                "A chamada ao modelo principal falhou (%s); tentando o Google Gemini.",
                type(error).__name__,
            )
            try:
                return await fallback.ainvoke(input, config=config)
            except Exception:
                logger.exception("A chamada de fallback ao Google Gemini também falhou.")
                raise

    return RunnableLambda(invoke, afunc=ainvoke, name="structured_output_with_google_fallback")

class E5Embeddings(Embeddings):
    """Embeddings locais da família E5, que exigem os prefixos "query: " e "passage: "."""

    def __init__(self, model: str, batch_size: int = 64, encoder=None):
        if encoder is None:
            from sentence_transformers import SentenceTransformer

            encoder = SentenceTransformer(model)
        self.model = encoder
        self.batch_size = batch_size
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
