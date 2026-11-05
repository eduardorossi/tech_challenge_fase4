import re
import unicodedata

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from voc_rag.schemas import ReviewFilters
from voc_rag.stats import filter_mask

STEM_LENGTH = 5


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in text if not unicodedata.combining(char))


# "não" fica de fora: "não chegou" e "chegou" pedem avaliações opostas.
STOPWORDS = set(strip_accents("""a o as os um uma uns umas de da do das dos em na no nas nos por para pra com e ou
que se ao aos à às é foi ser são era mais mas me meu minha eu ele ela isso esse essa este esta já tudo todo toda""").split())


def tokenize(text: str) -> list[str]:
    # Minúsculas, sem acentos e com radical aproximado por truncamento: entrega e entregue viram "entre".
    tokens = re.findall(r"[a-z0-9]+", strip_accents(text))
    return [token[:STEM_LENGTH] for token in tokens if token not in STOPWORDS and len(token) > 1]


class LexicalIndex:
    def __init__(self, documents: pd.DataFrame):
        self.documents = documents.reset_index(drop=True)
        self.bm25 = BM25Okapi([tokenize(text) for text in self.documents["text"]])

    def search(self, query: str, filters: ReviewFilters, k: int) -> list[str]:
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        scores[~filter_mask(self.documents, filters).to_numpy()] = 0
        top = np.argsort(-scores)[:k]
        return [self.documents["review_id"].iat[position] for position in top if scores[position] > 0]
