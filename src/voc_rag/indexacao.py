"""Etapa 2 — Criação dos embeddings e indexação vetorial (FAISS).

Cada avaliação vira um vetor (E5 multilíngue, normalizado) gravado em um índice
FAISS. O id de cada vetor é a posição da avaliação em `documentos.parquet`,
onde ficam o texto e os metadados — assim o filtro por metadados (pandas) gera
a lista de ids permitidos para a busca vetorial (IDSelectorBatch).
"""
import time

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from . import config


def carregar_documentos() -> pd.DataFrame:
    if not config.ARQ_DOCUMENTOS.exists():
        raise FileNotFoundError("Base não encontrada. Rode antes: python -m voc_rag.preparacao")
    return pd.read_parquet(config.ARQ_DOCUMENTOS)


def carregar_indice() -> faiss.Index:
    if not config.ARQ_INDICE.exists():
        raise FileNotFoundError("Índice não encontrado. Rode antes: python -m voc_rag.indexacao")
    return faiss.read_index(str(config.ARQ_INDICE))


def main():
    df = carregar_documentos()
    print(f"{len(df):,} documentos carregados. Modelo: {config.MODELO_EMBEDDINGS}")

    modelo = SentenceTransformer(config.MODELO_EMBEDDINGS)
    textos = [config.PREFIXO_DOCUMENTO + t for t in df["texto"]]

    inicio = time.perf_counter()
    vetores = modelo.encode(textos, batch_size=64, normalize_embeddings=True,
                            show_progress_bar=True).astype(np.float32)
    print(f"\nEmbeddings: {vetores.shape} em {time.perf_counter() - inicio:.0f}s")

    # IndexFlatIP = busca exata por produto interno; com vetores normalizados, é o cosseno.
    # Com ~42k vetores de 384 dimensões (~64 MB) a busca exata leva milissegundos, então
    # não há motivo para aceitar a perda de recall de um índice aproximado (IVF/HNSW).
    indice = faiss.IndexFlatIP(vetores.shape[1])
    indice.add(vetores)
    faiss.write_index(indice, str(config.ARQ_INDICE))
    print(f"Índice FAISS com {indice.ntotal:,} vetores salvo em {config.ARQ_INDICE}")


if __name__ == "__main__":
    main()
