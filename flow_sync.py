import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import db_adapter
from document_payload import build_documents_json, safe_json_loads


DOCUMENTOS_PATH = os.getenv(
    "DOCUMENTOS_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "documentos")),
)
PUBLIC_BASE_URL = os.getenv("ONENOTIFY_PUBLIC_BASE_URL", "").rstrip("/")
FLOW_INTAKE_URL = os.getenv("FLOW_ONENOTIFY_BB_INTAKE_URL") or os.getenv("ONENOTIFY_BB_INTAKE_URL") or ""
FLOW_INTAKE_API_KEY = (
    os.getenv("FLOW_ONENOTIFY_BB_INTAKE_API_KEY")
    or os.getenv("ONENOTIFY_BB_INTAKE_API_KEY")
    or ""
)
FLOW_SYNC_ENABLED = os.getenv("FLOW_SYNC_ENABLED", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}
FLOW_SYNC_BATCH_SIZE = int(os.getenv("FLOW_SYNC_BATCH_SIZE", "100"))
FLOW_SYNC_TIMEOUT_SECONDS = int(os.getenv("FLOW_SYNC_TIMEOUT_SECONDS", "30"))


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def _split_agg(value: Any) -> list[str]:
    if not value:
        return []
    separator = ";" if ";" in str(value) else ","
    return [part.strip() for part in str(value).split(separator) if part.strip()]


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt)
        except ValueError:
            continue
    return None


def _empty_documents_payload(reason: str = "not_generated") -> dict[str, Any]:
    return {
        "schema_version": "onenotify.documents.v1",
        "generated_at": _now_iso(),
        "extraction_status": reason,
        "items": [],
    }


def _resolve_document_path(caminho: str) -> str | None:
    diretorio_base = os.path.abspath(DOCUMENTOS_PATH)
    raw_path = str(caminho or "").strip()
    if not raw_path:
        return None

    normalized = raw_path.replace("\\", "/")
    candidates: list[str] = []

    windows_prefix = "C:/OneNotify/documentos/"
    if normalized.lower().startswith(windows_prefix.lower()):
        relative = normalized[len(windows_prefix):]
        candidates.append(os.path.join(diretorio_base, *relative.split("/")))

    documentos_prefix = "documentos/"
    if normalized.lower().startswith(documentos_prefix):
        relative = normalized[len(documentos_prefix):]
        candidates.append(os.path.join(diretorio_base, *relative.split("/")))

    base_normalized = diretorio_base.replace("\\", "/").rstrip("/") + "/"
    if normalized.startswith(base_normalized):
        candidates.append(normalized)

    candidates.append(raw_path)

    for candidate in candidates:
        caminho_seguro = os.path.abspath(candidate)
        try:
            if os.path.commonpath([diretorio_base, caminho_seguro]) == diretorio_base:
                return caminho_seguro
        except ValueError:
            continue

    return None


def _document_api_path(document: dict[str, Any]) -> str | None:
    relative_path = document.get("relative_path")
    if relative_path:
        resolved = _resolve_document_path(os.path.join(DOCUMENTOS_PATH, relative_path))
        return resolved.replace("\\", "/") if resolved else None

    original_path = document.get("original_path")
    if original_path:
        resolved = _resolve_document_path(str(original_path))
        return resolved.replace("\\", "/") if resolved else None

    return None


def _decorate_document_links(documentos_json: Any) -> Any:
    if not isinstance(documentos_json, dict):
        return documentos_json

    base_url = PUBLIC_BASE_URL or "https://onenotify.mdradvocacia.com"
    for item in documentos_json.get("items", []):
        if not isinstance(item, dict):
            continue
        api_path = _document_api_path(item)
        if not api_path:
            continue
        encoded_path = quote(api_path, safe="/")
        item["view_url"] = f"{base_url}/api/flow/documentos/view?path={encoded_path}"
        item["download_url"] = f"{base_url}/api/download?path={encoded_path}"
        extraction = item.get("extraction", {}) if isinstance(item.get("extraction"), dict) else {}
        item["access_mode"] = "metadata_and_link" if extraction.get("ocr_required") else "text_json"
    return documentos_json


def _document_text(item: dict[str, Any]) -> str:
    extraction = item.get("extraction", {}) if isinstance(item, dict) else {}
    pages = extraction.get("pages", []) if isinstance(extraction, dict) else []
    texts = []
    for page in pages:
        if isinstance(page, dict) and page.get("text"):
            texts.append(str(page["text"]))
    return "\n\n".join(texts).strip()


def _build_conteudo_payload(andamentos: Any, documentos_json: Any, documentos_originais: Any) -> dict[str, Any]:
    fontes_texto: list[dict[str, Any]] = []
    andamentos_lista = andamentos if isinstance(andamentos, list) else []

    for index, andamento in enumerate(andamentos_lista, start=1):
        if not isinstance(andamento, dict):
            continue
        texto = (andamento.get("detalhes") or andamento.get("descricao") or "").strip()
        if texto:
            fontes_texto.append({
                "tipo": "andamento",
                "ordem": index,
                "data": andamento.get("data"),
                "titulo": andamento.get("descricao"),
                "texto": texto,
            })

    documentos_items = []
    if isinstance(documentos_json, dict):
        documentos_items = [item for item in documentos_json.get("items", []) if isinstance(item, dict)]

    documentos_com_texto = 0
    documentos_exigem_ocr = 0
    documentos_links = []

    for index, item in enumerate(documentos_items, start=1):
        extraction = item.get("extraction", {}) if isinstance(item.get("extraction"), dict) else {}
        ocr_required = bool(extraction.get("ocr_required"))
        if ocr_required:
            documentos_exigem_ocr += 1

        texto_documento = _document_text(item)
        if texto_documento:
            documentos_com_texto += 1
            fontes_texto.append({
                "tipo": "documento",
                "ordem": index,
                "nome": item.get("nome"),
                "classification": extraction.get("classification"),
                "ocr_required": ocr_required,
                "view_url": item.get("view_url"),
                "download_url": item.get("download_url"),
                "texto": texto_documento,
            })

        documentos_links.append({
            "nome": item.get("nome"),
            "relative_path": item.get("relative_path"),
            "access_mode": item.get("access_mode"),
            "classification": extraction.get("classification"),
            "ocr_required": ocr_required,
            "view_url": item.get("view_url"),
            "download_url": item.get("download_url"),
        })

    if documentos_items:
        total_documentos = len(documentos_items)
    elif isinstance(documentos_originais, list):
        total_documentos = len(documentos_originais)
    else:
        total_documentos = 0

    return {
        "tem_texto": bool(fontes_texto),
        "tem_texto_andamentos": any(fonte["tipo"] == "andamento" for fonte in fontes_texto),
        "tem_documentos": total_documentos > 0,
        "tem_documentos_com_texto": documentos_com_texto > 0,
        "tem_documentos_ocr_required": documentos_exigem_ocr > 0,
        "total_andamentos": len(andamentos_lista),
        "total_documentos": total_documentos,
        "total_documentos_com_texto": documentos_com_texto,
        "total_documentos_ocr_required": documentos_exigem_ocr,
        "fontes_texto": fontes_texto,
        "documentos_links": documentos_links,
    }


def _documents_payload_needs_refresh(documentos_json: Any, documentos_originais: Any) -> bool:
    if not documentos_originais:
        return False
    if not isinstance(documentos_json, dict):
        return True

    items = [item for item in documentos_json.get("items", []) if isinstance(item, dict)]
    if not items:
        return True

    for item in items:
        extraction = item.get("extraction", {}) if isinstance(item.get("extraction"), dict) else {}
        if item.get("exists") is False or extraction.get("status") == "missing_file":
            return True
        if not item.get("mime_type") and item.get("original_path"):
            return True
    return False


def build_flow_payload(row: Any, include_documents: bool = True) -> dict[str, Any]:
    row_dict = _row_to_dict(row)
    andamentos = safe_json_loads(row_dict.get("andamentos"), fallback=[])
    documentos_json = safe_json_loads(row_dict.get("documentos_json"), fallback=None)
    documentos_originais = safe_json_loads(row_dict.get("documentos"), fallback=[])

    if include_documents and _documents_payload_needs_refresh(documentos_json, documentos_originais):
        documentos_json = build_documents_json(documentos_originais, base_dir=DOCUMENTOS_PATH)
    elif include_documents and not documentos_json:
        documentos_json = _empty_documents_payload()

    if not include_documents:
        documentos_json = None
    elif documentos_json:
        documentos_json = _decorate_document_links(documentos_json)

    npj = row_dict.get("npj") or row_dict.get("NPJ")
    data_notificacao = row_dict.get("data_notificacao")
    numero_processo = row_dict.get("numero_processo")
    polo = row_dict.get("polo")
    adverso_principal = row_dict.get("adverso_principal")
    ids = _split_agg(row_dict.get("ids"))

    return {
        "schema_version": "onenotify.flow-intake.v1",
        "external_group_id": f"{npj}|{data_notificacao}",
        "ids": [int(item) for item in ids if str(item).isdigit()],
        "npj": npj,
        "numero_processo_cnj": numero_processo,
        "cnj_principal_notify": numero_processo,
        "data_notificacao": data_notificacao,
        "numero_processo": numero_processo,
        "polo": polo,
        "adverso_principal": adverso_principal,
        "processo": {
            "npj": npj,
            "numero_cnj": numero_processo,
            "polo": polo,
            "adverso_principal": adverso_principal,
        },
        "tipos_notificacao": _split_agg(row_dict.get("tipos_notificacao")),
        "status_legacy": _split_agg(row_dict.get("status_legacy")),
        "rpa_status": _split_agg(row_dict.get("rpa_status")),
        "bb_ciencia_status": _split_agg(row_dict.get("bb_ciencia_status")),
        "human_status": _split_agg(row_dict.get("human_status")),
        "flow_status": _split_agg(row_dict.get("flow_status")),
        "responsavel": row_dict.get("responsavel"),
        "data_processamento": row_dict.get("data_processamento"),
        "detalhes_erro": row_dict.get("detalhes_erro"),
        "andamentos": andamentos if isinstance(andamentos, list) else [],
        "documentos": documentos_json,
        "conteudo": _build_conteudo_payload(andamentos, documentos_json, documentos_originais),
        "source": "ONENOTIFY_BB",
        "generated_at": _now_iso(),
    }


def _group_select_sql() -> str:
    if db_adapter.is_postgres():
        agg_ids = "STRING_AGG(id::text, ';')"
        agg_tipo = "STRING_AGG(DISTINCT tipo_notificacao::text, '; ' ORDER BY tipo_notificacao::text)"
        agg_status = "STRING_AGG(DISTINCT status::text, '; ' ORDER BY status::text)"
        agg_rpa = "STRING_AGG(DISTINCT rpa_status::text, '; ' ORDER BY rpa_status::text)"
        agg_ciencia = "STRING_AGG(DISTINCT bb_ciencia_status::text, '; ' ORDER BY bb_ciencia_status::text)"
        agg_human = "STRING_AGG(DISTINCT human_status::text, '; ' ORDER BY human_status::text)"
        agg_flow = "STRING_AGG(DISTINCT flow_status::text, '; ' ORDER BY flow_status::text)"
    else:
        agg_ids = "GROUP_CONCAT(id, ';')"
        agg_tipo = "GROUP_CONCAT(DISTINCT tipo_notificacao)"
        agg_status = "GROUP_CONCAT(DISTINCT status)"
        agg_rpa = "GROUP_CONCAT(DISTINCT rpa_status)"
        agg_ciencia = "GROUP_CONCAT(DISTINCT bb_ciencia_status)"
        agg_human = "GROUP_CONCAT(DISTINCT human_status)"
        agg_flow = "GROUP_CONCAT(DISTINCT flow_status)"

    return f"""
        SELECT
            NPJ as npj,
            data_notificacao,
            MAX(adverso_principal) as adverso_principal,
            MAX(numero_processo) as numero_processo,
            MAX(polo) as polo,
            {agg_ids} as ids,
            {agg_tipo} as tipos_notificacao,
            {agg_status} as status_legacy,
            {agg_rpa} as rpa_status,
            {agg_ciencia} as bb_ciencia_status,
            {agg_human} as human_status,
            {agg_flow} as flow_status,
            MAX(responsavel) as responsavel,
            MAX(data_processamento) as data_processamento,
            MAX(detalhes_erro) as detalhes_erro,
            MAX(andamentos) as andamentos,
            MAX(documentos) as documentos,
            MAX(documentos_json) as documentos_json,
            MAX(data_criacao) as data_criacao
        FROM notificacoes
    """


def _flow_pending_condition(retry_errors: bool) -> tuple[str, list[Any]]:
    statuses = ["NAO_ENVIADO", "ERRO_ENVIO"] if retry_errors else ["NAO_ENVIADO"]
    placeholders = db_adapter.placeholders(len(statuses))
    return f"COALESCE(flow_status, 'NAO_ENVIADO') IN ({placeholders})", statuses


def list_candidate_groups(
    days: int | None = None,
    force: bool = False,
    retry_errors: bool = False,
    limit: int | None = None,
    only_publicacao: bool = False,
    exclude_document_groups: bool = False,
) -> list[dict[str, Any]]:
    where = [
        "data_notificacao IS NOT NULL",
        "(rpa_status = 'PROCESSADO' OR status IN ('Processado', 'Tratada', 'Migrado', 'Arquivado'))",
    ]
    params: list[Any] = []
    if not force:
        condition, condition_params = _flow_pending_condition(retry_errors)
        where.append(condition)
        params.extend(condition_params)
    if days is not None:
        if db_adapter.is_postgres():
            where.append("data_notificacao ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'")
            where.append("to_date(data_notificacao, 'DD/MM/YYYY') >= CURRENT_DATE - (? * INTERVAL '1 day')")
            params.append(days)
        else:
            where.append("""
                date(substr(data_notificacao, 7, 4) || '-' || substr(data_notificacao, 4, 2) || '-' || substr(data_notificacao, 1, 2))
                >= date('now', ?)
            """)
            params.append(f"-{days} days")

    having: list[str] = []
    if only_publicacao:
        if db_adapter.is_postgres():
            having.append("BOOL_OR(COALESCE(tipo_notificacao::text, '') ILIKE '%%publica%%')")
        else:
            having.append("SUM(CASE WHEN lower(COALESCE(tipo_notificacao, '')) LIKE '%publica%' THEN 1 ELSE 0 END) > 0")
    if exclude_document_groups:
        if db_adapter.is_postgres():
            having.append("NOT BOOL_OR(COALESCE(tipo_notificacao::text, '') ILIKE '%%doc%%')")
        else:
            having.append("SUM(CASE WHEN lower(COALESCE(tipo_notificacao, '')) LIKE '%doc%' THEN 1 ELSE 0 END) = 0")

    query = f"""
        {_group_select_sql()}
        WHERE {" AND ".join(where)}
        GROUP BY NPJ, data_notificacao
        {"HAVING " + " AND ".join(having) if having else ""}
        ORDER BY MAX(data_criacao) DESC, MAX(id) DESC
    """
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with db_adapter.connect_main() as conn:
        rows = [_row_to_dict(row) for row in conn.execute(query, params).fetchall()]

    return rows


def fetch_group(npj: str, data_notificacao: str) -> dict[str, Any] | None:
    query = f"""
        {_group_select_sql()}
        WHERE NPJ = ? AND data_notificacao = ?
        GROUP BY NPJ, data_notificacao
    """
    with db_adapter.connect_main() as conn:
        row = conn.execute(query, (npj, data_notificacao)).fetchone()
        return _row_to_dict(row) if row else None


def _mark_groups(groups: list[dict[str, Any]], status: str, external_id: str | None = None, error: str | None = None) -> int:
    if not groups:
        return 0
    now = _now_iso()
    updated = 0
    with db_adapter.connect_main() as conn:
        for group in groups:
            cursor = conn.execute(
                """
                UPDATE notificacoes
                SET flow_status = ?, flow_external_id = ?, flow_synced_at = ?, flow_last_error = ?
                WHERE NPJ = ? AND data_notificacao = ?
                """,
                (
                    status,
                    external_id,
                    now,
                    error[:2000] if error else None,
                    group.get("npj") or group.get("NPJ"),
                    group.get("data_notificacao"),
                ),
            )
            updated += cursor.rowcount or 0
    return updated


def _mark_group_results(groups: list[dict[str, Any]], response_payload: dict[str, Any]) -> int:
    records = response_payload.get("records", []) if isinstance(response_payload, dict) else []
    by_external_id = {
        str(record.get("external_group_id")): record
        for record in records
        if isinstance(record, dict) and record.get("external_group_id")
    }
    updated = 0
    with db_adapter.connect_main() as conn:
        for group in groups:
            external_group_id = f"{group.get('npj') or group.get('NPJ')}|{group.get('data_notificacao')}"
            record = by_external_id.get(external_group_id)
            if record:
                external_id = json.dumps({
                    "flow_id": record.get("id"),
                    "external_group_id": record.get("external_group_id"),
                    "matched_publication_record_id": record.get("matched_publication_record_id"),
                    "match_score": record.get("match_score"),
                    "flow_status": record.get("flow_status"),
                    "action_suggested": record.get("action_suggested"),
                }, ensure_ascii=False)
            else:
                external_id = json.dumps(response_payload, ensure_ascii=False)[:2000]
            cursor = conn.execute(
                """
                UPDATE notificacoes
                SET flow_status = 'ENVIADO', flow_external_id = ?, flow_synced_at = ?, flow_last_error = NULL
                WHERE NPJ = ? AND data_notificacao = ?
                """,
                (
                    external_id,
                    _now_iso(),
                    group.get("npj") or group.get("NPJ"),
                    group.get("data_notificacao"),
                ),
            )
            updated += cursor.rowcount or 0
    return updated


def _post_to_flow(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not FLOW_INTAKE_URL:
        raise RuntimeError("FLOW_ONENOTIFY_BB_INTAKE_URL nao configurada.")
    if not FLOW_INTAKE_API_KEY:
        raise RuntimeError("FLOW_ONENOTIFY_BB_INTAKE_API_KEY nao configurada.")

    body = json.dumps({"items": items}, ensure_ascii=False).encode("utf-8")
    request = Request(
        FLOW_INTAKE_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Onenotify-Api-Key": FLOW_INTAKE_API_KEY,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=FLOW_SYNC_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Flow intake HTTP {exc.code}: {detail[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha de rede no Flow intake: {exc}") from exc


def sync_groups(
    groups: list[dict[str, Any]],
    include_documents: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not groups:
        return {"selected": 0, "sent": 0, "updated": 0, "dry_run": dry_run}

    payloads = [build_flow_payload(group, include_documents=include_documents) for group in groups]
    if dry_run:
        return {
            "selected": len(groups),
            "sent": 0,
            "updated": 0,
            "dry_run": True,
            "items": payloads,
        }

    try:
        _mark_groups(groups, "ENVIANDO")
        response_payload = _post_to_flow(payloads)
        updated = _mark_group_results(groups, response_payload)
        return {
            "selected": len(groups),
            "sent": len(payloads),
            "updated": updated,
            "dry_run": False,
            "response": response_payload,
        }
    except Exception as exc:
        error = str(exc)
        _mark_groups(groups, "ERRO_ENVIO", error=error)
        logging.error("Erro ao enviar lote OneNotify para o Flow: %s", error, exc_info=True)
        return {
            "selected": len(groups),
            "sent": 0,
            "updated": 0,
            "dry_run": False,
            "error": error,
        }


def sync_pending(
    limit: int | None = None,
    days: int | None = None,
    include_documents: bool = True,
    force: bool = False,
    retry_errors: bool = True,
    dry_run: bool = False,
    only_publicacao: bool = False,
    exclude_document_groups: bool = False,
) -> dict[str, Any]:
    selected_limit = limit or FLOW_SYNC_BATCH_SIZE
    groups = list_candidate_groups(
        days=days,
        force=force,
        retry_errors=retry_errors,
        limit=selected_limit,
        only_publicacao=only_publicacao,
        exclude_document_groups=exclude_document_groups,
    )
    return sync_groups(groups, include_documents=include_documents, dry_run=dry_run)


def sync_after_rpa_batch() -> dict[str, Any] | None:
    if not FLOW_SYNC_ENABLED:
        logging.info("Sincronizacao OneNotify -> Flow desativada por FLOW_SYNC_ENABLED=false.")
        return None
    if not FLOW_INTAKE_URL or not FLOW_INTAKE_API_KEY:
        logging.warning("Sincronizacao OneNotify -> Flow ignorada: URL ou API key nao configurada.")
        return None

    result = sync_pending(limit=FLOW_SYNC_BATCH_SIZE, retry_errors=True)
    logging.info(
        "Sincronizacao OneNotify -> Flow: selecionados=%s enviados=%s atualizados=%s erro=%s",
        result.get("selected"),
        result.get("sent"),
        result.get("updated"),
        result.get("error"),
    )
    return result
