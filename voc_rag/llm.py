import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, NamedTuple

from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from pydantic import BaseModel

from voc_rag.config import Settings

logger = logging.getLogger(__name__)

LANGCHAIN_PROVIDERS = {"openai": "openai", "google": "google_genai"}
API_KEYS = {"openai": ["OPENAI_API_KEY"], "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"]}
PLACEHOLDER_KEYS = {"sua-chave-aqui", "sua_chave_aqui", "your-api-key", "your_api_key", "changeme", "..."}
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

_fallbacks_used: ContextVar[list[str] | None] = ContextVar("voc_rag_fallbacks_used", default=None)


def configured_api_key(provider: str) -> str | None:
    """Devolve a primeira chave do provedor que não está vazia nem com o valor de exemplo."""
    if provider not in API_KEYS:
        raise ValueError(f"Provedor desconhecido: {provider}. Use {' ou '.join(API_KEYS)}.")
    for name in API_KEYS[provider]:
        value = os.getenv(name, "").strip()
        if value and value.lower() not in PLACEHOLDER_KEYS:
            return value
    return None


def require_api_key(provider: str) -> str:
    key = configured_api_key(provider)
    if key is None:
        raise RuntimeError(
            f"Defina {' ou '.join(API_KEYS[provider])} no arquivo .env para usar o provedor {provider} "
            "(o valor de exemplo do .env.example não vale como chave)."
        )
    return key


def create_chat_model(provider: str, model: str, temperature: float | None = None) -> BaseChatModel:
    options: dict[str, Any] = {"api_key": require_api_key(provider)}
    # Modelos de raciocínio recusam temperature; o parâmetro só é enviado quando definido no .env.
    if temperature is not None:
        options["temperature"] = temperature
    return init_chat_model(model, model_provider=LANGCHAIN_PROVIDERS[provider], **options)


class ChatModels(NamedTuple):
    llm: BaseChatModel | None
    fallback_llm: BaseChatModel | None
    # "provedor:modelo" de quem responde no lugar do principal, quando o principal não tem chave.
    replaced_primary: str | None = None


def create_chat_model_pair(
    provider: str,
    model: str,
    temperature: float | None = None,
    fallback_model: str | None = None,
    fallback_provider: str | None = "google",
) -> ChatModels:
    """Cria o modelo principal e o reserva. Sem chave do principal, o reserva assume o lugar dele."""
    primary = fallback = None
    try:
        primary = create_chat_model(provider, model, temperature)
    except RuntimeError as error:
        logger.warning("Modelo principal %s:%s indisponível: %s", provider, model, error)

    if fallback_provider and fallback_model and (fallback_provider, fallback_model) != (provider, model):
        try:
            fallback = create_chat_model(fallback_provider, fallback_model, temperature)
        except RuntimeError as error:
            logger.info("Modelo reserva %s:%s indisponível: %s", fallback_provider, fallback_model, error)

    if primary is None:
        if fallback is None:
            return ChatModels(None, None)
        replacement = f"{fallback_provider}:{fallback_model}"
        logger.warning("Usando o modelo reserva %s no lugar do principal.", replacement)
        return ChatModels(fallback, None, replacement)
    return ChatModels(primary, fallback)


def model_label(llm: BaseChatModel) -> str:
    name = getattr(llm, "model_name", None) or getattr(llm, "model", None) or type(llm).__name__
    return str(name).removeprefix("models/")


@contextmanager
def track_fallbacks() -> Iterator[list[str]]:
    """Coleta os modelos reservas acionados dentro do bloco (uma consulta do pipeline)."""
    used: list[str] = []
    token = _fallbacks_used.set(used)
    try:
        yield used
    finally:
        _fallbacks_used.reset(token)


def record_fallback(label: str) -> None:
    used = _fallbacks_used.get()
    if used is not None:
        used.append(label)


def structured_output_with_fallback(
    llm: BaseChatModel, schema: type[BaseModel], fallback_llm: BaseChatModel | None = None
) -> Runnable[Any, Any]:
    primary = llm.with_structured_output(schema)
    if fallback_llm is None:
        return primary
    fallback = fallback_llm.with_structured_output(schema)
    label = model_label(fallback_llm)

    def report(error: Exception) -> None:
        logger.warning(
            "O modelo principal (%s) falhou em %s: %s: %s. Tentando o modelo reserva %s.",
            model_label(llm), schema.__name__, type(error).__name__, error, label,
        )
        record_fallback(label)

    def invoke(input: Any, config: RunnableConfig | None = None) -> Any:
        try:
            return primary.invoke(input, config=config)
        except Exception as error:
            report(error)
            return fallback.invoke(input, config=config)

    async def ainvoke(input: Any, config: RunnableConfig | None = None) -> Any:
        try:
            return await primary.ainvoke(input, config=config)
        except Exception as error:
            report(error)
            return await fallback.ainvoke(input, config=config)

    return RunnableLambda(invoke, afunc=ainvoke, name=f"{schema.__name__}_with_fallback")


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
    api_key = require_api_key(settings.embedding_provider)
    if settings.embedding_provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model, api_key=api_key)
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.embedding_model, api_key=api_key)
