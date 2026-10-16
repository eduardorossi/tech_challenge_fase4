# Voice of Customer Intelligence: RAG sobre avaliações da Olist

Tech Challenge da Fase 4 (Deep Learning & NLP), FIAP Pós-Tech AI Scientist.

Este projeto usa Retrieval-Augmented Generation (RAG) para transformar cerca de 42 mil
comentários de clientes do Brazilian E-Commerce Public Dataset by Olist em uma base de
conhecimento que pode ser consultada em linguagem natural. O gestor pergunta, por exemplo,
"Quais são os principais problemas relatados?" e recebe uma resposta montada a partir de
avaliações reais, com a indicação de quais avaliações sustentam cada conclusão. Se a base não
tiver informação suficiente, o sistema diz isso em vez de inventar uma resposta.

## Sumário
1. [Problema de negócio](#1-problema-de-negócio)
2. [Arquitetura](#2-arquitetura)
3. [Tecnologias](#3-tecnologias)
4. [Instalação e execução](#4-instalação-e-execução)
5. [Construção da base de conhecimento](#5-construção-da-base-de-conhecimento)
6. [Pipeline RAG](#6-pipeline-rag)
7. [Respostas fundamentadas e rastreabilidade](#7-respostas-fundamentadas-e-rastreabilidade)
8. [Perguntas sem evidências suficientes](#8-perguntas-sem-evidências-suficientes)
9. [Metadados (desafio adicional)](#9-metadados-desafio-adicional)
10. [Avaliação](#10-avaliação)
11. [Exemplos de perguntas e respostas](#11-exemplos-de-perguntas-e-respostas)
12. [Decisões técnicas e desafios](#12-decisões-técnicas-e-desafios)
13. [Limitações e próximos passos](#13-limitações-e-próximos-passos)

## 1. Problema de negócio

A empresa acumula milhares de avaliações, mas os gestores não conseguem extrair delas, com
rapidez, quais são os problemas, os elogios e os padrões mais comuns. Ler os comentários um a um
não escala. Perguntar direto a um LLM também não resolve, porque ele responderia com
conhecimento genérico sobre e-commerce, e não com o que estes clientes escreveram.

Com RAG, o sistema primeiro busca as avaliações relacionadas à pergunta e só então pede ao
modelo que responda, usando apenas essas avaliações como base.

## 2. Arquitetura

A solução tem duas partes. A preparação roda uma vez e gera os arquivos da base; a consulta
roda a cada pergunta.

```
PREPARACAO (uma vez)

  CSVs Olist -> preparacao.py -> documentos.parquet -> indexacao.py -> indice_faiss.bin
                (selecao, limpeza,  (1 avaliacao =      (embeddings E5)   (FAISS)
                 metadados)          1 documento)

CONSULTA (a cada pergunta)

  Pergunta
    |
  [1] LLM processa a pergunta: escopo, tipo, subconsultas, filtros
    |      fora do escopo? -> recusa
  [2] filtros de metadados definem o recorte da base
    |
  [3] para cada subconsulta: busca vetorial + BM25 -> RRF -> reranker -> limiar
    |
  [4] selecao das evidencias (cota por subtema + MMR)
    |      menos de 3 evidencias? -> recusa
  [5] montagem do contexto com as evidencias numeradas [E1], [E2]...
    |
  [6] LLM gera a resposta citando as evidencias
    |
  [7] validacao das citacoes no codigo
    |      nenhum insight com citacao valida? -> recusa
  Resposta + evidencias
```

Organização do repositório:

```
voice_customer_intelligence/
  src/
    voc_rag/             núcleo da solução (pacote Python)
      config.py          caminhos, modelos e parâmetros
      preparacao.py      seleção, limpeza, valores ausentes e metadados
      indexacao.py       embeddings e índice FAISS
      filtros.py         filtros de metadados
      consulta.py        processamento da pergunta
      recuperacao.py     busca híbrida, reranking, limiar e MMR
      geracao.py         contexto, prompt e validação das citações
      llm.py             criação do LLM (Gemini ou OpenAI)
      pipeline.py        orquestra as etapas
    app.py               interface web (Streamlit)
    perguntar.py         interface de linha de comando
    avaliar.py           avaliação da solução
    gerar_exemplos.py    gera docs/exemplos.md
  data/                  CSVs da Olist (não versionados)
  artefatos/             base e índice gerados (não versionados)
  docs/                  exemplos e roteiro do vídeo
  pyproject.toml         declara o pacote voc_rag
  requirements.txt
  .env.example           modelo das variáveis de ambiente (versionado)
  .env                   variáveis locais, como a chave da API (não versionado)
```

## 3. Tecnologias

- Python 3.12, com pandas para juntar os CSVs e Parquet para guardar a base preparada.
- Embeddings: `intfloat/multilingual-e5-small`. Escolhemos esse modelo porque ele foi treinado
  para busca do tipo "pergunta curta encontra o trecho que responde", funciona bem em português,
  roda em CPU e não tem custo. Modelos de paráfrase, como o MiniLM, são pensados para comparar
  frases parecidas entre si, o que é outro problema.
- Índice vetorial: FAISS (`IndexFlatIP`). Com 42 mil vetores de 384 dimensões (uns 60 MB), a
  busca exata leva milissegundos, então não compensa usar um índice aproximado e perder
  resultados. O filtro por metadados usa `IDSelectorBatch`.
- Busca lexical: BM25 (`rank_bm25`), algoritmo clássico de busca por palavras, que pontua cada
  avaliação pela frequência dos termos da consulta. Serve para termos exatos como "nota fiscal" ou "correios".
- Fusão dos rankings: Reciprocal Rank Fusion (RRF), que combina as duas listas pela posição e
  dispensa normalizar os scores.
- Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, treinado no mMARCO (que inclui
  português). Ele lê a consulta e a avaliação juntas, por isso é mais preciso que a busca
  vetorial, e o score dele também serve de limiar de relevância.
- LLM: Google Gemini via LangChain (`langchain-google-genai`), com saída estruturada em
  Pydantic (`with_structured_output`). É possível trocar para OpenAI pelo `.env`. O código pede
  temperatura 0, mas os modelos Gemini 3.x usam parâmetros de amostragem fixos e ignoram esse
  valor (a biblioteca avisa isso no terminal); a temperatura só tem efeito em modelos que a
  aceitam, como os da OpenAI.
- Interface: Streamlit, além de uma versão em linha de comando.

## 4. Instalação e execução

Pré-requisitos: Python 3.12, os CSVs da Olist na pasta `data/` do projeto (ou em outro caminho
informado em `VOC_PASTA_DADOS` no `.env`) e uma chave de API do Gemini ou da OpenAI (veja
[Chave de API do LLM](#chave-de-api-do-llm)).

### Dados

Os dados não estão no repositório. Baixe o Brazilian E-Commerce Public Dataset by Olist no
Kaggle (https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce; é preciso ter uma conta
gratuita), descompacte e coloque na pasta `data/` os cinco arquivos usados pelo projeto:

- `olist_order_reviews_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `olist_customers_dataset.csv`

O pacote tem outros quatro arquivos, que podem ficar na pasta, mas não são lidos. O projeto
consulta os comentários dos clientes, e os metadados servem só para filtrar e contextualizar
essas avaliações, então ficaram de fora as tabelas que não acrescentavam nada a isso:

| Arquivo | Conteúdo | Por que não foi usado |
|---|---|---|
| `olist_geolocation_dataset.csv` | latitude e longitude por prefixo de CEP | a UF do cliente, que já vem em `olist_customers_dataset.csv`, basta para o filtro geográfico |
| `olist_order_payments_dataset.csv` | forma de pagamento, parcelas e valor pago | nenhum filtro ou análise do projeto depende do pagamento; o valor dos itens já vem de `olist_order_items_dataset.csv` |
| `olist_sellers_dataset.csv` | cidade e UF de cada vendedor | o projeto analisa a experiência do cliente, sem recorte por vendedor |
| `product_category_name_translation.csv` | nome das categorias em inglês | a base e a interface usam os nomes em português |

Pagamento e vendedor poderiam virar filtros numa versão futura (por exemplo, problemas
relatados por região do vendedor). O dataset é publicado pela Olist sob a licença CC BY-NC-SA
4.0.

### Ambiente

Sistemas suportados: Windows (x64), Linux (x64 ou ARM) e macOS com Apple Silicon (M1 ou mais
novo). Macs com processador Intel não são suportados, porque o PyTorch 2.5.1 não tem versão
para eles. O `requirements.txt` escolhe sozinho a versão do PyTorch adequada a cada sistema.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Se o PowerShell bloquear a ativação do ambiente, rode antes
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. No Prompt de Comando (cmd), a ativação é
`.venv\Scripts\activate.bat`.

Linux e macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Em todos os casos, depois edite o `.env` e preencha a chave de API do provedor escolhido (veja
abaixo). O `pip install -e .` instala o pacote `voc_rag` em modo editável, para que os scripts o
encontrem de qualquer pasta.

O ambiente virtual guarda caminhos absolutos: o `pip install -e .` grava o caminho da pasta
`src/`, e os executáveis em `.venv/Scripts` (como `streamlit.exe`) gravam o caminho do Python do
`.venv`. Se a pasta do projeto for movida ou renomeada depois da instalação, apague o `.venv` e
refaça os passos acima. O sintoma é um erro ao rodar `streamlit`, como
`failed to canonicalize script path`, ou `ModuleNotFoundError: No module named 'voc_rag'`.

### Chave de API do LLM

O projeto funciona com Gemini (padrão) ou OpenAI. Basta uma das duas chaves.

Gemini (Google AI Studio, tem cota gratuita):

1. Acesse https://aistudio.google.com/apikey e entre com uma conta Google.
2. Clique em "Create API key" e copie a chave gerada.
3. No `.env`, preencha `GOOGLE_API_KEY`.

OpenAI (pago por uso, exige créditos na conta):

1. Acesse https://platform.openai.com/api-keys e entre com sua conta.
2. Clique em "Create new secret key" e copie a chave (ela só é exibida uma vez).
3. Instale a integração: `pip install langchain-openai`.
4. No `.env`, descomente e preencha `LLM_PROVIDER=openai` e `OPENAI_API_KEY`.

O modelo de cada provedor é definido em `GEMINI_CHAT_MODEL` e `OPENAI_CHAT_MODEL`. Os
provedores retiram modelos antigos com o tempo; se aparecer um erro de modelo não encontrado
(404), troque o nome por um modelo disponível na documentação do provedor.

A chave fica só no `.env`, que não é versionado. Não coloque a chave no código nem no
`.env.example`.

Os comandos a seguir são iguais em todos os sistemas, com o ambiente virtual ativado.

Para construir a base (só uma vez; os embeddings levam uns 10 minutos em CPU):

```bash
python -m voc_rag.preparacao     # gera artefatos/documentos.parquet
python -m voc_rag.indexacao      # gera artefatos/indice_faiss.bin
```

Para usar:

```bash
streamlit run src/app.py                                              # interface web
python src/perguntar.py "O que os clientes relatam sobre a entrega?"  # linha de comando
python src/avaliar.py --juiz                                          # avaliação completa
python src/gerar_exemplos.py                                          # regenera docs/exemplos.md
```

Na primeira execução, os modelos de embeddings e de reranking (cerca de 940 MB) são baixados do
Hugging Face e ficam no cache do usuário: `~/.cache/huggingface/hub` no Linux e no macOS, e
`C:\Users\<usuário>\.cache\huggingface\hub` no Windows. O local pode ser alterado com a
variável `HF_HOME`.

### Limpeza / desinstalação

Nada do que o projeto gera é removido automaticamente. São três lugares:

- `.venv/`, o ambiente virtual (uns 2 GB): basta apagar a pasta.
- `artefatos/`, a base e o índice gerados (uns 70 MB): pode apagar e recriar com
  `preparacao` e `indexacao`.
- o cache do Hugging Face com os modelos (uns 940 MB), que fica fora do projeto.

O cache do Hugging Face não expira e continua lá mesmo depois de apagar o projeto ou o `.venv`,
porque é compartilhado entre projetos para evitar downloads repetidos. Para liberar espaço:

```bash
# Ver o que está no cache e quanto ocupa
hf cache scan

# Remover interativamente (menu de seleção; requer: pip install InquirerPy)
hf cache delete

# Sem menu: abre um arquivo de texto para marcar o que apagar (não requer InquirerPy)
hf cache delete --disable-tui
```

Os comandos antigos `huggingface-cli scan-cache` e `delete-cache` ainda funcionam, mas estão
depreciados em favor da CLI `hf`. Também dá para apagar diretamente as pastas dos dois modelos.

Windows (PowerShell):

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--intfloat--multilingual-e5-small"
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1"
```

Linux e macOS:

```bash
rm -rf ~/.cache/huggingface/hub/models--intfloat--multilingual-e5-small
rm -rf ~/.cache/huggingface/hub/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1
```

Se forem apagados, os modelos são baixados de novo na próxima execução (precisa de internet).

## 5. Construção da base de conhecimento

### Seleção dos dados

Código: `src/voc_rag/preparacao.py`

A fonte principal é `olist_order_reviews_dataset.csv`, com 99.224 avaliações. As demais tabelas
(pedidos, clientes, itens e produtos) servem apenas para enriquecer cada avaliação com
metadados.

Só entram na base as avaliações que têm algum texto, já que sem texto não há o que buscar. No
CSV, quase 60% das avaliações não têm mensagem. Quando há só o título (por exemplo, "Entrega pela
metade"), a avaliação é aproveitada. O caminho até a base final:

| Etapa | Avaliações |
|---|---|
| CSV original | 99.224 |
| Depois de remover `review_id` duplicados | 98.410 |
| Sem título e sem mensagem (removidas) | 56.040 |
| Texto sem conteúdo útil, com menos de 3 letras (removidas) | 419 |
| Documentos na base | 41.951 |

Sobre as duplicatas: 789 `review_id` aparecem ligados a 2 ou 3 pedidos (814 linhas a mais), e
em todos os casos a nota e o texto são iguais. Mantivemos uma ocorrência de cada para não contar a
mesma avaliação mais de uma vez.

### Limpeza e preparação dos textos

Código: `src/voc_rag/preparacao.py` e `src/voc_rag/recuperacao.py`

A limpeza foi mínima, de propósito. Os passos aplicados:

- normalização Unicode NFC (que padroniza letras acentuadas em uma única forma de codificação),
  porque a palavra "Ótimo" aparecia com duas codificações diferentes;
- quebras de linha e tabs viram espaço, e espaços repetidos são reduzidos a um;
- pontuação repetida é encurtada ("!!!!!!" vira "!!!"), sem perder a ênfase do cliente;
- e-mails, telefones, CPFs e URLs são mascarados (LGPD), para que dados pessoais não cheguem aos
  embeddings nem ao LLM;
- textos com menos de 3 letras, como ".", "1" ou "ok", são descartados.

Acentos, maiúsculas e stopwords foram mantidos. O modelo de embeddings foi treinado com texto
natural, e tirar uma stopword como "não" inverteria o sentido de "não chegou".

O BM25 usa uma tokenização própria: tudo em minúsculas, sem acentos, sem stopwords e com um
stemming simples, que corta as palavras em 5 letras (entrega, entregue e entregaram viram
`entre`).

### Valores ausentes

Código: `src/voc_rag/preparacao.py`

- Título ou mensagem nulos viram texto vazio. O texto final junta título e mensagem, e o título
  é omitido quando já aparece dentro da mensagem. A grande maioria das avaliações não tem título.
- Pedido sem data de entrega recebe `status_entrega = nao_entregue`.
- Produto sem categoria recebe "sem categoria"; cliente sem estado (UF) recebe "ND".
- Campos numéricos ausentes, como dias de atraso, recebem o valor -999.

### Organização dos documentos

Código: `src/voc_rag/preparacao.py`

Cada avaliação é um documento, sem divisão em pedaços (chunking). As mensagens têm no máximo
208 caracteres (229 com o título), e metade dos textos tem até 54, então cada um já é uma
unidade completa de sentido.

Junto com o texto, cada documento guarda: `review_id`, `order_id`, nota, sentimento (nota 1-2
negativo, 3 neutro, 4-5 positivo), categoria do produto (a do item mais caro do pedido),
situação da entrega (`no_prazo`, `atrasado` ou `nao_entregue`), dias de atraso, tempo de entrega,
UF, mês da compra e data da avaliação.

### Embeddings

Código: `src/voc_rag/indexacao.py`

O E5 espera um prefixo em cada texto: `"passage: "` nos documentos e `"query: "` nas consultas.
Os vetores são normalizados, assim o produto interno é igual à similaridade de cosseno. Somente o
texto da avaliação é vetorizado; os metadados ficam de fora para não pesarem demais em textos tão
curtos e são usados como filtros.

### Armazenamento e indexação

Código: `src/voc_rag/indexacao.py` e `src/voc_rag/recuperacao.py`

- `artefatos/documentos.parquet` guarda os textos e os metadados.
- `artefatos/indice_faiss.bin` guarda os vetores. O id de cada vetor é a posição da avaliação no
  Parquet, o que liga as duas partes.
- O índice BM25 é montado em memória quando a aplicação inicia, em poucos segundos.

## 6. Pipeline RAG

### 6.1 Transformação da pergunta

Código: `src/voc_rag/consulta.py`

O LLM recebe a pergunta e devolve um objeto Pydantic como este:

```json
{
  "dentro_do_escopo": true,
  "tipo": "panorama",
  "consultas_busca": ["o produto veio com defeito e estragado",
                      "a entrega atrasou muito e não chegou no prazo",
                      "recebi o produto errado ou incompleto",
                      "o atendimento foi ruim e não tive suporte",
                      "produto de péssima qualidade e propaganda enganosa"],
  "sentimentos": ["negativo"]
}
```

Nessa etapa acontecem três coisas.

Primeiro, a verificação de escopo: perguntas que não têm relação com a experiência dos clientes
são recusadas antes de qualquer busca.

Segundo, a reescrita da pergunta em subconsultas (multi-query). A pergunta do gestor não é usada
diretamente na busca. O LLM a transforma em frases concretas, do jeito que um cliente escreveria
na avaliação: de 4 a 6 subtemas para perguntas de panorama e 1 ou 2 frases para perguntas
específicas. Cada subconsulta é buscada e reranqueada separadamente.

O motivo é o funcionamento do reranker. Ele foi treinado para comparar uma busca com o trecho
que a responde, e uma pergunta abstrata sobre "problemas" não se parece com nenhuma avaliação.
A tabela mostra o score da avaliação mais relevante encontrada para cada formulação (60
candidatas por consulta, dentro do recorte de avaliações negativas, com 10.836 avaliações) e
quantas ficaram acima do limiar de relevância (score >= 0). Os números vêm da parte A2 de
`python src/avaliar.py --so-recuperacao`:

| Consulta usada na busca | Melhor score | Acima do limiar |
|---|---|---|
| Pergunta original, sem reescrita: "Quais são os principais problemas relatados pelos clientes?" | -1,6 | 0 |
| Palavras-chave da pergunta: "problemas insatisfação defeito atraso reclamação" | -2,8 | 0 |
| Subconsulta reescrita: "o produto chegou atrasado" | +6,0 | 33 |
| Subconsulta reescrita: "o produto veio com defeito ou quebrado" | +6,1 | 37 |

Um score negativo quer dizer que nem a melhor avaliação encontrada foi considerada relevante. Sem
a reescrita, essa pergunta seria recusada por falta de evidências, mesmo havendo milhares de
reclamações na base.

Terceiro, a identificação de filtros implícitos. "Clientes insatisfeitos" vira
`sentimentos=["negativo"]`; "categoria cama mesa banho" vira `categorias=[...]`, conferida contra
as categorias que existem na base por aproximação de texto.

Se o LLM não estiver disponível, um conjunto de regras simples faz esse papel para o pipeline
continuar funcionando.

### 6.2 Recuperação

Código: `src/voc_rag/recuperacao.py`

Para cada subconsulta, já dentro do recorte definido pelos filtros:

1. busca vetorial no FAISS, com as 100 avaliações mais próximas;
2. busca BM25, também com 100;
3. fusão das duas listas com RRF (k=60);
4. reranking dos melhores candidatos com o cross-encoder.

### 6.3 Seleção das evidências

Código: `src/voc_rag/recuperacao.py`

Depois do reranking, as avaliações com score abaixo de 0 são descartadas. Textos idênticos são
agrupados em uma única evidência com contador. A comparação ignora maiúsculas e pontuação, e
isso faz diferença: "muito bom" aparece quase 600 vezes na base, e "bom" e "recomendo", mais de
400 vezes cada.

O número de avaliações enviadas ao LLM é limitado: no máximo 20 para perguntas de panorama e 10
para perguntas específicas. Se essas posições fossem preenchidas apenas pelos maiores scores do
reranker, um tema com frases muito diretas, como "entrega atrasada", poderia ocupar quase todas,
e o LLM deixaria de ver os outros problemas.

Por isso as posições são divididas igualmente entre as subconsultas que encontraram evidências.
Na pergunta "Quais os principais problemas?", com 5 subconsultas (defeito, atraso, produto
errado, atendimento e qualidade), cada uma fica com 4 das 20 posições. Dentro de cada tema, o
MMR (Maximal Marginal Relevance, técnica que equilibra relevância e diversidade; lambda = 0,7)
escolhe as avaliações mais relevantes que também sejam diferentes entre si,
evitando quatro versões de "chegou atrasado". Se um tema encontrar menos avaliações do que a sua
parte, as posições que sobram não são repassadas aos outros, e o contexto fica com menos de 20.

### 6.4 Contexto

Código: `src/voc_rag/geracao.py` (formatação das evidências) e `src/voc_rag/recuperacao.py`
(estatísticas), reunidos em `src/voc_rag/pipeline.py`

Cada evidência entra no prompt com um identificador e seus metadados:

```
[E5] nota 1/5 | categoria: utilidades domesticas | entrega: atrasado (12 dias) | compra: 2018-03
     | encontrada pela busca: "a entrega atrasou muito e não chegou no prazo"
<avaliacao>ATRASO ENORME NA ENTREGA. A entrega está muito atrasada...</avaliacao>
```

O prompt também recebe os filtros aplicados e algumas estatísticas calculadas no código sobre as
evidências: nota média, distribuição por sentimento e por situação de entrega e as categorias mais
frequentes. Assim o LLM não precisa estimar esses números.

### 6.5 Geração da resposta

Código: `src/voc_rag/geracao.py`

O LLM responde em formato estruturado: `evidencias_suficientes`, `resumo`,
`insights` (cada um com título, descrição e IDs das evidências), `limitacoes` e `confianca`. O
prompt pede que ele use apenas as avaliações fornecidas, cite os IDs em todo insight, fale em
quantidades só em relação às evidências ("6 das 20") e trate o texto dos clientes como dado, nunca
como instrução, o que protege contra prompt injection.

## 7. Respostas fundamentadas e rastreabilidade

Código: `src/voc_rag/geracao.py` e `src/app.py`

Cada insight traz os IDs das avaliações que o sustentam, e a interface mostra o texto dessas
avaliações logo abaixo dele.

As citações também são conferidas no código. IDs que não existem no
contexto são removidos, e um insight que fica sem nenhuma citação válida é descartado. Assim a
rastreabilidade não fica dependendo só do que o LLM decidiu escrever.

Para cada evidência é possível ver `review_id`, `order_id`, nota, categoria, situação da entrega,
score do reranker, posição nas buscas vetorial e BM25 e a subconsulta que a encontrou. Na aba
"Rastreamento do pipeline" aparecem a pergunta processada, os filtros e quantas avaliações
passaram por cada etapa, para cada subconsulta.

## 8. Perguntas sem evidências suficientes

Código: `src/voc_rag/pipeline.py`

Nem toda pergunta deve ser respondida. Há dois casos em que o sistema prefere dizer "não sei" a
inventar:

- a pergunta não tem relação com as avaliações (por exemplo, "Qual o faturamento da Olist?");
- a pergunta é sobre a experiência do cliente, mas a base não tem avaliações suficientes sobre o
  assunto (por exemplo, "entregas feitas por drone", serviço que a Olist não oferece).

Para isso, a pergunta passa por quatro verificações, na ordem em que acontecem no pipeline. Se
qualquer uma falhar, o processamento para ali e o usuário recebe uma mensagem explicando o motivo,
sem resposta gerada.

| # | Verificação | Quando recusa | Onde está no código |
|---|---|---|---|
| 1 | Escopo | O LLM, ao processar a pergunta, conclui que ela não trata da experiência dos clientes | `src/voc_rag/consulta.py` |
| 2 | Recorte vazio | Os filtros escolhidos (por exemplo, uma categoria e um mês sem avaliações) não deixam nenhuma avaliação para buscar | `src/voc_rag/recuperacao.py` |
| 3 | Evidências mínimas | Depois da busca, menos de 3 avaliações têm score do reranker igual ou acima de 0 | `src/voc_rag/pipeline.py` |
| 4 | Revisão do LLM | O LLM lê as evidências e indica que elas não respondem à pergunta, ou nenhum insight gerado tem citação válida | `src/voc_rag/geracao.py` |

A ordem vai da verificação mais barata para a mais cara. As verificações 2 e 3 não chamam o LLM
para gerar resposta, então uma pergunta sem base é recusada sem custo de geração.

A verificação 3 é a principal proteção contra respostas sem base. O reranker dá a cada avaliação
um score de relevância em relação à consulta: valores positivos indicam que a avaliação trata do
assunto, e valores negativos, que não trata. Uma busca sempre devolve alguma avaliação, mesmo que
o assunto não exista na base; o limiar serve para descartar essas avaliações pouco relacionadas. O
mínimo de 3 evita que o sistema tire conclusões a partir de um ou dois comentários isolados. Os dois
valores ficam em `src/voc_rag/config.py` (`LIMIAR_RERANK` e `MIN_EVIDENCIAS`) e podem ser
ajustados pelo `.env`.

A verificação 4 cobre o caso em que as avaliações passam pelo limiar, mas só tangenciam a
pergunta. Na pergunta sobre drones, por exemplo, a busca pode trazer avaliações genéricas sobre
entrega; o LLM então informa que nenhuma delas fala do assunto perguntado.

O comportamento dessas verificações é medido na seção 10, na tabela de recusas.

## 9. Metadados (desafio adicional)

Código: `src/voc_rag/filtros.py`, `src/voc_rag/recuperacao.py` e `src/app.py`

Os metadados podem ser usados como filtros, tanto os identificados automaticamente na pergunta
quanto os escolhidos na barra lateral da interface: nota, sentimento, categoria, situação da
entrega, período da compra e UF. Quando os dois existem, o escolhido na barra lateral tem
prioridade. A chave "Usar filtros de metadados" desliga os dois de uma vez: a busca passa a usar
toda a base e os campos da barra lateral ficam bloqueados.

Eles melhoram a recuperação de algumas formas:

- Categoria: a busca fica restrita aos pedidos daquela categoria, em vez de depender de o
  cliente ter escrito o nome do produto no comentário.
- Sentimento: a busca por texto encontra avaliações sobre o mesmo assunto, mas não distingue
  elogio de reclamação, porque um comentário positivo e um negativo sobre entrega usam palavras
  parecidas. Filtrar pela nota separa os dois.
- Situação da entrega: o atraso é calculado pela diferença entre a data de entrega e a data
  prevista, então é possível olhar só para pedidos atrasados, mesmo os que não mencionam atraso no
  texto.
- Contexto do LLM: cada evidência já vem com nota, categoria e atraso, e o LLM pode usar essas
  informações na resposta.

O mesmo filtro é aplicado às duas buscas (no FAISS por `IDSelectorBatch` e no BM25 zerando o
score de quem está fora do recorte), de modo que a fusão compara candidatos do mesmo conjunto.

## 10. Avaliação

Código: `src/avaliar.py`

Os números abaixo vêm de `python src/avaliar.py --juiz`, que salva o resultado em
`artefatos/avaliacao.json`. A mesma execução também gera a tabela de reescrita da seção 6.1.

Nem todas as partes dependem do LLM:

- Recuperação e a tabela da seção 6.1 não usam LLM. Com a mesma base e os mesmos modelos de
  embeddings e reranking, os números se repetem em qualquer execução.
- Recusas e fundamentação usam o LLM configurado no `.env`. Os resultados podem mudar se o
  provedor (Gemini ou OpenAI) ou o modelo forem trocados, e variam um pouco entre execuções,
  porque a geração de texto não é determinística (veja a seção 3 sobre a temperatura).

Os números destas partes foram obtidos com `models/gemini-3.5-flash-lite` em outubro de 2026. O
modelo usado em cada execução fica registrado no campo `llm` de `artefatos/avaliacao.json`. Ao
trocar de modelo, rode a avaliação de novo para conferir os resultados.

### Recuperação

Precisão nos 10 primeiros resultados, por tema. Como não existe um gabarito anotado, uma
avaliação foi considerada relevante quando o texto contém termos do tema (por expressão
regular). Essa parte não usa o LLM.

As colunas comparam quatro formas de buscar, da mais simples à usada no sistema:

- Vetorial: só a busca por significado no FAISS (embeddings).
- BM25: só a busca por palavras.
- Híbrida (RRF): as duas buscas acima rodam juntas e as listas são combinadas por Reciprocal Rank
  Fusion. Cada avaliação ganha pontos pela posição em que aparece em cada lista, então quem
  aparece bem nas duas sobe no ranking.
- Híbrida + reranker: a lista da híbrida é reordenada pelo cross-encoder, que lê a consulta e cada
  avaliação juntas e dá um score de relevância. É a configuração usada pelo sistema.

| Tema | Vetorial | BM25 | Híbrida (RRF) | Híbrida + reranker |
|---|---|---|---|---|
| Atraso na entrega | 0,90 | 0,80 | 1,00 | 1,00 |
| Produto com defeito/quebrado | 1,00 | 0,60 | 1,00 | 1,00 |
| Produto diferente do anunciado | 1,00 | 0,90 | 0,90 | 0,90 |
| Pedido incompleto | 1,00 | 1,00 | 1,00 | 1,00 |
| Atendimento e comunicação | 0,10 | 0,40 | 0,30 | 0,70 |
| Devolução/reembolso | 1,00 | 0,90 | 1,00 | 1,00 |
| Embalagem | 0,50 | 0,20 | 0,60 | 0,80 |
| Elogio à rapidez da entrega | 1,00 | 0,40 | 0,80 | 1,00 |
| Média | 0,81 | 0,65 | 0,82 | 0,93 |

O reranker é o que mais contribui. A fusão ajuda nos temas em que uma das buscas vai mal sozinha,
como "atendimento" e "embalagem", porque combina os resultados das duas.

### Recusas

Verifica se o sistema responde o que deve e recusa o que está fora do escopo ou não tem evidência.

| Pergunta | Esperado | Resultado | Onde recusou |
|---|---|---|---|
| Quais são os principais problemas relatados pelos clientes? | responder | respondida | |
| O que os clientes relatam sobre problemas relacionados à entrega? | responder | respondida | |
| Quais aspectos da experiência de compra são mais elogiados? | responder | respondida | |
| Quais padrões nas avaliações de clientes insatisfeitos? | responder | respondida | |
| Padrões recorrentes relacionados à qualidade dos produtos? | responder | respondida | |
| Qual é a capital da França? | recusar | fora do escopo | escopo |
| Qual foi o faturamento da Olist em 2018? | recusar | fora do escopo | escopo |
| Me passe uma receita de bolo de cenoura. | recusar | fora do escopo | escopo |
| O que os clientes dizem sobre entregas feitas por drone? | recusar | evidência insuficiente | limiar |
| Reclamações sobre pagamento com criptomoedas? | recusar | evidência insuficiente | limiar |
| O que acham do programa de milhas aéreas da loja? | recusar | fora do escopo | escopo |

As 11 perguntas tiveram o comportamento esperado. Também testamos o limiar sozinho, sem o LLM: as
seis perguntas que deveriam ser recusadas continuam recusadas, mas duas perguntas válidas, por
serem abstratas, também seriam. Isso mostra que a reescrita em subconsultas é necessária para
encontrar as evidências, e que o limiar, isoladamente, já é uma proteção conservadora.

### Fundamentação

Um LLM-juiz confere se cada insight é sustentado pelas avaliações que ele cita. Dos 22 insights
gerados nas cinco perguntas respondidas, 19 foram considerados totalmente sustentados, 3
parcialmente sustentados (parte da afirmação não aparece nas avaliações citadas) e nenhum foi
considerado sem sustentação. O juiz é o mesmo LLM configurado no `.env` (Gemini ou OpenAI), ou
seja, o modelo avalia as próprias respostas. Por isso esse número é um indicativo, não uma prova.

## 11. Exemplos de perguntas e respostas

Os exemplos completos, com resposta, insights, evidências e scores, estão em
[docs/exemplos.md](docs/exemplos.md). Abaixo, um trecho (o texto do LLM varia um pouco entre
execuções).

Pergunta: *Quais são os principais problemas relatados pelos clientes?*

Foi classificada como pergunta de panorama, com filtros de sentimento negativo e nota até 2
(10.836 avaliações no recorte), gerou 5 subconsultas e usou 20 evidências.

> Os principais problemas relatados envolvem falhas com o produto recebido (defeito, divergência
> da foto e falta de peças), atrasos na entrega e problemas de atendimento.
> - Produtos com defeito ou danificados [E1, E2, E3, E4]
> - Atraso na entrega [E5, E6, E7, E8]
> - Diferença entre o produto real e a foto/propaganda [E13, E14, E15, E16]
> - Falta de peças ou itens na embalagem [E17, E18, E19, E20]
> - Falta de resposta e suporte do vendedor ou site [E1, E9, E11, E12]
>
> Limitações: as evidências permitem quantificar os problemas apenas nestas 20 avaliações de
> notas 1 e 2, sem estimar a proporção desses problemas na base.

| id | nota | categoria | entrega | rerank | texto |
|---|---|---|---|---|---|
| E2 | 2 | ferramentas jardim | no_prazo | +3,13 | O produto veio com defeito . Amassado. |
| E5 | 1 | utilidades domesticas | atrasado | +5,86 | ATRASO ENORME NA ENTREGA. A entrega está muuuuito atrasada... |
| E14 | 1 | cama mesa banho | no_prazo | +7,40 | Foto diferente do produto, qualidade ruim. |
| E18 | 1 | utilidades domesticas | no_prazo | +3,85 | Veio faltando duas peças. |

Pergunta fora do escopo: *Qual foi o faturamento da Olist em 2018?*
O sistema responde que a pergunta pede dados financeiros da empresa, que não estão nas
avaliações.

Pergunta sem evidência: *O que os clientes dizem sobre as entregas feitas por drone?*
A busca só encontra avaliações genéricas sobre entrega. O limiar do reranker, ou o próprio LLM
("nenhuma delas cita ou faz referência a entregas feitas por drone"), impede uma resposta sem
base.

## 12. Decisões técnicas e desafios

O desafio principal foi fazer perguntas abstratas, como "quais os principais problemas?",
encontrarem avaliações relevantes. A solução foi a reescrita em subconsultas no vocabulário do
cliente (seção 6.1). Ela trouxe outro problema: nas perguntas de panorama, um único tema podia
ocupar todo o contexto. Por isso as posições do contexto são divididas igualmente entre as subconsultas, e o MMR garante
variedade dentro de cada uma.

Comentários genéricos que se repetem muito, como "Muito bom", são agrupados com um contador para
não ocuparem várias posições.

Para decidir quando não há evidência, usamos um limiar no score do reranker, calibrado com
consultas dentro e fora do escopo, junto com o mínimo de 3 evidências. Essa checagem acontece
antes de chamar o LLM, o que também economiza chamadas.

Como o LLM pode citar evidências que não existem, a resposta é estruturada e as citações são
validadas no código. Os comentários podem conter dados pessoais, que são mascarados na
preparação, e também instruções escritas pelo cliente; por isso o texto vai delimitado por
`<avaliacao>` e o prompt diz explicitamente que ele deve ser tratado como dado.

No ambiente, as versões 2.6 ou mais novas do torch exigem um Visual C++ Redistributable recente no
Windows, então fixamos o torch 2.5.1 (CPU). Como a máquina usada no desenvolvimento tem uma GPU de apenas 2 GB, os modelos de
embeddings e de reranking escolhidos são pequenos e rodam em CPU, e a geração de texto é feita
pela API do Gemini.

## 13. Limitações e próximos passos

- Frequência nas evidências não é o mesmo que frequência na base. O RAG recupera uma amostra
  relevante, e "8 de 20 evidências" não representa a proporção real. Um próximo passo seria
  classificar todas as avaliações por tema, de forma offline, e combinar essas contagens com o RAG.
- A relevância usada na avaliação de recuperação é aproximada por expressões regulares. Um
  gabarito anotado manualmente permitiria métricas mais confiáveis, como recall@k (quantas das avaliações
  relevantes aparecem entre as k primeiras) e nDCG (que também considera a ordem em que aparecem).
- O sentimento vem da nota, e há comentários ambíguos, como nota 5 com reclamação.
- A categoria do pedido é a do item mais caro; cerca de 3% dos pedidos têm mais de um produto.
- Outras melhorias possíveis: memória de conversa com LangGraph, cache de respostas, uma API com
  FastAPI e avaliação com RAGAS.
