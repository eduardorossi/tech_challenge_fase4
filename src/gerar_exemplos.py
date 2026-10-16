"""Executa as perguntas de exemplo e salva perguntas, respostas e evidências em docs/exemplos.md.

Uso:  python src/gerar_exemplos.py
"""
import sys
from datetime import date

from voc_rag import config
from voc_rag.llm import nome_modelo
from voc_rag.pipeline import PipelineVoC

PERGUNTAS = [
    "Quais são os principais problemas relatados pelos clientes?",
    "O que os clientes relatam sobre problemas relacionados à entrega?",
    "Quais aspectos da experiência de compra são mais elogiados pelos clientes?",
    "Quais padrões podem ser identificados nas avaliações de clientes insatisfeitos?",
    "Quais avaliações sustentam a conclusão de que existem problemas recorrentes relacionados ao prazo de entrega?",
    "Existem padrões recorrentes nas avaliações relacionadas à qualidade dos produtos?",
    "Quais são os principais problemas relatados nas avaliações com nota baixa da categoria cama mesa banho?",
    "Qual foi o faturamento da Olist em 2018?",
    "O que os clientes dizem sobre as entregas feitas por drone?",
]


def para_markdown(res) -> str:
    linhas = [f"## {res.pergunta}\n"]
    if res.consulta:
        linhas.append(f"- **Tipo:** {res.consulta.tipo} · **Filtros:** `{res.filtros or 'nenhum'}`")
        linhas.append(f"- **Consultas de busca:** {', '.join(f'`{c}`' for c in res.consulta.consultas_busca)}")
    if res.rastreio.get("evidencias_finais") is not None:
        linhas.append(f"- **Recorte:** {res.rastreio['avaliacoes_no_recorte']:,} avaliações · "
                      f"**evidências finais:** {res.rastreio['evidencias_finais']} · "
                      f"**melhor score do reranker:** {res.rastreio.get('melhor_score_rerank')}")
    linhas.append("")
    if res.status != "respondida":
        linhas.append(f"> **{res.status}** — {res.mensagem}\n")
    else:
        r = res.resposta
        linhas.append(f"**Resposta (confiança {r.confianca}):** {r.resumo}\n")
        for ins in r.insights:
            linhas.append(f"- **{ins.titulo}** [{', '.join(ins.evidencias)}] — {ins.descricao}")
        linhas.append(f"\n*Limitações:* {r.limitacoes}\n")
    if res.evidencias:
        linhas.append("<details><summary>Evidências recuperadas</summary>\n")
        linhas.append("| id | nota | categoria | entrega | rerank | texto |")
        linhas.append("|---|---|---|---|---|---|")
        for i, e in enumerate(res.evidencias, 1):
            m = e.metadados
            texto = e.texto.replace("|", "/")
            linhas.append(f"| E{i} | {m['nota']} | {m['categoria']} | {m['status_entrega']} | "
                          f"{e.score_rerank:+.2f} | {texto} |")
        linhas.append("\n</details>\n")
    return "\n".join(linhas)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pipeline = PipelineVoC()
    partes = [f"# Exemplos de perguntas e respostas\n\nGerado em {date.today()} · LLM: "
              f"`{nome_modelo()}` · embeddings: `{config.MODELO_EMBEDDINGS}` · "
              f"reranker: `{config.MODELO_RERANKER}`\n"]
    for pergunta in PERGUNTAS:
        print(f"-> {pergunta}")
        partes.append(para_markdown(pipeline.responder(pergunta)))
    destino = config.RAIZ / "docs" / "exemplos.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"Salvo em {destino}")


if __name__ == "__main__":
    main()
