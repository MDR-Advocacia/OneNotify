# Revisão dirigida de cinco dossiês do Notify

Fonte: banco produtivo do Notify, consulta somente leitura em 01/10/2026. A amostra usa notificações de 22 a 25/09, já processadas. Os IDs são âncoras para localizar o dossiê `NPJ + data`; não indicam que um documento pertence à notificação de mesmo ID. A análise automática serviu apenas para variar a amostra e **não rotula os atos**.

| Caso | ID âncora | Composição observada | Pergunta que o caso ajuda a responder |
| --- | ---: | --- | --- |
| 1 | 164455 | Uma publicação e um PDF com texto extraível; três tipos de notificação no dossiê | Como a operadora reconhece o mesmo ato ou um complemento? |
| 2 | 164118 | Uma publicação, um TXT e um PDF; três tipos de notificação | Os dois documentos têm papéis diferentes? O link do TXT exige consulta externa? |
| 3 | 163811 | Uma publicação e um PDF curto; só uma notificação de publicação | O documento da janela se relaciona à publicação ou é apenas vizinho temporal? |
| 4 | 167236 | Duas notificações documentais, um TXT e nenhum andamento de publicação | O que permite concluir a partir do link e quando é preciso abrir o portal? |
| 5 | 168581 | Uma notificação documental, PDF imagem sem texto extraído e nenhum andamento de publicação | Como a operadora decide o que fazer quando a peça não é pesquisável? |

A página `/revisao` nomeia cada caso e pergunta sobre o conteúdo específico de cada arquivo, sem mostrar os scores usados na seleção. A publicação e o texto extraído aparecem lado a lado. O PDF original pode ser examinado no visualizador incorporado, com páginas e zoom; o caso 5 abre diretamente nesse modo porque a extração não produziu texto útil. Para TXT com link de tribunal, a página também oferece o link original.

As perguntas livres pedem trecho ou página, comando, prazo, providência e o motivo da decisão. Para copiar as respostas, o formulário exige escolhas e descrições com pelo menos 120 caracteres por documento e no fechamento, e 80 caracteres sobre a consulta externa. Isso não substitui a revisão qualitativa das respostas. O rascunho fica no navegador da operadora; o botão **Copiar respostas para o Teams** produz o texto a enviar. A página não grava tratamento, não altera o status histórico das notificações e não envia conteúdo ao Flow.

O frontend e a API precisam ser implantados juntos. A API oferece apenas leitura da amostra. Após receber as respostas, revisar os motivos em cada caso com a operadora antes de transformar as categorias do formulário em regras automáticas.

## Retorno inicial da operadora em 01/10

Fonte: respostas enviadas por Jesebel a Rildon após usar `/revisao`, recebidas neste chat em 01/10. São julgamentos operacionais preliminares; as justificativas livres frequentemente foram curtas e completadas com pontuação repetida para atingir o mínimo de caracteres. Assim, as escolhas ajudam a localizar critérios e dúvidas, mas ainda não servem como rótulos verificados para automação.

| Caso | Leitura da operadora | Ponto a confirmar |
| --- | --- | --- |
| 1 | O PDF reproduz a intimação sobre custas; uma tarefa já existente poderia cobrir ambos. | Qual tarefa e qual prazo ela verificaria antes de dispensar nova ação? A resposta não registrou o prazo da intimação. |
| 2 | O PDF reproduz o ato da publicação e a tarefa poderia ser única; a necessidade de abrir o link do TXT ficou inconclusiva. | Distinguir a intimação já disponível do arquivo adicional que o alerta diz não ter sido obtido. A justificativa chama de “PDF” a peça que apenas aponta para um texto externo, enquanto o PDF disponível contém o ato; confirmar se ela se referia ao TXT. Verificar se o link revela outra peça essencial. |
| 3 | A publicação geraria tarefa; o PDF de seguro foi chamado de “subsídio”, mas a operadora pede confirmação nos autos. | Subsídio é material solicitado ao BB para defesa, acordo ou outra finalidade; não se define pela publicação e pode ter ciclo próprio de pedido/resposta. O PDF de restituição tem ligação temática com a sentença, mas isso não prova que seja resposta de subsídio deste NPJ nem que pertença ao ato publicado. Conferir pedido, resposta, datas e vínculo quando os dados do robô de monitoramento de subsídios estiverem disponíveis. |
| 4 | O TXT, sozinho, não permite conhecer o conteúdo; a operadora buscaria o documento no tribunal/processo e decidiria a tarefa depois. | Registrar resultado da tentativa de acesso e manter pendência explícita até conhecer o ato. |
| 5 | A operadora viu providência de pagamento e encaminharia ao responsável da pasta, mas consultaria o processo. | Não há publicação DJ/DO capturada neste dossiê. O PDF é uma intimação cartorária de protesto de certidão de crédito judicial, expedida em 16/09, com limite de pagamento em 21/09. A data 22/09 é a data da notificação no portal BB; o registro só foi criado no Notify em 29/09. “Agendar antes do vencimento” não atende esse caso sem verificar pagamento/protesto e definir escalonamento. Confirmar vínculo ao NPJ e natureza da cobrança. |

Hipótese de classificação a validar: uma peça pode ser (a) outra captura do mesmo ato, (b) material de subsídio associado a um pedido/resposta do BB, (c) comunicação independente com providência, ou (d) conteúdo ainda desconhecido por falha de obtenção. A amostra não define limiares de comparação nem autoriza baixa automática. O formulário atual valida quantidade de caracteres, não substância; respostas preenchidas com pontuação passaram. Num próximo ciclo, preferir campos fechados para evidência, prazo, tarefa existente e resultado de consulta, com texto explicativo complementar.

Consulta somente leitura ao Notify em 01/10: os cinco IDs âncora ainda tinham status `Processado`. Esse status indica que a RPA processou a notificação, mas não demonstra se houve tarefa ou pagamento em outro sistema. O caso 5 requer conferência operacional prioritária: `data_notificacao=22/09`, criação no Notify em 29/09 às 19h35 BRT (`data_criacao` 22h35 UTC), `human_status=NOVO`, `flow_status=ERRO_ENVIO` e `gerou_tarefa=0` no Notify. Esses campos não comprovam ausência de tarefa fora dele.

No caso 4, o “original” que o Notify tem é o TXT baixado da seção DOCUMENTOS do portal BB. Seu conteúdo diz que arquivos adicionais da comunicação não foram acessados pelo Tribunal/DJE por erro ou indisponibilidade e aponta a um link do PJe. A RPA atual baixa o TXT disponível, mas não segue o link para recuperar outra peça; o dossiê não tem andamento `PUBLICACAO DJ/DO`. Uma requisição HEAD sem autenticação ao link específico retornou HTTP 403 em 01/10, o que não informa se a operadora consegue acessá-lo no portal. Não está demonstrado que exista um PDF adicional acessível nem a causa exata da falha na origem.

No caso 2, a resposta literal da operadora para o TXT foi “Não consigo concluir” e “Não consigo decidir” sobre abrir o link. Ela escreveu que o “PDF não me fornece o texto, indica onde o texto encontra-se”, embora o PDF do dossiê contenha o texto integral da intimação; pode ter se referido ao TXT por engano. No fechamento, disse que a publicação basta para agendar e que o TXT exigiria análise do processo. Não tratar a possível troca de nomes como fato confirmado.
