"""Prévia de envio v2; exige --send para transmitir publicações elegíveis."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flow_sync import (  # noqa: E402
    fetch_triage_group, list_candidate_groups, sync_triaged_publications,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100, help="máximo de dossiês pendentes")
    parser.add_argument("--days", type=int, help="recorte por data da notificação")
    parser.add_argument("--send", action="store_true", help="envia ao Flow e atualiza status no Notify")
    args = parser.parse_args()
    if args.limit < 1 or (args.days is not None and args.days < 0):
        parser.error("--limit deve ser >= 1 e --days deve ser >= 0")
    candidates = list_candidate_groups(
        days=args.days, limit=args.limit, retry_errors=True, exclude_migration=True,
    )
    groups = [group for candidate in candidates if (group := fetch_triage_group(
        str(candidate["npj"]), str(candidate["data_notificacao"])
    ))]
    result = sync_triaged_publications(groups, dry_run=not args.send)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("error"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
