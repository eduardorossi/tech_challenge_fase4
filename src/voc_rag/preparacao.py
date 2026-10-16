"""Etapa 1 — Construção da base de conhecimento.

Lê os CSVs da Olist, seleciona as avaliações com texto, limpa os comentários,
trata valores ausentes, enriquece cada avaliação com metadados do pedido
(entrega, categoria, período, estado) e salva um "documento" por avaliação.
"""
import re
import unicodedata

import numpy as np
import pandas as pd

from . import config

# --- Limpeza de texto -----------------------------------------------------------

# Padrões de dados pessoais que clientes às vezes escrevem nos comentários (LGPD).
# São mascarados antes de qualquer embedding ou envio ao LLM.
PADROES_PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[URL]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[TELEFONE]"),
]


def limpar_texto(texto) -> str:
    """Normaliza um comentário mantendo acentos e caixa (úteis ao modelo de embeddings)."""
    if not isinstance(texto, str):
        return ""
    # NFC: "Ótimo" composto e decomposto viram a mesma sequência de bytes
    texto = unicodedata.normalize("NFC", texto)
    # Quebras de linha (\r\n) e tabs viram espaço
    texto = re.sub(r"[\r\n\t]+", " ", texto)
    for padrao, marcador in PADROES_PII:
        texto = padrao.sub(marcador, texto)
    # Pontuação repetida ("!!!!!", "....") é reduzida para no máximo 3
    texto = re.sub(r"([!?.,])\1{3,}", r"\1\1\1", texto)
    # Espaços múltiplos
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tem_conteudo(texto: str) -> bool:
    """Descarta textos sem informação (vazios, só pontuação/números, 1-2 letras)."""
    return len(re.findall(r"[A-Za-zÀ-ÿ]", texto)) >= 3


def formatar_categoria(cat) -> str:
    """'cama_mesa_banho' -> 'cama mesa banho'; ausente -> 'sem categoria'."""
    if not isinstance(cat, str) or not cat.strip():
        return "sem categoria"
    return cat.replace("_", " ").strip()


def sentimento_por_nota(nota: int) -> str:
    """Nota 1-2 = negativo, 3 = neutro, 4-5 = positivo (proxy de sentimento)."""
    return "negativo" if nota <= 2 else ("neutro" if nota == 3 else "positivo")


# --- Montagem da base -----------------------------------------------------------

def carregar_csv(nome: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(config.PASTA_DADOS / nome, **kwargs)


def metadados_pedidos() -> pd.DataFrame:
    """Uma linha por pedido com informações de entrega, período, categoria e estado."""
    datas = ["order_purchase_timestamp", "order_delivered_customer_date",
             "order_estimated_delivery_date"]
    pedidos = carregar_csv("olist_orders_dataset.csv", parse_dates=datas)
    clientes = carregar_csv("olist_customers_dataset.csv",
                            usecols=["customer_id", "customer_state"])
    itens = carregar_csv("olist_order_items_dataset.csv",
                         usecols=["order_id", "order_item_id", "product_id", "price"])
    produtos = carregar_csv("olist_products_dataset.csv",
                            usecols=["product_id", "product_category_name"])

    # Categoria do pedido = categoria do item de maior valor
    # (~3% dos pedidos têm mais de um produto; o item mais caro é o mais provável alvo do comentário)
    itens = itens.merge(produtos, on="product_id", how="left")
    itens = itens.sort_values(["order_id", "price"], ascending=[True, False])
    resumo_itens = itens.groupby("order_id").agg(
        categoria=("product_category_name", "first"),
        n_itens=("order_item_id", "count"),
        valor_total=("price", "sum"),
    ).reset_index()

    df = pedidos.merge(clientes, on="customer_id", how="left")
    df = df.merge(resumo_itens, on="order_id", how="left")

    # Indicadores de entrega derivados das datas
    entregue = df["order_delivered_customer_date"]
    previsto = df["order_estimated_delivery_date"]
    df["dias_atraso"] = (entregue.dt.normalize() - previsto.dt.normalize()).dt.days
    df["tempo_entrega_dias"] = (entregue - df["order_purchase_timestamp"]).dt.days
    df["status_entrega"] = np.select(
        [entregue.isna(), df["dias_atraso"] > 0],
        ["nao_entregue", "atrasado"],
        default="no_prazo",
    )
    df["ano_mes"] = df["order_purchase_timestamp"].dt.strftime("%Y-%m")
    return df[["order_id", "order_status", "customer_state", "categoria", "n_itens",
               "valor_total", "dias_atraso", "tempo_entrega_dias", "status_entrega",
               "ano_mes"]]


def construir_documentos() -> pd.DataFrame:
    """Gera a tabela final de documentos (1 avaliação = 1 documento)."""
    reviews = carregar_csv("olist_order_reviews_dataset.csv")
    n_total = len(reviews)

    # 1) Seleção: 789 review_id aparecem ligados a 2-3 pedidos (814 linhas extras, mesma nota e texto);
    #    mantemos uma ocorrência para não duplicar evidências.
    reviews = reviews.drop_duplicates(subset="review_id", keep="first")

    # 2) Limpeza de título e mensagem
    reviews["titulo"] = reviews["review_comment_title"].map(limpar_texto)
    reviews["mensagem"] = reviews["review_comment_message"].map(limpar_texto)

    # 3) Valores ausentes: título/mensagem nulos viram "" e o texto final combina os dois.
    #    Avaliações sem nenhum texto (~59%) não têm conteúdo semântico e saem da base vetorial.
    def combinar(linha):
        titulo, msg = linha["titulo"], linha["mensagem"]
        if titulo and msg and titulo.lower() not in msg.lower():
            return f"{titulo}. {msg}"
        return msg or titulo

    reviews["texto"] = reviews.apply(combinar, axis=1)
    reviews = reviews[reviews["texto"].map(tem_conteudo)].copy()

    # 4) Enriquecimento com metadados do pedido
    df = reviews.merge(metadados_pedidos(), on="order_id", how="left")
    df["categoria"] = df["categoria"].map(formatar_categoria)
    df["customer_state"] = df["customer_state"].fillna("ND")
    df["status_entrega"] = df["status_entrega"].fillna("nao_entregue")
    df["ano_mes"] = df["ano_mes"].fillna(
        pd.to_datetime(df["review_creation_date"]).dt.strftime("%Y-%m"))
    # Versão numérica do período (201803) para filtros de intervalo (>= / <=)
    df["ano_mes_num"] = df["ano_mes"].str.replace("-", "").astype(int)
    # Numéricos ausentes recebem sentinela -999 (mantém a coluna inteira e explícita)
    for col in ["dias_atraso", "tempo_entrega_dias", "n_itens"]:
        df[col] = df[col].fillna(-999).astype(int)
    df["valor_total"] = df["valor_total"].fillna(-1.0).round(2)

    df["nota"] = df["review_score"].astype(int)
    df["sentimento"] = df["nota"].map(sentimento_por_nota)
    df["data_avaliacao"] = pd.to_datetime(df["review_creation_date"]).dt.strftime("%Y-%m-%d")

    colunas = ["review_id", "order_id", "texto", "nota", "sentimento", "categoria",
               "status_entrega", "dias_atraso", "tempo_entrega_dias", "customer_state",
               "ano_mes", "ano_mes_num", "data_avaliacao", "n_itens", "valor_total", "order_status"]
    df = df[colunas].reset_index(drop=True)

    print(f"Avaliações no CSV: {n_total:,} | com texto útil (documentos): {len(df):,}")
    return df


def main():
    config.PASTA_ARTEFATOS.mkdir(exist_ok=True)
    df = construir_documentos()
    df.to_parquet(config.ARQ_DOCUMENTOS, index=False)
    print(f"Base salva em {config.ARQ_DOCUMENTOS}")
    print("\nDistribuição por sentimento:\n", df["sentimento"].value_counts().to_string())
    print("\nDistribuição por status de entrega:\n", df["status_entrega"].value_counts().to_string())


if __name__ == "__main__":
    main()
