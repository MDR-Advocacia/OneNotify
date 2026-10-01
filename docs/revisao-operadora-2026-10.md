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
