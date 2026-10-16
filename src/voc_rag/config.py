"""Configurações centrais da solução (caminhos, modelos e hiperparâmetros).

Tudo que é decisão de projeto fica aqui, em um único lugar, para facilitar
experimentos e a justificativa técnica no README.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Caminhos -----------------------------------------------------------------
# config.py fica em <raiz>/src/voc_rag/, então a raiz do projeto está três níveis acima
RAIZ = Path(__file__).resolve().parent.parent.parent

# Carrega o .env do projeto (ou outro arquivo indicado em VOC_ENV_FILE)
load_dotenv(os.getenv("VOC_ENV_FILE", RAIZ / ".env"))

# Pasta com os CSVs da Olist (padrão: data/, dentro da pasta do projeto)
PASTA_DADOS = Path(os.getenv("VOC_PASTA_DADOS", RAIZ / "data"))
PASTA_ARTEFATOS = RAIZ / "artefatos"
ARQ_DOCUMENTOS = PASTA_ARTEFATOS / "documentos.parquet"
ARQ_INDICE = PASTA_ARTEFATOS / "indice_faiss.bin"

# --- Modelos ------------------------------------------------------------------
# Embeddings: E5 multilíngue, treinado para busca assimétrica (pergunta curta -> passagem).
# Exige os prefixos "query: " e "passage: ".
MODELO_EMBEDDINGS = os.getenv("VOC_MODELO_EMBEDDINGS", "intfloat/multilingual-e5-small")
PREFIXO_CONSULTA = "query: "
PREFIXO_DOCUMENTO = "passage: "

# Reranker: cross-encoder multilíngue treinado no mMARCO (inclui português)
MODELO_RERANKER = os.getenv("VOC_MODELO_RERANKER", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

# LLM: provedor e modelo de chat (Gemini por padrão, como nas aulas de LangChain)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").split("#")[0].strip()
if LLM_PROVIDER == "auto":
    LLM_PROVIDER = "google" if os.getenv("GOOGLE_API_KEY") else "openai"
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "models/gemini-3.5-flash-lite")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

# --- Hiperparâmetros da recuperação -------------------------------------------
N_CANDIDATOS_VETORIAL = 100   # top-N da busca semântica (FAISS)
N_CANDIDATOS_BM25 = 100       # top-N da busca lexical (BM25)
N_PARA_RERANK = 60            # candidatos fundidos pelo RRF que vão ao reranker
RRF_K = 60                    # constante do Reciprocal Rank Fusion
K_FINAL_ESPECIFICA = 10       # evidências no contexto para perguntas pontuais
K_FINAL_PANORAMA = 20         # evidências para perguntas de panorama ("principais problemas")
MMR_LAMBDA = 0.7              # 1.0 = só relevância; 0.0 = só diversidade

# Limiar de relevância no score do reranker (logit). Abaixo dele a avaliação
# não é considerada evidência. Calibrado com perguntas dentro/fora do escopo.
LIMIAR_RERANK = float(os.getenv("VOC_LIMIAR_RERANK", "0.0"))
# Mínimo de evidências relevantes para o LLM ser acionado
MIN_EVIDENCIAS = int(os.getenv("VOC_MIN_EVIDENCIAS", "3"))
