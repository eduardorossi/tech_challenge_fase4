from voc_rag.schemas import ReviewFilters

DELIVERY_LABELS = {"no_prazo": "No prazo", "atrasado": "Atrasada", "nao_entregue": "Não entregue"}
FILTER_LABELS = {
    "score": "Nota", "category": "Categoria", "delivery_status": "Entrega",
    "purchase_month_num": "Mês da compra", "state": "Estado",
}
OPERATOR_LABELS = {"in": "em"}


def format_condition(column: str, operator: str, value) -> str:
    if column == "purchase_month_num":
        value = f"{str(value)[:4]}-{str(value)[4:]}"
    elif column == "delivery_status":
        value = DELIVERY_LABELS.get(value, value)
    elif column == "category":
        value = str(value).replace("_", " ")
    elif isinstance(value, list):
        value = ", ".join(value)
    return f"{FILTER_LABELS.get(column, column)} {OPERATOR_LABELS.get(operator, operator)} {value}"


def describe_conditions(filters: ReviewFilters) -> str:
    return "; ".join(format_condition(*condition) for condition in filters.conditions()) or "toda a base"
