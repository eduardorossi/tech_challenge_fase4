"""Filtros de metadados usados na recuperação (desafio adicional).

Os filtros viram uma série booleana do pandas (True = avaliação no recorte).
A mesma seleção restringe a busca vetorial (ids permitidos no FAISS) e a
busca lexical (BM25), garantindo que as duas olhem para o mesmo recorte.
"""
from dataclasses import asdict, dataclass
from typing import Optional

import pandas as pd

SENTIMENTOS = ["negativo", "neutro", "positivo"]
STATUS_ENTREGA = ["no_prazo", "atrasado", "nao_entregue"]


@dataclass
class Filtros:
    sentimentos: Optional[list] = None       # ex.: ["negativo"]
    nota_min: Optional[int] = None           # 1..5
    nota_max: Optional[int] = None           # 1..5
    categorias: Optional[list] = None        # ex.: ["cama mesa banho"]
    status_entrega: Optional[list] = None    # ex.: ["atrasado", "nao_entregue"]
    ano_mes_inicio: Optional[str] = None     # "YYYY-MM"
    ano_mes_fim: Optional[str] = None        # "YYYY-MM"
    estados: Optional[list] = None           # UFs, ex.: ["SP", "RJ"]

    def vazio(self) -> bool:
        return all(v in (None, []) for v in asdict(self).values())

    def descricao(self) -> dict:
        """Somente os filtros ativos (para exibição/rastreamento)."""
        return {k: v for k, v in asdict(self).items() if v not in (None, [])}

    def mesclar(self, outro: "Filtros") -> "Filtros":
        """Filtros de `outro` (ex.: escolhidos manualmente na interface) têm prioridade."""
        base = asdict(self)
        base.update({k: v for k, v in asdict(outro).items() if v not in (None, [])})
        return Filtros(**base)

    # --- pandas ---------------------------------------------------------------
    def no_recorte(self, df: pd.DataFrame) -> pd.Series:
        """Uma posição por avaliação: True se ela atende a todos os filtros."""
        m = pd.Series(True, index=df.index)
        if self.sentimentos:
            m &= df["sentimento"].isin(self.sentimentos)
        if self.nota_min is not None:
            m &= df["nota"] >= int(self.nota_min)
        if self.nota_max is not None:
            m &= df["nota"] <= int(self.nota_max)
        if self.categorias:
            m &= df["categoria"].isin(self.categorias)
        if self.status_entrega:
            m &= df["status_entrega"].isin(self.status_entrega)
        if self.ano_mes_inicio:
            m &= df["ano_mes_num"] >= _ano_mes_num(self.ano_mes_inicio)
        if self.ano_mes_fim:
            m &= df["ano_mes_num"] <= _ano_mes_num(self.ano_mes_fim)
        if self.estados:
            m &= df["customer_state"].isin(self.estados)
        return m


def _ano_mes_num(ano_mes: str) -> int:
    """'2018-03' -> 201803."""
    return int(str(ano_mes).replace("-", "")[:6])
