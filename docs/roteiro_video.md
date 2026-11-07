# Roteiro do vídeo de 7 minutos

| Tempo | Tema | Conteúdo |
|---|---|---|
| 0:00 a 0:40 | Problema de negócio | A base tem 99.224 avaliações e só 41% têm comentário. O gestor quer os motivos por trás das notas sem ler milhares de textos. |
| 0:40 a 1:30 | Arquitetura | Abra o diagrama do README. Mostre a preparação e a consulta, com uma frase por classe. Diga que tudo roda por API (OpenAI ou Gemini), sem modelo local. |
| 1:30 a 2:20 | Preparação da base | Explique a limpeza leve, o mascaramento de dados pessoais, o filtro de duas palavras e os metadados. Mostre a saída do comando `prepare` ou a Parte 3 do notebook de EDA. |
| 2:20 a 3:30 | Pipeline RAG | Use o notebook do pipeline. Mostre as frases de busca de uma pergunta de panorama, o funil da busca híbrida com o rerank, a divisão das vagas por subtema, o prompt e a validação das citações. |
| 3:30 a 5:15 | Demonstração | No Streamlit, pergunte sobre problemas de entrega, nota baixa, cama, mesa e banho e clientes de São Paulo. Abra a tabela de evidências e a aba "Como chegamos à resposta". Escolha um recorte na barra lateral que contradiga a pergunta e mostre o aviso. |
| 5:15 a 5:50 | Recusas | Rode a pergunta sobre previsão do tempo (barreira de escopo) e a de cashback em criptomoedas (barreira do rerank). |
| 5:50 a 6:30 | Avaliação | Abra `docs/avaliacao.md`: precisão@10 por estratégia de busca, acurácia de respostas e recusas no split test por configuração, fundamentação pelo juiz e custo por pergunta. |
| 6:30 a 7:00 | Desafios e decisões | A nota 1 ocupa 22% do índice e 11,5% da base, e por isso o panorama usa pandas. As vagas divididas por subtema impedem ordenar temas por frequência. O rerank por LLM substitui um cross-encoder local para manter a instalação leve. |
