import unittest

import pandas as pd

from voc_rag.lexical import LexicalIndex, tokenize
from voc_rag.schemas import ReviewFilters
from voc_rag.stats import ReviewStats, filter_mask

FRAME = pd.DataFrame({
    "review_id": ["r1", "r2", "r3", "r4"],
    "text": ["Não recebi o produto", "Entrega atrasada demais", "Produto ótimo, entregue antes", "Atrasou a entrega"],
    "score": [1, 2, 5, 1],
    "has_comment": [True, True, True, False],
    "delivery_status": ["nao_entregue", "atrasado", "no_prazo", "atrasado"],
    "category": ["bebes", "bebes", "cama_mesa_banho", "bebes"],
    "purchase_month": ["2017-10", "2017-11", "2017-11", None],
    "purchase_month_num": [201710, 201711, 201711, None],
    "state": ["SP", "RJ", "SP", None],
})


def filters(**values) -> ReviewFilters:
    return ReviewFilters.empty().model_copy(update=values)


class StatsTest(unittest.TestCase):
    def test_mask_handles_missing_values(self):
        mask = filter_mask(FRAME, filters(start_month="2017-11", states=["SP"]))
        self.assertEqual(FRAME.loc[mask, "review_id"].tolist(), ["r3"])

    def test_describe_uses_whole_subset(self):
        overview = ReviewStats(FRAME).describe(filters(max_score=2))
        self.assertIn("Avaliações no recorte: 3 (67% com comentário)", overview)
        self.assertIn("nota 1: 67%, nota 2: 33%", overview)
        self.assertIn("Estados com mais avaliações: SP: 50%, RJ: 50%", overview)

    def test_count_and_months(self):
        stats = ReviewStats(FRAME)
        self.assertEqual(stats.count(filters(max_score=2)), 3)
        self.assertEqual(stats.count(filters(start_month="2025-01")), 0)
        self.assertEqual(stats.months, ["2017-10", "2017-11"])

    def test_describe_empty_subset(self):
        self.assertEqual(ReviewStats(FRAME).describe(filters(category="inexistente")), "Nenhuma avaliação corresponde aos filtros.")

    def test_state_distribution_hidden_when_filtering_states(self):
        self.assertNotIn("Estados", ReviewStats(FRAME).describe(filters(states=["SP"])))


class LexicalTest(unittest.TestCase):
    def test_tokenize_strips_accents_and_keeps_negation(self):
        self.assertEqual(tokenize("Não é ENTREGUE já"), ["nao", "entre"])

    def test_search_respects_filters(self):
        index = LexicalIndex(FRAME)
        self.assertEqual(sorted(index.search("entrega atrasada", filters(), 2)), ["r2", "r4"])
        self.assertEqual(index.search("entrega atrasada", filters(states=["RJ"]), 5), ["r2"])
        self.assertEqual(index.search("de o", filters(), 5), [])


if __name__ == "__main__":
    unittest.main()
