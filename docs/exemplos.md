# Exemplos de perguntas e respostas

Modelo de chat: `openai:gpt-5.6-luna`. Embeddings: `openai:text-embedding-3-small`. Multi-query: True. BM25: True. Rerank: True.

## Investigação de reclamações

### Quais são os principais problemas relatados pelos clientes em suas avaliações?

Status: `respondida`

Busca (overview): "o produto veio com defeito"; "a entrega atrasou e demorou muito"; "não recebi o pedido"; "o produto é diferente do anunciado"; "o vendedor não responde"

Filtros: nenhum

Entre as avaliações recuperadas, os clientes relatam principalmente produtos com defeito, atrasos ou não recebimento da entrega, divergências entre o produto recebido e o anunciado e falta de resposta dos vendedores. Também aparecem relatos de pedidos entregues parcialmente e de produtos danificados.

- Há reclamações de produtos que chegaram com defeito, incluindo boneca, carrinho e itens não especificados. (R1, R2, R3, R4)
- Atrasos e demora na entrega são relatados, incluindo um caso com 15 dias de atraso. Em um comentário, o cliente também reclama de não receber explicação sobre o atraso. (R5, R6, R7, R8)
- Clientes relatam não ter recebido o pedido, inclusive com caso em que o sistema informou a entrega apesar de o cliente não ter recebido. Também há pedido recebido apenas parcialmente. (R9, R10, R11, R12)
- Há queixas de produtos diferentes do anúncio, como cor ou fonte divergente, produto diferente do anunciado e alegação de falsificação. (R13, R14, R15, R16)
- A falta de resposta ou de retorno do vendedor aparece em reclamações sobre pedidos não recebidos, entrega parcial e produto danificado; há também relato de luminária que chegou amassada. (R17, R18, R19, R20)

Limitações: As avaliações recuperadas são uma amostra por similaridade e estão divididas entre subtemas; portanto, não permitem ordenar os problemas por frequência na base inteira nem afirmar que são os únicos problemas existentes. O panorama informa indicadores agregados de notas e entrega, mas não relaciona suas proporções a cada tipo de reclamação textual.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.94 | 3 | 5 | RJ | climatizacao | no_prazo | O produto veio com defeito. |
| R2 | sim | 0.64 | 3 | 1 | RS | cool_stuff | no_prazo | Minha boneca veio com defeito. |
| R3 | sim | 0.73 | 3 | 1 | PE | cool_stuff | no_prazo | o carrinho veio com defeito. |
| R4 | sim | 0.69 | 3 | 2 | SP | brinquedos | no_prazo | Veio com defeitos. |
| R5 | sim | 0.83 | 3 | 3 | ES | eletronicos | atrasado | Entrega muito demorada e ainda houve atraso! |
| R6 | sim | 0.82 | 3 | 3 | SC | esporte_lazer | atrasado | Demora na entrega e ainda atrasou. |
| R7 | sim | 0.67 | 3 | 1 | RO | bebes | nao_entregue | Demora muito e eles não dão satisfação pelo motivo do atraso. |
| R8 | sim | 0.60 | 3 | 3 | RO | perfumaria | atrasado | Perfume original, muito bom. Porém houve muita demora na entrega, 15 dias de atraso. |
| R9 | sim | 0.90 | 3 | 1 | RJ | moveis_decoracao | no_prazo | Não recebi o pedido. |
| R10 | sim | 0.63 | 3 | 1 | SP | esporte_lazer | no_prazo | Meu pedido não foi entregue, porém já recebi e-mail informando que foi entregue, e quero meu pedido. |
| R11 | sim | 0.74 | 3 | 1 | CE | sem_categoria | atrasado | nao recebi meu pedido, e agora o que faço. |
| R12 | sim | 0.61 | 3 | 3 | MG | moveis_decoracao | no_prazo | Recebi a metade do pedido. Nao recebi o lustre ainda. |
| R13 | sim | 0.85 | 3 | 1 | BA | telefonia | no_prazo | Produto Diferente. O produto que recebi é diferente do produto anunciado. |
| R14 | sim | 0.61 | 3 | 3 | SP | informatica_acessorios | no_prazo | Só deveria cumprir com o que está no anuncio. Veio uma cor bem diferente do anuncio. |
| R15 | sim | 0.76 | 3 | 1 | SP | brinquedos | no_prazo | O produto eh falsificado. Não eh o anunciado. |
| R16 | sim | 0.58 | 3 | 3 | SP | consoles_games | no_prazo | Fonte veio diferente do anunciado. |
| R17 | sim | 0.67 | 3 | 1 | SP | sem_categoria | nao_entregue | Total descaso! Não respondeu nenhum de meus e-mails, não deu satisfação nenhuma a respeito! Péssimo vendedor! |
| R18 | sim | 0.54 | 3 | 1 | PI | construcao_ferramentas_iluminacao | no_prazo | O produto (luminaria pendente) veio todo amassado. E ainda não obtive resposta da loja que vendeu. |
| R19 | sim | 0.63 | 3 | 1 | BA | beleza_saude | no_prazo | O pedido foi entregue parcial e o vendedor não entrou em contato comigo. Estou aguardando resposta da pág seguro. |
| R20 | sim | 0.58 | 3 | 2 | PR | cama_mesa_banho | no_prazo | Comprei dois produtos e só recebi um, já enviei dois emails ao vendedor mas ainda não obtive resposta. |

## Tema específico

### O que os clientes relatam sobre problemas relacionados à entrega?

Status: `respondida`

Busca (specific): "a entrega atrasou e demorou muito para chegar"; "não recebi o pedido ou a encomenda não chegou"

Filtros: nenhum

Entre os comentários recuperados, os clientes relatam demora e atrasos na entrega, pedidos que não chegaram e falta de esclarecimentos sobre a situação. Também há relato de entrega parcial, com itens faltando no mesmo pedido. No panorama geral do recorte, 6% dos pedidos estão classificados como atrasados e 3% como não entregues nos metadados da base.

- Clientes relatam que a entrega demorou muito ou sofreu atraso, inclusive com demora para a postagem e ausência de previsão de chegada. (R1, R2, R3, R4, R5, R6)
- Há relatos de pedidos ou encomendas que não chegaram; em um caso, o cliente também menciona estar sem esclarecimentos sobre o ocorrido. Em R9, o texto relata que foi a primeira vez que não recebeu a encomenda, enquanto o pedido está classificado como atrasado nos metadados. (R7, R8, R9, R10, R11)
- Um cliente relata entrega parcial: recebeu o pacote de chá, mas as cápsulas do mesmo pedido não foram entregues. (R12)

Limitações: As avaliações recuperadas mostram experiências específicas e não permitem estimar a frequência de cada problema na base inteira. O panorama informa percentuais gerais de classificação da entrega nos metadados, mas esses dados não significam necessariamente que os clientes tenham mencionado esses percentuais ou os respectivos problemas nos comentários.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.80 | 3 | 3 | SC | esporte_lazer | atrasado | Demora na entrega e ainda atrasou. |
| R2 | sim | 0.74 | 3 | 3 | PR | telefonia | no_prazo | Demorou muito para o produto ser postado para entrega, e depois demorou ainda mais pra chegar. |
| R3 | sim | 0.78 | 3 | 2 | MG | utilidades_domesticas | atrasado | A entrega está atrasada e sem previsão de quando vai chegar. |
| R4 | sim | 0.80 | 3 | 3 | ES | eletronicos | atrasado | Entrega muito demorada e ainda houve atraso! |
| R5 | sim | 0.68 | 2 | 2 | SP | beleza_saude | no_prazo | Demora muito pra chegar. |
| R6 | sim | 0.76 | 2 | 2 | GO | cool_stuff | atrasado | Achei q demorou muito a entrega. |
| R7 | sim | 0.78 | 3 | 1 | SC | informatica_acessorios | nao_entregue | não recebi meu pedido, estou sem a encomenda e sem esclarecimentos. |
| R8 | sim | 0.74 | 3 | 1 | SP | automotivo | nao_entregue | Não recebi. Não chegou não chegou. |
| R9 | sim | 0.59 | 3 | 3 | SP | ferramentas_jardim | atrasado | Nunca tive problemas em receber encomendas. A primeira vez que acontece de não receber a encomenda. |
| R10 | sim | 0.61 | 3 | 1 | SP | bebes | atrasado | não recomendo por que ate agora minha encomenda não chegou. |
| R11 | sim | 0.64 | 3 | 1 | SP | beleza_saude | nao_entregue | Não chego meu pedido. |
| R12 | sim | 0.63 | 3 | 1 | GO | beleza_saude | no_prazo | Ficou faltando produto que encomendei. O pacote de chá recebi, mas as cápsulas não entregaram era no mesmo pedido. |

## Experiências positivas

### Quais aspectos da experiência de compra são mais elogiados pelos clientes?

Status: `respondida`

Busca (overview): "a entrega foi rápida e chegou antes do prazo"; "o produto é de ótima qualidade e igual ao anunciado"; "o vendedor foi atencioso e respondeu rapidamente"; "o produto chegou bem embalado e em perfeito estado"; "a compra foi fácil e estou muito satisfeito"

Filtros: score >= 4

Entre as avaliações recuperadas, os clientes elogiam principalmente a rapidez da entrega, a qualidade e a correspondência do produto com o anúncio, além da atenção dos vendedores. Também aparecem elogios à embalagem, ao estado de recebimento e à facilidade da compra.

- A rapidez da entrega é frequentemente elogiada nos comentários, incluindo casos em que o pedido chegou antes do prazo. (R1, R2, R3, R4, R14, R18, R20)
- Os clientes destacam a boa qualidade dos produtos e a conformidade com o anúncio, mencionando também acabamento e satisfação com o item recebido. (R5, R6, R7, R8, R18)
- O atendimento dos vendedores é elogiado pela atenção, rapidez, cordialidade, presteza e eficiência. (R9, R10, R11, R12)
- Há elogios à embalagem e à conservação dos produtos, que chegaram protegidos e em perfeito estado. (R13, R14, R15, R16)
- Alguns clientes ressaltam a facilidade e a rapidez do processo de compra, associadas à satisfação geral com a experiência. (R17, R19, R20)

Limitações: As avaliações recuperadas são uma amostra por similaridade e foram distribuídas entre subtemas; portanto, não permitem ordenar esses aspectos por frequência na base inteira nem afirmar quais são os mais elogiados em termos quantitativos. O panorama informa que 75% das avaliações do recorte têm nota 5, mas não detalha quais aspectos explicam essas notas.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.94 | 3 | 5 | SP | malas_acessorios | no_prazo | a entrega foi rápida.chegou antes do prazo. |
| R2 | sim | 0.80 | 3 | 5 | MG | beleza_saude | no_prazo | O produto chegou antes do prazo. A entrega foi super rápida! |
| R3 | sim | 0.82 | 3 | 5 | DF | cool_stuff | no_prazo | Entrega rápida e antes do prazo. Excelente! |
| R4 | sim | 0.80 | 3 | 5 | SP | utilidades_domesticas | no_prazo | Recomendo super rápida a entrega,chegou antes do prazo. |
| R5 | sim | 0.81 | 3 | 5 | GO | cama_mesa_banho | no_prazo | Produto muito bom. Produto de ótima qualidade, conforme anunciado. |
| R6 | sim | 0.55 | 3 | 4 | MG | moveis_decoracao | no_prazo | Super recomendado igual o anúncio acabamento perfeito,ADOREI. |
| R7 | sim | 0.61 | 3 | 5 | SP | fashion_bolsas_e_acessorios | no_prazo | Carteira veio conforme anunciado e é de ótima qualidade, recomendo! |
| R8 | sim | 0.76 | 3 | 5 | RJ | eletronicos | no_prazo | Perfeito!! Produto perfeito, o mesmo que estava no anuncio e de muito boa qualidade, recomendo! |
| R9 | sim | 0.75 | 3 | 4 | SP | papelaria | no_prazo | Vendedor super atencioso e rápido, eu recomendo. |
| R10 | sim | 0.67 | 3 | 5 | SP | automotivo | no_prazo | Excelente. Ótimo vendedor. Atencioso e prestativo. O Sr. Bruno me atendeu de maneira gentil e eficiente. Recomendo. |
| R11 | sim | 0.72 | 3 | 5 | DF | informatica_acessorios | no_prazo | Muito bom o atendimento. Extremamente célere e cômodo. Recomendo esse vendedor. |
| R12 | sim | 0.71 | 3 | 5 | MT | casa_conforto | no_prazo | Vendedor rápido e atencioso, recomendo a todos. |
| R13 | sim | 0.86 | 3 | 5 | SP | sinalizacao_e_seguranca | no_prazo | Ótimo. Produto chegou em perfeito Estado. Bem embalado e protegido. |
| R14 | sim | 0.75 | 3 | 4 | SP | telefonia | no_prazo | a entrega foi antes do prazo determinado e tudo estava bem embalado e perfeito estado. |
| R15 | sim | 0.66 | 3 | 4 | SP | moveis_escritorio | no_prazo | O produto veio bem embalado, em perfeito estado. É um pouco complicado de montar. |
| R16 | sim | 0.66 | 3 | 5 | SP | utilidades_domesticas | no_prazo | Empresa idônea, pontualidade, produto chegou bem embalado e em perfeito estado. Parabéns lannister. |
| R17 | sim | 0.82 | 3 | 5 | SP | beleza_saude | no_prazo | fiquei satisfeita com a facilidade da compra. |
| R18 | sim | 0.73 | 3 | 5 | SP | relogios_presentes | no_prazo | Muito satisfeito! A entrega foi extremamente rápida e o produto é excelente. Estou muito satisfeito com a compra. |
| R19 | sim | 0.80 | 3 | 5 | SP | utilidades_domesticas | no_prazo | Satisfeito. Compra rápida e fácil. |
| R20 | sim | 0.79 | 3 | 5 | MG | cool_stuff | no_prazo | Fiquei muito satisfeita com a compra, facilidade e entrega rápida. |

## Insatisfação

### Quais padrões podem ser identificados nas avaliações de clientes insatisfeitos?

Status: `respondida`

Busca (overview): "o produto veio com defeito ou não funciona"; "a entrega atrasou e demorou muito para chegar"; "não recebi o pedido ou ele foi extraviado"; "o produto é diferente do anunciado ou da descrição"; "o vendedor não responde e não resolve o problema"

Filtros: score <= 2

Entre as avaliações recuperadas de clientes insatisfeitos, aparecem cinco padrões: produtos com defeito, atrasos ou não recebimento, divergência em relação ao anúncio e falta de resposta ou solução pelo vendedor. No panorama do recorte, todas as avaliações têm nota 1 ou 2, sendo 78% nota 1 e 22% nota 2; quanto à entrega, 57% estão classificadas como no prazo, 28% como atrasadas e 15% como não entregues nos metadados.

- Há reclamações de produtos que já chegaram com defeito ou que não funcionavam, incluindo falhas completas e componentes que não operavam mesmo após testes. (R1, R2, R3, R4)
- A demora na entrega é um padrão presente nos comentários: clientes mencionam atraso ou tempo excessivo para receber o pedido. Em alguns casos, porém, os metadados classificam a entrega como no prazo, portanto essa classificação não deve ser convertida em ausência de reclamação de demora. (R5, R6, R7, R8)
- Também aparecem casos de não recebimento ou possível extravio do pedido, inclusive com menções a prazos já ultrapassados. (R9, R10, R11, R12)
- Alguns clientes relatam que o produto recebido era diferente do anunciado, da imagem ou da descrição, incluindo divergências de medidas e suspeita de falsificação. (R13, R14, R15, R16)
- A falta de comunicação e de resolução pelo vendedor surge em situações de produto indisponível, não recebimento, atraso e solicitação de estorno; os clientes mencionam ausência de respostas e de justificativas. (R17, R18, R19, R20)

Limitações: As avaliações recuperadas são uma amostra por similaridade e não permitem ordenar os padrões por frequência na base inteira. O panorama fornece percentuais agregados de notas e de status de entrega, mas não distribui esses percentuais por motivo de insatisfação. Além disso, os estados e demais metadados identificam o pedido, mas não devem ser tratados como afirmações feitas pelos clientes.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.85 | 3 | 1 | SP | relogios_presentes | no_prazo | Produto já veio com defeito não funciona. |
| R2 | sim | 0.57 | 3 | 1 | RJ | relogios_presentes | no_prazo | O relogio não esta funcionando. Nao esta quebrado. Mas nao funciona com a pilha de jeito nenhum. Veio com defeito. |
| R3 | sim | 0.65 | 3 | 1 | SC | cool_stuff | no_prazo | Não funciona, mais uma vez meu produto chegou com defeito! |
| R4 | sim | 0.68 | 3 | 1 | BA | beleza_saude | no_prazo | Produto com defeito! 2 dos 4 sensores não funciona. Ja foram feito todos os testes e produto não esta funcionando. |
| R5 | sim | 0.79 | 3 | 1 | BA | esporte_lazer | atrasado | Atrasou na entrega. |
| R6 | sim | 0.65 | 3 | 1 | SP | esporte_lazer | atrasado | o produto demora muita para chegar ! |
| R7 | sim | 0.66 | 3 | 1 | MG | cama_mesa_banho | no_prazo | Gostei só que demorou muito p chegar. |
| R8 | sim | 0.66 | 3 | 1 | SP | beleza_saude | no_prazo | bom dia não sei se foi os correios que atrasou mas o produto demorou demais para chegar. |
| R9 | sim | 0.80 | 3 | 1 | RJ | moveis_decoracao | no_prazo | Não recebi o pedido. |
| R10 | sim | 0.47 | 3 | 1 | RJ | ferramentas_jardim | atrasado | Produto deve ter extraviado. |
| R11 | sim | 0.53 | 3 | 1 | AL | moveis_decoracao | atrasado | Não recebi o produto até o momento. Já extrapolaramse todos os prazos e estimativas. Aguardo uma posição urgente. |
| R12 | sim | 0.67 | 3 | 1 | RN | beleza_saude | nao_entregue | Fiquei muito desapontado com o extravio do meu pedido. |
| R13 | sim | 0.80 | 3 | 1 | BA | telefonia | no_prazo | Produto Diferente. O produto que recebi é diferente do produto anunciado. |
| R14 | sim | 0.70 | 3 | 1 | SP | moveis_sala | no_prazo | Produto entregue fora do prazo previsto. E com medidas diferentes da descrição da pagina na web. |
| R15 | sim | 0.58 | 3 | 2 | PR | relogios_presentes | no_prazo | Tamanho super diferente da imagem do anúncio! Super chateada com a diferença! |
| R16 | sim | 0.71 | 3 | 1 | SP | brinquedos | no_prazo | O produto eh falsificado. Não eh o anunciado. |
| R17 | sim | 0.72 | 3 | 1 | SP | sem_categoria | nao_entregue | Vende produto indisponível, não resolve o problema do cliente, não responde os e-mails. |
| R18 | sim | 0.62 | 3 | 1 | SC | papelaria | atrasado | Não recebi o produto não recebi uma justificativa do vendedor. entrei em contato mas até agora não obtive uma resposta. |
| R19 | sim | 0.63 | 3 | 1 | SP | utilidades_domesticas | no_prazo | NÃO ENTRA EM CONTATO PARA SOLUCIONAR O ESTORNO DA COMPRA. |
| R20 | sim | 0.49 | 3 | 1 | AL | malas_acessorios | atrasado | Não sei como a lannister resolve usar o próprio nome pra vender produtos de um loja tão descompromissada com o cliente. Não respondem o meu e-mail reclamando do atraso e da falta de atenção . |

## Exploração baseada em evidências

### Quais avaliações sustentam a conclusão de que existem problemas recorrentes relacionados ao prazo de entrega?

Status: `respondida`

Busca (specific): "o pedido atrasou e chegou depois do prazo de entrega"; "a entrega demorou mais do que o prazo informado"

Filtros: nenhum

As avaliações R1 a R12 sustentam problemas relacionados ao prazo de entrega: algumas relatam explicitamente atraso ou demora, e R6 também relata cancelamento após atraso e demora no ressarcimento. No panorama de toda a base, 6% dos pedidos estão classificados como atrasados e 3% como não entregues, indicando ocorrência do problema no recorte analisado.

- R1 a R9 relatam explicitamente entrega após o prazo, atraso ou não cumprimento da data prevista. Em R5, o cliente também menciona demora na postagem; em R6, relata atraso, cancelamento por falta do produto e demora no ressarcimento. (R1, R2, R3, R4, R5, R6, R7, R8, R9)
- R10, R11 e R12 registram reclamações textuais de entrega demorada ou demora na entrega. Embora os metadados desses pedidos indiquem entrega no prazo, essa classificação não elimina o fato de que os clientes fizeram esses relatos no texto. (R10, R11, R12)

Limitações: As avaliações recuperadas são uma amostra por similaridade e não permitem medir a frequência de cada tipo de reclamação entre os comentários nem afirmar quais categorias, estados ou períodos concentram o problema. Os percentuais de atraso e não entrega vêm dos metadados do panorama, não necessariamente de relatos textuais dos clientes.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.80 | 3 | 3 | RS | eletronicos | no_prazo | Atrasou a entrega. |
| R2 | sim | 0.50 | 3 | 4 | PR | eletronicos | atrasado | Chegou um dia depois do prazo, mas chegou funcionando, então tudo okay! |
| R3 | sim | 0.68 | 3 | 4 | SP | esporte_lazer | no_prazo | O produto chegou depois do prazo, mais recomendaria esse site. |
| R4 | sim | 0.68 | 3 | 3 | MG | informatica_acessorios | atrasado | não do 5 estrela pois atrasou pedido. |
| R5 | sim | 0.62 | 3 | 4 | RJ | pet_shop | atrasado | bom. demoraram a colocar nos correios, mas depois foi rápido, mas atrasou ! |
| R6 | sim | 0.65 | 3 | 1 | SP | relogios_presentes | nao_entregue | comprei ,atrasaram a data da entrega e depois que entrei em contato me disseram que não tinha o produto e cancelaram o pedido,agora estou atras para me ressarcirem o valor,resumindo,péssimo vendedor!! |
| R7 | sim | 0.77 | 3 | 1 | BA | esporte_lazer | atrasado | Atrasou na entrega. |
| R8 | sim | 0.69 | 3 | 2 | MA | beleza_saude | atrasado | O produto não foi entregue na data prevista e o vendedor não me informou os motivos da demora para a entrega. |
| R9 | sim | 0.75 | 3 | 1 | PE | esporte_lazer | atrasado | Passou do prazo de entrega, demorou. |
| R10 | sim | 0.63 | 2 | 3 | MG | relogios_presentes | no_prazo | entrega demorada e pouca informação, se o produto for vendido por outro site darei a preferencia. |
| R11 | sim | 0.79 | 2 | 4 | MG | utilidades_domesticas | no_prazo | A entrega demorou demais. |
| R12 | sim | 0.76 | 2 | 1 | MG | cama_mesa_banho | no_prazo | demora na entrega . |

## Metadados: nota baixa

### Quais são os principais problemas relatados nas avaliações com nota baixa?

Status: `respondida`

Busca (overview): "o produto veio com defeito"; "a entrega atrasou ou demorou muito"; "não recebi o pedido"; "o produto é diferente do anunciado"; "o vendedor não responde"; "o pedido veio incompleto ou errado"

Filtros: score <= 2

Entre as avaliações recuperadas com notas 1 e 2, os principais problemas relatados são produtos com defeito ou danificados, atrasos ou não recebimento, divergência em relação ao anúncio, pedidos incompletos ou errados e falta de resposta do vendedor. O panorama mostra que o recorte é composto por 78% de notas 1 e 22% de notas 2, mas não permite medir a frequência de cada problema.

- Há relatos de produtos que chegaram com defeito, incluindo item que não ligava, além de produto danificado e item diferente do comprado. (R1, R2, R3, R4, R16)
- A entrega aparece como problema em relatos de atraso ou demora excessiva, incluindo casos em que o cliente afirma não ter recebido o pedido ou recebeu aviso de entrega sem ter recebido a mercadoria. (R5, R6, R7, R8, R9, R10, R11)
- Alguns clientes relatam divergências entre o produto recebido e o anúncio, como produto diferente, composição incompatível e tamanho distinto da imagem. (R12, R13, R14)
- Também há reclamações de pedidos incompletos, entrega parcial ou recebimento de produto errado. (R4, R17, R18, R19, R20)
- A falta de resposta ou de satisfação do vendedor é relatada em casos de atraso, produto danificado, entrega parcial e ausência de solução para o pedido. (R6, R15, R16, R17, R20)

Limitações: As avaliações recuperadas são uma amostra por similaridade e estão divididas entre subtemas; portanto, não é possível afirmar quais problemas são os mais frequentes em toda a base. O panorama informa a distribuição geral das notas e das situações de entrega, mas não relaciona esses percentuais a cada problema específico.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.94 | 3 | 1 | BA | telefonia | no_prazo | O produto veio com defeito. |
| R2 | sim | 0.64 | 3 | 1 | RS | cool_stuff | no_prazo | Minha boneca veio com defeito. |
| R3 | sim | 0.78 | 3 | 1 | SP | telefonia | no_prazo | o produto veio com defeito, não esta ligando. |
| R4 | sim | 0.77 | 3 | 1 | PE | consoles_games | no_prazo | Meu produto veio com defeito e comprei um e veio outro no lugar. |
| R5 | sim | 0.80 | 3 | 1 | BA | esporte_lazer | atrasado | Atrasou na entrega. |
| R6 | sim | 0.63 | 3 | 1 | RO | bebes | nao_entregue | Demora muito e eles não dão satisfação pelo motivo do atraso. |
| R7 | sim | 0.63 | 3 | 1 | PB | beleza_saude | nao_entregue | minha compra está muito atrasada. |
| R8 | sim | 0.67 | 3 | 1 | RJ | construcao_ferramentas_construcao | nao_entregue | Não gostei da entrega está demorando muito.Essa empresa demora muito para entregar a mercadoria. |
| R9 | sim | 0.90 | 3 | 1 | RJ | moveis_decoracao | no_prazo | Não recebi o pedido. |
| R10 | sim | 0.58 | 3 | 1 | RJ | beleza_saude | no_prazo | Eu não recebi este produto e eu gostaria de cancelar o pedido. |
| R11 | sim | 0.63 | 3 | 1 | SP | esporte_lazer | no_prazo | Meu pedido não foi entregue, porém já recebi e-mail informando que foi entregue, e quero meu pedido. |
| R12 | sim | 0.85 | 3 | 1 | BA | telefonia | no_prazo | Produto Diferente. O produto que recebi é diferente do produto anunciado. |
| R13 | sim | 0.73 | 3 | 1 | SP | bebidas | no_prazo | A composição do produto não corresponde ao anunciado. |
| R14 | sim | 0.60 | 3 | 2 | PR | relogios_presentes | no_prazo | Tamanho super diferente da imagem do anúncio! Super chateada com a diferença! |
| R15 | sim | 0.67 | 3 | 1 | SP | sem_categoria | nao_entregue | Total descaso! Não respondeu nenhum de meus e-mails, não deu satisfação nenhuma a respeito! Péssimo vendedor! |
| R16 | sim | 0.54 | 3 | 1 | PI | construcao_ferramentas_iluminacao | no_prazo | O produto (luminaria pendente) veio todo amassado. E ainda não obtive resposta da loja que vendeu. |
| R17 | sim | 0.63 | 3 | 1 | BA | beleza_saude | no_prazo | O pedido foi entregue parcial e o vendedor não entrou em contato comigo. Estou aguardando resposta da pág seguro. |
| R18 | sim | 0.78 | 3 | 1 | AL | beleza_saude | no_prazo | Chegou meu pedido incompleto. |
| R19 | sim | 0.64 | 3 | 1 | SP | utilidades_domesticas | no_prazo | o produto recebido veio errado. |
| R20 | sim | 0.64 | 3 | 1 | SP | telefonia | no_prazo | pedido veio incompleto e não me atenderam nem por telefone e nem por email. |

## Metadados: categoria

### O que os clientes mais elogiam em produtos de cama, mesa e banho?

Status: `respondida`

Busca (overview): "produto de cama mesa e banho de ótima qualidade"; "produto de cama mesa e banho bonito e bem acabado"; "produto de cama mesa e banho feito com material bom"; "produto de cama mesa e banho corresponde ao anúncio"; "produto de cama mesa e banho tem bom custo-benefício"

Filtros: score >= 4, category == cama_mesa_banho

Entre os comentários recuperados, os clientes elogiam principalmente a qualidade dos produtos e dos materiais, a beleza com bom acabamento e o efeito visual que proporcionam ao ambiente. Também aparecem elogios ao conforto, à adequação às especificações e ao custo-benefício.

- Há elogios à qualidade geral dos produtos e dos materiais, incluindo tecidos considerados bons, produtos bem feitos e itens descritos como excelentes. (R1, R2, R3, R5, R9, R10, R12, R15)
- Os clientes valorizam a aparência dos produtos, o acabamento e a capacidade de deixar a cama ou o quarto mais bonito e arrumado. (R4, R5, R6, R8, R11, R14, R16, R18)
- Também são elogiados o conforto e a maciez de alguns itens, além do bom ajuste ao tamanho ou atendimento às especificações anunciadas. (R3, R10, R11, R13, R16)
- Entre os comentários recuperados, há avaliações positivas sobre preço, variedade de cores e custo-benefício. (R12, R17, R18, R19, R20)

Limitações: As avaliações recuperadas permitem identificar atributos elogiados, mas não permitem ordenar esses atributos por frequência na base inteira. A amostra foi recuperada por similaridade e está dividida entre subtemas; portanto, os insights representam os comentários disponíveis, não necessariamente todos os clientes.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.70 | 3 | 5 | SP | cama_mesa_banho | no_prazo | produto de otima qualidade. |
| R2 | sim | 0.70 | 3 | 5 | SC | cama_mesa_banho | no_prazo | Roupa de cama de muito boa qualidade. Deixa o quarto lindo. |
| R3 | sim | 0.59 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Super recomendado. Para minha cama box conjugado o tamanho foi perfeito e o produto de muita qualidade. |
| R4 | sim | 0.61 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Muito Linda! Produto de ótima qualidade, ficou perfeita na minha cama. Chegou antes do prazo. |
| R5 | sim | 0.61 | 3 | 5 | SP | cama_mesa_banho | atrasado | Produto excelente. Produto de exelente qualidade,ótimo acabamento e muito bonito. Fiquei muito satisfeita. |
| R6 | sim | 0.57 | 3 | 4 | SP | cama_mesa_banho | no_prazo | Tapete bem bonito, com acabamento bem feito. Não é exatamente um capacho, mas vale a compra! |
| R7 |  | 0.58 | 3 | 5 | MT | cama_mesa_banho | no_prazo | Muito bom. Entrega rápida, produto bonito conforme descrito no site, porém so chegou o lençol ainda não chegou a saia da cama. |
| R8 | sim | 0.59 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Ótimo produto, deixou minha cama mais linda, deu um acabamento perfeito por baixo do edredon. Adorei, recomendo para aqueles que gostam de um quarto com uma cama bem arrumada.Adoro comprar no baratheon. |
| R9 | sim | 0.62 | 3 | 5 | AP | cama_mesa_banho | no_prazo | Um produto bonito e qualidade muito boa. |
| R10 | sim | 0.57 | 3 | 4 | MG | cama_mesa_banho | no_prazo | O jogo de cama King de cetim é tal qual a propaganda e chegou até antes do prazo.Poderia ser apesar do tecido ser bom ,um pouco mais bem feito. |
| R11 | sim | 0.57 | 3 | 5 | PR | cama_mesa_banho | no_prazo | Jogo de lençol muito lindo.macio e aconchegante.ficou linda a minha cama.. |
| R12 | sim | 0.59 | 3 | 5 | SP | cama_mesa_banho | no_prazo | material do tecido muito. preço otimo,e material muito bom,eu recomendo. |
| R13 | sim | 0.59 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Produto e entrega conforme anúncio. |
| R14 | sim | 0.44 | 3 | 5 | MG | cama_mesa_banho | no_prazo | Muito lindo a saia ficou lindissima em minha cama. |
| R15 | sim | 0.59 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Jogo de cama. Excelente produto. Recomendo a todos. |
| R16 | sim | 0.54 | 3 | 5 | MS | cama_mesa_banho | no_prazo | O produto atende as especificações. É bem simples, mas condiz com o valor. Ficou bonito na cama. |
| R17 | sim | 0.65 | 3 | 5 | SC | cama_mesa_banho | no_prazo | Produto bom. Produto tem um bom custo beneficio. |
| R18 | sim | 0.59 | 3 | 5 | RJ | cama_mesa_banho | no_prazo | Jogo de cama cetim, excelente preço, várias opções de cores, muito lindo. |
| R19 | sim | 0.57 | 3 | 4 | SP | cama_mesa_banho | no_prazo | adorei o tapete, otimo custo beneficio. Melhor que imaginava. |
| R20 | sim | 0.58 | 3 | 5 | SP | cama_mesa_banho | no_prazo | Cortinas de boa qualidade e com preço bom. Gostei ? |

## Metadados: entrega atrasada

### Quais temas aparecem nas avaliações de pedidos entregues com atraso?

Status: `respondida`

Busca (overview): "meu pedido entregue com atraso demorou muito para chegar"; "o pedido foi entregue com atraso e o produto veio com defeito"; "o pedido entregue com atraso veio diferente do anunciado"; "o pedido entregue com atraso chegou com a embalagem danificada"; "o pedido entregue com atraso chegou em perfeito estado e gostei do produto"

Filtros: delivery_status == atrasado

Entre os comentários recuperados, aparecem reclamações sobre demora ou entrega fora do prazo, casos em que o pedido ainda não havia sido recebido e falta de informações ou suporte. Também há relatos de problemas no transporte, como embalagem danificada, produto amassado, item incompleto ou com defeito, além de avaliações que elogiam o produto apesar do atraso.

- Demora e descumprimento do prazo são temas recorrentes nos textos, com clientes mencionando que a entrega demorou, estava atrasada ou não ocorreu dentro do prazo. (R1, R4, R5, R7, R8, R10, R14, R18)
- Há relatos de pedido ainda não recebido, cancelamento e falta de informações ou suporte sobre o atraso da entrega. (R2, R3, R5, R9)
- Alguns clientes atribuem o atraso ou problemas da entrega aos Correios, incluindo demora no transporte e necessidade de buscar o pedido. (R3, R11, R12, R15, R16)
- Aparecem problemas associados ao transporte ou à embalagem, como caixa rasgada, produto amassado, lacre aberto, embalagem danificada, produto com defeito e peça faltante. (R6, R11, R12, R13)
- Mesmo com atraso, alguns comentários elogiam o produto, destacando boa qualidade, estado perfeito, beleza ou recomendação. (R14, R15, R16, R17, R18)

Limitações: A análise se baseia nas avaliações recuperadas por similaridade, não em todas as 6.362 avaliações; portanto, não permite afirmar a frequência ou a ordem de importância dos temas na base inteira. Embora todos os pedidos estejam classificados como atrasados nos metadados, alguns textos dizem que o pedido ainda não foi recebido ou foi cancelado (R2, R3, R5 e R9), e outros não mencionam atraso no comentário (R13 e R17).

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.72 | 3 | 2 | PR | utilidades_domesticas | atrasado | Demorou de mais pra entrega. |
| R2 | sim | 0.57 | 3 | 1 | RJ | esporte_lazer | atrasado | Cancelei esse pedido, nem era para chegar o e-mail em questão e tenho outros 2 pedidos pendentes, com atraso na entrega, sem qualquer suporte das lannister. |
| R3 | sim | 0.72 | 3 | 1 | RS | cama_mesa_banho | atrasado | Estou esperando o pedido sei que o correio sempre atrasa. |
| R4 | sim | 0.64 | 3 | 2 | RJ | relogios_presentes | atrasado | Está demorando a chegar o meu produto ! |
| R5 | sim | 0.69 | 3 | 1 | PA | beleza_saude | atrasado | Meu pedido ainda não foi entregue e ta com dois dias de atraso,isso é um absurdo. |
| R6 | sim | 0.86 | 3 | 1 | SP | instrumentos_musicais | atrasado | a entrega demorou e o produto chegou com defeito. |
| R7 | sim | 0.49 | 2 | 1 | BA | cama_mesa_banho | atrasado | É a primeira vez que há atraso nos meus pedidos. |
| R8 | sim | 0.60 | 2 | 3 | MG | informatica_acessorios | atrasado | não do 5 estrela pois atrasou pedido. |
| R9 | sim | 0.56 | 2 | 1 | PE | cool_stuff | atrasado | Até o momento não recebi o pedido, também não recebi informações do atraso de entrega do pedido. |
| R10 | sim | 0.59 | 2 | 1 | SP | cama_mesa_banho | atrasado | Entrega atrasada. |
| R11 | sim | 0.67 | 3 | 1 | MG | cool_stuff | atrasado | PRODUTO CHEGOU COM MUITO ATRASO, EMBALAGEM DANIFICADA, PRODUTO VEIO FALTANDO UMA PORCA(PARAFUSO) PARA MONTAGEM, CORREIO NÃO ENTREGOU, TIVE QUE BUSCÁ-LO. NÃO RECOMENDO. |
| R12 | sim | 0.67 | 3 | 3 | CE | moveis_cozinha_area_de_servico_jantar_e_jardim | atrasado | O produto chegou como o esperado mais no decorrer da entrega meu produto veio amassado e caixa rasgada. sei que a culpa fio dos correios. |
| R13 | sim | 0.70 | 2 | 3 | SP | esporte_lazer | atrasado | Produto entregue no tempo correto. Porém a embalagem estava danificada e consequentemente o lacre do produto foi aberto! |
| R14 | sim | 0.73 | 3 | 4 | BA | casa_conforto | atrasado | recomendo. Houve o atraso da entrega , mais o produto é perfeito! |
| R15 | sim | 0.62 | 3 | 4 | BA | esporte_lazer | atrasado | gostei e o atraso foi por conta dos correios aqui. |
| R16 | sim | 0.65 | 3 | 5 | GO | pet_shop | atrasado | O produto foi entregue em perfeito estado. Houve um pequeno atraso na entrega, mas creio devido ao fim de ano. As coleirinhas são lindas e resistentes. Recomendo. |
| R17 | sim | 0.69 | 3 | 5 | BA | papelaria | atrasado | Gostei muito do produto. Chegou perfeito e tem excelente qualidade. |
| R18 | sim | 0.61 | 3 | 2 | BA | beleza_saude | atrasado | Recomendo. óculos lindo, chegou em perfeito estado. Mas não foi entregue dentro do prazo. |

## Metadados: período

### Do que os clientes reclamaram nas compras de novembro de 2017?

Status: `respondida`

Busca (overview): "nas compras de novembro de 2017 o produto veio com defeito"; "nas compras de novembro de 2017 a entrega atrasou ou demorou muito"; "nas compras de novembro de 2017 não recebi o pedido"; "nas compras de novembro de 2017 o produto era diferente do anunciado"; "nas compras de novembro de 2017 o vendedor não respondeu"

Filtros: purchase_month_num >= 201711, purchase_month_num <= 201711

Entre as avaliações recuperadas de compras de novembro de 2017, os clientes reclamaram de produtos defeituosos ou mal acabados, itens diferentes do anunciado ou do comprado, atrasos e não recebimento das encomendas. Também aparecem queixas sobre pedidos incompletos e falta de resposta dos vendedores.

- Há reclamações de produtos com defeitos, acabamento ruim ou divergências no pedido: partes quebradas, zíper defeituoso, produto mal acabado, item com defeito e produto diferente do comprado. (R1, R2, R3, R4)
- Clientes relataram que o produto recebido não correspondia ao anúncio, à foto ou às características informadas, incluindo um caso em que o rótulo indicava ausência de lactose, mas o produto continha lactose. (R13, R14, R15, R16)
- Também houve queixas de atraso ou demora na entrega. Nos textos, os clientes mencionam prazo ultrapassado, entrega atrasada ou demora; em R8, o cliente informa que o atraso foi resolvido rapidamente. (R5, R6, R7, R8)
- Alguns clientes afirmaram não ter recebido o pedido mesmo após a previsão ou a indicação de entrega. Em R11, o texto relata não recebimento, embora os metadados classifiquem a entrega como no prazo. (R9, R10, R11, R12)
- Foram relatados problemas de comunicação com os vendedores, incluindo ausência de resposta, além de pedido incompleto e produto atrasado sem retorno da loja. (R17, R18, R19, R20)

Limitações: As avaliações recuperadas são uma amostra por similaridade, portanto não permitem afirmar que esses foram todos os tipos de reclamação nem ordenar os temas por frequência na base inteira. Os percentuais do panorama descrevem o recorte geral e não a frequência de cada reclamação; além disso, classificações dos metadados, como atraso ou entrega no prazo, não substituem o relato textual do cliente.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.72 | 3 | 1 | RJ | cine_foto | atrasado | Dia 18 de dezembro de 2017, o produto veio com uma das partes quebrada e outra mal confeccionada (com um encaixe mal feito). Solicito a troca deste produto defeituoso por outro em perfeito estado. |
| R2 | sim | 0.57 | 3 | 1 | RJ | malas_acessorios | no_prazo | O zíper veio com defeito. |
| R3 | sim | 0.60 | 3 | 3 | RJ | automotivo | no_prazo | O produto que veio não vale o que paguei, mau acabado e irregular. |
| R4 | sim | 0.66 | 3 | 1 | PE | consoles_games | no_prazo | Meu produto veio com defeito e comprei um e veio outro no lugar. |
| R5 | sim | 0.65 | 3 | 2 | RJ | brinquedos | atrasado | Comprei o produto no fim de novembro e o prazo de entrega já passou. |
| R6 | sim | 0.59 | 3 | 1 | SE | relogios_presentes | atrasado | Entrega atrasada. |
| R7 | sim | 0.45 | 3 | 3 | MG | perfumaria | no_prazo | Demorou muito pra chegar. |
| R8 | sim | 0.58 | 3 | 3 | SP | moveis_cozinha_area_de_servico_jantar_e_jardim | no_prazo | Atrasou na entrega de um item mas foi resolvido muito rapido. |
| R9 | sim | 0.68 | 3 | 1 | RJ | utilidades_domesticas | atrasado | Não recebi o pedido. |
| R10 | sim | 0.61 | 3 | 1 | SP | informatica_acessorios | atrasado | Produto comprado e pago dia 17/11/2017 com previsão de entrega até 15/12. Mas nada! |
| R11 | sim | 0.58 | 3 | 1 | SP | fashion_bolsas_e_acessorios | no_prazo | Disseram que entregaram meu pedido em 30///2017 e não entregaram, quero meu dinheiro de volta. |
| R12 | sim | 0.53 | 3 | 1 | RJ | cama_mesa_banho | atrasado | nao posso avaliar pois ainda nao recebi.26/12/2017. |
| R13 | sim | 0.65 | 3 | 1 | RS | beleza_saude | no_prazo | Recebi o produto diferente do que foi anunciado e comprado. |
| R14 | sim | 0.54 | 3 | 2 | SP | telefonia | no_prazo | Produto anunciado não condiz com o aparelho. |
| R15 | sim | 0.51 | 3 | 1 | SC | esporte_lazer | no_prazo | o produto anunciado é diferente do entregue. No rotulo no site diz: zero lactose. O produto possui lactose. |
| R16 | sim | 0.59 | 3 | 2 | SP | pet_shop | no_prazo | Foi aberto chamado no site ontem dia 22/11, pois o produto recebido é diferente da foto do anuncio. |
| R17 | sim | 0.63 | 3 | 1 | PI | moveis_decoracao | atrasado | produto atrasado sem resposta da loja. |
| R18 | sim | 0.55 | 3 | 1 | MT | ferramentas_jardim | no_prazo | Foi comprado 2 unidades e só veio uma, mandei 4 email pro vendedor e até agora sem resposta. |
| R19 | sim | 0.56 | 3 | 1 | MT | esporte_lazer | nao_entregue | comprei tento entra em contado eles nao responde, e nao entregam o iten. |
| R20 | sim | 0.57 | 3 | 1 | SP | sem_categoria | nao_entregue | Vende produto indisponível, não resolve o problema do cliente, não responde os e-mails. |

## Metadados: estado

### O que os clientes de São Paulo reclamam sobre a entrega?

Status: `respondida`

Busca (overview): "a entrega do pedido em São Paulo atrasou e demorou muito"; "não recebi o pedido em São Paulo"; "o pedido não chegou em São Paulo"; "o produto chegou danificado por causa da entrega em São Paulo"; "o rastreamento da entrega em São Paulo não foi atualizado"; "o entregador não conseguiu entregar o pedido em São Paulo"

Filtros: state in ['SP']

Clientes de São Paulo reclamam principalmente de atrasos, pedidos não recebidos ou entregas não realizadas, muitas vezes acompanhados de falta de esclarecimentos. Também aparecem queixas sobre rastreamento desatualizado, roteamento incorreto e produtos danificados ou com embalagem inadequada.

- Há relatos de entrega atrasada ou além do prazo, incluindo pedidos que ficaram parados durante o transporte. (R1, R3, R4, R8, R11, R17)
- Clientes mencionam pedidos que não foram recebidos ou cuja entrega não foi realizada, inclusive casos em que o sistema indicava entrega, mas o cliente afirma não ter recebido. Em um caso, apenas parte dos produtos foi recebida. (R2, R5, R6, R7, R10, R18, R19, R20)
- Há reclamações sobre falta de esclarecimentos e dificuldade para acompanhar o pedido, incluindo rastreamento sem atualização ou com atualização tardia. (R2, R15, R16, R19)
- Alguns clientes relatam problemas no percurso ou no destino da entrega, como envio para Campinas em vez do local correto e pedido encaminhado de São Paulo para Belém sem chegar ao destino. (R5, R9)
- Também há queixas sobre a condição da entrega: embalagem em péssimo estado e produtos que chegaram riscados, manchados, quebrados ou avariados. (R12, R13, R14)

Limitações: As avaliações são uma amostra recuperada por similaridade, portanto não permitem afirmar a frequência ou a ordem de prevalência dessas reclamações entre todos os clientes de São Paulo. Alguns metadados divergem do texto: por exemplo, R3 está classificada como entrega no prazo, mas o cliente menciona atraso; R7, R9, R10, R18 e R20 também têm metadados de entrega no prazo ou status distinto do relato textual. Os percentuais do panorama são do recorte geral e não foram usados para quantificar as reclamações de São Paulo.

| ID | Citada | Similaridade | Relevância | Nota | Estado | Categoria | Entrega | Texto |
|---|---|---|---|---|---|---|---|---|
| R1 | sim | 0.72 | 3 | 1 | SP | moveis_decoracao | no_prazo | demorou mto pra fazer a entrega. |
| R2 | sim | 0.59 | 3 | 1 | SP | beleza_saude | nao_entregue | PEDIDO NÃO ENTREGUE. NENHUMA ESCLARECIMENTO SOBRE ATRASO DA ENTREGA. |
| R3 | sim | 0.66 | 3 | 5 | SP | esporte_lazer | no_prazo | Demanda alta. Creio q pela alta demanda de pedidos , o meu foi entregue um pouco atrasado.mas é compreensível. |
| R4 | sim | 0.69 | 3 | 1 | SP | moveis_escritorio | atrasado | entrega muito atrasada. |
| R5 | sim | 0.71 | 3 | 1 | SP | telefonia | atrasado | Meu pedido não foi entregue De São Paulo SP foi para em Belém PA e nunca chegou aqui. |
| R6 | sim | 0.66 | 3 | 2 | SP | moveis_sala | atrasado | não recebi. |
| R7 | sim | 0.59 | 3 | 1 | SP | beleza_saude | no_prazo | Nao recebi o produto o carteiro Paulo foi assaltado perto da minha resistência quero uma resposta pois esta constando q eu recebi mas nao recebi vou no procom e processar por danos morais sem resposta. |
| R8 | sim | 0.59 | 3 | 1 | SP | bebidas | atrasado | O pedido seria entregue até 14/8 ,mas até o momento não recebi. |
| R9 | sim | 0.74 | 3 | 1 | SP | moveis_decoracao | no_prazo | Pedido feito para São Paulo e foi despachado para Campinas. Não foram capazes de entregar no local correto. |
| R10 | sim | 0.59 | 3 | 1 | SP | beleza_saude | nao_entregue | Não chego meu pedido. |
| R11 | sim | 0.61 | 3 | 1 | SP | perfumaria | atrasado | o meu produto não chegou. segundo o rastreio está parado em Ribeirão Preto sp. |
| R12 | sim | 0.68 | 3 | 1 | SP | relogios_presentes | no_prazo | Produto mal embalado. Produto chegou com risco e manchado. |
| R13 | sim | 0.61 | 3 | 3 | SP | market_place | no_prazo | O quadro foi entregue pelos correios e chegou com uma madeira atrás quebrada e a tela do quadro danificada afundada.ou seja.chegou avariado o produto. |
| R14 | sim | 0.58 | 3 | 1 | SP | cool_stuff | no_prazo | Produto chegou com a embalagem em péssimo estado, faltando componentes para montagem e danificado, nao recomendo. |
| R15 | sim | 0.61 | 3 | 4 | SP | moveis_decoracao | no_prazo | Demora para atualizar o rastreamento do produto. ( exemplo o produto já tinha chegado, mas a atualização que o produto estava no transporte, só apareceu no outro dia.). |
| R16 | sim | 0.49 | 3 | 1 | SP | moveis_decoracao | atrasado | A ultima atualização do meu pedido foi em 28/11. Ngm dá uma satisfação! |
| R17 | sim | 0.61 | 3 | 1 | SP | bebes | atrasado | Fiquei acompanhado o produto é ele estálava parado em Ribeirão Preto desdo dia 27 de fevereiro. Só agora, depois da data que está vindo pra São Paulo. |
| R18 | sim | 0.62 | 3 | 1 | SP | audio | atrasado | a Entrega não foi realizada. |
| R19 | sim | 0.47 | 3 | 3 | SP | relogios_presentes | no_prazo | comprei 3 produtos e até agora só recebi 1, a gente não consegue acompanhar os pedidos! |
| R20 | sim | 0.49 | 3 | 1 | SP | esporte_lazer | no_prazo | Meu pedido não foi entregue, porém já recebi e-mail informando que foi entregue, e quero meu pedido. |

## Fora do escopo

### Qual é a previsão do tempo para São Paulo amanhã?

Status: `fora_do_escopo`

A pergunta está fora do escopo da base. Consigo responder sobre a experiência dos clientes da Olist, como produtos, entregas, vendedores e atendimento.


## Sem evidências suficientes

### O que os clientes dizem sobre o programa de cashback em criptomoedas da loja?

Status: `evidencia_insuficiente`

Busca (specific): "o cashback em criptomoedas da loja não funcionou"; "não recebi o cashback em criptomoedas da loja"

Filtros: nenhum

Não encontrei avaliações suficientes para responder com segurança. Tente reformular a pergunta ou remover filtros.

