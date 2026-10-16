"""Interface de linha de comando.

Uso:
    python src/perguntar.py "Quais são os principais problemas relatados pelos clientes?"
    python src/perguntar.py            # modo interativo
"""
import sys

from voc_rag.pipeline import PipelineVoC, ResultadoPipeline


def imprimir(res: ResultadoPipeline) -> None:
    print("\n" + "=" * 80)
    print(f"PERGUNTA: {res.pergunta}")
    if res.consulta:
        c = res.consulta
        print(f"\n[1] Processamento ({res.origem_consulta}): tipo={c.tipo} | escopo={c.dentro_do_escopo}")
        print(f"    consultas de busca: {c.consultas_busca}")
        print(f"    filtros:            {res.filtros or 'nenhum'}")
    if res.rastreio:
        geral = {k: v for k, v in res.rastreio.items() if k != "subconsultas"}
        print(f"\n[2] Recuperação: {geral}")
        for d in res.rastreio.get("subconsultas", []):
            print(f"    - {d}")

    if res.status != "respondida":
        print(f"\n>>> {res.status.upper()}: {res.mensagem}")
    else:
        r = res.resposta
        print(f"\n[3] RESPOSTA (confiança: {r.confianca})\n{r.resumo}\n")
        for ins in r.insights:
            print(f"  • {ins.titulo} [{', '.join(ins.evidencias)}]\n    {ins.descricao}")
        print(f"\n  Limitações: {r.limitacoes}")

    if res.evidencias:
        print("\n[4] EVIDÊNCIAS")
        for i, e in enumerate(res.evidencias, 1):
            m = e.metadados
            print(f"  [E{i}] (rerank {e.score_rerank:+.2f}) nota {m['nota']} | {m['categoria']} | "
                  f"{m['status_entrega']} | review_id={e.review_id}\n        \"{e.texto}\"")


def main():
    pipeline = PipelineVoC()
    if len(sys.argv) > 1:
        imprimir(pipeline.responder(" ".join(sys.argv[1:])))
        return
    while True:
        pergunta = input("\nPergunta (Enter para sair): ").strip()
        if not pergunta:
            break
        imprimir(pipeline.responder(pergunta))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
