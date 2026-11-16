import asyncio
import os
import unittest
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from tests.fakes import TEST_SETTINGS, StubChatModel
from voc_rag.config import Settings
from voc_rag.llm import (
    ChatModels, configured_api_key, create_chat_model, create_chat_model_pair, require_api_key,
    structured_output_with_fallback, track_fallbacks,
)
from voc_rag.query_analyzer import QueryAnalyzer
from voc_rag.reranker import LLMReranker, RelevanceGrades, create_reranker
from voc_rag.schemas import QueryAnalysis, ReviewFilters

KEYS = ("OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")


@contextmanager
def api_keys(**values):
    # Isola o teste das chaves reais carregadas do .env.
    with patch.dict(os.environ, {}, clear=False):
        for name in KEYS:
            os.environ.pop(name, None)
        os.environ.update({name: value for name, value in values.items()})
        yield


def fake_init_chat_model(model, model_provider, **options):
    return StubChatModel(model=f"{model_provider}:{model}")


def analysis() -> QueryAnalysis:
    return QueryAnalysis(in_scope=True, question_type="specific", search_queries=["atraso"], filters=ReviewFilters.empty())


class ApiKeyTest(unittest.TestCase):
    def test_placeholder_is_not_a_key(self):
        with api_keys(OPENAI_API_KEY="sua-chave-aqui"), self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            require_api_key("openai")

    def test_missing_key(self):
        with api_keys(), self.assertRaises(RuntimeError):
            require_api_key("google")

    def test_valid_gemini_key_is_used_when_google_key_is_a_placeholder(self):
        with api_keys(GOOGLE_API_KEY="sua-chave-aqui", GEMINI_API_KEY="chave-real"):
            self.assertEqual(configured_api_key("google"), "chave-real")

    def test_unknown_provider(self):
        with self.assertRaises(ValueError):
            require_api_key("gemini")

    def test_validated_key_is_passed_explicitly_and_temperature_only_when_set(self):
        with api_keys(GOOGLE_API_KEY=" sua-chave-aqui ", GEMINI_API_KEY="chave-real"), \
                patch("voc_rag.llm.init_chat_model") as init:
            create_chat_model("google", "gemini-x")
            create_chat_model("google", "gemini-x", temperature=0.0)
        self.assertEqual(init.call_args_list[0].kwargs, {"model_provider": "google_genai", "api_key": "chave-real"})
        self.assertEqual(init.call_args_list[1].kwargs["temperature"], 0.0)


class ChatModelPairTest(unittest.TestCase):
    def pair(self, provider="openai", model="gpt-x", fallback_model="gemini-x", fallback_provider="google") -> ChatModels:
        with patch("voc_rag.llm.init_chat_model", side_effect=fake_init_chat_model):
            return create_chat_model_pair(provider, model, None, fallback_model, fallback_provider)

    def test_both_keys(self):
        with api_keys(OPENAI_API_KEY="sk-1", GOOGLE_API_KEY="g-1"):
            models = self.pair()
        self.assertEqual((models.llm.model_name, models.fallback_llm.model_name), ("openai:gpt-x", "google_genai:gemini-x"))
        self.assertIsNone(models.replaced_primary)

    def test_only_primary_key(self):
        with api_keys(OPENAI_API_KEY="sk-1"):
            models = self.pair()
        self.assertEqual((models.llm.model_name, models.fallback_llm), ("openai:gpt-x", None))

    def test_reserve_takes_the_place_of_a_primary_without_key(self):
        with api_keys(OPENAI_API_KEY="sua-chave-aqui", GOOGLE_API_KEY="g-1"), self.assertLogs("voc_rag.llm", "WARNING"):
            models = self.pair()
        self.assertEqual((models.llm.model_name, models.fallback_llm), ("google_genai:gemini-x", None))
        self.assertEqual(models.replaced_primary, "google:gemini-x")

    def test_no_keys(self):
        with api_keys(), self.assertLogs("voc_rag.llm", "WARNING"):
            self.assertEqual(self.pair(), ChatModels(None, None))

    def test_google_primary_can_fall_back_to_openai(self):
        with api_keys(OPENAI_API_KEY="sk-1", GOOGLE_API_KEY="g-1"):
            models = self.pair("google", "gemini-x", "gpt-x", "openai")
        self.assertEqual(models.fallback_llm.model_name, "openai:gpt-x")

    def test_reserve_identical_to_primary_or_disabled_is_skipped(self):
        with api_keys(OPENAI_API_KEY="sk-1", GOOGLE_API_KEY="g-1"):
            self.assertIsNone(self.pair("google", "gemini-x", "gemini-x", "google").fallback_llm)
            self.assertIsNone(self.pair(fallback_provider="").fallback_llm)


class StructuredOutputFallbackTest(unittest.TestCase):
    def test_primary_answers_without_touching_the_reserve(self):
        reserve = StubChatModel("reserva")
        chain = structured_output_with_fallback(StubChatModel("principal"), QueryAnalysis, reserve)
        with track_fallbacks() as used:
            self.assertEqual(chain.invoke("x"), "principal")
        self.assertEqual((reserve.calls, used), (0, []))

    def test_reserve_answers_when_primary_fails_and_the_reason_is_logged(self):
        primary = StubChatModel(error=PermissionError("Incorrect API key provided"), model="gpt-x")
        chain = structured_output_with_fallback(primary, QueryAnalysis, StubChatModel("reserva", model="models/gemini-x"))
        with track_fallbacks() as used, self.assertLogs("voc_rag.llm", "WARNING") as logs:
            self.assertEqual(chain.invoke("x"), "reserva")
        self.assertEqual(used, ["gemini-x"])
        self.assertIn("Incorrect API key provided", logs.output[0])

    def test_async_path_also_falls_back(self):
        chain = structured_output_with_fallback(StubChatModel(error=TimeoutError()), QueryAnalysis, StubChatModel("reserva"))
        with self.assertLogs("voc_rag.llm", "WARNING"):
            self.assertEqual(asyncio.run(chain.ainvoke("x")), "reserva")

    def test_error_propagates_when_both_fail(self):
        chain = structured_output_with_fallback(
            StubChatModel(error=TimeoutError()), QueryAnalysis, StubChatModel(error=ConnectionError("fora do ar"))
        )
        with self.assertLogs("voc_rag.llm", "WARNING"), self.assertRaises(ConnectionError):
            chain.invoke("x")

    def test_fallback_is_not_recorded_outside_a_tracked_block(self):
        chain = structured_output_with_fallback(StubChatModel(error=TimeoutError()), QueryAnalysis, StubChatModel("reserva"))
        with self.assertLogs("voc_rag.llm", "WARNING"):
            self.assertEqual(chain.invoke("x"), "reserva")


class QueryAnalyzerFallbackTest(unittest.TestCase):
    def test_accepts_the_reserve_model_and_uses_it(self):
        analyzer = QueryAnalyzer(StubChatModel(error=TimeoutError("sem cota")), ["bebes"], StubChatModel(analysis()))
        with self.assertLogs("voc_rag.llm", "WARNING"):
            result = analyzer.analyze("O que os clientes relatam sobre atrasos?")
        self.assertEqual((result.source, result.search_queries), ("llm", ["atraso"]))

    def test_rules_only_when_both_models_fail(self):
        analyzer = QueryAnalyzer(StubChatModel(error=TimeoutError()), ["bebes"], StubChatModel(error=TimeoutError()))
        with self.assertLogs("voc_rag", "WARNING") as logs:
            result = analyzer.analyze("Quais os principais problemas dos clientes insatisfeitos?")
        self.assertEqual(result.source, "rules")
        self.assertTrue(any("usando regras" in line for line in logs.output))


class LLMRerankerTest(unittest.TestCase):
    def test_batch_falls_back_per_query(self):
        grades = RelevanceGrades(grades=[{"id": "C1", "relevance": 3}])
        reranker = LLMReranker(StubChatModel(error=TimeoutError()), fallback_llm=StubChatModel(grades))
        with track_fallbacks() as used, self.assertLogs("voc_rag.llm", "WARNING"):
            self.assertEqual(reranker.grade("p", "nenhum", ["q1", "q2"], [["a"], ["b"]]), [[3], [3]])
        self.assertEqual(len(used), 2)

    def test_llm_reranker_without_any_model_explains_the_setting(self):
        settings = replace(TEST_SETTINGS, reranker="llm")
        with patch("voc_rag.reranker.create_chat_model_pair", return_value=ChatModels(None, None)), \
                self.assertRaisesRegex(RuntimeError, "RERANKER=cross_encoder"):
            create_reranker(settings)


class SettingsTest(unittest.TestCase):
    def test_unknown_llm_provider_is_rejected_early(self):
        with self.assertRaisesRegex(ValueError, "LLM_PROVIDER"):
            Settings(llm_provider="gemini")

    def test_fallback_can_be_disabled(self):
        self.assertEqual(Settings(fallback_provider="none").fallback_provider, "")
        with self.assertRaisesRegex(ValueError, "FALLBACK_PROVIDER"):
            Settings(fallback_provider="anthropic")

    def test_judge_model_is_inherited_only_from_the_same_provider(self):
        common = {"llm_provider": "openai", "chat_model": "gpt-x", "judge_provider": "google", "judge_model": ""}
        self.assertEqual(Settings(**common, fallback_provider="google", fallback_chat_model="gemini-x").judge_model, "gemini-x")
        self.assertEqual(Settings(**common, fallback_provider="none").judge_model, "")
        self.assertEqual(Settings(llm_provider="openai", chat_model="gpt-x", judge_provider="", judge_model="").judge_model, "gpt-x")


if __name__ == "__main__":
    unittest.main()
