import operator

import pandas as pd

from voc_rag.schemas import ReviewFilters

OPERATORS = {">=": operator.ge, "<=": operator.le, "==": operator.eq, "in": lambda column, values: column.isin(values)}
DELIVERY_LABELS = {"no_prazo": "no prazo", "atrasado": "atrasada", "nao_entregue": "não entregue"}
TOP_STATES = 5


def filter_mask(frame: pd.DataFrame, filters: ReviewFilters) -> pd.Series:
    # Mesmas condições do filtro do Chroma, aplicadas com pandas.
    mask = pd.Series(True, index=frame.index)
    for column, op, value in filters.conditions():
        mask &= OPERATORS[op](frame[column], value).fillna(False).astype(bool)
    return mask


class ReviewStats:
    def __init__(self, analytics: pd.DataFrame):
        self.analytics = analytics

    @property
    def categories(self) -> list[str]:
        return sorted(self.analytics["category"].unique())

    @property
    def months(self) -> list[str]:
        return sorted(self.analytics["purchase_month"].dropna().unique())

    def count(self, filters: ReviewFilters) -> int:
        return int(filter_mask(self.analytics, filters).sum())

    def describe(self, filters: ReviewFilters) -> str:
        subset = self.analytics[filter_mask(self.analytics, filters)]
        if subset.empty:
            return "Nenhuma avaliação corresponde aos filtros."

        scores = subset["score"].value_counts(normalize=True).sort_index()
        delivery = subset["delivery_status"].value_counts(normalize=True)
        lines = [
            f"Avaliações no recorte: {len(subset)} ({subset['has_comment'].mean():.0%} com comentário)",
            "Distribuição de notas: " + ", ".join(f"nota {s}: {p:.0%}" for s, p in scores.items()),
            "Entrega: " + ", ".join(f"{DELIVERY_LABELS[k]}: {p:.0%}" for k, p in delivery.items()),
        ]
        if not any(column == "state" for column, _, _ in filters.conditions()):
            states = subset["state"].value_counts(normalize=True).head(TOP_STATES)
            lines.append("Estados com mais avaliações: " + ", ".join(f"{k}: {p:.0%}" for k, p in states.items()))
        return "\n".join(lines)
