"""Mede a primeira faixa de triagem em dados locais, sem enviar ao Flow.

Exemplo: python scripts/preview_triagem_publicacoes.py --days 30 --limit 500
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flow_sync import (  # noqa: E402
    build_publication_intake_preview, build_triage_preview, fetch_triage_group,
    list_triage_groups, materialize_triage_group,
)

SNAPSHOT_SCHEMA = "onenotify.triage-snapshot.v1"


def _load_snapshot(path: Path, limit: int) -> list[dict]:
    groups = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or record.get("snapshot_schema") != SNAPSHOT_SCHEMA or not isinstance(record.get("group"), dict):
                raise ValueError(f"Linha {line_number}: formato de snapshot desconhecido")
            groups.append(record["group"])
            if len(groups) >= limit:
                break
    return groups


def _write_private_jsonl(path: Path, records: list[dict]) -> None:
    """Cria arquivo local privado, sem substituir um relatório anterior."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")


def _case_summary(result: dict) -> dict:
    """Identificadores e decisões técnicas, sem texto das peças nem URL."""
    return {
        "external_group_id": result["external_group_id"],
        "status": result["status"],
        "publicacoes_para_analise_individual": result["publicacoes_para_analise_individual"],
        "itens_publicacao": result["itens_publicacao"],
        "documentos_pendentes": result["documentos_pendentes"],
        "andamentos_pendentes": result["andamentos_pendentes"],
        "motivos_revisao": result["motivos_revisao"],
        "documentos": [
            {
                "indice": doc["indice"],
                "relacao": doc["relacao"],
                "motivo": doc["motivo"],
                "evidencia": doc["evidencia"],
                "publicacao_ids_candidatas": doc["publicacao_ids_candidatas"],
                "proxima_analise": doc["proxima_analise"],
            }
            for doc in result["documentos"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--npj")
    parser.add_argument("--data", help="DD/MM/AAAA, obrigatório com --npj")
    parser.add_argument("--input-jsonl", type=Path, help="reexecuta snapshot local sem conexão ao banco")
    parser.add_argument("--snapshot-out", type=Path, help="exporta dossiês completos para arquivo privado")
    parser.add_argument("--cases-out", type=Path, help="resumo por dossiê sem texto nem links")
    parser.add_argument("--publication-intake-out", type=Path, help="payload v2 privado, somente publicações elegíveis; não envia")
    args = parser.parse_args()
    if bool(args.npj) != bool(args.data):
        parser.error("--npj e --data devem ser informados juntos")
    if args.days < 0 or args.limit < 1:
        parser.error("--days deve ser >= 0 e --limit deve ser >= 1")
    if args.input_jsonl and (args.npj or args.data or args.snapshot_out):
        parser.error("--input-jsonl não pode ser combinado com --npj, --data ou --snapshot-out")
    output_paths = [path.resolve() for path in (args.snapshot_out, args.cases_out, args.publication_intake_out) if path]
    if len(output_paths) != len(set(output_paths)):
        parser.error("arquivos de saída precisam de caminhos diferentes")

    if args.input_jsonl:
        groups = _load_snapshot(args.input_jsonl, args.limit)
    elif args.npj:
        group = fetch_triage_group(args.npj, args.data)
        groups = [group] if group else []
    else:
        groups = list_triage_groups(days=args.days, limit=args.limit)

    if args.snapshot_out:
        groups = [materialize_triage_group(group) for group in groups]
        _write_private_jsonl(args.snapshot_out, [
            {"snapshot_schema": SNAPSHOT_SCHEMA, "group": group} for group in groups
        ])

    statuses: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    documents: Counter[str] = Counter()
    individual_publications = 0
    publication_items = 0
    pending_documents = 0
    intake_ready = 0
    intake_blocked: Counter[str] = Counter()
    intake_items = []
    cases = []
    for group in groups:
        result = build_triage_preview(group, refresh_documents=not (args.input_jsonl or args.snapshot_out))
        if args.cases_out:
            cases.append(_case_summary(result))
        statuses[result["status"]] += 1
        reasons.update(result["motivos_revisao"])
        documents.update(item["relacao"] for item in result["documentos"])
        individual_publications += bool(result["publicacoes_para_analise_individual"])
        publication_items += len(result["publicacoes_para_analise_individual"])
        pending_documents += len(result["documentos_pendentes"])
        if args.publication_intake_out:
            prepared = build_publication_intake_preview(group, refresh_documents=not (args.input_jsonl or args.snapshot_out))
            if prepared["ready"]:
                intake_ready += 1
                intake_items.extend(prepared["items"])
            else:
                intake_blocked.update(prepared["reasons"])
    if args.cases_out:
        _write_private_jsonl(args.cases_out, cases)
    if args.publication_intake_out:
        _write_private_jsonl(args.publication_intake_out, intake_items)

    print(json.dumps({
        "grupos_analisados": len(groups),
        "status": statuses,
        "motivos_revisao": reasons,
        "relacao_documentos": documents,
        "grupos_com_publicacao_para_analise_individual": individual_publications,
        "publicacoes_para_analise_individual": publication_items,
        "documentos_pendentes_de_analise": pending_documents,
        "intake_v2_publicacoes_elegiveis": intake_ready,
        "intake_v2_itens": len(intake_items),
        "intake_v2_bloqueios": intake_blocked,
        "escopo": "snapshot_local" if args.input_jsonl else "avisos_correntes_sem_origem_migracao",
        "efeito": "somente_leitura_sem_envio",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
