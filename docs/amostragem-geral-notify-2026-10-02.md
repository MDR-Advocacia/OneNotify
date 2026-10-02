# Amostragem geral do Notify — 02/10/2026

Leituras somente no PostgreSQL produtivo do Notify (PC129) e do Flow (EC2).
Nenhum status, tarefa, arquivo ou configuração foi alterado. Os exemplos abaixo
usam apenas IDs internos, sem reproduzir peças ou dados das partes.

## A categoria da notificação não define o conteúdo do arquivo

Entre **74.598 dossiês distintos NPJ/data criados de abril a 02/10/2026**:

| Mês de criação | Só andamento de publicação | Publicação e documento | Documento sem andamento DJ/DO | Nenhum dos dois | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Abr | 1.616 | 739 | 158 | 33 | 2.546 |
| Mai | 17.509 | 4.848 | 1.818 | 337 | 24.512 |
| Jun | 7.984 | 1.717 | 612 | 216 | 10.529 |
| Jul | 9.199 | 1.797 | 792 | 179 | 11.967 |
| Ago | 8.214 | 2.220 | 1.016 | 199 | 11.649 |
| Set | 8.540 | 2.453 | 918 | 255 | 12.166 |
| Out (parcial) | 821 | 306 | 79 | 23 | 1.229 |
| **Total** | **53.883** | **14.080** | **5.393** | **1.242** | **74.598** |

Dos 5.393 dossiês com documento e sem andamento DJ/DO, 4.490 já tinham algum
texto extraído, 837 continham arquivo que pede OCR e 4.046 tinham URL em algum
texto. Em 3.331, uma busca ampla encontrou termos como intimação, decisão ou
sentença. Essas contagens se sobrepõem e **não** classificam o ato. A amostra
qualitativa encontrou sentença integral (`167006`), decisão (`159341`),
intimação (`159594`), material interno de subsídio (`168573`), TXT com link de
arquivo não obtido (`157175`) e PDF sem texto (`157123`). Portanto “sem
andamento DJ/DO” não equivale a “sem publicação”.

## Primeira triagem textual, com corte fixo

Nos 1.000 grupos processados mais recentes criados entre 02/09 e **02/10 às
18h UTC**, a versão atual da prévia retornou:

| Resultado | Grupos |
| --- | ---: |
| Publicação isolada | 547 |
| Publicação com documento de correspondência textual forte | 11 |
| Publicação com conteúdo ainda em revisão | 348 |
| Possível ato judicial em documento, sem andamento DJ/DO | 37 |
| Sem andamento DJ/DO nem sinal forte no texto documental | 57 |

O sinal documental procura um título de sentença, decisão, despacho,
intimação, citação, acórdão ou ato ordinatório junto de CNJ no PDF extraído.
É uma **fila de investigação**, não prova de publicação oficial nem decisão de
providência. Os 11 documentos com correspondência forte também precisam de
conferência de amostra antes de qualquer consolidação automática.

Ainda nesse recorte, 92 grupos continham mais de um texto distinto de
andamento de publicação. Em 113 documentos, a comparação encontrou um trecho
longo em comum com a publicação, mas não a equivalência estrita exigida pela
prévia. Esses dois conjuntos mostram por que a separação por ato e a leitura
dos candidatos rejeitados são necessárias. O sinal de título + CNJ dos 37
documentos é deliberadamente estreito; não mede quantos atos documentais a
regra deixou de encontrar.

## O que “Tratada” permite reconstruir

No banco atual há 54.770 linhas `Tratada`, 92.516 `Processado` e 11.093
`Arquivado`; são **linhas de notificação**, não dossiês. Das tratadas, 1.074
têm `gerou_tarefa=1`. O registro guarda o estado atual, sem tabela de
transições ou trigger de auditoria. O endpoint que marca `Tratada` não grava
data, autor ou motivo; `data_processamento` é normalmente da RPA e
`responsavel` é a pessoa designada para a fila. A rotina de conciliação por
planilha pode regravar `data_processamento`, mas isso tampouco cria histórico.
As tabelas de log registram execução da RPA, e `track_commit_timestamp` do
PostgreSQL está desativado. Backups podem delimitar um intervalo de mudança,
não recuperar uma trilha completa.

## Conciliação reversa: amostra estratificada de 180 dossiês

Seleção determinística de 30 dossiês por estrato, sem escolher casos pelo
resultado. Para os recentes, o recorte contém grupos criados em setembro e
outubro; para `Tratada`, grupos criados antes de junho (notificações de
fevereiro a abril). A busca no Flow usou **CNJ e data da notificação ±7 dias**;
a correspondência textual forte exige contenção de fragmentos de cinco
palavras ≥0,8. Ela aponta candidatos, não substitui leitura do ato.

| Estrato (30 cada) | Flow mesmo CNJ ±7d | Texto forte | Texto forte + auditoria de tarefa no registro Flow |
| --- | ---: | ---: | ---: |
| Recente: publicação e documento | 28 | 21 | 10 |
| Recente: publicação isolada | 29 | 26 | 10 |
| Recente: só documento | 15 | 2 | 1 |
| Antigo `Tratada`: publicação e documento | 0 | 0 | 0 |
| Antigo `Tratada`: publicação isolada | 0 | 0 | 0 |
| Antigo `Tratada`: só documento | 0 | 0 | 0 |

Os dois positivos fortes só de documento são PDFs com sentença: no grupo
`157404`, o melhor registro Flow estava `IGNORADO`; no `157174`, estava
`AGENDADO` e tinha duas linhas de auditoria de tarefa. Esses estados não
autorizam equiparar os outros documentos da janela ao mesmo ato. Nos 90
antigos `Tratada`, nenhum melhor par apareceu no Flow na janela de sete dias,
mas **78/90 tinham alguma tarefa do mesmo CNJ** no espelho Legal One em até
30 dias. Os 90 tinham `gerou_tarefa=0`. A tarefa do processo pode ter outro
motivo: essa comparação não comprova tratamento de cada notificação. O Flow
tem cobertura a partir de 2026, mas esse recorte antigo é de fevereiro a
abril e não serve para medir a conciliação dos meses recentes.

## Decisões que a análise permite testar no Notify

1. Classificar **cada andamento e cada arquivo**, mantendo sua origem e a
   janela de três dias: publicação no andamento; possível ato judicial no
   documento; comunicação interna/subsídio; link não resolvido; imagem sem
   texto; conteúdo indeterminado.
2. Para publicação ou possível ato documental, procurar candidatos históricos
   por CNJ/data e comparar texto. Só considerar “já coberto” quando o mesmo
   ato e a decisão registrada estiverem ligados; `IGNORADO` significa decisão
   de não agir, não identidade por si só.
3. Dividir a fila por idade. Casos antigos não devem gerar tarefas retroativas
   em massa nem uma auditoria automática de prazos; podem receber destino
   histórico após reconciliação e critérios operacionais explícitos. Documento
   antigo com obrigação ainda atual exige análise própria. O corte de idade e
   o destino dos resíduos seguem **sem decisão**.

Próxima validação: ler os 11 positivos da triagem e uma amostra de negativos,
inspecionar os dois PDFs documentais ligados ao Flow, testar resolução de TXT
e medir o que continua sem texto. Até lá, os números são cobertura potencial,
não taxa de acerto da automação.
