import unittest

import pandas as pd

from voc_rag.config import Settings
from voc_rag.preparation import ReviewDataPreparer, clean_text, compose_text


class CleanTextTest(unittest.TestCase):
    def test_masks_personal_data(self):
        text = clean_text("Contato joao.silva@mail.com.br, (11) 98765-4321, CPF 123.456.789-09 e https://loja.com/x")
        self.assertEqual(text, "Contato [email], [telefone], CPF [cpf] e [url]")

    def test_keeps_order_numbers_that_are_not_phones(self):
        self.assertEqual(clean_text("pedido 12345 chegou"), "pedido 12345 chegou")

    def test_normalizes_spacing_and_punctuation(self):
        self.assertEqual(clean_text("Não\r\nchegou!!!!   Péssimo..."), "Não chegou! Péssimo.")

    def test_empty_values_become_none(self):
        self.assertIsNone(clean_text(float("nan")))
        self.assertIsNone(clean_text("   "))


class ComposeTextTest(unittest.TestCase):
    def test_drops_title_repeated_in_comment(self):
        self.assertEqual(compose_text("Ótimo", "ótimo produto"), "ótimo produto.")

    def test_joins_title_and_comment(self):
        self.assertEqual(compose_text("Atraso", "Chegou tarde!"), "Atraso. Chegou tarde!")

    def test_missing_parts(self):
        self.assertEqual(compose_text(None, "Recomendo"), "Recomendo.")
        self.assertIsNone(compose_text(None, None))


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tables = {
            "reviews": pd.DataFrame({
                "review_id": ["r1", "r1", "r2", "r3"],
                "order_id": ["o1", "o1", "o2", "o3"],
                "review_score": [1, 1, 5, 4],
                "review_comment_title": [None, None, None, None],
                "review_comment_message": ["Não recebi o produto", "Não recebi o produto", "bom", None],
            }),
            "orders": pd.DataFrame({
                "order_id": ["o1", "o2", "o3"],
                "customer_id": ["c1", "c2", "c3"],
                "order_purchase_timestamp": ["2017-11-05 10:00", "2017-10-01 10:00", "2018-01-02 10:00"],
                "order_delivered_customer_date": [None, "2017-10-03 10:00", "2018-01-20 10:00"],
                "order_estimated_delivery_date": ["2017-11-20", "2017-10-10", "2018-01-15"],
            }),
            "customers": pd.DataFrame({"customer_id": ["c1", "c2", "c3"], "customer_state": ["SP", "RJ", "MG"]}),
            "items": pd.DataFrame({
                "order_id": ["o1", "o1", "o2"], "product_id": ["p1", "p2", "p1"], "price": [10.0, 50.0, 10.0],
            }),
            "products": pd.DataFrame({"product_id": ["p1", "p2"], "product_category_name": ["bebes", "cama_mesa_banho"]}),
        }
        self.base = ReviewDataPreparer(Settings()).build(self.tables).set_index("review_id")

    def test_removes_duplicated_review_ids(self):
        self.assertEqual(sorted(self.base.index), ["r1", "r2", "r3"])

    def test_delivery_status_and_delay(self):
        self.assertEqual(self.base.loc["r1", "delivery_status"], "nao_entregue")
        self.assertEqual(self.base.loc["r2", "delivery_status"], "no_prazo")
        self.assertEqual(self.base.loc["r3", "delivery_status"], "atrasado")
        self.assertEqual(self.base.loc["r3", "delay_days"], 5)

    def test_category_comes_from_most_expensive_item(self):
        self.assertEqual(self.base.loc["r1", "category"], "cama_mesa_banho")
        self.assertEqual(self.base.loc["r3", "category"], "sem_categoria")

    def test_month_and_state(self):
        self.assertEqual(self.base.loc["r1", "purchase_month"], "2017-11")
        self.assertEqual(self.base.loc["r1", "purchase_month_num"], 201711)
        self.assertEqual(self.base.loc["r2", "state"], "RJ")

    def test_indexable_needs_two_words(self):
        self.assertTrue(self.base.loc["r1", "indexable"])
        self.assertFalse(self.base.loc["r2", "indexable"])
        self.assertFalse(self.base.loc["r3", "indexable"])


if __name__ == "__main__":
    unittest.main()
