import re

from langchain_core.prompts import ChatPromptTemplate

from voc_rag.prompts import GENERATOR_HUMAN, GENERATOR_SYSTEM
from voc_rag.schemas import Evidence, GeneratedAnswer

DELIVERY_LABELS = {"no_prazo": "entrega no prazo", "atrasado": "entrega atrasada", "nao_entregue": "não entregue"}
CITATION_RANGE = re.compile(r"(\d+)\s*(?:-|–|—|A|ATÉ)\s*R?\s*(\d+)")
MAX_CITATION_RANGE = 50


def parse_citations(raw: str) -> list[str]:
    # Aceita "R3", "[r3]", "R 3", "R1-R4" e "R1 a R4".
    raw = raw.upper()
    numbers = []
    for start, end in CITATION_RANGE.findall(raw):
        if int(end) - int(start) <= MAX_CITATION_RANGE:
            numbers += range(int(start), int(end) + 1)
    numbers += [int(number) for number in re.findall(r"\d+", CITATION_RANGE.sub(" ", raw))]
    return [f"R{number}" for number in numbers]


def clean_citations(raw_ids: list[str], valid_ids: set[str]) -> list[str]:
    cited = (evidence_id for raw in raw_ids for evidence_id in parse_citations(raw))
    return list(dict.fromkeys(evidence_id for evidence_id in cited if evidence_id in valid_ids))


def format_context(evidences: list[Evidence]) -> str:
    blocks = []
    for evidence in evidences:
        meta = evidence.metadata
        header = (
            f"[{evidence.id}]\nMetadados do pedido (dados da base, não fala do cliente): "
            f"nota {meta.get('score')} | {meta.get('category')} | "
            f"{DELIVERY_LABELS.get(meta.get('delivery_status'), 'entrega desconhecida')} | {meta.get('purchase_month')} | "
            f"estado do cliente: {meta.get('state') or 'não informado'}"
        )
        if evidence.occurrences > 1:
            header += f" | texto igual em {evidence.occurrences} avaliações recuperadas"
        if evidence.matched_query:
            header += f'\nEncontrada pela busca: "{evidence.matched_query}"'
        blocks.append(f"{header}\nTexto do cliente (título e comentário):\n{evidence.text}")
    return "\n\n".join(blocks)


class AnswerGenerator:
    def __init__(self, llm):
        prompt = ChatPromptTemplate.from_messages([("system", GENERATOR_SYSTEM), ("human", GENERATOR_HUMAN)])
        self.chain = prompt | llm.with_structured_output(GeneratedAnswer)

    def generate(self, question: str, evidences: list[Evidence], overview: str) -> GeneratedAnswer:
        answer = self.chain.invoke({
            "question": question,
            "overview": overview,
            "context": format_context(evidences),
        })
        valid_ids = {evidence.id for evidence in evidences}
        for insight in answer.insights:
            insight.evidence_ids = clean_citations(insight.evidence_ids, valid_ids)
        cited = [insight for insight in answer.insights if insight.evidence_ids]
        answer._dropped_insights = len(answer.insights) - len(cited)
        answer.insights = cited
        return answer
