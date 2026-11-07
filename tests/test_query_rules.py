import unittest

from voc_rag.query_analyzer import NEGATIVE_TOPICS, POSITIVE_TOPICS, CategoryMatcher, QueryAnalyzer, rules_analysis

CATEGORIES = CategoryMatcher(["bebes", "cama_mesa_banho", "moveis_decoracao", "moveis_escritorio"])


def rules(question: str):
    return rules_analysis(question, CATEGORIES)


class CategoryMatcherTest(unittest.TestCase):
    def test_exact_and_misspelled_names(self):
        self.assertEqual(CATEGORIES.match("cama_mesa_banho"), "cama_mesa_banho")
        self.assertEqual(CATEGORIES.match("Cama Mesa Banho"), "cama_mesa_banho")
        self.assertEqual(CATEGORIES.match("móveis decoracão"), "moveis_decoracao")
        self.assertEqual(CATEGORIES.match("bebês"), "bebes")

    def test_distant_names_are_rejected(self):
        self.assertIsNone(CATEGORIES.match("eletronicos"))
        self.assertIsNone(CATEGORIES.match(None))

    def test_find_in_prefers_the_longest_name(self):
        self.assertEqual(CATEGORIES.find_in("Reclamações de móveis escritório"), "moveis_escritorio")


class RulesAnalysisTest(unittest.TestCase):
    def test_dissatisfied_overview(self):
        result = rules("Quais padrões aparecem nas avaliações de clientes insatisfeitos?")
        self.assertEqual(result.source, "rules")
        self.assertTrue(result.in_scope)
        self.assertEqual(result.question_type, "overview")
        self.assertEqual(result.search_queries, NEGATIVE_TOPICS)
        self.assertEqual(result.filters.conditions(), [("score", "<=", 2)])

    def test_praise_overview(self):
        result = rules("Quais aspectos são mais elogiados?")
        self.assertEqual(result.search_queries, POSITIVE_TOPICS)
        self.assertEqual(result.filters.conditions(), [("score", ">=", 4)])

    def test_complaints_do_not_restrict_the_score(self):
        result = rules("Quais as principais reclamações dos clientes?")
        self.assertEqual(result.search_queries, NEGATIVE_TOPICS)
        self.assertEqual(result.filters.conditions(), [])

    def test_specific_question_keeps_the_question_as_query(self):
        result = rules("O que dizem sobre a embalagem?")
        self.assertEqual((result.question_type, result.search_queries), ("specific", ["O que dizem sobre a embalagem?"]))
        self.assertEqual(result.filters.conditions(), [])

    def test_period_delivery_category_and_state(self):
        result = rules("Do que reclamam em cama, mesa e banho os clientes de São Paulo e RJ com pedidos entregues com atraso em novembro de 2017?")
        conditions = dict(((column, op), value) for column, op, value in result.filters.conditions())
        self.assertEqual(conditions[("delivery_status", "==")], "atrasado")
        self.assertEqual(conditions[("category", "==")], "cama_mesa_banho")
        self.assertEqual(conditions[("purchase_month_num", ">=")], 201711)
        self.assertEqual(conditions[("purchase_month_num", "<=")], 201711)
        self.assertEqual(conditions[("state", "in")], ["RJ", "SP"])

    def test_year_and_undelivered(self):
        result = rules("Quem comprou e não chegou em 2025?")
        self.assertEqual((result.filters.start_month, result.filters.end_month), ("2025-01", "2025-12"))
        self.assertEqual(result.filters.delivery_status, "nao_entregue")

    def test_preposition_para_is_not_a_state(self):
        self.assertIsNone(rules("O que falta para melhorar a entrega?").filters.states)

    def test_analyzer_without_llm_uses_rules(self):
        result = QueryAnalyzer(None, ["bebes"]).analyze("Elogios sobre bebês")
        self.assertEqual((result.source, result.filters.category), ("rules", "bebes"))


if __name__ == "__main__":
    unittest.main()
