import re
import unicodedata

import numpy as np
import pandas as pd

from voc_rag.config import Settings

FILES = {
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "customers": "olist_customers_dataset.csv",
}

LINE_BREAKS = re.compile(r"[\r\n\t]+")
EXTRA_SPACES = re.compile(r"\s{2,}")
REPEATED_PUNCTUATION = re.compile(r"([!?.,])\1{2,}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL = re.compile(r"https?://\S+|www\.\S+")
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
PHONE = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b")
HAS_LETTER = r"[A-Za-zÀ-ÿ]"
MIN_WORDS = 2


def clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFC", value)
    text = LINE_BREAKS.sub(" ", text)
    text = EMAIL.sub("[email]", text)
    text = URL.sub("[url]", text)
    text = CPF.sub("[cpf]", text)
    text = PHONE.sub("[telefone]", text)
    text = REPEATED_PUNCTUATION.sub(r"\1", text)
    text = EXTRA_SPACES.sub(" ", text).strip()
    return text or None


def compose_text(title: str | None, comment: str | None) -> str | None:
    if title and comment and title.lower() in comment.lower():
        title = None
    parts = [part if part[-1] in ".!?" else f"{part}." for part in (title, comment) if part]
    return " ".join(parts) if parts else None


class ReviewDataPreparer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self) -> str:
        tables = {name: pd.read_csv(self.settings.raw_dir / file) for name, file in FILES.items()}
        base = self.build(tables)
        self.settings.processed_dir.mkdir(parents=True, exist_ok=True)
        base.to_parquet(self.settings.analytics_path, index=False)
        base[base["indexable"]].to_parquet(self.settings.documents_path, index=False)
        return self._report(tables["reviews"], base)

    def build(self, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
        base = (
            self._prepare_reviews(tables["reviews"])
            .merge(self._prepare_orders(tables["orders"], tables["customers"]), on="order_id", how="left")
            .merge(self._main_category(tables["items"], tables["products"]), on="order_id", how="left")
        )
        base["category"] = base["category"].fillna("sem_categoria")
        text = base["text"].fillna("")
        base["indexable"] = text.str.contains(HAS_LETTER) & (text.str.split().str.len() >= MIN_WORDS)
        return base

    @staticmethod
    def _prepare_reviews(raw: pd.DataFrame) -> pd.DataFrame:
        reviews = raw.drop_duplicates("review_id").copy()
        reviews["text"] = [
            compose_text(clean_text(title), clean_text(comment))
            for title, comment in zip(reviews["review_comment_title"], reviews["review_comment_message"])
        ]
        reviews["has_comment"] = reviews["review_comment_message"].notna()
        reviews = reviews.rename(columns={"review_score": "score"})
        return reviews[["review_id", "order_id", "score", "text", "has_comment"]]

    @staticmethod
    def _prepare_orders(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
        orders = orders.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
        purchase = pd.to_datetime(orders["order_purchase_timestamp"])
        delivered = pd.to_datetime(orders["order_delivered_customer_date"])
        estimated = pd.to_datetime(orders["order_estimated_delivery_date"])

        delay = (delivered.dt.normalize() - estimated.dt.normalize()).dt.days
        orders["delay_days"] = delay.astype("Int64")
        orders["delivery_status"] = np.select(
            [delivered.isna(), delay > 0], ["nao_entregue", "atrasado"], default="no_prazo"
        )
        orders["purchase_month"] = purchase.dt.strftime("%Y-%m")
        orders["purchase_month_num"] = purchase.dt.year * 100 + purchase.dt.month
        orders = orders.rename(columns={"customer_state": "state"})
        return orders[["order_id", "purchase_month", "purchase_month_num", "delivery_status", "delay_days", "state"]]

    @staticmethod
    def _main_category(items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
        items = items.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
        main_item = items.sort_values("price", ascending=False).drop_duplicates("order_id")
        return main_item.rename(columns={"product_category_name": "category"})[["order_id", "category"]]

    @staticmethod
    def _report(raw: pd.DataFrame, base: pd.DataFrame) -> str:
        comment_rate = raw.groupby("review_score")["review_comment_message"].apply(lambda s: s.notna().mean())
        score_one = base.groupby("delivery_status")["score"].apply(lambda s: (s == 1).mean())
        return "\n".join([
            f"Avaliações brutas: {len(raw)}",
            f"review_id duplicados removidos: {len(raw) - len(base)}",
            f"Sem título: {raw['review_comment_title'].isna().mean():.1%}",
            f"Sem comentário: {raw['review_comment_message'].isna().mean():.1%}",
            f"Com texto após limpeza: {base['text'].notna().sum()}",
            f"Documentos indexáveis: {base['indexable'].sum()}",
            "Taxa de comentário por nota: " + ", ".join(f"{s}: {r:.1%}" for s, r in comment_rate.items()),
            "Nota 1 por situação de entrega: " + ", ".join(f"{k}: {v:.1%}" for k, v in score_one.items()),
        ])
