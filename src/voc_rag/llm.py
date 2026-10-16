"""Fábrica do modelo de linguagem (LangChain), com troca de provedor via .env."""
import os
from functools import lru_cache

from . import config


@lru_cache(maxsize=2)
def criar_llm(temperatura: float = 0.0):
    """Retorna um chat model do LangChain. Temperatura 0 = respostas determinísticas,
    o que reduz variação e "criatividade" indesejada em respostas baseadas em evidências.
    Modelos Gemini 3.x usam amostragem fixa e ignoram a temperatura (com um UserWarning)."""
    if config.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI  # dependência opcional
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY não definida no .env")
        return ChatOpenAI(model=config.OPENAI_CHAT_MODEL, temperature=temperatura)

    from langchain_google_genai import ChatGoogleGenerativeAI
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise RuntimeError("GOOGLE_API_KEY não definida no .env")
    return ChatGoogleGenerativeAI(model=config.GEMINI_CHAT_MODEL, temperature=temperatura)


def nome_modelo() -> str:
    return config.OPENAI_CHAT_MODEL if config.LLM_PROVIDER == "openai" else config.GEMINI_CHAT_MODEL
