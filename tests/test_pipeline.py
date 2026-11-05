import unittest
from dataclasses import replace

import pandas as pd

from tests.fakes import TEST_SETTINGS
from voc_rag.pipeline import VoCPipeline
from voc_rag.prompts import ERROR_MESSAGE, INSUFFICIENT_MESSAGE, OUT_OF_SCOPE_MESSAGE
from voc_rag.query_analyzer import QueryAnalyzer
from voc_rag.retriever import Retrieval
from voc_rag.schemas import Evidence, GeneratedAnswer, Insight, QueryAnalysis, ReviewFilters, Status
from voc_rag.stats import ReviewStats

ANALYTICS = pd.DataFrame({
    "score": [1, 2, 5], "has_comment": [True, True, False],
    "delivery_status": ["atrasado", "no_prazo", "no_prazo"], "category": ["bebes"] * 3,
    "purchase_month": ["2017-11"] * 3, "purchase_month_num": [201711] * 3, "state": ["SP", "RJ", "SP"],
})


def analysis(in_scope=True, question_type="specific", queries=("chegou atrasado",), **filter_values) -> QueryAnalysis:
    return QueryAnalysis(
        in_scope=in_scope, question_type=question_type, search_queries=list(queries),
        filters=ReviewFilters.empty().model_copy(update=filter_values),
    )


def evidences(count: int) -> list[Evidence]:
    return [Evidence(f"R{n}", f"texto {n}", 0.8, {}) for n in range(1, count + 1)]


class FakeAnalyzer:
    def __init__(self, result):
        self.result = result
        self.manual = None

    def analyze(self, question, manual_filters=None):
        self.manual = manual_filters
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRetriever:
    def __init__(self, found: list[Evidence], trace=None):
        self.found = found
        self.trace = trace or [{"query": "q", "above_similarity": len(found)}]
        self.calls = []

    def retrieve(self, question, queries, filters, top_k, on_progress=None):
        self.calls.append((queries, filters, top_k))
        if on_progress:
            on_progress("candidates", {"candidates": 10, "rerank": False})
        return Retrieval(self.found, self.trace)


class FakeGenerator:
    def __init__(self, result):
        self.result = result

    def generate(self, question, found, overview):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


ANSWER = GeneratedAnswer(
    sufficient_evidence=True, summary="Clientes relatam atrasos.", limitations="amostra",
    insights=[Insight(text="Atrasos", evidence_ids=["R1"])],
)


def pipeline(analyzer_result, retriever=None, generator_result=ANSWER, **settings) -> VoCPipeline:
    return VoCPipeline(
        FakeAnalyzer(analyzer_result), retriever or FakeRetriever(evidences(3)),
        FakeGenerator(generator_result), ReviewStats(ANALYTICS), replace(TEST_SETTINGS, **settings),
    )


class PipelineTest(unittest.TestCase):
    def test_answered(self):
        result = pipeline(analysis()).ask("atrasos?")
        self.assertEqual(result.status, Status.ANSWERED)
        self.assertEqual(result.summary, "Clientes relatam atrasos.")
        self.assertIn("Avaliações no recorte: 3", result.overview)
        self.assertIsNone(result.trace["stopped_at"])
        self.assertIn("total", result.trace["timings_s"])

    def test_progress_reports_each_stage(self):
        events = []
        pipeline(analysis()).ask("atrasos?", on_progress=lambda stage, data: events.append((stage, data)))
        self.assertEqual([stage for stage, _ in events], ["analyzed", "candidates", "retrieved"])
        self.assertEqual(events[0][1]["queries"], ["chegou atrasado"])
        self.assertEqual(events[2][1], {"evidences": 3, "enough": True})

    def test_out_of_scope_stops_before_search(self):
        retriever = FakeRetriever(evidences(3))
        result = pipeline(analysis(in_scope=False), retriever).ask("previsão do tempo?")
        self.assertEqual((result.status, result.summary), (Status.OUT_OF_SCOPE, OUT_OF_SCOPE_MESSAGE))
        self.assertEqual(retriever.calls, [])

    def test_few_evidences_skip_generation(self):
        trace = [{"query": "q", "above_similarity": 4, "relevant": 2}]
        result = pipeline(analysis(), FakeRetriever(evidences(2), trace), RuntimeError("não chamar")).ask("drone?")
        self.assertEqual((result.status, result.summary), (Status.INSUFFICIENT, INSUFFICIENT_MESSAGE))
        self.assertEqual(result.trace["stopped_at"], "rerank")

    def test_empty_filter_stops_before_search_and_explains_the_period(self):
        retriever = FakeRetriever(evidences(3))
        result = pipeline(analysis(start_month="2025-01", end_month="2025-12", delivery_status="nao_entregue"), retriever).ask(
            "Quem comprou e não chegou em 2025?"
        )
        self.assertEqual(result.status, Status.INSUFFICIENT)
        self.assertEqual(result.trace["stopped_at"], "empty_filter")
        self.assertEqual(retriever.calls, [])
        self.assertIn("Entrega == Não entregue; Mês da compra >= 2025-01; Mês da compra <= 2025-12", result.summary)
        self.assertIn("A base cobre compras de 2017-11 a 2017-11", result.summary)

    def test_similarity_gate_is_reported(self):
        trace = [{"query": "q", "above_similarity": 0}]
        result = pipeline(analysis(), FakeRetriever([], trace)).ask("Lua?")
        self.assertEqual(result.trace["stopped_at"], "similarity")

    def test_generator_can_refuse(self):
        refusal = ANSWER.model_copy(update={"sufficient_evidence": False, "limitations": "sem relatos"})
        result = pipeline(analysis(), generator_result=refusal).ask("cashback?")
        self.assertEqual(result.status, Status.INSUFFICIENT)
        self.assertEqual(result.limitations, "sem relatos")
        self.assertEqual(result.trace["stopped_at"], "generator")

    def test_errors_keep_retrieved_evidences(self):
        with self.assertLogs("voc_rag.pipeline", "ERROR"):
            result = pipeline(analysis(), generator_result=TimeoutError()).ask("atrasos?")
        self.assertEqual((result.status, result.summary), (Status.ERROR, ERROR_MESSAGE))
        self.assertEqual(len(result.evidences), 3)

    def test_analyzer_error(self):
        with self.assertLogs("voc_rag.pipeline", "ERROR"):
            result = pipeline(RuntimeError("sem chave")).ask("atrasos?")
        self.assertEqual(result.status, Status.ERROR)
        self.assertEqual(result.trace["stopped_at"], "error")

    def test_overview_questions_use_every_query_and_more_slots(self):
        retriever = FakeRetriever(evidences(3))
        pipeline(analysis(question_type="overview", queries=["a", "b", "c"]), retriever).ask("principais problemas?")
        self.assertEqual((retriever.calls[0][0], retriever.calls[0][2]), (["a", "b", "c"], 6))

    def test_single_query_when_multi_query_is_off(self):
        retriever = FakeRetriever(evidences(3))
        pipeline(analysis(question_type="overview", queries=["a", "b"]), retriever, use_multi_query=False).ask("p?")
        self.assertEqual((retriever.calls[0][0], retriever.calls[0][2]), (["a"], 4))

    def test_manual_filters_take_priority_and_warn(self):
        retriever = FakeRetriever(evidences(3))
        manual = ReviewFilters.empty().model_copy(update={"min_score": 4})
        selected = pipeline(analysis(min_score=1, category="bebes"), retriever)
        result = selected.ask("problemas?", manual)
        applied = retriever.calls[0][1]
        self.assertEqual((applied.min_score, applied.category), (4, "bebes"))
        self.assertEqual(len(result.notices), 1)
        self.assertIn("nota mínima", result.notices[0])
        self.assertIs(selected.analyzer.manual, manual)

    def test_filters_can_be_disabled(self):
        retriever = FakeRetriever(evidences(3))
        pipeline(analysis(max_score=2), retriever).ask("problemas?", use_filters=False)
        self.assertEqual(retriever.calls[0][1].conditions(), [])


class StubChain:
    def __init__(self, output):
        self.output = output

    def invoke(self, inputs):
        self.inputs = inputs
        return self.output


class QueryAnalyzerTest(unittest.TestCase):
    def analyzer(self, output) -> QueryAnalyzer:
        analyzer = QueryAnalyzer.__new__(QueryAnalyzer)
        analyzer.categories = {"bebes"}
        analyzer.chain = StubChain(output)
        return analyzer

    def test_unknown_category_is_dropped(self):
        result = self.analyzer(analysis(category="bed_bath")).analyze("p")
        self.assertIsNone(result.filters.category)

    def test_queries_are_cleaned_and_limited(self):
        result = self.analyzer(analysis(queries=[" a ", "a", "", "b", "c", "d", "e", "f", "g"])).analyze("p")
        self.assertEqual(result.search_queries, ["a", "b", "c", "d", "e", "f"])

    def test_empty_queries_fall_back_to_question(self):
        self.assertEqual(self.analyzer(analysis(queries=[])).analyze("pergunta").search_queries, ["pergunta"])

    def test_manual_filters_are_sent_as_context(self):
        analyzer = self.analyzer(analysis())
        analyzer.analyze("p", ReviewFilters.empty().model_copy(update={"states": ["SP"]}))
        self.assertEqual(analyzer.chain.inputs["manual_filters"], "state in ['SP']")


if __name__ == "__main__":
    unittest.main()
