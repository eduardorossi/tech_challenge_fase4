import json
import re
import statistics
from collections import Counter
from copy import copy
from dataclasses import replace
from datetime import date
from typing import Literal

import pandas as pd
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from voc_rag.config import ROOT, Settings
from voc_rag.generator import AnswerGenerator, format_context
from voc_rag.indexing import check_index, create_vector_store
from voc_rag.lexical import LexicalIndex
from voc_rag.llm import create_chat_model
from voc_rag.pipeline import VoCPipeline
from voc_rag.prompts import JUDGE_HUMAN, JUDGE_SYSTEM
from voc_rag.query_analyzer import QueryAnalyzer
from voc_rag.reranker import create_reranker
from voc_rag.retriever import ReviewRetriever
from voc_rag.schemas import PipelineResult, QueryAnalysis, ReviewFilters, Status
from voc_rag.stats import ReviewStats

EVAL_SET_PATH = ROOT / "examples" / "eval_set.json"
REPORT_PATH = ROOT / "docs" / "avaliacao.md"

# Configurações da ablação, da mais simples à completa.
PIPELINE_CONFIGS = {
    "baseline": {"use_multi_query": False, "use_bm25": False, "use_rerank": False},
    "multi_query": {"use_multi_query": True, "use_bm25": False, "use_rerank": False},
    "hybrid": {"use_multi_query": True, "use_bm25": True, "use_rerank": False},
    "full": {"use_multi_query": True, "use_bm25": True, "use_rerank": True},
}
RETRIEVAL_CONFIGS = {
    "dense": {"use_bm25": False, "use_rerank": False},
    "hybrid": {"use_bm25": True, "use_rerank": False},
    "dense_rerank": {"use_bm25": False, "use_rerank": True},
    "hybrid_rerank": {"use_bm25": True, "use_rerank": True},
}
REFUSALS = {Status.OUT_OF_SCOPE, Status.INSUFFICIENT}
PRECISION_K = 10


class InsightVerdict(BaseModel):
    supported: Literal["sim", "parcial", "nao"]
    metadata_as_customer_speech: bool = Field(description="True se atribui ao cliente algo que só está nos metadados")
    justification: str = Field(description="Justificativa curta")


class Verdicts(BaseModel):
    verdicts: list[InsightVerdict]


def precision_at_k(texts: list[str], pattern: str, k: int = PRECISION_K) -> float:
    top = texts[:k]
    return sum(bool(re.search(pattern, text.lower())) for text in top) / len(top) if top else 0.0


def normalized_conditions(conditions) -> list[tuple]:
    return sorted((column, op, tuple(value) if isinstance(value, list) else value) for column, op, value in conditions)


def is_correct(expected: str, status: Status) -> bool:
    return status == Status.ANSWERED if expected == "answer" else status in REFUSALS


def mean_std(values: list[float]) -> str:
    if not values:
        return "—"
    if len(values) == 1:
        return f"{values[0]:.2f}"
    return f"{statistics.mean(values):.2f} ± {statistics.stdev(values):.2f}"


def total_tokens(usage: dict) -> tuple[int, int]:
    return sum(item.get("input_tokens", 0) for item in usage.values()), sum(item.get("output_tokens", 0) for item in usage.values())


class CachedAnalyzer:
    # Todas as configurações recebem a mesma análise da pergunta, o que isola o efeito da recuperação.
    def __init__(self, analyzer: QueryAnalyzer):
        self.analyzer = analyzer
        self.cache: dict[str, QueryAnalysis] = {}
        self.tokens: dict[str, dict] = {}

    def analyze(self, question: str, manual_filters: ReviewFilters | None = None) -> QueryAnalysis:
        if question not in self.cache:
            with get_usage_metadata_callback() as usage:
                self.cache[question] = self.analyzer.analyze(question, manual_filters)
            self.tokens[question] = dict(usage.usage_metadata)
        return self.cache[question].model_copy(deep=True)


class EvaluationRunner:
    def __init__(self, settings: Settings, use_judge: bool):
        self.settings = settings
        llm = create_chat_model(settings.llm_provider, settings.chat_model, settings.temperature)
        self.stats = ReviewStats(pd.read_parquet(settings.analytics_path))
        self.store = create_vector_store(settings)
        check_index(self.store, settings)
        self.lexical = LexicalIndex(pd.read_parquet(settings.documents_path))
        self.reranker = create_reranker(settings)
        self.analyzer = CachedAnalyzer(QueryAnalyzer(llm, self.stats.categories))
        self.generator = AnswerGenerator(llm)
        self.judge = None
        if use_judge:
            judge_llm = create_chat_model(settings.judge_provider, settings.judge_model, settings.temperature)
            prompt = ChatPromptTemplate.from_messages([("system", JUDGE_SYSTEM), ("human", JUDGE_HUMAN)])
            self.judge = prompt | judge_llm.with_structured_output(Verdicts)

    def retriever(self, settings: Settings, unfiltered: bool = False) -> ReviewRetriever:
        reranker = self.reranker if settings.use_rerank else None
        if reranker is not None and unfiltered:
            reranker = copy(reranker)
            reranker.min_score = float("-inf")
        return ReviewRetriever(self.store, settings, self.lexical if settings.use_bm25 else None, reranker)

    def pipeline(self, config: dict) -> VoCPipeline:
        settings = replace(self.settings, **config)
        return VoCPipeline(self.analyzer, self.retriever(settings), self.generator, self.stats, settings)

    def evaluate_retrieval(self, themes: list[dict]) -> list[dict]:
        # Ranking puro: sem corte de similaridade e sem descartar notas baixas do rerank.
        rows = []
        for theme in themes:
            row = {"question": theme["question"]}
            for name, config in RETRIEVAL_CONFIGS.items():
                settings = replace(self.settings, min_similarity=-1.0, **config)
                pools, _ = self.retriever(settings, unfiltered=True).rank(theme["question"], [theme["question"]], ReviewFilters.empty())
                row[name] = precision_at_k([candidate.text for candidate in pools[0]], theme["pattern"])
            rows.append(row)
            print(f"recuperação: {theme['question']}")
        return rows

    def judge_result(self, result: PipelineResult) -> list[dict]:
        evidences = {evidence.id: evidence for evidence in result.evidences}
        blocks = [
            f"Insight {position}: {insight.text}\nAvaliações citadas:\n"
            + format_context([evidences[evidence_id] for evidence_id in insight.evidence_ids])
            for position, insight in enumerate(result.insights, 1)
        ]
        verdicts = self.judge.invoke({"question": result.question, "insights": "\n\n".join(blocks)}).verdicts
        return [verdict.model_dump() for verdict in verdicts[:len(result.insights)]]

    def evaluate_questions(self, questions: list[dict], configs: list[str], repeat: int) -> list[dict]:
        records = []
        for repetition in range(repeat):
            self.analyzer.cache.clear()
            for item in questions:
                try:
                    self.analyzer.analyze(item["question"])
                except Exception as error:
                    # O pipeline tenta de novo e registra o status de erro.
                    print(f"[aviso] análise falhou ({type(error).__name__}): {item['question']}")
            for config in configs:
                pipeline = self.pipeline(PIPELINE_CONFIGS[config])
                for item in questions:
                    result = pipeline.ask(item["question"])
                    records.append(self._record(item, result, config, repetition))
                    print(f"[{repetition + 1}/{repeat}] {config}: {result.status.value} | {item['question']}")
        return records

    def _record(self, item: dict, result: PipelineResult, config: str, repetition: int) -> dict:
        queries = result.trace.get("queries", [])
        input_tokens, output_tokens = total_tokens(result.trace.get("tokens", {}))
        analysis_input, analysis_output = total_tokens(self.analyzer.tokens.get(item["question"], {}))
        record = {
            "config": config, "repetition": repetition, "split": item["split"], "question": item["question"],
            "expected": item["expected"], "status": result.status.value,
            "correct": is_correct(item["expected"], result.status), "stopped_at": result.trace.get("stopped_at"),
            "evidences": len(result.evidences), "cited": len(result.cited_ids), "insights": len(result.insights),
            "dropped_insights": result.trace.get("dropped_insights", 0),
            "search_queries": result.analysis.search_queries if result.analysis else [],
            "conditions": [list(condition) for condition in result.filters.conditions()] if result.filters else [],
            "filters_ok": None,
            "best_similarity": max((info["best_similarity"] for info in queries), default=None),
            "best_relevance": max((info.get("best_relevance") or 0 for info in queries), default=None),
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "analysis_input_tokens": analysis_input, "analysis_output_tokens": analysis_output,
            "seconds": result.trace.get("timings_s", {}).get("total"),
        }
        if "expected_filters" in item and result.analysis:
            record["filters_ok"] = (
                normalized_conditions(result.analysis.filters.conditions()) == normalized_conditions(item["expected_filters"])
            )
        if self.judge and result.status == Status.ANSWERED:
            record["verdicts"] = self.judge_result(result)
        return record


def summarize(records: list[dict], configs: list[str]) -> dict:
    summary = {}
    repetitions = sorted({record["repetition"] for record in records})
    for config in configs:
        rows = [record for record in records if record["config"] == config]
        item = {}
        for split in ("dev", "test"):
            split_rows = [row for row in rows if row["split"] == split]
            item[f"accuracy_{split}"] = [
                statistics.mean(row["correct"] for row in split_rows if row["repetition"] == repetition)
                for repetition in repetitions if any(row["repetition"] == repetition for row in split_rows)
            ]
        item["false_refusals"] = sum(row["expected"] == "answer" and row["status"] != Status.ANSWERED.value for row in rows)
        item["false_answers"] = sum(row["expected"] == "refuse" and row["status"] == Status.ANSWERED.value for row in rows)
        item["errors"] = sum(row["status"] == Status.ERROR.value for row in rows)
        item["gates"] = dict(Counter(row["stopped_at"] for row in rows if row["stopped_at"]))
        verdicts = [verdict for row in rows for verdict in row.get("verdicts", [])]
        item["verdicts"] = dict(Counter(verdict["supported"] for verdict in verdicts))
        item["misattributions"] = sum(verdict["metadata_as_customer_speech"] for verdict in verdicts)
        item["dropped_insights"] = sum(row["dropped_insights"] for row in rows)
        item["insights"] = sum(row["insights"] for row in rows)
        item["input_tokens"] = statistics.mean(row["input_tokens"] for row in rows)
        item["output_tokens"] = statistics.mean(row["output_tokens"] for row in rows)
        item["seconds"] = statistics.mean(row["seconds"] or 0 for row in rows)
        summary[config] = item
    checked = [record for record in records if record["config"] == configs[0] and record["filters_ok"] is not None]
    summary["filters"] = {"checked": len(checked), "correct": sum(record["filters_ok"] for record in checked)}
    first = [record for record in records if record["config"] == configs[0]]
    summary["analysis_tokens"] = {
        "input": statistics.mean(record["analysis_input_tokens"] for record in first) if first else 0,
        "output": statistics.mean(record["analysis_output_tokens"] for record in first) if first else 0,
    }
    return summary


def to_markdown(report: dict) -> str:
    meta, summary, configs = report["meta"], report["summary"], report["configs"]
    lines = [
        "# Avaliação do pipeline", "",
        f"Gerado em {meta['date']} pelo comando `python -m voc_rag.cli evaluate`. "
        f"Repetições: {meta['repeat']}. Juiz: {meta['judge'] or 'não usado'}.", "",
        "| Item | Valor |", "|---|---|",
        f"| Modelo de chat | `{meta['llm']}` |", f"| Modelo do rerank | `{meta['rerank']}` |",
        f"| Embeddings | `{meta['embeddings']}` |", f"| Banco vetorial | `{meta.get('vector_store', 'chroma')}` |",
        f"| Similaridade mínima | {meta['min_similarity']} |",
        f"| Corte do rerank | {meta['min_relevance']} |", "",
    ]
    if meta.get("judge_warning"):
        lines += [f"> {meta['judge_warning']}", ""]
    if report.get("retrieval"):
        names = list(RETRIEVAL_CONFIGS)
        lines += [
            f"## Recuperação: precisão@{PRECISION_K}", "",
            "Ranking da própria pergunta, sem reescrita, sem corte de similaridade e sem filtro de metadados. "
            "Uma avaliação conta como relevante quando o texto casa com a expressão regular do tema; é um rótulo aproximado, "
            "útil para comparar as estratégias entre si.", "",
            "| Tema | " + " | ".join(names) + " |", "|---|" + "---|" * len(names),
        ]
        for row in report["retrieval"]:
            lines.append(f"| {row['question']} | " + " | ".join(f"{row[name]:.2f}" for name in names) + " |")
        means = [statistics.mean(row[name] for row in report["retrieval"]) for name in names]
        lines += ["| **Média** | " + " | ".join(f"**{value:.2f}**" for value in means) + " |", ""]
    lines += [
        "## Respostas e recusas por configuração", "",
        "Todas as configurações recebem a mesma análise da pergunta em cada repetição. "
        "A configuração `baseline` usa só a primeira frase de busca, busca densa e corte de similaridade.", "",
        "| Configuração | Acurácia dev | Acurácia test | Recusas indevidas | Respostas indevidas | Erros | Barreiras | Tokens por pergunta (entrada/saída) | Segundos |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for config in configs:
        item = summary[config]
        gates = ", ".join(f"{gate}: {count}" for gate, count in sorted(item["gates"].items())) or "—"
        lines.append(
            f"| `{config}` | {mean_std(item['accuracy_dev'])} | {mean_std(item['accuracy_test'])} | {item['false_refusals']} "
            f"| {item['false_answers']} | {item['errors']} | {gates} | {item['input_tokens']:.0f} / {item['output_tokens']:.0f} "
            f"| {item['seconds']:.1f} |"
        )
    analysis = summary["analysis_tokens"]
    lines += [
        "", f"A análise da pergunta, comum a todas as configurações, usa em média {analysis['input']:.0f} tokens de entrada "
        f"e {analysis['output']:.0f} de saída. Esses tokens ficam fora da coluna acima.", "",
        "## Fundamentação", "",
        "| Configuração | Insights | Sustentados | Parciais | Não sustentados | Metadado atribuído ao cliente | Descartados pela validação de citações |",
        "|---|---|---|---|---|---|---|",
    ]
    for config in configs:
        item = summary[config]
        verdicts = item["verdicts"]
        lines.append(
            f"| `{config}` | {item['insights']} | {verdicts.get('sim', 0)} | {verdicts.get('parcial', 0)} | {verdicts.get('nao', 0)} "
            f"| {item['misattributions']} | {item['dropped_insights']} |"
        )
    filters = summary["filters"]
    lines += ["", "## Extração de filtros", "", f"{filters['correct']} de {filters['checked']} perguntas com filtros esperados acertaram todas as condições.", ""]
    lines += [
        "## Detalhe por pergunta (primeira repetição)", "",
        "| Split | Pergunta | Esperado | " + " | ".join(f"`{config}`" for config in configs) + " | Similaridade máxima | Relevância máxima | Filtros |",
        "|---|---|---|" + "---|" * len(configs) + "---|---|---|",
    ]
    first = {(record["config"], record["question"]): record for record in report["records"] if record["repetition"] == 0}
    for item in report["questions"]:
        rows = [first.get((config, item["question"])) for config in configs]
        cells = [
            "—" if row is None else f"{'✅' if row['correct'] else '❌'} {row['status']}" + (f" ({row['stopped_at']})" if row["stopped_at"] else "")
            for row in rows
        ]
        last = next((row for row in reversed(rows) if row), None)
        filters_cell = "" if last is None or last["filters_ok"] is None else ("ok" if last["filters_ok"] else "erro")
        similarity = "" if last is None or last["best_similarity"] is None else f"{last['best_similarity']:.2f}"
        relevance = "" if last is None or not last["best_relevance"] else last["best_relevance"]
        lines.append(
            f"| {item['split']} | {item['question']} | {item['expected']} | " + " | ".join(cells)
            + f" | {similarity} | {relevance} | {filters_cell} |"
        )
    return "\n".join(lines) + "\n"


def run_evaluation(
    settings: Settings, use_judge: bool, repeat: int, configs: list[str], with_retrieval: bool, split: str
) -> str:
    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    questions = [item for item in eval_set["questions"] if split == "all" or item["split"] == split]
    runner = EvaluationRunner(settings, use_judge)
    judge_warning = ""
    if use_judge and settings.judge_provider == settings.llm_provider:
        judge_warning = (
            "O juiz usa o mesmo provedor do gerador, o que favorece as próprias respostas. "
            "Defina JUDGE_PROVIDER e JUDGE_MODEL com outro provedor para reduzir esse viés."
        )
        print(f"[aviso] {judge_warning}")
    report = {
        "meta": {
            "date": date.today().isoformat(), "repeat": repeat, "split": split,
            "llm": f"{settings.llm_provider}:{settings.chat_model}", "rerank": runner.reranker.model and f"{runner.reranker.name}:{runner.reranker.model}",
            "judge": f"{settings.judge_provider}:{settings.judge_model}" if use_judge else None, "judge_warning": judge_warning,
            "embeddings": f"{settings.embedding_provider}:{settings.embedding_model}",
            "min_similarity": settings.min_similarity, "min_relevance": runner.reranker.min_score,
            "vector_store": settings.vector_store,
        },
        "configs": configs,
        "questions": questions,
        "retrieval": runner.evaluate_retrieval(eval_set["retrieval"]) if with_retrieval else [],
    }
    report["records"] = runner.evaluate_questions(questions, configs, repeat)
    report["summary"] = summarize(report["records"], configs)

    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    (settings.eval_dir / "avaliacao.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(to_markdown(report), encoding="utf-8")
    return f"Relatório salvo em {REPORT_PATH} e {settings.eval_dir / 'avaliacao.json'}"
