import unittest
from dataclasses import replace

import numpy as np

from tests.fakes import TEST_SETTINGS, FakeLexical, FakeReranker, FakeVectorStore, record
from voc_rag.retriever import (
    ReviewRetriever, maximal_marginal_relevance, reciprocal_rank_fusion, to_chroma_filter,
)
from voc_rag.schemas import ReviewFilters

LATE = [1.0, 0.0, 0.0]
BROKEN = [0.0, 1.0, 0.0]

RECORDS = [
    record("a", "Não recebi o produto", [1.0, 0.1, 0.0], score=1),
    record("b", "não recebi o produto.", [1.0, 0.1, 0.0], score=1),
    record("c", "Chegou com atraso de uma semana", [0.9, 0.2, 0.0], score=2),
    record("d", "Produto veio quebrado", [0.1, 1.0, 0.0], score=1),
    record("e", "Veio com defeito na tampa", [0.2, 0.9, 0.1], score=2),
    record("f", "Ótimo atendimento", [0.0, 0.0, 1.0], score=5),
]


def retriever(lexical=None, reranker=None, **settings) -> ReviewRetriever:
    store = FakeVectorStore(RECORDS, {"atraso": LATE, "quebrado": BROKEN, "atendimento": [0.0, 0.0, 1.0]})
    return ReviewRetriever(store, replace(TEST_SETTINGS, **settings), lexical, reranker)


class FunctionsTest(unittest.TestCase):
    def test_chroma_filter(self):
        empty = ReviewFilters.empty()
        self.assertIsNone(to_chroma_filter(empty))
        self.assertEqual(to_chroma_filter(empty.model_copy(update={"max_score": 2})), {"score": {"$lte": 2}})
        both = empty.model_copy(update={"max_score": 2, "states": ["SP"]})
        self.assertEqual(to_chroma_filter(both), {"$and": [{"score": {"$lte": 2}}, {"state": {"$in": ["SP"]}}]})

    def test_rrf_rewards_documents_in_both_lists(self):
        self.assertEqual(reciprocal_rank_fusion([["a", "b", "c"], ["c", "d"]], k=60)[0], "c")

    def test_mmr_prefers_diverse_second_choice(self):
        vectors = np.array([[1.0, 0.0], [0.99, 0.141], [0.0, 1.0]])
        self.assertEqual(maximal_marginal_relevance(np.array([1.0, 0.95, 0.9]), vectors, 2, 0.5), [0, 2])


class RetrieverTest(unittest.TestCase):
    def test_groups_identical_texts_and_applies_similarity_cut(self):
        result = retriever().retrieve("atrasos?", ["atraso"], ReviewFilters.empty(), top_k=4)
        texts = [evidence.text for evidence in result.evidences]
        self.assertEqual(texts[0], "Não recebi o produto")
        self.assertEqual(result.evidences[0].occurrences, 2)
        self.assertNotIn("Ótimo atendimento", texts)
        self.assertEqual([evidence.id for evidence in result.evidences], [f"R{n}" for n in range(1, len(texts) + 1)])

    def test_each_query_gets_a_share_of_the_slots(self):
        result = retriever().retrieve("problemas?", ["atraso", "quebrado"], ReviewFilters.empty(), top_k=4)
        queries = [evidence.matched_query for evidence in result.evidences]
        self.assertEqual(queries.count("atraso"), 2)
        self.assertEqual(queries.count("quebrado"), 2)
        self.assertEqual([info["selected"] for info in result.trace], [2, 2])

    def test_every_query_gets_a_slot_when_they_do_not_divide_evenly(self):
        result = retriever().retrieve("p?", ["atraso", "quebrado", "atendimento"], ReviewFilters.empty(), top_k=4)
        self.assertEqual([info["selected"] for info in result.trace], [2, 1, 1])

    def test_lexical_results_join_the_pool(self):
        lexical = FakeLexical({"atraso": ["f"]})
        result = retriever(lexical, min_similarity=-1).retrieve("atrasos?", ["atraso"], ReviewFilters.empty(), top_k=6)
        found = {evidence.review_id: evidence for evidence in result.evidences}
        self.assertEqual(found["f"].lexical_rank, 1)
        self.assertEqual(result.trace[0]["lexical"], 1)

    def test_reranker_is_the_relevance_gate(self):
        reranker = FakeReranker({"Chegou com atraso de uma semana": 3, "Não recebi o produto": 1})
        result = retriever(reranker=reranker).retrieve("atrasos?", ["atraso"], ReviewFilters.empty(), top_k=4)
        self.assertEqual([evidence.text for evidence in result.evidences], ["Chegou com atraso de uma semana"])
        self.assertEqual(result.evidences[0].relevance, 3)
        self.assertEqual(result.trace[0]["relevant"], 1)
        self.assertEqual(reranker.calls[0][1], "nenhum")

    def test_progress_reports_candidates_before_rerank(self):
        events = []
        reranker = FakeReranker({})
        retriever(reranker=reranker).retrieve(
            "q", ["atraso"], ReviewFilters.empty(), top_k=4, on_progress=lambda stage, data: events.append((stage, data))
        )
        self.assertEqual(events, [("candidates", {"candidates": 3, "rerank": True})])

    def test_filters_reach_the_vector_store(self):
        selected = retriever()
        selected.retrieve("q", ["atraso"], ReviewFilters.empty().model_copy(update={"max_score": 2}), top_k=4)
        self.assertEqual(selected.vector_store.filters, [{"score": {"$lte": 2}}])


if __name__ == "__main__":
    unittest.main()
