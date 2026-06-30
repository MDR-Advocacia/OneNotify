# OneNotify -> Flow API

O OneNotify continua como motor local da RPA do Portal BB. O Flow deve consumir
grupos de notificacao por `NPJ + data_notificacao`, com os tipos recebidos no dia
agregados no mesmo payload.

## Base URL

O Flow deve consumir a API pela URL publica do OneNotify:

```text
https://onenotify.mdradvocacia.com
```

Todos os endpoints abaixo devem ser chamados com esse prefixo. Exemplo:

```http
GET https://onenotify.mdradvocacia.com/api/flow/health
```

## Autenticacao

Quando `ONENOTIFY_FLOW_API_KEY` estiver configurada, enviar:

```http
X-Onenotify-Api-Key: <chave>
```

No ambiente local do OneNotify, a chave fica no arquivo `C:\OneNotify\.env`:

```env
ONENOTIFY_FLOW_API_KEY=<chave-compartilhada-com-o-flow>
```

Esse arquivo nao deve ser versionado. Para validar a chave no Windows:

```powershell
Get-Content C:\OneNotify\.env | Where-Object { $_ -like 'ONENOTIFY_FLOW_API_KEY=*' }
```

## Listar grupos prontos para intake

```http
GET https://onenotify.mdradvocacia.com/api/flow/notificacoes?flow_status=NAO_ENVIADO&rpa_status=PROCESSADO&limit=50&offset=0
```

Filtros opcionais:

- `flow_status`
- `rpa_status`
- `human_status`
- `npj`
- `data_notificacao` no formato `DD/MM/AAAA`
- `include_documents=true` para incluir o JSON estruturado dos documentos ja persistido pela RPA

Resposta:

```json
{
  "total": 1,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "schema_version": "onenotify.flow-intake.v1",
      "external_group_id": "2013/0167739-000|03/06/2026",
      "ids": [112118, 112232],
      "npj": "2013/0167739-000",
      "numero_processo_cnj": "0027807-47.2013.8.14.0301",
      "data_notificacao": "03/06/2026",
      "numero_processo": "0027807-47.2013.8.14.0301",
      "processo": {
        "npj": "2013/0167739-000",
        "numero_cnj": "0027807-47.2013.8.14.0301",
        "polo": "Passivo",
        "adverso_principal": "MARIA DE NAZARE NOGUEIRA GUIMARAES ROLIM"
      },
      "polo": "Passivo",
      "tipos_notificacao": ["Inclusao de Documentos no NPJ"],
      "rpa_status": ["PROCESSADO"],
      "bb_ciencia_status": ["ENVIADA"],
      "human_status": ["NOVO"],
      "flow_status": ["NAO_ENVIADO"],
      "andamentos": [],
      "documentos": {
        "schema_version": "onenotify.documents.v1",
        "items": [
          {
            "nome": "arquivo.pdf",
            "relative_path": "2013_0167739-000/arquivo.pdf",
            "size_bytes": 12345,
            "sha256": "...",
            "mime_type": "application/pdf",
            "view_url": "https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/2013_0167739-000/arquivo.pdf",
            "download_url": "https://onenotify.mdradvocacia.com/api/download?path=/app/documentos/2013_0167739-000/arquivo.pdf",
            "access_mode": "text_json",
            "extraction": {
              "status": "ok",
              "classification": "text_extractable",
              "ocr_required": false,
              "pages": [{"page": 1, "text": "...", "char_count": 1000}]
            }
          }
        ]
      },
      "conteudo": {
        "tem_texto": true,
        "tem_texto_andamentos": true,
        "tem_documentos": true,
        "tem_documentos_com_texto": true,
        "tem_documentos_ocr_required": false,
        "total_andamentos": 1,
        "total_documentos": 1,
        "total_documentos_com_texto": 1,
        "total_documentos_ocr_required": 0,
        "fontes_texto": [
          {
            "tipo": "andamento",
            "data": "02/06/2026",
            "titulo": "PUBLICACAO DJ/DO",
            "texto": "texto completo do andamento/publicacao..."
          },
          {
            "tipo": "documento",
            "nome": "arquivo.pdf",
            "classification": "text_extractable",
            "ocr_required": false,
            "view_url": "https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/2013_0167739-000/arquivo.pdf",
            "texto": "texto extraido das paginas do PDF..."
          }
        ],
        "documentos_links": [
          {
            "nome": "arquivo.pdf",
            "access_mode": "text_json",
            "classification": "text_extractable",
            "ocr_required": false,
            "view_url": "https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/2013_0167739-000/arquivo.pdf"
          }
        ]
      },
      "source": "ONENOTIFY_BB"
    }
  ]
}
```

Por padrao, `documentos` vem como `null` na listagem para evitar payload pesado.
Quando `include_documents=true`, a API retorna somente o conteudo ja salvo em
`documentos_json`. A extracao de PDF para JSON nao acontece durante a chamada
HTTP; ela deve ser feita pela RPA no processamento detalhado da notificacao.
Se a notificacao ainda nao tiver sido reprocessada pela RPA nova, `documentos`
retorna um envelope vazio com `extraction_status: "not_generated"`.

### Diferença entre JSON textual e JSON de referência

O campo `documentos.items[]` sempre representa o documento original, mas existem
dois cenarios:

1. PDF com texto extraivel:
   - `access_mode: "text_json"`
   - `extraction.status: "ok"`
   - `extraction.classification: "text_extractable"` ou `"mixed_text_and_images"`
   - `extraction.ocr_required: false` quando todo o conteudo relevante foi extraido
   - `extraction.pages[].text` contem o texto que o Flow pode usar no intake.

2. PDF escaneado/baseado em imagem:
   - `access_mode: "metadata_and_link"`
   - `extraction.status: "image_only_or_scanned"` ou `"no_text_detected"`
   - `extraction.ocr_required: true`
   - `extraction.pages[].text` vem vazio ou insuficiente
   - o JSON leva metadados, hash e links para visualizacao/download do PDF.

Nesses casos de imagem, o JSON nao e uma transcricao do documento. Ele e um
envelope de referencia para o Flow saber que precisa abrir o PDF, mandar para OCR
ou encaminhar para revisao humana.

### Texto da notificacao e identificadores do processo

Uma notificacao do OneNotify pode ter texto de andamento/publicacao, documentos,
ou ambos. O Flow deve considerar:

- `npj`: identificador interno do Portal BB.
- `numero_processo_cnj`: numero CNJ do processo, quando a RPA ja processou o detalhe.
- `processo.numero_cnj`: alias estruturado do mesmo CNJ.
- `andamentos[]`: lista original de andamentos/publicacoes capturados.
- `conteudo.fontes_texto[]`: lista unificada de textos que podem alimentar o intake.

`conteudo.fontes_texto[]` pode conter:

- `tipo: "andamento"` para textos vindos da aba/accordion de andamentos, incluindo
  publicacoes DJ/DO.
- `tipo: "documento"` para texto extraido de PDF/documento. Arquivos `.txt`
  baixados pela RPA tambem entram aqui com o texto completo em
  `documentos.items[].extraction.pages[0].text`.

Quando `include_documents=false`, a API ainda retorna textos de `andamentos`, mas
nao duplica textos extraidos de PDFs ou TXTs. Para o intake completo com texto
de documentos, chamar com `include_documents=true`.

Exemplo de documento `.txt` extraivel:

```json
{
  "nome": "08024898920248205114-Intimacao-1780475272767-614955.txt",
  "mime_type": "text/plain",
  "access_mode": "text_json",
  "extraction": {
    "status": "ok",
    "classification": "text_extractable",
    "ocr_required": false,
    "pages": [
      {"page": 1, "text": "texto integral do arquivo...", "char_count": 12345}
    ]
  }
}
```

### PDFs escaneados ou baseados em imagem

Alguns documentos do Portal BB, especialmente citacoes/intimacoes, podem ser PDFs
sem texto extraivel. Nesses casos o item de documento continua levando metadados
como `nome`, `relative_path`, `size_bytes`, `sha256`, `mime_type`, `view_url` e
`download_url`, mas a extracao textual vem marcada assim:

```json
{
  "view_url": "https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/2025_0354068-000/PI%20SELMA%20MARIA%20LINHARES%20MENDES.pdf",
  "download_url": "https://onenotify.mdradvocacia.com/api/download?path=/app/documentos/2025_0354068-000/PI%20SELMA%20MARIA%20LINHARES%20MENDES.pdf",
  "access_mode": "metadata_and_link",
  "extraction": {
    "status": "image_only_or_scanned",
    "classification": "image_only_or_scanned",
    "ocr_required": true,
    "page_count": 17,
    "char_count": 0,
    "text_pages": 0,
    "image_pages": 17,
    "image_count": 25,
    "pages": [
      {"page": 1, "text": "", "char_count": 0, "image_count": 3}
    ]
  }
}
```

O Flow nao deve tratar esse documento como conteudo textual completo. Para esses
casos, o intake deve preservar o vinculo com o documento original e decidir se
envia para OCR, revisao humana ou armazenamento externo.

## Visualizacao de documentos no navegador

Para abrir PDF ou TXT dentro do navegador, sem forcar download, use:

```http
GET https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/<pasta>/<arquivo.pdf>
GET https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/<pasta>/<arquivo.txt>
```

Essa rota retorna `Content-Disposition: inline` e deve ser usada para links de
visualizacao no Flow. A rota antiga abaixo continua existindo para download:

```http
GET https://onenotify.mdradvocacia.com/api/download?path=/app/documentos/<pasta>/<arquivo.pdf>
GET https://onenotify.mdradvocacia.com/api/download?path=/app/documentos/<pasta>/<arquivo.txt>
```

Exemplo real:

```http
GET https://onenotify.mdradvocacia.com/api/flow/documentos/view?path=/app/documentos/2022_0040961-000/PETICAOPESQUISAENDERECO.pdf
```

## Buscar um grupo especifico

Use URL-encoding no `external_group_id`.

```http
GET https://onenotify.mdradvocacia.com/api/flow/notificacoes/2013%2F0167739-000%7C03%2F06%2F2026
```

## Atualizar status de sincronizacao

```http
POST https://onenotify.mdradvocacia.com/api/flow/sync-status
Content-Type: application/json

{
  "external_group_id": "2013/0167739-000|03/06/2026",
  "flow_status": "ACEITO",
  "flow_external_id": "flow-publication-123",
  "flow_last_error": null
}
```

`flow_status` aceitos:

- `NAO_ENVIADO`
- `ENVIADO`
- `ACEITO`
- `REJEITADO`
- `SINCRONIZADO`
- `ERRO`
