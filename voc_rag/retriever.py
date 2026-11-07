from dataclasses import dataclass, field

import numpy as np

from voc_rag.config import Settings
from voc_rag.schemas import Evidence, ReviewFilters


def describe_filters(filters: ReviewFilters) -> str:
    return ", ".join(f"{column} {op} {value}" for column, op, value in filters.conditions()) or "nenhum"


def reciprocal_rank_fusion(rankings: list[list[str]], k: int) -> list[str]:
    # Soma 1 / (k + posição) de cada lista; dispensa normalizar scores de buscas diferentes.
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1 / (k + position)
    return sorted(scores, key=scores.get, reverse=True)


def text_key(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".!?")


def normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def maximal_marginal_relevance(relevance: np.ndarray, vectors: np.ndarray, k: int, weight: float) -> list[int]:
    # Equilibra relevância e diversidade: evita gastar as vagas com variações de "chegou atrasado".
    if len(relevance) <= k:
        return list(range(len(relevance)))
    similarity = vectors @ vectors.T
    chosen = [int(np.argmax(relevance))]
    while len(chosen) < k:
        remaining = [index for index in range(len(relevance)) if index not in chosen]
        redundancy = similarity[np.ix_(remaining, chosen)].max(axis=1)
        scores = weight * relevance[remaining] - (1 - weight) * redundancy
        chosen.append(remaining[int(np.argmax(scores))])
    return chosen


@dataclass
class Candidate:
    review_id: str
    text: str
    metadata: dict
    vector: np.ndarray
    similarity: float
    query: str
    dense_rank: int | None = None
    lexical_rank: int | None = None
    relevance: float | None = None
    rank_score: float | None = None

    @property
    def score(self) -> float:
        # Com rerank, o reranker define a escala (nota do LLM ou sigmoide do logit); sem ele, vale a similaridade.
        return self.rank_score if self.rank_score is not None else self.similarity


@dataclass
class Retrieval:
    evidences: list[Evidence]
    trace: list[dict] = field(default_factory=list)


class ReviewRetriever:
    def __init__(self, vector_store, settings: Settings, lexical=None, reranker=None):
        self.vector_store = vector_store
        self.settings = settings
        self.lexical = lexical
        self.reranker = reranker

    def retrieve(
        self, question: str, queries: list[str], filters: ReviewFilters, top_k: int, on_progress=None
    ) -> Retrieval:
        pools, trace = self.rank(question, queries, filters, on_progress)
        evidences = self._select(pools, top_k)
        for info in trace:
            info["selected"] = sum(evidence.matched_query == info["query"] for evidence in evidences)
        return Retrieval(evidences, trace)

    def rank(
        self, question: str, queries: list[str], filters: ReviewFilters, on_progress=None
    ) -> tuple[list[list[Candidate]], list[dict]]:
        pools, trace = [], []
        for query in queries:
            pool, info = self._candidates(query, filters)
            pools.append(pool)
            trace.append(info)
        if on_progress:
            on_progress("candidates", {"candidates": sum(len(pool) for pool in pools), "rerank": self.reranker is not None})
        if self.reranker:
            pools = [pool[:self.settings.rerank_k] for pool in pools]
            grades = self.reranker.grade(question, describe_filters(filters), queries, [[c.text for c in pool] for pool in pools])
            for pool, pool_grades, info in zip(pools, grades, trace):
                for candidate, grade in zip(pool, pool_grades):
                    candidate.relevance = grade
                    candidate.rank_score = self.reranker.score(grade, candidate.similarity)
                info["best_relevance"] = max(pool_grades, default=None)
            # sorted é estável: empates mantêm a ordem da fusão.
            pools = [
                sorted((c for c in pool if c.relevance >= self.reranker.min_score), key=lambda c: -c.relevance)
                for pool in pools
            ]
            for pool, info in zip(pools, trace):
                info["relevant"] = len(pool)
        return pools, trace

    def _candidates(self, query: str, filters: ReviewFilters) -> tuple[list[Candidate], dict]:
        settings = self.settings
        query_vector = normalize(np.array(self.vector_store.embeddings.embed_query(query)))
        dense_ids = self.vector_store.search(query_vector.tolist(), settings.fetch_k, filters)
        lexical_ids = self.lexical.search(query, filters, settings.lexical_k) if self.lexical else []
        fused = reciprocal_rank_fusion([dense_ids, lexical_ids], settings.rrf_k) if lexical_ids else dense_ids

        found = self.vector_store.fetch(fused)
        dense_rank = {doc_id: position for position, doc_id in enumerate(dense_ids, 1)}
        lexical_rank = {doc_id: position for position, doc_id in enumerate(lexical_ids, 1)}
        pool = []
        for doc_id in fused:
            if doc_id not in found:
                continue
            text, metadata, vector = found[doc_id]
            vector = normalize(np.array(vector))
            similarity = float(vector @ query_vector)
            if similarity >= settings.min_similarity:
                pool.append(Candidate(
                    doc_id, text, metadata, vector, similarity, query,
                    dense_rank.get(doc_id), lexical_rank.get(doc_id),
                ))
        info = {
            "query": query, "dense": len(dense_ids), "lexical": len(lexical_ids), "fused": len(fused),
            "above_similarity": len(pool), "best_similarity": round(max((c.similarity for c in pool), default=0), 3),
        }
        return pool, info

    def _select(self, pools: list[list[Candidate]], top_k: int) -> list[Evidence]:
        active = [pool for pool in pools if pool]
        if not active:
            return []
        # 20 vagas para 6 frases viram 4, 4, 3, 3, 3 e 3: nenhuma frase fica sem vaga.
        base, extra = divmod(top_k, len(active))
        members: dict[str, set[str]] = {}
        picked: list[tuple[str, Candidate]] = []
        for position, pool in enumerate(active):
            quota = base + (position < extra)
            if quota == 0:
                continue
            # Textos idênticos viram um candidato com a lista de review_ids agrupados.
            unique: dict[str, Candidate] = {}
            copies: dict[str, set[str]] = {}
            for candidate in pool:
                key = text_key(candidate.text)
                unique.setdefault(key, candidate)
                copies.setdefault(key, set()).add(candidate.review_id)
            for key in [key for key in unique if key in members]:
                members[key] |= copies[key]
                del unique[key]
            keys = list(unique)
            if not keys:
                continue
            chosen = maximal_marginal_relevance(
                np.array([unique[key].score for key in keys]),
                np.array([unique[key].vector for key in keys]),
                quota, self.settings.mmr_lambda,
            )
            for index in chosen:
                members[keys[index]] = copies[keys[index]]
                picked.append((keys[index], unique[keys[index]]))
        return [
            Evidence(
                id=f"R{position}", text=candidate.text, similarity=round(candidate.similarity, 3),
                metadata=candidate.metadata, occurrences=len(members[key]), review_id=candidate.review_id,
                matched_query=candidate.query, dense_rank=candidate.dense_rank,
                lexical_rank=candidate.lexical_rank, relevance=candidate.relevance,
            )
            for position, (key, candidate) in enumerate(picked, 1)
        ]
