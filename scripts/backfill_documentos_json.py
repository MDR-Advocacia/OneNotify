import argparse
import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import DictCursor

from document_payload import build_documents_json


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill documentos_json for OneNotify notifications.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to process. 0 means no limit.")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep seconds between batches.")
    parser.add_argument("--refresh", action="store_true", help="Rebuild even when documentos_json already exists.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-dir", default=os.getenv("DOCUMENTOS_PATH", "/app/documentos"))
    parser.add_argument("--report", default="/app/logs/documentos_json_backfill_report.json")
    return parser.parse_args()


def select_batch(conn, batch_size, refresh):
    where_json = "1 = 1" if refresh else "(documentos_json IS NULL OR documentos_json = '')"
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            f"""
            SELECT id, NPJ, data_notificacao, tipo_notificacao, documentos
            FROM notificacoes
            WHERE documentos IS NOT NULL
              AND documentos <> ''
              AND documentos <> '[]'
              AND {where_json}
            ORDER BY data_processamento DESC NULLS LAST, id DESC
            LIMIT %s
            """,
            (batch_size,),
        )
        return cur.fetchall()


def update_row(conn, row_id, documentos_json):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE notificacoes SET documentos_json = %s WHERE id = %s",
            (json.dumps(documentos_json, ensure_ascii=False), row_id),
        )


def count_classifications(documentos_json):
    counts = Counter()
    for item in documentos_json.get("items", []):
        extraction = item.get("extraction", {}) if isinstance(item, dict) else {}
        counts[extraction.get("classification") or extraction.get("status") or "unknown"] += 1
    return counts


def main():
    args = parse_args()
    dsn = os.environ["DATABASE_URL"]
    processed = 0
    failed = 0
    classification_counts = Counter()
    started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    examples = []

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect(dsn) as conn:
        while True:
            remaining_limit = args.limit - processed if args.limit else args.batch_size
            if args.limit and remaining_limit <= 0:
                break

            batch_size = min(args.batch_size, remaining_limit) if args.limit else args.batch_size
            rows = select_batch(conn, batch_size, args.refresh)
            if not rows:
                break

            for row in rows:
                try:
                    documentos_json = build_documents_json(row["documentos"], base_dir=args.base_dir)
                    classification_counts.update(count_classifications(documentos_json))
                    if len(examples) < 20:
                        first_item = (documentos_json.get("items") or [{}])[0]
                        extraction = first_item.get("extraction", {}) if isinstance(first_item, dict) else {}
                        examples.append({
                            "id": row["id"],
                            "npj": row["npj"],
                            "data_notificacao": row["data_notificacao"],
                            "tipo_notificacao": row["tipo_notificacao"],
                            "classification": extraction.get("classification"),
                            "ocr_required": extraction.get("ocr_required"),
                            "relative_path": first_item.get("relative_path") if isinstance(first_item, dict) else None,
                        })
                    if not args.dry_run:
                        update_row(conn, row["id"], documentos_json)
                    processed += 1
                except Exception as exc:
                    failed += 1
                    print(f"[ERRO] id={row['id']} npj={row['npj']}: {exc}", flush=True)

            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

            report = {
                "started_at": started_at,
                "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "processed": processed,
                "failed": failed,
                "dry_run": args.dry_run,
                "refresh": args.refresh,
                "classification_counts": dict(classification_counts),
                "examples": examples,
            }
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({key: report[key] for key in ["processed", "failed", "classification_counts"]}, ensure_ascii=False), flush=True)

            if args.sleep:
                time.sleep(args.sleep)

    print(f"Backfill finished. processed={processed} failed={failed} report={args.report}", flush=True)


if __name__ == "__main__":
    main()
