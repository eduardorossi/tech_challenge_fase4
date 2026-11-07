import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
STATES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}


class ReviewFilters(BaseModel):
    min_score: int | None = Field(description="Nota mínima de 1 a 5")
    max_score: int | None = Field(description="Nota máxima de 1 a 5")
    delivery_status: Literal["no_prazo", "atrasado", "nao_entregue"] | None = Field(
        description="Situação da entrega do pedido"
    )
    category: str | None = Field(description="Categoria de produto escrita exatamente como na lista")
    start_month: str | None = Field(description="Mês inicial da compra no formato AAAA-MM")
    end_month: str | None = Field(description="Mês final da compra no formato AAAA-MM")
    states: list[str] | None = Field(description="Siglas das UFs do cliente, como SP ou RJ")

    @classmethod
    def empty(cls) -> "ReviewFilters":
        return cls(**dict.fromkeys(cls.model_fields))

    def conditions(self) -> list[tuple[str, str, str | int | list[str]]]:
        conditions = []
        # Nota mínima 1 e máxima 5 não restringem nada e ficam de fora.
        if self.min_score in range(2, 6):
            conditions.append(("score", ">=", self.min_score))
        if self.max_score in range(1, 5):
            conditions.append(("score", "<=", self.max_score))
        if self.delivery_status:
            conditions.append(("delivery_status", "==", self.delivery_status))
        if self.category:
            conditions.append(("category", "==", self.category))
        if self.start_month and MONTH_PATTERN.match(self.start_month):
            conditions.append(("purchase_month_num", ">=", int(self.start_month.replace("-", ""))))
        if self.end_month and MONTH_PATTERN.match(self.end_month):
            conditions.append(("purchase_month_num", "<=", int(self.end_month.replace("-", ""))))
        states = sorted({state.strip().upper() for state in self.states or []} & STATES)
        if states:
            conditions.append(("state", "in", states))
        return conditions

    def merged(self, override: "ReviewFilters") -> "ReviewFilters":
        values = self.model_dump()
        values.update({name: value for name, value in override.model_dump().items() if value is not None})
        return ReviewFilters(**values)

    def overridden_by(self, override: "ReviewFilters") -> list[str]:
        mine, theirs = self.model_dump(), override.model_dump()
        return [name for name, value in theirs.items() if value is not None and mine[name] not in (None, value)]


class QueryAnalysis(BaseModel):
    in_scope: bool = Field(description="True se a pergunta trata da experiência de clientes do e-commerce")
    question_type: Literal["overview", "specific"] = Field(
        description="overview quando a pergunta pede principais temas ou padrões; specific quando foca um assunto"
    )
    search_queries: list[str] = Field(
        description="Frases escritas como um cliente escreveria uma avaliação: 1 ou 2 em specific, 4 a 6 em overview"
    )
    filters: ReviewFilters
    # "llm" ou "rules" (fallback quando o modelo de linguagem falha); fica fora do esquema enviado ao LLM.
    _source: str = PrivateAttr(default="llm")

    @property
    def source(self) -> str:
        return self._source


class Insight(BaseModel):
    text: str = Field(description="Insight em uma ou duas frases")
    evidence_ids: list[str] = Field(description="IDs das avaliações que sustentam o insight, ex.: R1")


class GeneratedAnswer(BaseModel):
    sufficient_evidence: bool = Field(description="False se as avaliações não respondem à pergunta")
    summary: str = Field(description="Resposta direta à pergunta em até três frases")
    insights: list[Insight]
    limitations: str = Field(description="O que as evidências não permitem afirmar")
    # Preenchido pelo código na validação das citações; fica fora do esquema enviado ao LLM.
    _dropped_insights: int = PrivateAttr(default=0)

    @property
    def dropped_insights(self) -> int:
        return self._dropped_insights


class Status(str, Enum):
    ANSWERED = "respondida"
    OUT_OF_SCOPE = "fora_do_escopo"
    INSUFFICIENT = "evidencia_insuficiente"
    ERROR = "erro"


@dataclass
class Evidence:
    id: str
    text: str
    similarity: float
    metadata: dict
    occurrences: int = 1
    review_id: str = ""
    matched_query: str = ""
    dense_rank: int | None = None
    lexical_rank: int | None = None
    relevance: float | None = None


@dataclass
class PipelineResult:
    question: str
    status: Status
    summary: str
    insights: list[Insight] = field(default_factory=list)
    limitations: str = ""
    evidences: list[Evidence] = field(default_factory=list)
    analysis: QueryAnalysis | None = None
    overview: str = ""
    filters: ReviewFilters | None = None
    notices: list[str] = field(default_factory=list)
    trace: dict = field(default_factory=dict)

    @property
    def cited_ids(self) -> set[str]:
        return {evidence_id for insight in self.insights for evidence_id in insight.evidence_ids}

    def to_markdown(self) -> str:
        lines = [f"### {self.question}", "", f"Status: `{self.status.value}`", ""]
        if self.analysis and self.status not in (Status.OUT_OF_SCOPE, Status.ERROR):
            filters = self.filters or self.analysis.filters
            conditions = [f"{col} {op} {value}" for col, op, value in filters.conditions()]
            queries = "; ".join(f'"{query}"' for query in self.analysis.search_queries)
            lines += [f"Busca ({self.analysis.question_type}): {queries}", "", f"Filtros: {', '.join(conditions) or 'nenhum'}", ""]
        lines += [f"> {notice}" for notice in self.notices]
        if self.notices:
            lines.append("")
        lines += [self.summary, ""]
        lines += [f"- {insight.text} ({', '.join(insight.evidence_ids)})" for insight in self.insights]
        if self.limitations:
            lines += ["", f"Limitações: {self.limitations}"]
        if self.evidences:
            lines += [
                "", "| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
            for evidence in self.evidences:
                meta = evidence.metadata
                text = evidence.text.replace("|", "/")
                cited = "sim" if evidence.id in self.cited_ids else ""
                relevance = "" if evidence.relevance is None else evidence.relevance
                lines.append(
                    f"| {evidence.id} | {cited} | {evidence.similarity:.2f} | {relevance} | {meta.get('score')} "
                    f"| {meta.get('state') or 'não informado'} | {meta.get('category')} | {meta.get('delivery_status')} | {text} |"
                )
        return "\n".join(lines) + "\n"
