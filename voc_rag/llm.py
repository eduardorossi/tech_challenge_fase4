import os

from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from voc_rag.config import Settings

LANGCHAIN_PROVIDERS = {"openai": "openai", "google": "google_genai"}
API_KEYS = {"openai": ["OPENAI_API_KEY"], "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"]}


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


def create_embeddings(settings: Settings) -> Embeddings:
    require_api_key(settings.embedding_provider)
    if settings.embedding_provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.embedding_model)
