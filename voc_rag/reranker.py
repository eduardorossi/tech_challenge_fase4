import math

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


class CrossEncoderReranker:
    """Cross-encoder local: lê frase de busca e avaliação juntas e devolve um logit de relevância.

    Determinístico, sem custo por consulta. O logit é contínuo, então o corte (min_score) é calibrável.
    """

    name = "cross_encoder"

    def __init__(self, model: str, min_score: float = 0.0, encoder=None):
        if encoder is None:
            from sentence_transformers import CrossEncoder

            encoder = CrossEncoder(model)
        self.encoder = encoder
        self.model = model
        self.min_score = min_score

    def grade(self, question: str, filters: str, queries: list[str], texts: list[list[str]]) -> list[list[float]]:
        # Um único lote para todas as frases de busca.
        pairs = [(queries[index], text) for index, candidates in enumerate(texts) for text in candidates]
        scores = iter(self.encoder.predict(pairs, show_progress_bar=False).tolist() if pairs else [])
        return [[round(float(next(scores)), 3) for _ in candidates] for candidates in texts]

    @staticmethod
    def score(relevance: float, similarity: float) -> float:
        # Sigmoide do logit: relevância em [0, 1] para o MMR.
        return 1 / (1 + math.exp(-relevance))


class LLMReranker:
    name = "llm"

    def __init__(self, llm, min_score: int = 2, model: str = ""):
        prompt = ChatPromptTemplate.from_messages([("system", RERANK_SYSTEM), ("human", RERANK_HUMAN)])
        self.chain = prompt | llm.with_structured_output(RelevanceGrades)
        self.min_score = min_score
        self.model = model

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

    @staticmethod
    def score(relevance: float, similarity: float) -> float:
        # A nota do rerank domina; a similaridade desempata candidatos com a mesma nota.
        return (relevance + similarity) / 4


def create_reranker(settings):
    if settings.reranker == "cross_encoder":
        return CrossEncoderReranker(settings.cross_encoder_model, settings.min_rerank_score)
    from voc_rag.llm import create_chat_model

    llm = create_chat_model(settings.llm_provider, settings.rerank_model, settings.temperature)
    return LLMReranker(llm, settings.min_relevance, f"{settings.llm_provider}:{settings.rerank_model}")
