import json
import logging

import pandas as pd
import streamlit as st

from voc_rag.config import ROOT, Settings
from voc_rag.labels import DELIVERY_LABELS, describe_conditions, format_condition
from voc_rag.pipeline import build_pipeline
from voc_rag.schemas import PipelineResult, ReviewFilters, Status

st.set_page_config(page_title="Voz do Cliente | Olist", page_icon="◉", layout="wide")

st.html("""
    <style>
        [data-testid="stChatMessage"]:has([aria-label="Chat message from user"])
        > [data-testid="stChatMessageAvatarImage"],
        [data-testid="stChatMessage"] > img[alt="user avatar"] {
            background-color: #ED145B;
            object-fit: contain;
        }

        [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
            flex-direction: row-reverse;
            margin-left: auto;
            width: fit-content;
            max-width: 80%;
        }

        [data-testid="stChatMessage"]:has([aria-label="Chat message from user"])
        [data-testid="stChatMessageContent"] {
            min-width: 0;
            overflow-wrap: anywhere;
        }

        [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"])
        > [data-testid="stChatMessageAvatarImage"],
        [data-testid="stChatMessage"] > img[alt="assistant avatar"] {
            width: 3.5rem;
            object-fit: contain;
            border-radius: 0;
        }

        @media (max-width: 640px) {
            [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
                max-width: 95%;
            }
        }
    </style>
""")

EXAMPLES_PATH = ROOT / "examples" / "questions.json"
ASSISTANT_AVATAR = str(ROOT / "images" / "fiap.svg")
USER_AVATAR = str(ROOT / "images" / "estudante.png")
ALL_OPTIONS = "Todas"
TRACE_COLUMNS = {
    "query": "Frase de busca", "dense": "Busca densa", "lexical": "BM25", "fused": "Candidatos",
    "above_similarity": "Acima da similaridade mínima", "best_similarity": "Maior similaridade",
    "relevant": "Relevantes no rerank", "best_relevance": "Maior relevância no rerank", "selected": "Evidências usadas",
}


@st.cache_resource
def get_pipeline():
    return build_pipeline()


@st.cache_data(ttl=60)
def base_summary() -> dict | None:
    path = Settings().analytics_path
    if not path.exists():
        return None
    base = pd.read_parquet(path, columns=["has_comment", "purchase_month"])
    months = base["purchase_month"].dropna()
    return {
        "total": f"{len(base):,}".replace(",", "."),
        "comments": f"{base['has_comment'].mean():.1%}".replace(".", ",") if len(base) else "—",
        "period": f"{months.min()[:4]}–{months.max()[:4]}" if not months.empty else "—",
    }


@st.cache_data(ttl=60)
def filter_options() -> dict | None:
    path = Settings().analytics_path
    if not path.exists():
        return None
    base = pd.read_parquet(path, columns=["category", "purchase_month", "state"])
    return {
        "categories": sorted(base["category"].dropna().unique()),
        "months": sorted(base["purchase_month"].dropna().unique()),
        "states": sorted(base["state"].dropna().unique()),
    }


def plural(count: int, singular: str, plural_form: str) -> str:
    return f"{count} {singular if count == 1 else plural_form}"


class AnalysisProgress:
    # Traduz as etapas do pipeline em mensagens do st.status enquanto a análise roda.
    def __init__(self, status):
        self.status = status

    def update(self, stage: str, data: dict) -> None:
        if stage == "analyzed":
            kind = "Pergunta de panorama" if data["question_type"] == "overview" else "Pergunta específica"
            queries = data["queries"]
            self.status.write(f"{kind}. Buscando com {plural(len(queries), 'frase', 'frases')}:")
            self.status.markdown("\n".join(f"- *{query}*" for query in queries))
            if data["filters"].conditions():
                self.status.caption(f"Recorte: {describe_conditions(data['filters'])}")
            self.status.update(label="Buscando avaliações…", expanded=True)
        elif stage == "candidates":
            self.status.write(f"{plural(data['candidates'], 'avaliação candidata encontrada', 'avaliações candidatas encontradas')}.")
            if data["rerank"]:
                self.status.update(label="Avaliando a relevância de cada avaliação…", expanded=True)
        elif stage == "retrieved":
            if data["enough"]:
                self.status.write(f"{plural(data['evidences'], 'avaliação selecionada', 'avaliações selecionadas')} como evidência.")
                self.status.update(label="Escrevendo a análise…", expanded=True)
            else:
                self.status.write("Poucas avaliações tratam do assunto da pergunta.")


def render_filters(busy: bool) -> tuple[ReviewFilters | None, bool]:
    options = filter_options()
    st.markdown("#### Recorte da análise")
    use_filters = st.toggle(
        "Usar filtros de metadados", value=True, disabled=busy,
        help="Desligado, a busca usa toda a base e ignora os filtros identificados na pergunta.",
    )
    if busy:
        st.caption("Recorte travado até a análise terminar. Os valores abaixo continuam aplicados.")
    if not options:
        return None, use_filters
    disabled = busy or not use_filters
    scores = st.slider("Nota", 1, 5, (1, 5), disabled=disabled)
    delivery = st.selectbox(
        "Entrega", [ALL_OPTIONS, *DELIVERY_LABELS], disabled=disabled,
        format_func=lambda value: DELIVERY_LABELS.get(value, value),
    )
    category = st.selectbox(
        "Categoria", [ALL_OPTIONS, *options["categories"]], disabled=disabled,
        format_func=lambda value: value.replace("_", " "),
    )
    months = options["months"]
    start, end = st.select_slider("Mês da compra", months, value=(months[0], months[-1]), disabled=disabled)
    states = st.multiselect("Estado do cliente", options["states"], placeholder="Todos", disabled=disabled)
    st.caption("Os campos preenchidos têm prioridade sobre os filtros identificados na pergunta.")
    manual = ReviewFilters.empty().model_copy(update={
        "min_score": scores[0] if scores[0] > 1 else None,
        "max_score": scores[1] if scores[1] < 5 else None,
        "delivery_status": None if delivery == ALL_OPTIONS else delivery,
        "category": None if category == ALL_OPTIONS else category,
        "start_month": start if start != months[0] else None,
        "end_month": end if end != months[-1] else None,
        "states": states or None,
    })
    return (manual if manual.conditions() else None), use_filters


def evidence_table(result: PipelineResult) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ID": evidence.id,
            "Citada": evidence.id in result.cited_ids,
            "Avaliação": evidence.text,
            "Nota": evidence.metadata.get("score"),
            "Estado": evidence.metadata.get("state") or "Não informado",
            "Categoria": str(evidence.metadata.get("category") or "Não informada").replace("_", " "),
            "Entrega": DELIVERY_LABELS.get(evidence.metadata.get("delivery_status"), "Não informada"),
            "Mês": evidence.metadata.get("purchase_month"),
            "Repetições": evidence.occurrences,
            "Similaridade": evidence.similarity,
            "Relevância": evidence.relevance,
            "Busca": evidence.matched_query,
        }
        for evidence in result.evidences
    ])


def render(result: PipelineResult, index: int) -> None:
    for notice in result.notices:
        st.warning(notice)
    if result.status == Status.ANSWERED:
        st.caption("ANÁLISE REALIZADA")
        st.markdown(result.summary)
        if result.insights:
            st.markdown("#### Principais achados")
            for insight in result.insights:
                st.markdown(f"- {insight.text} **[{', '.join(insight.evidence_ids)}]**")
        st.caption(f"{len(result.cited_ids)} evidências citadas · {len(result.evidences)} evidências recuperadas")
    elif result.status == Status.OUT_OF_SCOPE:
        st.info(result.summary)
        st.caption("Experimente perguntar sobre produtos, entregas ou atendimento.")
    else:
        st.markdown(result.summary)
        if result.trace.get("stopped_at") != "empty_filter":
            st.caption("Tente ampliar o período, remover uma restrição ou mudar o tema da pergunta.")

    if result.limitations:
        st.caption(f"Limites da análise: {result.limitations}")

    if result.status != Status.OUT_OF_SCOPE:
        evaluations, overview, method = st.tabs(["Avaliações", "Panorama do recorte", "Como chegamos à resposta"])
        with evaluations:
            if result.evidences:
                st.caption("Confira os comentários que sustentam a análise. Os IDs correspondem às citações acima.")
                st.dataframe(
                    evidence_table(result), hide_index=True, width="stretch",
                    column_config={
                        "Avaliação": st.column_config.TextColumn(width="large"),
                        "Citada": st.column_config.CheckboxColumn(help="Avaliação citada nos achados da resposta."),
                        "Nota": st.column_config.NumberColumn(format="%d ★"),
                        "Similaridade": st.column_config.NumberColumn(
                            format="%.3f", help="Proximidade do texto com a busca; não é uma medida de satisfação."
                        ),
                        "Repetições": st.column_config.NumberColumn(
                            help="Textos iguais agrupados na busca. O estado é o da avaliação exibida."
                        ),
                        "Relevância": st.column_config.NumberColumn(
                            help="Relevância dada pelo rerank: logit do cross-encoder (acima do corte, -1 por padrão, é relevante) ou nota de 0 a 3 do LLM.",
                            format="%.2f",
                        ),
                        "Busca": st.column_config.TextColumn(help="Frase de busca que encontrou a avaliação."),
                    },
                )
                st.caption("Esta seleção ajuda a explicar as experiências; não representa a frequência dos temas na base.")
            else:
                st.info("Nenhuma avaliação disponível para esta consulta.")
        with overview:
            if result.overview:
                st.caption("Indicadores calculados sobre todas as avaliações que atendem aos filtros da consulta.")
                for line in result.overview.splitlines():
                    label, separator, value = line.partition(": ")
                    st.markdown(f"**{label}**  \n{value}" if separator else line)
            else:
                st.caption("Panorama indisponível para esta consulta.")
        with method:
            if result.analysis:
                st.markdown("**Filtros aplicados**")
                conditions = (result.filters or result.analysis.filters).conditions()
                for condition in conditions:
                    st.write(format_condition(*condition))
                if not conditions:
                    st.write("Toda a base, sem filtros adicionais.")
                kind = "panorama" if result.analysis.question_type == "overview" else "pergunta específica"
                st.markdown(f"**Frases usadas para encontrar avaliações** ({kind})")
                for query in result.analysis.search_queries:
                    st.write(f"- {query}")
                if result.trace.get("queries"):
                    st.markdown("**Funil da busca**")
                    funnel = pd.DataFrame(result.trace["queries"]).rename(columns=TRACE_COLUMNS)
                    st.dataframe(funnel, hide_index=True, width="stretch")
                timings = result.trace.get("timings_s", {})
                tokens = sum(usage.get("total_tokens", 0) for usage in result.trace.get("tokens", {}).values())
                st.caption(f"Tempo total: {timings.get('total', 0):.1f} s · Tokens: {tokens:,}".replace(",", "."))
            else:
                st.caption("Detalhes da busca indisponíveis.")

    if result.status == Status.ANSWERED:
        st.download_button(
            "Baixar análise", result.to_markdown(), file_name=f"analise-olist-{index + 1}.md",
            mime="text/markdown", key=f"download_{index}", on_click="ignore",
        )


def render_sidebar(examples: list[dict], busy: bool = False) -> tuple[str | None, ReviewFilters | None, bool]:
    with st.sidebar:
        st.markdown("## Olist")
        st.caption("VOZ DO CLIENTE")
        if st.button("Nova conversa", width="stretch", disabled=busy or not (
            st.session_state.history or st.session_state.get("failed_question")
        )):
            st.session_state.history = []
            st.session_state.pop("failed_question", None)
            st.rerun()
        st.divider()
        st.markdown("#### Explore uma pergunta")
        example = st.selectbox(
            "Sugestões de análise", range(len(examples)),
            format_func=lambda i: examples[i]["type"], disabled=busy,
        )
        st.caption(examples[example]["question"])
        selected = st.button(
            "Analisando…" if busy else "Analisar pergunta",
            key="analyze_question", type="primary", width="stretch", disabled=busy,
        )
        st.divider()
        manual_filters, use_filters = render_filters(busy)
        st.divider()
        st.markdown("#### Uma boa pergunta inclui")
        st.markdown("Um **tema**, como entrega ou produto, e, se necessário, uma **nota**, **categoria**, **período** ou **estado**.")
        st.caption("Cada pergunta é analisada de forma independente. Inclua nela o contexto necessário.")
        st.caption("Fonte: avaliações de compras da Olist. As respostas incluem comentários para conferência.")
    return (examples[example]["question"] if selected else None), manual_filters, use_filters


def render_welcome(examples: list[dict]) -> str | None:
    summary = base_summary()
    if summary:
        for column, label, value in zip(
            st.columns(3), ["Avaliações na base", "Com comentário", "Período de compras"],
            [summary["total"], summary["comments"], summary["period"]],
        ):
            with column.container(border=True):
                st.metric(label, value)
    else:
        st.info("A base de avaliações ainda não está disponível. Prepare os dados para iniciar as análises.")

    st.markdown("### Por onde você quer começar?")
    question = None
    cards = [
        ("Pontos de atenção", "Entenda os problemas relatados nas compras.", 0),
        ("Experiência de entrega", "Explore atrasos e dificuldades no recebimento.", 1),
        ("O que funciona bem", "Conheça os aspectos elogiados pelos clientes.", 2),
    ]
    for column, (title, description, example_index) in zip(st.columns(3), cards):
        with column.container(border=True):
            st.markdown(f"#### {title}")
            st.write(description)
            if st.button("Explorar tema", key=f"starter_{example_index}", width="stretch"):
                question = examples[example_index]["question"]
    return question


def main() -> None:
    st.session_state.setdefault("history", [])
    pending_question = st.session_state.get("pending_question")
    busy = pending_question is not None
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    question, manual_filters, use_filters = render_sidebar(examples, busy)

    st.caption("INTELIGÊNCIA DA EXPERIÊNCIA DO CLIENTE")
    st.title("Ouça seus clientes. Entenda os motivos.")
    st.write("Explore elogios e reclamações, encontre padrões e confira as avaliações por trás de cada resposta.")
    st.divider()

    # Espaço fixo da tela inicial: fica vazio durante a análise, para que os cartões não continuem
    # visíveis, esmaecidos, enquanto o Streamlit espera a resposta.
    welcome_slot = st.empty()
    if not busy and not st.session_state.history and not st.session_state.get("failed_question") and not question:
        with welcome_slot.container():
            question = render_welcome(examples)

    for index, past in enumerate(st.session_state.history):
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(past.question)
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            render(past, index)

    if failed_question := st.session_state.get("failed_question"):
        st.error("Não foi possível concluir a análise. Tente novamente em instantes.")
        st.write(f"Pergunta: {failed_question}")
        if st.button("Tentar novamente", disabled=busy):
            question = failed_question

    question = st.chat_input(
        "Aguarde a conclusão da análise…" if busy else "Ex.: O que os clientes relatam sobre atrasos na entrega?",
        key="question_input", disabled=busy,
    ) or question
    if not busy and question and question.strip():
        # Renderiza os controles bloqueados antes de iniciar a chamada demorada.
        st.session_state.pending_question = question.strip()
        st.rerun()

    if busy:
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(pending_question)
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            status = st.status("Preparando a análise…", expanded=True)
            status.caption("Costuma levar de 10 a 20 segundos.")
            try:
                pipeline = get_pipeline()
                status.update(label="Entendendo a pergunta…", expanded=True)
                result = pipeline.ask(
                    pending_question, manual_filters, use_filters, on_progress=AnalysisProgress(status).update
                )
                if result.status == Status.ERROR:
                    raise RuntimeError(result.summary)
            except Exception:
                logging.getLogger(__name__).exception("Falha ao consultar o pipeline de avaliações")
                st.session_state.failed_question = pending_question
                status.update(label="A análise não foi concluída", state="error", expanded=False)
            else:
                st.session_state.history.append(result)
                st.session_state.pop("failed_question", None)
                total = result.trace.get("timings_s", {}).get("total", 0)
                status.update(label=f"Análise concluída em {total:.0f} s", state="complete", expanded=False)
            finally:
                st.session_state.pop("pending_question", None)
        st.rerun()


if __name__ == "__main__":
    main()
