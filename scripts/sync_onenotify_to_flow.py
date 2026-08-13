import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import database
import flow_sync


def _chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envia grupos processados do OneNotify para o intake do Flow."
    )
    parser.add_argument("--days", type=int, default=60, help="Janela em dias a partir de hoje.")
    parser.add_argument("--batch-size", type=int, default=100, help="Quantidade de grupos por POST.")
    parser.add_argument("--limit", type=int, default=None, help="Limite total de grupos para esta execução.")
    parser.add_argument("--force", action="store_true", help="Reenvia tambem grupos ja marcados como ENVIADO.")
    parser.add_argument("--retry-errors", action="store_true", help="Inclui grupos com ERRO_ENVIO.")
    parser.add_argument("--dry-run", action="store_true", help="Nao envia nem atualiza status; apenas monta payloads.")
    parser.add_argument(
        "--only-publicacao",
        action="store_true",
        help="Seleciona apenas grupos com tipo de notificacao de publicacao.",
    )
    parser.add_argument(
        "--exclude-document-groups",
        action="store_true",
        help="Remove grupos que tambem tenham notificacao de documento na mesma data/NPJ.",
    )
    parser.add_argument(
        "--no-documents",
        action="store_true",
        help="Nao inclui JSON de documentos no payload. Use apenas para diagnostico.",
    )
    parser.add_argument(
        "--dry-run-output",
        default=None,
        help="Arquivo JSON opcional para salvar a primeira pagina de payloads do dry-run.",
    )
    args = parser.parse_args()

    database.inicializar_banco()
    groups = flow_sync.list_candidate_groups(
        days=args.days,
        force=args.force,
        retry_errors=args.retry_errors,
        limit=None,
        only_publicacao=args.only_publicacao,
        exclude_document_groups=args.exclude_document_groups,
    )
    if args.limit is not None:
        groups = groups[:args.limit]

    print(
        json.dumps(
            {
                "selected": len(groups),
                "days": args.days,
                "force": args.force,
                "retry_errors": args.retry_errors,
                "dry_run": args.dry_run,
                "include_documents": not args.no_documents,
                "only_publicacao": args.only_publicacao,
                "exclude_document_groups": args.exclude_document_groups,
            },
            ensure_ascii=False,
        )
    )

    total_sent = 0
    total_updated = 0
    first_payload_page = None

    for batch_number, batch in enumerate(_chunked(groups, args.batch_size), start=1):
        result = flow_sync.sync_groups(
            batch,
            include_documents=not args.no_documents,
            dry_run=args.dry_run,
        )
        if args.dry_run and first_payload_page is None:
            first_payload_page = result.get("items", [])
        total_sent += result.get("sent", 0) or 0
        total_updated += result.get("updated", 0) or 0
        print(
            json.dumps(
                {
                    "batch": batch_number,
                    "selected": result.get("selected"),
                    "sent": result.get("sent"),
                    "updated": result.get("updated"),
                    "error": result.get("error"),
                },
                ensure_ascii=False,
            )
        )
        if result.get("error") and not args.retry_errors:
            break

    if args.dry_run and args.dry_run_output:
        output_path = Path(args.dry_run_output)
        output_path.write_text(
            json.dumps({"items": first_payload_page or []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"dry_run_output": str(output_path)}, ensure_ascii=False))

    print(json.dumps({"done": True, "sent": total_sent, "updated": total_updated}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
