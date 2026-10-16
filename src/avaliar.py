"""Avaliação da solução em três frentes.

A) Recuperação (sem LLM): compara estratégias — vetorial, BM25, híbrida (RRF) e
   híbrida + reranker — pela precisão@10 em temas com rótulo aproximado por regex.
   A2) Reescrita (sem LLM): score do reranker para a pergunta original, palavras-chave
   e subconsultas reescritas.
B) Abstenção (pipeline completo): o sistema responde perguntas no escopo e recusa
   perguntas fora do escopo ou sem evidências na base?
C) Fundamentação (LLM como juiz, opcional --juiz): cada insight é sustentado pelas
   avaliações que ele cita?

Uso:
    python src/avaliar.py              # A + B
    python src/avaliar.py --juiz       # A + B + C
    python src/avaliar.py --so-recuperacao
"""
import argparse
import json
import re
import sys
from typing import List, Literal

import numpy as np
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from voc_rag import config
from voc_rag.consulta import processar_por_regras
from voc_rag.filtros import Filtros
from voc_rag.llm import criar_llm, nome_modelo
from voc_rag.pipeline import PipelineVoC
from voc_rag.recuperacao import rrf

# --- A) Temas para avaliar a recuperação --------------------------------------
# Rótulo de relevância aproximado: a avaliação é relevante se o texto casa com a regex do tema.
# É um proxy (não um gabarito humano), suficiente para comparar estratégias entre si.
TEMAS = [
    ("Clientes reclamam de atraso na entrega?",
     r"atras|demor|prazo|ainda n[aã]o (cheg|receb)|n[aã]o (cheg|receb)"),
    ("Há relatos de produtos com defeito ou quebrados?",
     r"defeit|quebr|danific|estrag|n[aã]o funcion|parou de funcionar|trinc|amassad"),
    ("Clientes receberam produto diferente do anunciado?",
     r"diferente|errad|outro produto|n[aã]o ([eé]|era) o (que|mesmo)|n[aã]o correspond|trocad"),
    ("Os pedidos chegaram incompletos, faltando itens?",
     r"falt|incomplet|metade|s[oó] (veio|chegou|recebi)|apenas (um|uma|1)|n[aã]o veio"),
    ("Como os clientes avaliam o atendimento e a comunicação com a loja?",
     r"atend|contato|respond|retorno|suporte|sac|e-?mail|comunica"),
    ("Clientes pediram devolução ou reembolso?",
     r"devol|reembols|estorn|dinheiro de volta|cancel"),
    ("O que dizem sobre a embalagem dos produtos?",
     r"embala|caixa|embrulh|protegid|lacrad"),
    ("Clientes elogiam a rapidez da entrega?",
     r"r[aá]pid|antes do prazo|antes da data|cedo|super ?r[aá]pid|chegou logo"),
]

# --- A2) Efeito da reescrita da pergunta no reranker ----------------------------
# Mesma intenção ("principais problemas") formulada de quatro jeitos. Todas usam o recorte
# de sentimento negativo, que é o filtro que o pipeline aplica a essa pergunta.
FORMULACOES = [
    ("pergunta original", "Quais são os principais problemas relatados pelos clientes?"),
    ("palavras-chave", "problemas insatisfação defeito atraso reclamação"),
    ("subconsulta reescrita", "o produto chegou atrasado"),
    ("subconsulta reescrita", "o produto veio com defeito ou quebrado"),
]

# --- B) Perguntas para avaliar abstenção ----------------------------------------
PERGUNTAS_ESCOPO = [
    ("Quais são os principais problemas relatados pelos clientes?", "responder"),
    ("O que os clientes relatam sobre problemas relacionados à entrega?", "responder"),
    ("Quais aspectos da experiência de compra são mais elogiados pelos clientes?", "responder"),
    ("Quais padrões podem ser identificados nas avaliações de clientes insatisfeitos?", "responder"),
    ("Existem padrões recorrentes nas avaliações relacionadas à qualidade dos produtos?", "responder"),
    ("Qual é a capital da França?", "recusar"),
    ("Qual foi o faturamento da Olist em 2018?", "recusar"),
    ("Me passe uma receita de bolo de cenoura.", "recusar"),
    ("O que os clientes dizem sobre as entregas feitas por drone?", "recusar"),
    ("Quais reclamações existem sobre pagamento com criptomoedas?", "recusar"),
    ("O que os clientes acham do programa de milhas aéreas da loja?", "recusar"),
]


def precisao(textos: list, regex: str, k: int = 10) -> float:
    textos = textos[:k]
    return sum(bool(re.search(regex, t.lower())) for t in textos) / max(len(textos), 1)


def avaliar_recuperacao(pipeline: PipelineVoC) -> dict:
    rec = pipeline.recuperador
    filtros = Filtros()
    mascara = filtros.para_mascara(rec.df)
    texto = lambda ids: [rec.df["texto"].iat[rec.posicao[i]] for i in ids]
    resultados = {"vetorial": [], "bm25": [], "hibrida_rrf": [], "hibrida_rrf_rerank": []}

    print("\nA) RECUPERAÇÃO — precisão@10 por tema (rótulo aproximado por regex)")
    print(f"{'tema':55s} {'vet':>5s} {'bm25':>5s} {'rrf':>5s} {'rrf+rr':>6s}")
    for pergunta, regex in TEMAS:
        ids_vet = rec.busca_vetorial(pergunta, mascara, config.N_CANDIDATOS_VETORIAL)
        ids_bm = rec.busca_bm25(pergunta, mascara, config.N_CANDIDATOS_BM25)
        ids_rrf = [d for d, _ in rrf([ids_vet, ids_bm])][: config.N_PARA_RERANK]
        scores = rec.reranker.predict([(pergunta, t) for t in texto(ids_rrf)],
                                      show_progress_bar=False)
        ids_rr = [ids_rrf[i] for i in np.argsort(-scores)]
        linha = {
            "vetorial": precisao(texto(ids_vet), regex),
            "bm25": precisao(texto(ids_bm), regex),
            "hibrida_rrf": precisao(texto(ids_rrf), regex),
            "hibrida_rrf_rerank": precisao(texto(ids_rr), regex),
        }
        for chave, valor in linha.items():
            resultados[chave].append(valor)
        print(f"{pergunta[:55]:55s} " + " ".join(f"{v:5.2f}" for v in linha.values()))
    medias = {k: round(float(np.mean(v)), 3) for k, v in resultados.items()}
    print(f"{'MÉDIA':55s} " + " ".join(f"{v:5.2f}" for v in medias.values()))
    return medias


def avaliar_reescrita(pipeline: PipelineVoC) -> list:
    """Melhor score do reranker e candidatos acima do limiar para cada formulação."""
    rec = pipeline.recuperador
    mascara = Filtros(sentimentos=["negativo"]).para_mascara(rec.df)
    n_universo = int(mascara.sum())
    resultados = []

    print(f"\nA2) REESCRITA — score do reranker por formulação "
          f"({config.N_PARA_RERANK} candidatas, recorte negativo com {n_universo:,} avaliações)")
    print(f"{'formulação':24s} {'melhor':>7s} {'acima':>6s}  consulta")
    for tipo, consulta in FORMULACOES:
        candidatos = rec.candidatos_reranqueados(consulta, mascara, n_universo, config.N_PARA_RERANK)
        melhor = round(candidatos[0].score_rerank, 2) if candidatos else None
        acima = sum(e.score_rerank >= config.LIMIAR_RERANK for e in candidatos)
        resultados.append({"tipo": tipo, "consulta": consulta, "candidatos": len(candidatos),
                           "melhor_score_rerank": melhor, "acima_do_limiar": acima})
        print(f"{tipo:24s} {melhor:7.2f} {acima:6d}  {consulta}")
    return resultados


class Veredito(BaseModel):
    suportado: Literal["sim", "parcial", "nao"]
    justificativa: str


class Vereditos(BaseModel):
    vereditos: List[Veredito]


JUIZ = """Você é um auditor de respostas de sistemas RAG. Para cada insight, verifique se as
avaliações citadas sustentam o que o insight afirma. 'sim' = totalmente sustentado;
'parcial' = parte da afirmação não aparece nas avaliações; 'nao' = não sustentado.
Devolva um veredito por insight, na mesma ordem."""


def julgar(res) -> list:
    blocos = []
    for n, ins in enumerate(res.resposta.insights, 1):
        citadas = "\n".join(f"  {ref}: {res.evidencias[int(ref[1:]) - 1].texto}"
                            for ref in ins.evidencias)
        blocos.append(f"Insight {n}: {ins.titulo} — {ins.descricao}\nAvaliações citadas:\n{citadas}")
    prompt = ChatPromptTemplate.from_messages([("system", JUIZ), ("human", "{insights}")])
    saida = (prompt | criar_llm().with_structured_output(Vereditos)).invoke(
        {"insights": "\n\n".join(blocos)})
    return [v.suportado for v in saida.vereditos]


def avaliar_abstencao(pipeline: PipelineVoC, usar_juiz: bool) -> dict:
    print("\nB) ABSTENÇÃO — o sistema responde quando deve e recusa quando deve?")
    acertos, vereditos, detalhes = 0, [], []
    for pergunta, esperado in PERGUNTAS_ESCOPO:
        res = pipeline.responder(pergunta)
        obtido = "responder" if res.status == "respondida" else "recusar"
        acertos += obtido == esperado
        info = {"pergunta": pergunta, "esperado": esperado, "status": res.status,
                "evidencias": len(res.evidencias),
                "melhor_rerank": res.rastreio.get("melhor_score_rerank")}
        if usar_juiz and res.status == "respondida" and res.resposta.insights:
            info["juiz"] = julgar(res)
            vereditos += info["juiz"]
        detalhes.append(info)
        marca = "OK  " if obtido == esperado else "ERRO"
        print(f"  [{marca}] esperado={esperado:9s} status={res.status:22s} "
              f"rerank_max={info['melhor_rerank']}  {pergunta[:60]}")
    saida = {"acuracia_abstencao": round(acertos / len(PERGUNTAS_ESCOPO), 3), "detalhes": detalhes}
    print(f"  Acurácia: {acertos}/{len(PERGUNTAS_ESCOPO)}")

    # B2) Barreira de evidência isolada: sem o filtro de escopo do LLM, o limiar do reranker
    #     sozinho também recusaria? (pergunta usada como consulta, sem reescrita)
    print("\nB2) BARREIRA DO LIMIAR (sem LLM): evidências acima do limiar por pergunta")
    acertos_limiar = 0
    for pergunta, esperado in PERGUNTAS_ESCOPO:
        consulta = processar_por_regras(pergunta)
        rec = pipeline.recuperador.recuperar(consulta.consultas_busca, Filtros(), 10)
        obtido = "responder" if len(rec.evidencias) >= config.MIN_EVIDENCIAS else "recusar"
        acertos_limiar += obtido == esperado
        print(f"  [{'OK  ' if obtido == esperado else 'ERRO'}] esperado={esperado:9s} "
              f"evidencias={len(rec.evidencias):2d}  {pergunta[:60]}")
    saida["acuracia_barreira_limiar"] = round(acertos_limiar / len(PERGUNTAS_ESCOPO), 3)
    print(f"  Acurácia só com o limiar: {acertos_limiar}/{len(PERGUNTAS_ESCOPO)}")
    if vereditos:
        saida["fundamentacao"] = {v: vereditos.count(v) for v in ("sim", "parcial", "nao")}
        print(f"\nC) FUNDAMENTAÇÃO (LLM-juiz) por insight: {saida['fundamentacao']}")
    return saida


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--juiz", action="store_true", help="avaliar fundamentação com LLM-juiz")
    parser.add_argument("--so-recuperacao", action="store_true", help="somente a parte A (sem LLM)")
    args = parser.parse_args()

    pipeline = PipelineVoC()
    relatorio = {"recuperacao_precisao@10": avaliar_recuperacao(pipeline),
                 "reescrita": avaliar_reescrita(pipeline)}
    if not args.so_recuperacao:
        relatorio["llm"] = f"{config.LLM_PROVIDER}: {nome_modelo()}"
        print(f"\nLLM usado nas partes B e C: {relatorio['llm']}")
        relatorio["abstencao"] = avaliar_abstencao(pipeline, args.juiz)
    destino = config.PASTA_ARTEFATOS / "avaliacao.json"
    destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRelatório salvo em {destino}")


if __name__ == "__main__":
    main()
