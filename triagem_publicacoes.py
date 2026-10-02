"""Triagem local, sem efeitos colaterais, dos atos de publicação do BB.

O dossiê do Notify é uma janela de consulta por NPJ/data. Um documento presente
nessa janela não pertence necessariamente à notificação de publicação.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any


SCHEMA_VERSION = "onenotify.publication-triage.v1"
MIN_EQUIVALENT_TOKENS = 20
MAX_COMPARE_TOKENS = 2500
CNJ_PATTERN = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
EXTRA_DECISION_WORDS = {"defiro", "indefiro", "julgo", "condeno", "determino", "homologo"}
CRITICAL_WORDS = {
    "defiro", "indefiro", "deferido", "indeferido", "procedente", "improcedente",
    "julgo", "condeno", "determino", "homologo", "acolho", "rejeito", "nego",
    "concedo", "revogo", "suspensao", "arquivamento",
    "cinco", "dez", "quinze", "trinta", "sessenta", "noventa", "prazo", "dias",
}


def _json_value(value: Any, fallback: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return fallback
    try:
        return json.loads(value)
    except ValueError:
        return fallback


def _document_key(item: dict[str, Any], original: dict[str, Any], row_id: Any, index: int) -> tuple[Any, ...]:
    digest = item.get("sha256") or original.get("sha256")
    if digest:
        return ("sha256", str(digest))
    path = item.get("relative_path") or item.get("original_path") or original.get("caminho")
    if path:
        return ("path", str(path).replace("\\", "/").casefold())
    # Sem identificador seguro, manter referências distintas.
    return ("unknown", row_id, index)


def _extraction_quality(item: dict[str, Any]) -> tuple[int, int]:
    extraction = item.get("extraction") or {}
    if not isinstance(extraction, dict):
        return (0, 0)
    chars = sum(
        len(str(page.get("text") or ""))
        for page in extraction.get("pages") or []
        if isinstance(page, dict)
    )
    complete = (
        extraction.get("status") == "ok"
        and not extraction.get("truncated")
        and not extraction.get("ocr_required")
    )
    return (int(bool(complete)), chars)


def reunir_linhas_notificacao(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Reúne capturas do mesmo NPJ/data sem escolher JSON por MAX lexicográfico.

    `vistos_nas_notificacoes` é proveniência de cópia da janela, não prova que a
    notificação específica tenha causado a inclusão do arquivo/andamento.
    """
    if not rows:
        return {}
    ordered = sorted(rows, key=lambda row: int(row.get("id") or 0))
    first = ordered[0]
    movements: list[dict[str, Any]] = []
    movement_sources: list[list[int]] = []
    movement_index: dict[tuple[str, str, str], int] = {}
    documents: list[dict[str, Any]] = []
    originals: list[dict[str, Any]] = []
    document_sources: list[list[int]] = []
    document_references: list[list[dict[str, int]]] = []
    document_index: dict[tuple[Any, ...], int] = {}
    types: set[str] = set()
    notifications = []
    parse_errors: list[dict[str, Any]] = []

    def parsed(row: dict[str, Any], field: str, fallback: Any) -> Any:
        raw = row.get(field)
        sentinel = object()
        value = _json_value(raw, sentinel)
        if value is sentinel:
            if isinstance(raw, str) and raw.strip():
                parse_errors.append({"id_notificacao": int(row["id"]), "campo": field})
            return fallback
        return value

    for row in ordered:
        row_id = int(row["id"])
        kind = str(row.get("tipo_notificacao") or "").strip()
        if kind:
            types.add(kind)
        notifications.append({
            "id": row_id,
            "tipo_notificacao": kind,
            "data_criacao": str(row["data_criacao"]) if row.get("data_criacao") else None,
        })
        raw_movements = parsed(row, "andamentos", [])
        for movement in raw_movements if isinstance(raw_movements, list) else []:
            if not isinstance(movement, dict):
                continue
            key = tuple(str(movement.get(field) or "").strip() for field in ("data", "descricao", "detalhes"))
            position = movement_index.get(key)
            if position is None:
                position = len(movements)
                movement_index[key] = position
                movements.append(movement)
                movement_sources.append([])
            if row_id not in movement_sources[position]:
                movement_sources[position].append(row_id)

        envelope = parsed(row, "documentos_json", {})
        items = envelope.get("items") if isinstance(envelope, dict) else []
        items = items if isinstance(items, list) else []
        raw_originals = parsed(row, "documentos", [])
        raw_originals = raw_originals if isinstance(raw_originals, list) else []
        for index in range(max(len(items), len(raw_originals))):
            item = items[index] if index < len(items) and isinstance(items[index], dict) else {}
            original = (
                raw_originals[index]
                if index < len(raw_originals) and isinstance(raw_originals[index], dict)
                else {}
            )
            key = _document_key(item, original, row_id, index)
            position = document_index.get(key)
            if position is None:
                position = len(documents)
                document_index[key] = position
                documents.append(item)
                originals.append(original)
                document_sources.append([])
                document_references.append([])
            elif _extraction_quality(item) > _extraction_quality(documents[position]):
                documents[position], originals[position] = item, original
            if row_id not in document_sources[position]:
                document_sources[position].append(row_id)
            document_references[position].append({"id_notificacao": row_id, "indice_documento": index})

    return {
        "npj": first.get("npj") or first.get("NPJ"),
        "data_notificacao": first.get("data_notificacao"),
        "ids": ";".join(str(row["id"]) for row in ordered),
        "tipos_notificacao_recebidos": sorted(types),
        "notificacoes_origem": notifications,
        "andamentos": movements,
        "documentos_json": {"schema_version": "onenotify.documents.v1", "items": documents},
        "documentos": originals,
        "vistos_nas_notificacoes": {"andamentos": movement_sources, "documentos": document_sources},
        "referencias_documentos": document_references,
        "erros_json": parse_errors,
    }


def _tokens(value: Any) -> list[str]:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", text)


def _document_text(document: dict[str, Any]) -> str:
    extraction = document.get("extraction") or {}
    return "\n\n".join(
        str(page.get("text") or "")
        for page in extraction.get("pages") or []
        if isinstance(page, dict)
    ).strip()


def _document_has_judicial_act(text: str) -> bool:
    """Sinal para investigação; uma peça judicial não prova publicação oficial."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    heading = re.search(
        r"(?m)^\s*(?:sentenca|decisao|despacho|intimacao|citacao|acordao|ato ordinatorio)\b",
        normalized,
    )
    return bool(heading and CNJ_PATTERN.search(text))


def _deadline_signatures(value: str) -> set[str]:
    tokens = _tokens(value)
    return {
        tokens[index + 2]
        for index in range(len(tokens) - 3)
        if tokens[index:index + 2] == ["prazo", "de"] and tokens[index + 3] == "dias"
    }


def _is_publication(andamento: dict[str, Any]) -> bool:
    title = " ".join(_tokens(andamento.get("descricao")))
    return "publicacao" in title and ("dj do" in title or "djen" in title)


def _candidate_overlap(publication: list[str], document: list[str]) -> dict[str, Any]:
    if not publication or not document:
        return {"longest_common_tokens": 0, "publication_coverage": 0.0, "document_coverage": 0.0}
    blocks = SequenceMatcher(None, publication, document, autojunk=False).get_matching_blocks()
    common = sum(block.size for block in blocks)
    return {
        "longest_common_tokens": max(block.size for block in blocks),
        "publication_coverage": round(common / len(publication), 3),
        "document_coverage": round(common / len(document), 3),
    }


def _same_core(publication_text: str, document_text: str, evidence: dict[str, Any]) -> bool:
    """Reconhece o mesmo corpo final com cabeçalhos diferentes, sem decidir por score só."""
    publication = _tokens(publication_text)
    document = _tokens(document_text)
    if not publication or not document:
        return False
    publication_cnjs = set(CNJ_PATTERN.findall(publication_text))
    document_cnjs = set(CNJ_PATTERN.findall(document_text))
    if len(publication_cnjs) != 1 or publication_cnjs != document_cnjs:
        return False
    block = max(
        SequenceMatcher(None, publication, document, autojunk=False).get_matching_blocks(),
        key=lambda item: item.size,
    )
    if (block.size < 80 or len(publication) - block.a - block.size > 5
            or len(document) - block.b - block.size > 50):
        return False
    if evidence["publication_coverage"] < 0.6 or evidence["document_coverage"] < 0.5:
        return False
    publication_critical = Counter(token for token in publication if token in CRITICAL_WORDS)
    document_critical = Counter(token for token in document if token in CRITICAL_WORDS)
    if publication_critical != document_critical:
        return False
    if _deadline_signatures(publication_text) != _deadline_signatures(document_text):
        return False
    unmatched_document = document[:block.b] + document[block.b + block.size:]
    return not EXTRA_DECISION_WORDS.intersection(unmatched_document)


def analisar_dossie(
    andamentos: Any,
    documentos_json: Any,
    documentos_originais: Any = None,
) -> dict[str, Any]:
    """Separa publicação e documentos; só libera repetição textual demonstrável.

    Não envia ao Flow, altera status, descarta arquivo nem toma decisão jurídica.
    `documentos_originais` detecta arquivos ainda sem extração estruturada.
    """
    andamentos = andamentos if isinstance(andamentos, list) else []
    originais = documentos_originais if isinstance(documentos_originais, list) else []
    envelope = documentos_json if isinstance(documentos_json, dict) else {}
    items = envelope.get("items") if isinstance(envelope.get("items"), list) else []

    publications: dict[str, dict[str, Any]] = {}
    other_movements = []
    for index, andamento in enumerate(andamentos):
        if not isinstance(andamento, dict):
            other_movements.append(index)
            continue
        if not _is_publication(andamento):
            other_movements.append(index)
            continue
        text = str(andamento.get("detalhes") or "").strip()
        tokens = _tokens(text)
        identity = hashlib.sha256(
            (str(andamento.get("data") or "") + "|" + " ".join(tokens)).encode("utf-8")
        ).hexdigest()[:20]
        if identity not in publications:
            publications[identity] = {
                "id": identity,
                "data": andamento.get("data"),
                "texto": text,
                "indices_andamentos": [],
                "texto_util": len(tokens) >= MIN_EQUIVALENT_TOKENS,
            }
        publications[identity]["indices_andamentos"].append(index)

    publication_list = list(publications.values())
    reference_tokens = _tokens(publication_list[0]["texto"]) if len(publication_list) == 1 else []
    documents = []
    total_documents = max(len(items), len(originais))
    for index in range(total_documents):
        item = items[index] if index < len(items) and isinstance(items[index], dict) else {}
        original = originais[index] if index < len(originais) and isinstance(originais[index], dict) else {}
        extraction = item.get("extraction") or {}
        text = _document_text(item)
        tokens = _tokens(text)
        relation = "NAO_ANALISADO"
        reason = "sem_andamento_publicacao_unico"
        evidence = None
        if reference_tokens:
            if not item or extraction.get("status") != "ok" or extraction.get("truncated") or extraction.get("ocr_required"):
                relation, reason = "INCONCLUSIVO", "texto_ausente_incompleto_ou_imagem"
            elif len(tokens) < MIN_EQUIVALENT_TOKENS:
                relation, reason = "INCONCLUSIVO", "texto_curto_ou_insuficiente"
            elif tokens == reference_tokens:
                relation, reason = "REPETE_PUBLICACAO", "texto_integral_normalizado_igual"
            elif len(reference_tokens) > MAX_COMPARE_TOKENS or len(tokens) > MAX_COMPARE_TOKENS:
                relation, reason = "INCONCLUSIVO", "texto_longo_sem_comparacao_segura"
            else:
                evidence = _candidate_overlap(reference_tokens, tokens)
                if _same_core(publication_list[0]["texto"], text, evidence):
                    relation, reason = "REPETE_PUBLICACAO", "nucleo_final_identico_com_cnj_compartilhado"
                elif evidence["longest_common_tokens"] >= 40:
                    relation, reason = "CANDIDATO_MESMO_ATO", "trecho_longo_em_comum_sem_equivalencia_integral"
                else:
                    relation, reason = "INCONCLUSIVO", "conteudo_nao_equivalente"
        elif _document_has_judicial_act(text):
            relation, reason = "ATO_JUDICIAL_CANDIDATO", "peca_judicial_no_documento_sem_andamento_dj_do"
        documents.append({
            "indice": index,
            "nome": item.get("nome") or original.get("nome"),
            "sha256": item.get("sha256"),
            "relacao": relation,
            "motivo": reason,
            "evidencia": evidence,
        })

    reasons = []
    if not publication_list:
        reasons.append("sem_andamento_publicacao_dj_do")
    elif len(publication_list) > 1:
        reasons.append("multiplas_publicacoes_distintas")
    elif not publication_list[0]["texto_util"]:
        reasons.append("texto_publicacao_ausente_ou_curto")
    if other_movements:
        reasons.append("outros_andamentos_na_janela")
    if any(doc["relacao"] != "REPETE_PUBLICACAO" for doc in documents):
        reasons.append("documentos_sem_equivalencia_comprovada")

    automatic = not reasons
    if not publication_list and any(doc["relacao"] == "ATO_JUDICIAL_CANDIDATO" for doc in documents):
        status = "POSSIVEL_ATO_EM_DOCUMENTO"
    elif not publication_list:
        status = "SEM_ANDAMENTO_PUBLICACAO"
    elif automatic and documents:
        status = "PUBLICACAO_COM_REPETICOES_COMPROVADAS"
    elif automatic:
        status = "PUBLICACAO_ISOLADA"
    else:
        status = "REVISAO_NECESSARIA"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "apto_para_etapa_publicacao": automatic,
        "publicacoes": publication_list,
        "documentos": documents,
        "outros_andamentos": other_movements,
        "motivos_revisao": reasons,
    }
