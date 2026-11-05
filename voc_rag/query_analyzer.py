from langchain_core.prompts import ChatPromptTemplate

from voc_rag.prompts import ANALYZER_SYSTEM
from voc_rag.retriever import describe_filters
from voc_rag.schemas import QueryAnalysis, ReviewFilters

MAX_SEARCH_QUERIES = 6


class QueryAnalyzer:
    def __init__(self, llm, categories: list[str]):
        self.categories = set(categories)
        prompt = ChatPromptTemplate.from_messages([("system", ANALYZER_SYSTEM), ("human", "{question}")])
        prompt = prompt.partial(categories=", ".join(categories))
        self.chain = prompt | llm.with_structured_output(QueryAnalysis)

    def analyze(self, question: str, manual_filters: ReviewFilters | None = None) -> QueryAnalysis:
        manual = describe_filters(manual_filters) if manual_filters else "nenhum"
        analysis = self.chain.invoke({"question": question, "manual_filters": manual})
        if analysis.filters.category not in self.categories:
            analysis.filters.category = None
        queries = [query.strip() for query in analysis.search_queries if query.strip()]
        analysis.search_queries = list(dict.fromkeys(queries))[:MAX_SEARCH_QUERIES] or [question]
        return analysis
