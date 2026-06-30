import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor
from pypdf import PdfReader


WINDOWS_DOC_PREFIX = "C:\\OneNotify\\documentos"
CONTAINER_DOC_PREFIX = Path("/app/documentos")


def parse_args():
    parser = argparse.ArgumentParser(description="Classify OneNotify PDFs by text extractability.")
    parser.add_argument("--limit", type=int, default=500, help="Number of notification rows to sample.")
    parser.add_argument("--random", action="store_true", help="Use random sample instead of latest processed rows.")
    parser.add_argument("--output", default="/app/logs/pdf_incidence_report.json", help="Output JSON path.")
    parser.add_argument("--min-page-text-chars", type=int, default=25)
    parser.add_argument("--min-document-text-chars", type=int, default=80)
    return parser.parse_args()


def resolve_path(raw_path):
    if not raw_path:
        return None

    raw = str(raw_path)
    normalized = raw.replace("/", "\\")
    if normalized.lower().startswith(WINDOWS_DOC_PREFIX.lower()):
        relative = normalized[len(WINDOWS_DOC_PREFIX):].lstrip("\\")
        return CONTAINER_DOC_PREFIX / Path(*relative.split("\\"))

    path = Path(raw)
    if path.exists():
        return path

    if raw.startswith("documentos\\") or raw.startswith("documentos/"):
        relative = raw.split("\\", 1)[-1] if "\\" in raw else raw.split("/", 1)[-1]
        return CONTAINER_DOC_PREFIX / Path(*relative.replace("/", "\\").split("\\"))

    return path


def image_count_for_page(page):
    try:
        return len(page.images)
    except Exception:
        pass

    try:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") or {}
        count = 0
        for obj in xobjects.values():
            resolved = obj.get_object()
            if resolved.get("/Subtype") == "/Image":
                count += 1
        return count
    except Exception:
        return 0


def classify_pdf(path, min_page_text_chars, min_document_text_chars):
    if path is None:
        return {"classification": "missing_path", "error": "empty path"}
    if not path.exists():
        return {"classification": "missing_file", "error": str(path)}
    if path.suffix.lower() != ".pdf":
        return {"classification": "non_pdf", "error": None}

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        total_chars = 0
        text_pages = 0
        image_pages = 0
        total_images = 0

        for page in reader.pages:
            text = page.extract_text() or ""
            char_count = len(text.strip())
            image_count = image_count_for_page(page)

            total_chars += char_count
            total_images += image_count
            if char_count >= min_page_text_chars:
                text_pages += 1
            if image_count > 0:
                image_pages += 1

        if page_count == 0:
            classification = "empty_pdf"
        elif total_chars < min_document_text_chars and image_pages > 0:
            classification = "image_only_or_scanned"
        elif total_chars < min_document_text_chars:
            classification = "no_text_detected"
        elif text_pages < page_count and image_pages > 0:
            classification = "mixed_text_and_images"
        else:
            classification = "text_extractable"

        return {
            "classification": classification,
            "error": None,
            "page_count": page_count,
            "char_count": total_chars,
            "text_pages": text_pages,
            "image_pages": image_pages,
            "image_count": total_images,
            "path": str(path),
        }
    except Exception as exc:
        return {"classification": "error", "error": str(exc), "path": str(path)}


def iter_documents(row):
    try:
        docs = json.loads(row["documentos"] or "[]")
    except Exception:
        return []
    return docs if isinstance(docs, list) else []


def main():
    args = parse_args()
    dsn = os.environ["DATABASE_URL"]
    order_sql = "random()" if args.random else "data_processamento DESC NULLS LAST, id DESC"

    sql = f"""
        SELECT id, NPJ, data_notificacao, tipo_notificacao, status, rpa_status, documentos
        FROM notificacoes
        WHERE documentos IS NOT NULL
          AND documentos <> ''
          AND documentos <> '[]'
        ORDER BY {order_sql}
        LIMIT %s
    """

    report = {
        "sample": {"limit": args.limit, "random": args.random},
        "rows_sampled": 0,
        "documents_seen": 0,
        "pdfs_seen": 0,
        "classification_counts": {},
        "by_tipo_notificacao": {},
        "examples": defaultdict(list),
    }

    with psycopg2.connect(dsn, cursor_factory=DictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.limit,))
            rows = cur.fetchall()

    counts = Counter()
    by_tipo = defaultdict(Counter)
    report["rows_sampled"] = len(rows)

    for row in rows:
        docs = iter_documents(row)
        for doc in docs:
            report["documents_seen"] += 1
            raw_path = doc.get("caminho") or doc.get("path") or doc.get("arquivo")
            path = resolve_path(raw_path)
            if not path or path.suffix.lower() != ".pdf":
                result = {"classification": "non_pdf_or_missing_path", "error": str(raw_path)}
            else:
                report["pdfs_seen"] += 1
                result = classify_pdf(path, args.min_page_text_chars, args.min_document_text_chars)

            classification = result["classification"]
            counts[classification] += 1
            by_tipo[row["tipo_notificacao"]][classification] += 1

            examples = report["examples"][classification]
            if len(examples) < 10:
                examples.append({
                    "id": row["id"],
                    "npj": row["npj"],
                    "data_notificacao": row["data_notificacao"],
                    "tipo_notificacao": row["tipo_notificacao"],
                    "nome": doc.get("nome"),
                    "raw_path": raw_path,
                    "resolved_path": result.get("path"),
                    "page_count": result.get("page_count"),
                    "char_count": result.get("char_count"),
                    "text_pages": result.get("text_pages"),
                    "image_pages": result.get("image_pages"),
                    "image_count": result.get("image_count"),
                    "error": result.get("error"),
                })

    report["classification_counts"] = dict(counts)
    report["by_tipo_notificacao"] = {key: dict(value) for key, value in by_tipo.items()}
    report["examples"] = dict(report["examples"])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "output": str(output),
        "rows_sampled": report["rows_sampled"],
        "documents_seen": report["documents_seen"],
        "pdfs_seen": report["pdfs_seen"],
        "classification_counts": report["classification_counts"],
        "by_tipo_notificacao": report["by_tipo_notificacao"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
