import unittest

from voc_rag.labels import describe_conditions, format_condition
from voc_rag.schemas import ReviewFilters


class LabelsTest(unittest.TestCase):
    def test_format_condition(self):
        self.assertEqual(format_condition("purchase_month_num", ">=", 201711), "Mês da compra >= 2017-11")
        self.assertEqual(format_condition("delivery_status", "==", "atrasado"), "Entrega == Atrasada")
        self.assertEqual(format_condition("category", "==", "cama_mesa_banho"), "Categoria == cama mesa banho")
        self.assertEqual(format_condition("state", "in", ["RJ", "SP"]), "Estado em RJ, SP")

    def test_describe_conditions(self):
        self.assertEqual(describe_conditions(ReviewFilters.empty()), "toda a base")
        filters = ReviewFilters.empty().model_copy(update={"max_score": 2, "states": ["sp"]})
        self.assertEqual(describe_conditions(filters), "Nota <= 2; Estado em SP")


if __name__ == "__main__":
    unittest.main()
