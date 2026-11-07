import logging
import time
from collections.abc import Callable
from dataclasses import replace

import pandas as pd
from langchain_core.callbacks import get_usage_metadata_callback

from voc_rag.config import Settings
from voc_rag.generator import AnswerGenerator
from voc_rag.indexing import check_index, create_vector_store
from voc_rag.lexical import LexicalIndex
from voc_rag.llm import create_chat_model
from voc_rag.labels import describe_conditions
from voc_rag.prompts import (
    EMPTY_FILTER_MESSAGE, ERROR_MESSAGE, FILTER_FIELD_LABELS, GENERATION_UNAVAILABLE_MESSAGE, INSUFFICIENT_MESSAGE,
    OUT_OF_SCOPE_MESSAGE, OVERRIDE_NOTICE, RULES_NOTICE,
)
from voc_rag.query_analyzer import QueryAnalyzer
from voc_rag.reranker import create_reranker
from voc_rag.retriever import ReviewRetriever
from voc_rag.schemas import PipelineResult, QueryAnalysis, ReviewFilters, Status
from voc_rag.stats import ReviewStats

logger = logging.getLogger(__name__)

# Recebe o nome da etapa concluída ("analyzed", "candidates" ou "retrieved") e os dados dela.
ProgressCallback = Callable[[str, dict], None]


def refusal_gate(query_traces: list[dict]) -> str:
    if not any(info["above_similarity"] for info in query_traces):
        return "similarity"
    if any("relevant" in info for info in query_traces):
        return "rerank"
    return "min_evidences"


class VoCPipeline:
    def __init__(
        self,
        analyzer: QueryAnalyzer,
        retriever: ReviewRetriever,
        generator: AnswerGenerator,
        stats: ReviewStats,
        settings: Settings,
    ):
        self.analyzer = analyzer
        self.retriever = retriever
        self.generator = generator
        self.stats = stats
        self.settings = settings

    def ask(
        self,
        question: str,
        manual_filters: ReviewFilters | None = None,
        use_filters: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        started = time.perf_counter()
        with get_usage_metadata_callback() as usage:
            result = self._ask(question, manual_filters, use_filters, on_progress or (lambda stage, data: None))
        result.trace["tokens"] = {model: dict(tokens) for model, tokens in usage.usage_metadata.items()}
        result.trace.setdefault("timings_s", {})["total"] = round(time.perf_counter() - started, 2)
        return result

    def _ask(
        self, question: str, manual_filters: ReviewFilters | None, use_filters: bool, on_progress: ProgressCallback
    ) -> PipelineResult:
        timings: dict[str, float] = {}
        trace: dict = {"timings_s": timings}
        step = time.perf_counter()
        try:
            analysis = self.analyzer.analyze(question, manual_filters if use_filters else None)
        except Exception:
            logger.exception("Falha na análise da pergunta")
            return PipelineResult(question, Status.ERROR, ERROR_MESSAGE, trace=trace | {"stopped_at": "error"})
        timings["analysis"] = round(time.perf_counter() - step, 2)
        trace["analysis_source"] = analysis.source
        if not analysis.in_scope:
            trace["stopped_at"] = "scope"
            return PipelineResult(question, Status.OUT_OF_SCOPE, OUT_OF_SCOPE_MESSAGE, analysis=analysis, trace=trace)

        filters, notices = self._filters(analysis, manual_filters, use_filters)
        if analysis.source == "rules":
            notices.append(RULES_NOTICE)
        overview_question = self.settings.use_multi_query and analysis.question_type == "overview"
        queries = analysis.search_queries if self.settings.use_multi_query else analysis.search_queries[:1]
        top_k = self.settings.overview_top_k if overview_question else self.settings.top_k
        base = PipelineResult(
            question, Status.INSUFFICIENT, INSUFFICIENT_MESSAGE,
            analysis=analysis, filters=filters, notices=notices, trace=trace,
        )
        on_progress("analyzed", {"question_type": analysis.question_type, "queries": queries, "filters": filters})
        if self.stats.count(filters) == 0:
            # Recorte sem nenhuma avaliação, como um ano fora da base: não há o que buscar.
            months = self.stats.months
            trace["stopped_at"] = "empty_filter"
            base.summary = EMPTY_FILTER_MESSAGE.format(
                conditions=describe_conditions(filters), first_month=months[0], last_month=months[-1]
            )
            base.overview = self.stats.describe(filters)
            return base

        step = time.perf_counter()
        try:
            retrieval = self.retriever.retrieve(question, queries, filters, top_k, on_progress=on_progress)
        except Exception:
            logger.exception("Falha na recuperação das avaliações")
            trace["stopped_at"] = "error"
            return replace(base, status=Status.ERROR, summary=ERROR_MESSAGE)
        timings["retrieval"] = round(time.perf_counter() - step, 2)
        trace["queries"] = retrieval.trace
        base.evidences = retrieval.evidences
        base.overview = self.stats.describe(filters)
        enough = len(retrieval.evidences) >= self.settings.min_evidences
        on_progress("retrieved", {"evidences": len(retrieval.evidences), "enough": enough})
        if not enough:
            trace["stopped_at"] = refusal_gate(retrieval.trace)
            return base

        if not self.generator.available:
            trace["stopped_at"] = "no_llm"
            return replace(base, status=Status.ERROR, summary=GENERATION_UNAVAILABLE_MESSAGE)
        step = time.perf_counter()
        try:
            answer = self.generator.generate(question, retrieval.evidences, base.overview)
        except Exception:
            logger.exception("Falha na geração da resposta")
            trace["stopped_at"] = "error"
            return replace(base, status=Status.ERROR, summary=ERROR_MESSAGE)
        timings["generation"] = round(time.perf_counter() - step, 2)
        trace["dropped_insights"] = answer.dropped_insights
        if not answer.sufficient_evidence or not answer.insights:
            trace["stopped_at"] = "generator"
            base.limitations = answer.limitations
            return base

        trace["stopped_at"] = None
        return replace(
            base, status=Status.ANSWERED, summary=answer.summary,
            insights=answer.insights, limitations=answer.limitations,
        )

    @staticmethod
    def _filters(
        analysis: QueryAnalysis, manual_filters: ReviewFilters | None, use_filters: bool
    ) -> tuple[ReviewFilters, list[str]]:
        if not use_filters:
            return ReviewFilters.empty(), []
        if manual_filters is None:
            return analysis.filters, []
        overridden = analysis.filters.overridden_by(manual_filters)
        notices = [OVERRIDE_NOTICE.format(fields=", ".join(FILTER_FIELD_LABELS[name] for name in overridden))] if overridden else []
        return analysis.filters.merged(manual_filters), notices


def build_pipeline(settings: Settings | None = None) -> VoCPipeline:
    settings = settings or Settings()
    try:
        llm = create_chat_model(settings.llm_provider, settings.chat_model, settings.temperature)
    except RuntimeError as error:
        # Sem chave de API: a análise cai nas regras e a busca continua funcionando.
        logger.warning("%s A análise usará regras e a síntese ficará indisponível.", error)
        llm = None
    stats = ReviewStats(pd.read_parquet(settings.analytics_path))
    store = create_vector_store(settings)
    check_index(store, settings)
    lexical = LexicalIndex(pd.read_parquet(settings.documents_path)) if settings.use_bm25 else None
    reranker = create_reranker(settings) if settings.use_rerank else None
    return VoCPipeline(
        analyzer=QueryAnalyzer(llm, stats.categories),
        retriever=ReviewRetriever(store, settings, lexical, reranker),
        generator=AnswerGenerator(llm),
        stats=stats,
        settings=settings,
    )
