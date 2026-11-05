from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from voc_rag.prompts import RERANK_HUMAN, RERANK_SYSTEM


class Grade(BaseModel):
    id: str = Field(description="ID do candidato, ex.: C3")
    relevance: int = Field(description="Nota de 0 a 3")


class RelevanceGrades(BaseModel):
    grades: list[Grade]


def format_candidates(texts: list[str]) -> str:
    return "\n".join(f"[C{position}] {text}" for position, text in enumerate(texts, 1))


class LLMReranker:
    def __init__(self, llm):
        prompt = ChatPromptTemplate.from_messages([("system", RERANK_SYSTEM), ("human", RERANK_HUMAN)])
        self.chain = prompt | llm.with_structured_output(RelevanceGrades)

    def grade(self, question: str, filters: str, queries: list[str], texts: list[list[str]]) -> list[list[int]]:
        # Uma chamada por frase de busca, todas em paralelo.
        pending = [index for index, candidates in enumerate(texts) if candidates]
        outputs = self.chain.batch([
            {"question": question, "filters": filters, "query": queries[index], "candidates": format_candidates(texts[index])}
            for index in pending
        ])
        grades = [[0] * len(candidates) for candidates in texts]
        for index, output in zip(pending, outputs):
            for grade in output.grades:
                position = grade.id.strip("[] ").upper().removeprefix("C")
                if position.isdigit() and 1 <= int(position) <= len(texts[index]):
                    grades[index][int(position) - 1] = min(max(grade.relevance, 0), 3)
        return grades
