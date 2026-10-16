"""Interface web (Streamlit) do Voice of Customer Intelligence.

Executar:  streamlit run src/app.py
"""
import pandas as pd
import streamlit as st

from voc_rag import config
from voc_rag.filtros import SENTIMENTOS, STATUS_ENTREGA, Filtros
from voc_rag.llm import nome_modelo
from voc_rag.pipeline import PipelineVoC

st.set_page_config(page_title="VoC Intelligence — Olist", page_icon="💬", layout="wide")

EXEMPLOS = [
    "Quais são os principais problemas relatados pelos clientes?",
    "O que os clientes relatam sobre problemas relacionados à entrega?",
    "Quais aspectos da experiência de compra são mais elogiados pelos clientes?",
    "Quais padrões podem ser identificados nas avaliações de clientes insatisfeitos?",
    "Quais avaliações sustentam a conclusão de que existem problemas recorrentes relacionados ao prazo de entrega?",
    "Existem padrões recorrentes nas avaliações relacionadas à qualidade dos produtos?",
    "O que os clientes mais elogiam na categoria beleza saude?",
    "Qual foi o faturamento da Olist em 2018?",
]

OPCOES = "Escolha uma ou mais opções"


@st.cache_resource(show_spinner="Carregando índices e modelos...")
def carregar_pipeline() -> PipelineVoC:
    """Carregado uma vez por processo (modelos e BM25 ficam em memória)."""
    return PipelineVoC()


pipeline = carregar_pipeline()
df = pipeline.recuperador.df

# --- Barra lateral: filtros manuais (metadados) ---------------------------------
with st.sidebar:
    st.header("Filtros de metadados")
    auto = st.toggle("Usar filtros de metadados", value=True)
    if auto:
        st.caption("O LLM identifica filtros na pergunta. Os campos abaixo são opcionais e, "
                   "quando preenchidos, têm prioridade sobre os identificados.")
    else:
        st.caption("Desligado: a busca usa toda a base, sem filtros. Os campos abaixo são ignorados.")
    f_sent = st.multiselect("Sentimento", SENTIMENTOS, placeholder=OPCOES, disabled=not auto)
    f_notas = st.slider("Nota", 1, 5, (1, 5), disabled=not auto)
    f_cat = st.multiselect("Categoria", pipeline.recuperador.categorias,
                           placeholder=OPCOES, disabled=not auto)
    f_ent = st.multiselect("Situação da entrega", STATUS_ENTREGA, placeholder=OPCOES,
                           disabled=not auto)
    meses = sorted(df["ano_mes"].unique())
    f_ini, f_fim = st.select_slider("Período da compra", meses, value=(meses[0], meses[-1]),
                                    disabled=not auto)
    f_uf = st.multiselect("UF do cliente", sorted(df["customer_state"].unique()),
                          placeholder=OPCOES, disabled=not auto)
    st.divider()
    st.caption(f"Base: {len(df):,} avaliações com texto  \n"
               f"LLM: {nome_modelo()}  \n"
               f"Embeddings: {config.MODELO_EMBEDDINGS.split('/')[-1]}")

filtros_manuais = Filtros(
    sentimentos=f_sent or None,
    nota_min=f_notas[0] if f_notas != (1, 5) else None,
    nota_max=f_notas[1] if f_notas != (1, 5) else None,
    categorias=f_cat or None,
    status_entrega=f_ent or None,
    ano_mes_inicio=f_ini if f_ini != meses[0] else None,
    ano_mes_fim=f_fim if f_fim != meses[-1] else None,
    estados=f_uf or None,
) if auto else None  # desligado: valores que ficaram selecionados não são aplicados

# --- Área principal --------------------------------------------------------------
st.title("💬 Voice of Customer Intelligence")
st.caption("Explore as avaliações de clientes da Olist com respostas fundamentadas em evidências (RAG).")

exemplo = st.selectbox("Perguntas de exemplo", EXEMPLOS, index=None,
                       placeholder="Escolha uma pergunta de exemplo")
pergunta = st.text_input("Sua pergunta", value=exemplo or "")

clicou = st.button("Perguntar", type="primary")
if clicou and not pergunta.strip():
    st.warning("Digite uma pergunta ou escolha um dos exemplos acima.")

if clicou and pergunta.strip():
    with st.spinner("Recuperando evidências e gerando resposta..."):
        res = pipeline.responder(pergunta, filtros_manuais, usar_filtros_automaticos=auto)

    aba_resp, aba_evid, aba_rastreio = st.tabs(["Resposta", "Evidências", "Rastreamento do pipeline"])

    with aba_resp:
        if res.status == "respondida":
            r = res.resposta
            st.markdown(f"**Confiança:** `{r.confianca}` · **Evidências usadas:** {len(res.evidencias)}")
            st.markdown(r.resumo)
            for ins in r.insights:
                with st.container(border=True):
                    st.markdown(f"**{ins.titulo}** — sustentado por {len(ins.evidencias)} "
                                f"evidência(s): `{', '.join(ins.evidencias)}`")
                    st.write(ins.descricao)
                    for ref in ins.evidencias:
                        e = res.evidencias[int(ref[1:]) - 1]
                        st.caption(f"{ref} · nota {e.metadados['nota']} · "
                                   f"{e.metadados['categoria']} — “{e.texto}”")
            st.info(f"**Limitações:** {r.limitacoes}")
        elif res.status == "fora_do_escopo":
            st.warning(res.mensagem)
        else:
            st.error(res.mensagem)

    with aba_evid:
        if res.evidencias:
            if res.estatisticas:
                st.json(res.estatisticas, expanded=False)
            tabela = pd.DataFrame([{
                "id": f"E{i}", "texto": e.texto, "nota": e.metadados["nota"],
                "categoria": e.metadados["categoria"], "entrega": e.metadados["status_entrega"],
                "compra": e.metadados["ano_mes"], "subconsulta": e.subconsulta,
                "score_rerank": round(e.score_rerank, 2),
                "pos_vetorial": e.pos_vetorial, "pos_bm25": e.pos_bm25,
                "repetições": e.repeticoes, "review_id": e.review_id,
            } for i, e in enumerate(res.evidencias, 1)])
            st.dataframe(tabela, hide_index=True, width="stretch")
        else:
            st.write("Nenhuma evidência recuperada.")

    with aba_rastreio:
        if res.consulta:
            st.subheader("1. Processamento da pergunta")
            st.caption(f"Origem: {res.origem_consulta}")
            st.json(res.consulta.model_dump())
            st.subheader("2. Filtros aplicados")
            st.json(res.filtros or {})
        st.subheader("3. Funil de recuperação")
        st.json(res.rastreio)
