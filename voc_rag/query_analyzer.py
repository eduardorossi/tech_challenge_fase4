import difflib
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from voc_rag.lexical import strip_accents
from voc_rag.prompts import ANALYZER_SYSTEM
from voc_rag.retriever import describe_filters
from voc_rag.schemas import QueryAnalysis, ReviewFilters

logger = logging.getLogger(__name__)

MAX_SEARCH_QUERIES = 6
CATEGORY_CUTOFF = 0.75

# Fallback por regras: subtemas usados nas perguntas de panorama.
NEGATIVE_TOPICS = [
    "o produto chegou atrasado", "o produto veio com defeito ou quebrado", "não recebi o meu pedido",
    "o produto é diferente do anunciado", "faltou item no pedido", "o vendedor não responde",
]
POSITIVE_TOPICS = [
    "a entrega foi rápida, chegou antes do prazo", "o produto é de ótima qualidade",
    "recomendo o vendedor, ótimo atendimento", "produto bem embalado", "ótimo custo benefício",
]
# Mesmas regras do prompt: insatisfação e nota baixa restringem a nota; reclamações só mudam os subtemas.
LOW_SCORE = re.compile(r"nota baixa|notas baixas|insatisf|negativ")
HIGH_SCORE = re.compile(r"nota alta|notas altas|elogi|positiv|satisf")
NEGATIVE = re.compile(r"problema|reclam|ruim|pior")
POSITIVE = re.compile(r"gost|melhor")
OVERVIEW = re.compile(r"principa|mais |padr|frequen|recorrent|aspectos|temas")
LATE_ORDERS = re.compile(r"(pedidos|entregues|entregas) com atraso")
UNDELIVERED = re.compile(r"nao (foram |foi )?entregues?|pedidos? que nao cheg|e nao (chegou|chegaram|recebeu|receberam)")
MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
MONTH_YEAR = re.compile(r"\b(" + "|".join(MONTHS) + r") de (\d{4})\b")
YEAR = re.compile(r"\b(?:em|de|no ano de) (20\d{2})\b")
STATE_NAMES = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA", "ceara": "CE",
    "distrito federal": "DF", "espirito santo": "ES", "goias": "GO", "maranhao": "MA", "mato grosso do sul": "MS",
    # "Pará" fica de fora: sem acento, colide com a preposição "para". A sigla PA continua aceita.
    "mato grosso": "MT", "minas gerais": "MG", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS", "rondonia": "RO",
    "roraima": "RR", "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO",
}
STATE_ACRONYM = re.compile(r"\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b")


CONNECTORS = {"e", "de", "da", "do", "das", "dos"}


def normalize_name(text: str) -> str:
    # "Cama, mesa e banho" e "cama_mesa_banho" viram "cama mesa banho".
    return " ".join(token for token in re.findall(r"[a-z0-9]+", strip_accents(text)) if token not in CONNECTORS)


class CategoryMatcher:
    """Aproxima a categoria escrita pelo LLM (ou pelo usuário) da grafia da base."""

    def __init__(self, categories: list[str]):
        self.by_name = {normalize_name(category): category for category in categories}

    def match(self, value: str | None) -> str | None:
        if not value:
            return None
        name = normalize_name(value)
        if name in self.by_name:
            return self.by_name[name]
        close = difflib.get_close_matches(name, self.by_name, n=1, cutoff=CATEGORY_CUTOFF)
        return self.by_name[close[0]] if close else None

    def find_in(self, text: str) -> str | None:
        # A categoria mais longa citada no texto: "moveis escritorio" antes de "moveis".
        text = f" {normalize_name(text)} "
        found = [name for name in self.by_name if f" {name} " in text]
        return self.by_name[max(found, key=len)] if found else None


def rules_analysis(question: str, categories: CategoryMatcher) -> QueryAnalysis:
    """Fallback determinístico, usado quando o LLM falha (sem chave, sem cota, timeout)."""
    text = strip_accents(question)
    filters = ReviewFilters.empty()
    topics = [question]
    if LOW_SCORE.search(text):
        filters.max_score, topics = 2, NEGATIVE_TOPICS
    elif HIGH_SCORE.search(text):
        filters.min_score, topics = 4, POSITIVE_TOPICS
    elif NEGATIVE.search(text):
        topics = NEGATIVE_TOPICS
    elif POSITIVE.search(text):
        topics = POSITIVE_TOPICS
    if LATE_ORDERS.search(text):
        filters.delivery_status = "atrasado"
    elif UNDELIVERED.search(text):
        filters.delivery_status = "nao_entregue"
    if month := MONTH_YEAR.search(text):
        filters.start_month = filters.end_month = f"{month.group(2)}-{MONTHS[month.group(1)]:02d}"
    elif year := YEAR.search(text):
        filters.start_month, filters.end_month = f"{year.group(1)}-01", f"{year.group(1)}-12"
    filters.category = categories.find_in(question)
    states = set(STATE_ACRONYM.findall(question))
    padded = f" {normalize_name(question)} "
    states |= {acronym for name, acronym in STATE_NAMES.items() if f" {name} " in padded}
    filters.states = sorted(states) or None

    overview = bool(OVERVIEW.search(text))
    analysis = QueryAnalysis(
        in_scope=True, question_type="overview" if overview else "specific",
        search_queries=topics if overview else [question], filters=filters,
    )
    analysis._source = "rules"
    return analysis


class QueryAnalyzer:
    def __init__(self, llm, categories: list[str]):
        self.categories = CategoryMatcher(categories)
        self.chain = None
        if llm is not None:
            prompt = ChatPromptTemplate.from_messages([("system", ANALYZER_SYSTEM), ("human", "{question}")])
            prompt = prompt.partial(categories=", ".join(categories))
            self.chain = prompt | llm.with_structured_output(QueryAnalysis)

    def analyze(self, question: str, manual_filters: ReviewFilters | None = None) -> QueryAnalysis:
        if self.chain is None:
            return rules_analysis(question, self.categories)
        manual = describe_filters(manual_filters) if manual_filters else "nenhum"
        try:
            analysis = self.chain.invoke({"question": question, "manual_filters": manual})
        except Exception as error:
            logger.warning("Análise por LLM falhou (%s); usando regras.", type(error).__name__)
            return rules_analysis(question, self.categories)
        analysis.filters.category = self.categories.match(analysis.filters.category)
        queries = [query.strip() for query in analysis.search_queries if query.strip()]
        analysis.search_queries = list(dict.fromkeys(queries))[:MAX_SEARCH_QUERIES] or [question]
        return analysis
