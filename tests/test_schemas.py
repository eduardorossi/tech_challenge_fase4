import unittest

from voc_rag.schemas import Evidence, Insight, PipelineResult, ReviewFilters, Status


def filters(**values) -> ReviewFilters:
    return ReviewFilters.empty().model_copy(update=values)


class ReviewFiltersTest(unittest.TestCase):
    def test_empty_has_no_conditions(self):
        self.assertEqual(ReviewFilters.empty().conditions(), [])

    def test_conditions_cover_every_field(self):
        result = filters(
            min_score=4, max_score=5, delivery_status="atrasado", category="cama_mesa_banho",
            start_month="2017-11", end_month="2018-01", states=["sp", " rj "],
        ).conditions()
        self.assertEqual(result, [
            ("score", ">=", 4), ("score", "<=", 5), ("delivery_status", "==", "atrasado"),
            ("category", "==", "cama_mesa_banho"), ("purchase_month_num", ">=", 201711),
            ("purchase_month_num", "<=", 201801), ("state", "in", ["RJ", "SP"]),
        ])

    def test_invalid_values_are_ignored(self):
        result = filters(min_score=0, max_score=9, start_month="2017-13", end_month="nov", states=["XX", "Lua"])
        self.assertEqual(result.conditions(), [])

    def test_merged_gives_priority_to_override(self):
        merged = filters(max_score=2, category="bebes").merged(filters(max_score=1, states=["SP"]))
        self.assertEqual((merged.max_score, merged.category, merged.states), (1, "bebes", ["SP"]))

    def test_overridden_by_lists_only_conflicts(self):
        detected = filters(max_score=2, category="bebes")
        self.assertEqual(detected.overridden_by(filters(max_score=5, category="bebes", states=["SP"])), ["max_score"])


class PipelineResultTest(unittest.TestCase):
    def test_markdown_marks_cited_evidences(self):
        result = PipelineResult(
            "pergunta", Status.ANSWERED, "resumo",
            insights=[Insight(text="achado", evidence_ids=["R1"])],
            evidences=[
                Evidence("R1", "texto | com barra", 0.8, {"score": 1, "state": "SP"}, relevance=3),
                Evidence("R2", "outro", 0.7, {"score": 2}),
            ],
        )
        markdown = result.to_markdown()
        self.assertIn("| R1 | sim | 0.80 | 3 | 1 | SP |", markdown)
        self.assertIn("| R2 |  | 0.70 |  | 2 | não informado |", markdown)
        self.assertIn("texto / com barra", markdown)


if __name__ == "__main__":
    unittest.main()
