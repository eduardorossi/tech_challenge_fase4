"""Etapa 3 — Recuperação das avaliações mais relevantes.

Estratégia (busca híbrida em dois estágios):
1. Busca vetorial no FAISS (significado)    ┐
2. Busca lexical BM25 (termos exatos)        ┘-> fusão por RRF
3. Reranking com cross-encoder (lê pergunta + avaliação juntos, mais preciso)
4. Limiar de relevância (descarta o que não responde à pergunta)
5. Remoção de textos repetidos + MMR (diversidade de evidências)
"""
import math
import re
import time
import unicodedata
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from . import config
from .filtros import Filtros
from .indexacao import carregar_documentos, carregar_indice

# Stopwords mínimas para o BM25 (palavras sem poder discriminativo)
STOPWORDS = set("""a o as os um uma uns umas de da do das dos em na no nas nos por para pra
com sem e ou que se ao aos à às é foi ser são era muito mais mas me meu minha eu ele ela
isso esse essa este esta já não nao sim tudo todo toda bem""".split())


def tokenizar_bm25(texto: str) -> list:
    """Minúsculas, sem acentos, sem stopwords e com 'stemming' por truncamento (5 letras).

    O truncamento aproxima variações da mesma raiz sem depender de recursos externos:
    entrega/entregue/entregaram -> 'entre'; atraso/atrasado -> 'atras'.
    """
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", texto)
    return [t[:5] for t in tokens if t not in STOPWORDS and len(t) > 1]


def rrf(rankings: list, k: int = config.RRF_K) -> list:
    """Reciprocal Rank Fusion: soma 1/(k + posição) de cada ranking."""
    pontos = {}
    for ranking in rankings:
        for posicao, doc_id in enumerate(ranking):
            pontos[doc_id] = pontos.get(doc_id, 0.0) + 1.0 / (k + posicao + 1)
    return sorted(pontos.items(), key=lambda par: -par[1])


@dataclass
class Evidencia:
    """Uma avaliação recuperada, com todos os scores para rastreabilidade."""
    review_id: str
    texto: str
    metadados: dict
    score_rerank: float
    score_rrf: float
    pos_vetorial: int | None = None   # posição no ranking vetorial (None = não apareceu)
    pos_bm25: int | None = None       # posição no ranking BM25
    repeticoes: int = 1               # quantas avaliações idênticas foram agrupadas nesta
    subconsulta: str = ""             # subconsulta (subtema) que recuperou esta avaliação


@dataclass
class ResultadoRecuperacao:
    evidencias: list
    rastreio: dict = field(default_factory=dict)  # números de cada etapa (exibidos na interface)


class Recuperador:
    """Carrega índices e modelos uma única vez e executa a recuperação híbrida."""

    def __init__(self):
        t0 = time.perf_counter()
        self.df = carregar_documentos()
        self.posicao = {rid: i for i, rid in enumerate(self.df["review_id"])}
        self.indice = carregar_indice()
        if self.indice.ntotal != len(self.df):
            raise RuntimeError("Índice desatualizado em relação à base. Rode: python -m voc_rag.indexacao")
        self.embedder = SentenceTransformer(config.MODELO_EMBEDDINGS)
        self.reranker = CrossEncoder(config.MODELO_RERANKER)
        # BM25 é reconstruído em memória (poucos segundos para ~42k textos curtos)
        self.bm25 = BM25Okapi([tokenizar_bm25(t) for t in self.df["texto"]])
        self.categorias = sorted(self.df["categoria"].unique())
        print(f"Recuperador pronto em {time.perf_counter() - t0:.1f}s "
              f"({len(self.df):,} avaliações indexadas)")

    # --- Estágio 1: candidatos -------------------------------------------------
    def busca_vetorial(self, consulta: str, no_recorte: pd.Series, n: int) -> list:
        """Top-n por similaridade de cosseno, restrito às avaliações do recorte."""
        vetor = self.embedder.encode([config.PREFIXO_CONSULTA + consulta],
                                     normalize_embeddings=True).astype(np.float32)
        params = None
        if not no_recorte.all():
            # IDSelectorBatch: o FAISS só considera os ids (posições) que passaram nos filtros
            permitidos = np.flatnonzero(no_recorte.to_numpy()).astype(np.int64)
            params = faiss.SearchParameters(sel=faiss.IDSelectorBatch(permitidos))
        _, posicoes = self.indice.search(vetor, n, params=params)
        return [self.df["review_id"].iat[p] for p in posicoes[0] if p >= 0]

    def busca_bm25(self, consulta: str, no_recorte: pd.Series, n: int) -> list:
        tokens = tokenizar_bm25(consulta)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        scores[~no_recorte.to_numpy()] = -1          # aplica os filtros de metadados
        top = np.argsort(-scores)[:n]
        return [self.df["review_id"].iat[i] for i in top if scores[i] > 0]

    def candidatos_reranqueados(self, consulta: str, no_recorte: pd.Series, n_universo: int,
                                n_rerank: int) -> list:
        """Vetorial + BM25 -> RRF -> cross-encoder. Devolve Evidencias ordenadas pelo reranker."""
        ids_vet = self.busca_vetorial(consulta, no_recorte,
                                      min(config.N_CANDIDATOS_VETORIAL, n_universo))
        ids_bm25 = self.busca_bm25(consulta, no_recorte, config.N_CANDIDATOS_BM25)
        fundidos = rrf([ids_vet, ids_bm25])[:n_rerank]
        if not fundidos:
            return []
        textos = [self.df["texto"].iat[self.posicao[d]] for d, _ in fundidos]
        scores = self.reranker.predict([(consulta, t) for t in textos], show_progress_bar=False)
        pos_vet = {d: p for p, d in enumerate(ids_vet)}
        pos_bm = {d: p for p, d in enumerate(ids_bm25)}
        candidatos = [
            Evidencia(review_id=d, texto=t, score_rerank=float(s), score_rrf=s_rrf,
                      metadados=_metadados(self.df.iloc[self.posicao[d]]),
                      pos_vetorial=pos_vet.get(d), pos_bm25=pos_bm.get(d), subconsulta=consulta)
            for (d, s_rrf), t, s in zip(fundidos, textos, scores)
        ]
        return sorted(candidatos, key=lambda e: -e.score_rerank)

    # --- Pipeline completo -----------------------------------------------------
    def recuperar(self, consultas: list, filtros: Filtros, k: int) -> ResultadoRecuperacao:
        """Recupera evidências para uma ou mais consultas (multi-query).

        Cada subconsulta é buscada e reranqueada separadamente; depois cada uma recebe
        uma cota de vagas no contexto, para que todos os subtemas com evidência apareçam.
        """
        rastreio = {"filtros_metadados": filtros.descricao()}
        t0 = time.perf_counter()

        no_recorte = filtros.no_recorte(self.df)
        n_universo = int(no_recorte.sum())
        rastreio["avaliacoes_no_recorte"] = n_universo
        if n_universo == 0:
            rastreio["motivo"] = "Nenhuma avaliação atende aos filtros de metadados."
            return ResultadoRecuperacao([], rastreio)

        # Com várias subconsultas, cada uma reranqueia menos candidatos (custo controlado)
        n_rerank = config.N_PARA_RERANK if len(consultas) == 1 else max(30, config.N_PARA_RERANK // len(consultas))

        por_consulta, detalhes = [], []
        for consulta in consultas:
            candidatos = self.candidatos_reranqueados(consulta, no_recorte, n_universo, n_rerank)
            # Limiar de relevância + agrupamento de textos idênticos ("Muito bom" x200)
            relevantes = _agrupar_repetidos(
                [e for e in candidatos if e.score_rerank >= config.LIMIAR_RERANK])
            por_consulta.append(relevantes)
            detalhes.append({
                "consulta": consulta,
                "candidatos_reranqueados": len(candidatos),
                "melhor_score_rerank": round(candidatos[0].score_rerank, 2) if candidatos else None,
                "relevantes_acima_do_limiar": len(relevantes),
            })
        rastreio["subconsultas"] = detalhes
        melhores = [d["melhor_score_rerank"] for d in detalhes if d["melhor_score_rerank"] is not None]
        rastreio["melhor_score_rerank"] = max(melhores) if melhores else None

        # Seleção: cota por subconsulta (cobertura de subtemas) + MMR dentro de cada cota
        com_evidencia = [r for r in por_consulta if r]
        cota = math.ceil(k / len(com_evidencia)) if com_evidencia else 0
        selecionadas, usados = [], set()
        for relevantes in com_evidencia:
            novas = [e for e in relevantes if e.review_id not in usados]
            for e in self._mmr(novas, cota):
                selecionadas.append(e)
                usados.add(e.review_id)
        selecionadas = selecionadas[:k]
        rastreio["evidencias_finais"] = len(selecionadas)
        rastreio["tempo_recuperacao_s"] = round(time.perf_counter() - t0, 2)
        return ResultadoRecuperacao(selecionadas, rastreio)

    def _mmr(self, candidatos: list, k: int) -> list:
        """Maximal Marginal Relevance: equilibra relevância e diversidade.

        Evita que o contexto seja ocupado por 10 variações de "chegou atrasado",
        o que é essencial em perguntas de panorama ("principais problemas").
        """
        if len(candidatos) <= k:
            return candidatos
        # Vetores já estão no índice: reconstruímos em vez de recalcular embeddings
        vetores = np.vstack([self.indice.reconstruct(int(self.posicao[e.review_id]))
                             for e in candidatos])
        relevancia = 1 / (1 + np.exp(-np.array([e.score_rerank for e in candidatos])))  # sigmoide
        similaridade = vetores @ vetores.T
        escolhidos = [0]  # o mais relevante entra primeiro
        while len(escolhidos) < k:
            restantes = [i for i in range(len(candidatos)) if i not in escolhidos]
            redundancia = similaridade[np.ix_(restantes, escolhidos)].max(axis=1)
            mmr = config.MMR_LAMBDA * relevancia[restantes] - (1 - config.MMR_LAMBDA) * redundancia
            escolhidos.append(restantes[int(np.argmax(mmr))])
        return [candidatos[i] for i in escolhidos]


def _metadados(linha: pd.Series) -> dict:
    return {c: (linha[c].item() if hasattr(linha[c], "item") else linha[c])
            for c in ["nota", "sentimento", "categoria", "status_entrega", "dias_atraso",
                      "customer_state", "ano_mes", "data_avaliacao", "order_id"]}


def _agrupar_repetidos(evidencias: list) -> list:
    """Mantém a primeira ocorrência de cada texto e conta as repetições."""
    vistos = {}
    for e in evidencias:
        chave = re.sub(r"\W+", " ", e.texto.lower()).strip()
        if chave in vistos:
            vistos[chave].repeticoes += 1
        else:
            vistos[chave] = e
    return list(vistos.values())


def estatisticas(evidencias: list) -> dict:
    """Resumo quantitativo das evidências (calculado nos dados, não pelo LLM)."""
    if not evidencias:
        return {}
    meta = pd.DataFrame([e.metadados for e in evidencias])
    pesos = pd.Series([e.repeticoes for e in evidencias])
    return {
        "total_avaliacoes": int(pesos.sum()),
        "nota_media": round(float(np.average(meta["nota"], weights=pesos)), 2),
        "por_sentimento": meta.groupby("sentimento").size().to_dict(),
        "por_status_entrega": meta.groupby("status_entrega").size().to_dict(),
        "top_categorias": meta["categoria"].value_counts().head(5).to_dict(),
    }
