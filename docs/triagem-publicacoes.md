# Primeira faixa de triagem de publicações do BB

O módulo `triagem_publicacoes.py` lê um dossiê `NPJ + data_notificacao` já
capturado pelo Notify e produz um plano de leitura. Ele não muda o estado das
notificações, não descarta documentos e não envia itens ao Flow. O contrato
atual de intake do Flow continua agrupado por `NPJ + data_notificacao`.

## Regras implementadas

- Reconhece os andamentos `PUBLICACAO DJ/DO` ou `PUBLICACAO DJEN` pelo título.
  Linhas copiadas do mesmo andamento são uma única publicação; textos ou datas
  diferentes permanecem atos distintos.
- Uma publicação com texto útil, sem outros andamentos nem documentos na janela,
  entra em `PUBLICACAO_ISOLADA`.
- Cada documento da janela é comparado **individualmente** com a publicação.
  Texto integral normalizado igual é repetição textual. Um PDF com cabeçalho
  diferente pode entrar em `PUBLICACAO_COM_REPETICOES_COMPROVADAS` quando há um
  núcleo final idêntico longo, CNJ único igual e termos decisórios/prazos
  preservados. A evidência e a razão ficam no resultado.
- TXT de erro ou link, PDF sem texto, OCR pendente, extração truncada, texto
  longo demais, outro andamento e vários atos distintos permanecem em revisão.
  Um hash igual entre dois arquivos não prova que sejam a publicação.
- O resultado preserva índices dos andamentos, nome/hash dos arquivos e motivos
  de revisão. O arquivo original continua acessível no dossiê.

O nome `COM_REPETICOES_COMPROVADAS` indica que a regra textual passou. Ele não
substitui a conferência jurídica do piloto nem prova que todos os documentos
da janela pertençam à notificação que gerou o grupo.

## Medição de 02/10/2026

Consulta somente leitura no PostgreSQL produtivo do Notify, sobre os **1.000
grupos processados mais recentes** criados dentro dos últimos 30 dias. O mesmo
código de triagem foi transmitido para execução em memória no container da API;
nenhum arquivo ou status produtivo foi alterado.

| Resultado | Grupos |
| --- | ---: |
| Publicação isolada | 549 |
| Publicação com repetição textual forte | 11 |
| Revisão necessária | 346 |
| Sem publicação DJ/DO no dossiê | 94 |

Entre os documentos, 13 passaram no critério de núcleo final idêntico e CNJ
igual. Os 11 grupos correspondentes ainda não tiveram validação individual de
conteúdo; a amostra é recente e limitada a 1.000 grupos, sem estimativa de
acurácia nem extrapolação para todo o backlog.

Nos cinco dossiês já discutidos, o caso 1 (publicação + PDF) passou no critério
de núcleo; o caso 2 teve PDF com mesmo núcleo, mas o TXT de erro ficou em
revisão; o caso 3 (seguro) não foi conciliado; os casos 4 e 5 não têm publicação
DJ/DO capturada. Isso é coerente com a leitura da amostra, sem torná-la um
conjunto de treinamento suficiente.

## Como executar uma prévia local

```bash
python scripts/preview_triagem_publicacoes.py --days 30 --limit 500
python scripts/preview_triagem_publicacoes.py --npj 'NPJ' --data 'DD/MM/AAAA'
```

O comando só imprime totais agregados e não envia ao Flow. Para avançar da
prévia à operação: conferir uma amostra dos 11 casos e dos candidatos rejeitados,
registrar a decisão por documento, e definir no Flow a entrega de um item por
ato com suas origens. A sincronização atual por grupo não consome esta triagem;
ativá-la ou liberar backfill agora repetiria a lacuna de granularidade.
