"""Mede a primeira faixa de triagem em dados locais, sem enviar ao Flow.

Exemplo: python scripts/preview_triagem_publicacoes.py --days 30 --limit 500
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flow_sync import build_triage_preview, fetch_triage_group, list_triage_groups  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--npj")
    parser.add_argument("--data", help="DD/MM/AAAA, obrigatório com --npj")
    args = parser.parse_args()
    if bool(args.npj) != bool(args.data):
        parser.error("--npj e --data devem ser informados juntos")
    if args.days < 0 or args.limit < 1:
        parser.error("--days deve ser >= 0 e --limit deve ser >= 1")

    if args.npj:
        group = fetch_triage_group(args.npj, args.data)
        groups = [group] if group else []
    else:
        groups = list_triage_groups(days=args.days, limit=args.limit)

    statuses: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    documents: Counter[str] = Counter()
    for group in groups:
        result = build_triage_preview(group)
        statuses[result["status"]] += 1
        reasons.update(result["motivos_revisao"])
        documents.update(item["relacao"] for item in result["documentos"])

    print(json.dumps({
        "grupos_analisados": len(groups),
        "status": statuses,
        "motivos_revisao": reasons,
        "relacao_documentos": documents,
        "efeito": "somente_leitura_sem_envio",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
