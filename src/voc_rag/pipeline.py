"""Orquestrador do pipeline RAG de Voice of Customer.

Pergunta -> processamento (escopo, reescrita, filtros) -> recuperação híbrida
-> verificação de suficiência -> contexto -> LLM -> validação de citações.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from . import config
from .consulta import ConsultaProcessada, para_filtros, processar_pergunta
from .filtros import Filtros
from .geracao import RespostaVoC, gerar_resposta
from .recuperacao import Recuperador, estatisticas

MSG_FORA_ESCOPO = ("Esta pergunta está fora do escopo da base de conhecimento, que contém "
                   "apenas avaliações de clientes da Olist. Motivo: {motivo}")
MSG_SEM_EVIDENCIA = ("Não encontrei avaliações suficientemente relevantes para responder com "
                     "segurança ({n} evidência(s) acima do limiar; mínimo exigido: {minimo}). "
                     "Tente reformular a pergunta ou remover filtros.")
MSG_RECORTE = " Recorte usado: {filtros} ({n} avaliação(ões))."
MSG_SUBSTITUIDO = (" O filtro escolhido na barra lateral substituiu o identificado na pergunta "
                   "({campos}); verifique se ele combina com o que foi perguntado.")
MSG_SEM_LLM = (" Atenção: o LLM não está disponível (verifique a GOOGLE_API_KEY no .env). Sem ele, "
               "a pergunta não é reescrita e a busca fica limitada, o que pode causar esta recusa.")


@dataclass
class ResultadoPipeline:
    pergunta: str
    status: str                         # respondida | fora_do_escopo | evidencia_insuficiente | erro_llm
    mensagem: str = ""                  # texto para status diferentes de "respondida"
    consulta: Optional[ConsultaProcessada] = None
    origem_consulta: str = ""           # 'llm' ou 'regras'
    filtros: dict = field(default_factory=dict)
    evidencias: list = field(default_factory=list)
    estatisticas: dict = field(default_factory=dict)
    resposta: Optional[RespostaVoC] = None
    rastreio: dict = field(default_factory=dict)


class PipelineVoC:
    def __init__(self):
        self.recuperador = Recuperador()

    def responder(self, pergunta: str, filtros_manuais: Optional[Filtros] = None,
                  usar_filtros_automaticos: bool = True) -> ResultadoPipeline:
        t0 = time.perf_counter()
        pergunta = pergunta.strip()

        # 1) Processamento da pergunta (os filtros manuais entram como contexto)
        consulta, origem = processar_pergunta(pergunta, self.recuperador.categorias,
                                              filtros_manuais)
        res = ResultadoPipeline(pergunta=pergunta, status="respondida",
                                consulta=consulta, origem_consulta=origem)
        if not consulta.dentro_do_escopo:
            res.status = "fora_do_escopo"
            res.mensagem = MSG_FORA_ESCOPO.format(motivo=consulta.motivo_escopo)
            return res

        # 2) Filtros: os inferidos pelo LLM + os escolhidos manualmente (prioridade)
        automaticos = para_filtros(consulta, self.recuperador.categorias) \
            if usar_filtros_automaticos else Filtros()
        filtros = automaticos.mesclar(filtros_manuais) if filtros_manuais else automaticos
        substituidos = _substituidos(automaticos, filtros_manuais)
        res.filtros = filtros.descricao()

        # 3) Recuperação híbrida
        k = config.K_FINAL_PANORAMA if consulta.tipo == "panorama" else config.K_FINAL_ESPECIFICA
        rec = self.recuperador.recuperar(consulta.consultas_busca or [pergunta], filtros, k)
        res.evidencias, res.rastreio = rec.evidencias, rec.rastreio
        res.estatisticas = estatisticas(rec.evidencias)

        # 4) Suficiência das evidências: sem base, o LLM nem é chamado
        if len(rec.evidencias) < config.MIN_EVIDENCIAS:
            res.status = "evidencia_insuficiente"
            res.mensagem = rec.rastreio.get("motivo") or MSG_SEM_EVIDENCIA.format(
                n=len(rec.evidencias), minimo=config.MIN_EVIDENCIAS)
            n_recorte = rec.rastreio.get("avaliacoes_no_recorte")
            if n_recorte and not filtros.vazio():
                res.mensagem += MSG_RECORTE.format(filtros=_formatar(res.filtros),
                                                   n=f"{n_recorte:,}".replace(",", "."))
            if substituidos:
                res.mensagem += MSG_SUBSTITUIDO.format(campos="; ".join(substituidos))
            if origem == "regras":
                res.mensagem += MSG_SEM_LLM
            return res

        # 5) Geração com citações validadas
        try:
            t1 = time.perf_counter()
            res.resposta = gerar_resposta(pergunta, rec.evidencias, res.filtros, res.estatisticas)
            res.rastreio["tempo_geracao_s"] = round(time.perf_counter() - t1, 2)
        except Exception as erro:
            res.status = "erro_llm"
            res.mensagem = (f"O modelo de linguagem não respondeu ({type(erro).__name__}: "
                            f"{str(erro)[:150]}). As evidências recuperadas estão listadas abaixo.")
            return res
        if not res.resposta.evidencias_suficientes:
            res.status = "evidencia_insuficiente"
            res.mensagem = res.resposta.resumo
        res.rastreio["tempo_total_s"] = round(time.perf_counter() - t0, 2)
        return res


def _substituidos(automaticos: Filtros, manuais: Optional[Filtros]) -> list:
    """Campos em que o filtro manual trocou um valor diferente identificado na pergunta."""
    if not manuais:
        return []
    auto, manual = automaticos.descricao(), manuais.descricao()
    return [f"{campo}: {_valor(auto[campo])} -> {_valor(manual[campo])}"
            for campo in manual if campo in auto and auto[campo] != manual[campo]]


def _valor(valor) -> str:
    return ", ".join(map(str, valor)) if isinstance(valor, list) else str(valor)


def _formatar(filtros: dict) -> str:
    """{'sentimentos': ['positivo'], 'estados': ['AC']} -> 'sentimentos: positivo; estados: AC'."""
    return "; ".join(f"{campo}: {_valor(valor)}" for campo, valor in filtros.items())
