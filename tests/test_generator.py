import unittest

from voc_rag.generator import AnswerGenerator, clean_citations, format_context, parse_citations
from voc_rag.schemas import Evidence, GeneratedAnswer, Insight


class StubChain:
    def __init__(self, output):
        self.output = output
        self.inputs = None

    def invoke(self, inputs):
        self.inputs = inputs
        return self.output


def evidence(evidence_id: str, **values) -> Evidence:
    return Evidence(evidence_id, f"texto {evidence_id}", 0.8, {"score": 1, "delivery_status": "atrasado"}, **values)


class CitationTest(unittest.TestCase):
    def test_parse_variants(self):
        self.assertEqual(parse_citations("R3"), ["R3"])
        self.assertEqual(parse_citations("[r3]"), ["R3"])
        self.assertEqual(parse_citations("R 3"), ["R3"])
        self.assertEqual(parse_citations("R1, R4"), ["R1", "R4"])

    def test_parse_ranges(self):
        self.assertEqual(parse_citations("R1-R3"), ["R1", "R2", "R3"])
        self.assertEqual(parse_citations("R2 a R4"), ["R2", "R3", "R4"])
        self.assertEqual(parse_citations("R5 até R6"), ["R5", "R6"])

    def test_huge_range_is_ignored(self):
        self.assertEqual(parse_citations("R1-R999999"), [])

    def test_clean_removes_unknown_and_duplicates(self):
        self.assertEqual(clean_citations(["R2", "[R2]", "R9", "R1-R2"], {"R1", "R2"}), ["R2", "R1"])


class AnswerGeneratorTest(unittest.TestCase):
    def test_drops_insights_without_valid_citation(self):
        answer = GeneratedAnswer(
            sufficient_evidence=True, summary="resumo", limitations="",
            insights=[Insight(text="válido", evidence_ids=["[R1]"]), Insight(text="inventado", evidence_ids=["R7"])],
        )
        generator = AnswerGenerator.__new__(AnswerGenerator)
        generator.chain = StubChain(answer)
        result = generator.generate("pergunta", [evidence("R1"), evidence("R2")], "panorama")
        self.assertEqual([(insight.text, insight.evidence_ids) for insight in result.insights], [("válido", ["R1"])])
        self.assertEqual(result.dropped_insights, 1)
        self.assertIn("[R2]", generator.chain.inputs["context"])

    def test_context_separates_metadata_from_customer_text(self):
        context = format_context([evidence("R1", occurrences=3, matched_query="não chegou")])
        self.assertIn("Metadados do pedido (dados da base, não fala do cliente): nota 1", context)
        self.assertIn("entrega atrasada", context)
        self.assertIn("texto igual em 3 avaliações", context)
        self.assertIn('Encontrada pela busca: "não chegou"', context)
        self.assertIn("Texto do cliente (título e comentário):\ntexto R1", context)


if __name__ == "__main__":
    unittest.main()
