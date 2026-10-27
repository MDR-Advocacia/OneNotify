# Primeira faixa de triagem de publicações do BB

O módulo `triagem_publicacoes.py` lê um dossiê `NPJ + data_notificacao` já
capturado pelo Notify e produz um plano de leitura. Ele não muda o estado das
notificações, não descarta documentos e não envia itens ao Flow. O contrato
atual de intake do Flow continua agrupado por `NPJ + data_notificacao`.
Para a prévia, todas as linhas do mesmo NPJ/data são reunidas; escolher o
`MAX(andamentos)` do grupo pode esconder uma publicação presente em outra
linha. O resultado mantém os tipos de notificação recebidos e as referências
de cada arquivo nas linhas, sem inferir qual aviso causou sua inclusão.

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
- Quando a publicação e o PDF apontam para um único **mesmo ID de documento do
  PJe**, a prévia também pode ligar os dois se houver pelo menos 40 tokens
  consecutivos em comum, CNJ único igual e os mesmos termos decisórios/prazos.
  O ID isolado não basta; PDFs com outros processos ou IDs permanecem em
  revisão. A ligação conserva o PDF e registra o ID da peça como evidência.
- TXT de erro ou link, PDF sem texto, OCR pendente, extração truncada, texto
  longo demais, outro andamento e vários atos distintos permanecem em revisão.
  Um hash igual entre dois arquivos não prova que sejam a publicação.
- O TXT do BB com campo explícito `Link documento:` é identificado como
  `LINK_DOCUMENTO_PENDENTE`. A prévia conserva o endereço e indica que o
  original precisa ser obtido; não abre links nem supõe que seu conteúdo seja
  igual à publicação.
- Sem andamento DJ/DO, um PDF ainda pode trazer sentença, decisão ou intimação.
  Título de ato judicial junto de CNJ no texto produz
  `POSSIVEL_ATO_EM_DOCUMENTO`, sempre para investigação; não prova publicação
  oficial. Os demais ficam em `SEM_ANDAMENTO_PUBLICACAO`, que também **não**
  afirma ausência de publicação em outra fonte.
- O tipo da **notificação recebida** e o conteúdo do arquivo são sinais
  diferentes. Um aviso documental com peça judicial não vira automaticamente
  trabalho da operadora especializada; um aviso chamado “andamento de
  publicação” também pode conter somente outro tipo de andamento. A rota
  operacional exige verificar o ato e sua cobertura em outros fluxos.
- O resultado preserva índices dos andamentos, nome/hash dos arquivos e motivos
  de revisão. O arquivo original continua acessível no dossiê.

O nome `COM_REPETICOES_COMPROVADAS` indica que a regra textual passou. Ele não
substitui a conferência jurídica do piloto nem prova que todos os documentos
da janela pertençam à notificação que gerou o grupo.

## Plano individual na prévia local — 27/10/2026

O resultado também traz `publicacoes_para_analise_individual`,
`itens_publicacao`, `documentos_pendentes` e `andamentos_pendentes`. Cada item
de publicação aponta para seus índices de andamento, PDFs repetidos ligados
unicamente a ele e PDFs ainda candidatos em revisão. O relatório privado por
caso inclui esse mapa sem duplicar o texto das peças. Uma publicação com texto útil
continua identificada para a próxima análise mesmo quando um PDF, TXT ou outro
andamento do mesmo NPJ/data exige revisão. Isso **não** libera o dossiê inteiro:
`apto_para_etapa_publicacao` continua falso enquanto houver pendência. JSON
inválido em qualquer linha suspende até a indicação individual, pois pode
ocultar outra publicação.

Quando há várias publicações distintas no mesmo dia, a prévia compara cada
documento com cada uma. Uma repetição textual ligada a uma única publicação
guarda o ID dessa publicação; compatibilidade com mais de uma permanece para
conferência. Cada documento indica a próxima análise sugerida, preservando os
demais arquivos da janela. Isso prepara decisões **por item**, ainda sem
conciliação ou providência automática no Flow.

A listagem da prévia exclui linhas cuja `origem` é `migracao`, conforme a decisão
de Rildon de deixar o legado Ajus fora do recorte atual. Isso não altera os
registros produtivos nem a seleção existente do sincronizador Flow. O comando
agregado passou a contar publicações identificadas individualmente e documentos
pendentes, além dos estados por dossiê. As contagens de 02/10 abaixo são a
fotografia anterior a este bloco e não foram recalculadas.

## Medição de 02/10/2026

Consulta somente leitura no PostgreSQL produtivo do Notify, sobre os **1.000
grupos processados mais recentes** criados de 02/09 até 02/10 às 18h UTC. O mesmo
código de triagem foi transmitido para execução em memória no container da API;
nenhum arquivo ou status produtivo foi alterado.

| Resultado | Grupos |
| --- | ---: |
| Publicação isolada | 546 |
| Publicação com repetição textual forte | 11 |
| Revisão necessária | 350 |
| Possível ato judicial em documento, sem andamento DJ/DO | 44 |
| Sem andamento DJ/DO nem sinal forte no texto documental | 49 |

Esta medição reúne todas as linhas de cada dossiê. A leitura anterior por
`MAX` no JSON apontava 547/11/348/37/57; ela perdeu andamentos e documentos
que estavam em outras linhas da janela. Dos 44 possíveis atos em documento,
43 pertencem a grupos cujos tipos de aviso recebidos são documentais e um a
um grupo com tipo “andamento de publicação” mas sem `PUBLICACAO DJ/DO` no
conteúdo capturado. Não encaminhar esses 44 em bloco à mesma fila.
O replay em memória executou também `build_triage_preview` completo nos 1.000
grupos produtivos; os cinco totais acima se mantiveram, sem divergência causada
por eventual atualização da extração dos arquivos.

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
registrar a decisão por documento e testar se o mesmo ato já tem providência ou
decisão em outro fluxo. Esse vínculo pode tornar o aviso **sem trabalho novo no
Notify**, sem afirmar que a notificação foi tratada ali. O Notify ainda precisa
resolver TXT com link quando possível e decidir a rota de atos documentais sem
cobertura externa. A sincronização atual por grupo não consome esta triagem.

## Exportação e replay local — 27/10/2026

É possível congelar uma amostra do banco, com os textos extraídos disponíveis,
para repetir a triagem fora do PC. O exportador não altera banco, status nem
envio. O resumo por caso identifica decisões e pendências sem copiar textos das
peças ou endereços de links:

```bash
python scripts/preview_triagem_publicacoes.py --days 30 --limit 500 \
  --snapshot-out /caminho/privado/amostra.jsonl \
  --cases-out /caminho/privado/casos.jsonl
python scripts/preview_triagem_publicacoes.py \
  --input-jsonl /caminho/privado/amostra.jsonl \
  --cases-out /caminho/privado/casos-replay.jsonl \
  --publication-intake-out /caminho/privado/publicacoes-v2.jsonl
```

O snapshot e `publicacoes-v2.jsonl` contêm dados completos, **inclusive textos,
identificadores, caminhos e URLs**. Guardá-los em pasta privada e não anexá-los
ao repositório ou PR. O segundo arquivo é apenas uma prévia de payload v2,
**sem POST ao Flow**. Ele aceita somente notificações `PROCESSADO` fora do
legado de migração, com uma publicação de texto/data/CNJ único e nenhum
andamento ou documento sem equivalência demonstrada. Cada item tem ID externo
estável, um único texto de publicação para a conciliação, PDFs repetidos
preservados e proveniência da janela. Dossiês mistos e CNJs ambíguos ficam fora.

Os três tipos de saída são criados com permissão `0600` e nunca sobrescrevem um
arquivo existente; o relatório por caso ainda contém o NPJ e a evidência
técnica, inclusive o ID da peça PJe quando houver, mas não o texto ou URL.
No replay, o texto congelado é usado sem reler o arquivo original. A extração do PDF requer a
dependência `pypdf` do projeto no ambiente que faz a exportação.

Uma leitura somente local do diretório `documentos/` em 27/10 encontrou 36 PDFs
e 13 TXTs: 35 PDFs com texto extraível, um PDF com texto e imagem e oito TXTs
com `Link documento:`. É uma amostra pequena e histórica, sem base para estimar
frequências no banco. No mesmo dia, o acesso SSH ao PC funcionou, mas o serviço
Docker Desktop estava parado e a API/banco do Notify não estavam disponíveis.
Naquela checagem, **não houve replay novo em dossiês produtivos** nem validação
de OCR. O Docker foi restaurado mais tarde em 27/10, conforme a medição abaixo.

## Replay após restaurar o Docker — 27/10/2026

O código local foi executado somente em leitura sobre 100 dossiês já
`PROCESSADO` capturados de 01 a 13/10 (132 notificações). Nenhum status,
arquivo ou envio ao Flow foi alterado.

| Resultado | Grupos |
| --- | ---: |
| Publicação isolada | 50 |
| Revisão necessária | 24 |
| Sem andamento DJ/DO capturado | 24 |
| Possível ato em documento | 2 |

Foram identificadas 83 publicações individuais e 56 documentos ainda pendentes
de análise. Os dois casos `POSSIVEL_ATO_EM_DOCUMENTO` mostram por que o rótulo
é apenas uma indicação para investigar: um contém um PDF curto de intimação,
copiado em dois avisos documentais; o outro tem andamentos de regularização de
representação e juntada de procuração, mais PDFs extensos do processo (56 e
101 páginas), sem andamento DJ/DO capturado. O detector encontrou títulos de
peças judiciais no texto; isso não demonstra que exista uma publicação oficial
nova nem que o pacote inteiro seja um só ato. A análise por item deve confirmar
o conteúdo e verificar cobertura em outros fluxos antes de propor trabalho.

No mesmo retorno da RPA, os novos registros ainda estavam `PENDENTE`, sem
andamentos ou documentos extraídos. Eles ficaram fora deste replay. Esta
amostra dirigida não mede a acurácia da regra nem a proporção do backlog.

## Validação ampliada da referência PJe — 27/10/2026

Em 1.000 dossiês `PROCESSADO` capturados de 01 a 13/10 (1.254 notificações),
o replay local anterior à nova referência PJe produziu 452 publicações
isoladas, 4 dossiês com repetição comprovada, 379 em revisão, 67 possíveis
atos em documento e 98 sem andamento DJ/DO capturado. Havia 1.210 publicações
individuais, 429 documentos pendentes e nenhum JSON inválido.

Cinco PDFs já tinham passado no critério de núcleo textual; os trechos
desiguais eram cabeçalhos, metadados ou rodapés da peça. Um desses dossiês
continuava em revisão por conter outro documento. A inspeção dos candidatos
mostrou PDFs cujo texto diferia pela extração e formatação, mas apontava para
o **mesmo identificador da peça no PJe** presente na publicação. A regra nova
exige esse ID único em ambos os textos, CNJ único igual, trecho comum mínimo
de 40 tokens e termos decisórios/prazos iguais. Não usa coincidência de
processo, data ou link isoladamente.

No replay com a regra nova, 30 PDFs adicionais foram relacionados à
publicação. Os dossiês com repetição comprovada passaram de 4 para 17 e os
em revisão de 379 para 366; 37 documentos continuaram apenas candidatos.
Os demais totais não mudaram. A diferença entre 30 documentos relacionados
e 13 dossiês liberados ocorre porque outros arquivos/andamentos no mesmo
dossiê continuam pendentes. Esta é **validação técnica local**, não decisão de
descarte nem medida de acurácia jurídica. Os PDFs e sua proveniência são
preservados para revisão; a integração produtiva com o Flow não consome a
nova relação.

Aplicando a faixa v2 apenas em memória aos mesmos 1.000 dossiês, 409
publicações produziram payloads distintos, com uma fonte de texto cada e 16
PDFs relacionados. Sete casos adicionais foram bloqueados porque o texto
continha outro CNJ em formato compacto, reconhecido pelo Flow e inicialmente
não reconhecido pelo Notify. O restante não foi exportado. Esta contagem não
autoriza envio: o contrato e a coexistência com grupos v1 foram validados
localmente, mas o sincronizador v2 não está ativo em produção.

O comando `scripts/sync_triaged_publications.py` seleciona dossiês pendentes,
reúne todas as linhas e, por padrão, apenas informa quantos itens v2 seriam
elegíveis ou bloqueados. `--send` é explícito: transmite somente os elegíveis,
confere o recibo completo do Flow antes de marcar `ENVIADO` no Notify e deixa
os demais sem mudança de status. Falha de envio marca somente o lote tentado
como `ERRO_ENVIO`, para reenvio idempotente. Este caminho **não** foi ligado ao
ciclo automático da RPA e não foi executado contra o Flow produtivo.

```bash
python scripts/sync_triaged_publications.py --limit 100
# Somente depois de implantar/configurar o receptor e fazer o corte do v1:
python scripts/sync_triaged_publications.py --limit 100 --send
```
