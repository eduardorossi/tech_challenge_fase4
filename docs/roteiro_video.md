# Roteiro sugerido para o vídeo (até 5 min)

| Tempo | Bloco | O que mostrar |
|---|---|---|
| 0:00–0:30 | Problema de negócio | Milhares de avaliações e gestores sem visão rápida de problemas e elogios; um LLM sozinho responderia com conhecimento genérico, não com o que estes clientes escreveram |
| 0:30–1:05 | Arquitetura | Diagrama da seção 2 do README: preparação (uma vez) e consulta (a cada pergunta, 7 etapas) |
| 1:05–1:40 | Base de conhecimento | 99.224 avaliações, 41.951 com texto; limpeza mínima e dados pessoais mascarados; 1 avaliação = 1 documento, sem chunking; metadados de nota, categoria e entrega |
| 1:40–2:30 | Estratégia RAG | Reescrita em subconsultas (score do reranker −1,6 na pergunta original contra +6,0 na subconsulta); busca híbrida + reranker (precisão@10 de 0,81 para 0,93); limiar e mínimo de 3 evidências; citações validadas no código |
| 2:30–4:15 | Demonstração (Streamlit) | 1) "Quais são os principais problemas relatados pelos clientes?": resposta com insights e [E#], aba Evidências e aba Rastreamento. 2) "Qual foi o faturamento da Olist em 2018?": fora do escopo. 3) "O que os clientes dizem sobre as entregas feitas por drone?": evidência insuficiente |
| 4:15–5:00 | Resultados e limitações | Recusas 11/11; LLM-juiz com 19 de 22 insights sustentados e 3 parciais; frequência nas evidências não é frequência na base; próximos passos |

Dicas para caber no tempo:

- Mire em 4:45 de gravação, para ter margem.
- Deixe o Streamlit aberto e já carregado antes de gravar. O carregamento inicial dos modelos
  leva uns 10 a 30 segundos, e cada pergunta, de 10 a 30 segundos.
- Corte a espera das respostas na edição, ou faça as três perguntas antes e mostre os
  resultados já prontos, em abas separadas do navegador.
- Se precisar cortar algo, tire o detalhe da aba Rastreamento na demonstração: a aba
  Evidências já mostra a rastreabilidade.
