import unittest
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from flow_sync import (
    build_triage_preview, fetch_triage_group, list_candidate_groups,
    list_triage_groups, materialize_triage_group,
)
from triagem_publicacoes import analisar_dossie, reunir_linhas_notificacao


PUBLICATION = {
    "data": "24/09/2026",
    "descricao": "PUBLICACAO DJ/DO",
    "detalhes": "Fica a parte intimada para requerer o prosseguimento do feito no prazo de quinze dias, sob pena de suspensão e posterior arquivamento dos autos.",
}


def document(text, **extraction_overrides):
    extraction = {
        "status": "ok",
        "pages": [{"text": text}],
        "truncated": False,
        "ocr_required": False,
    }
    extraction.update(extraction_overrides)
    return {"items": [{"nome": "ato.pdf", "sha256": "abc", "extraction": extraction}]}


class PublicationTriageTest(unittest.TestCase):
    def test_isolated_publication_is_ready(self):
        result = analisar_dossie([PUBLICATION], {"items": []})
        self.assertEqual(result["status"], "PUBLICACAO_ISOLADA")
        self.assertTrue(result["apto_para_etapa_publicacao"])

    def test_copied_rows_do_not_create_another_act(self):
        result = analisar_dossie([PUBLICATION, dict(PUBLICATION)], {"items": []})
        self.assertEqual(len(result["publicacoes"]), 1)
        self.assertEqual(result["publicacoes"][0]["indices_andamentos"], [0, 1])

    def test_normalized_identical_document_is_proven_repeat(self):
        text = PUBLICATION["detalhes"].upper().replace("à", "A")
        result = analisar_dossie([PUBLICATION], document(text))
        self.assertEqual(result["status"], "PUBLICACAO_COM_REPETICOES_COMPROVADAS")
        self.assertEqual(result["documentos"][0]["relacao"], "REPETE_PUBLICACAO")

    def test_different_decision_stays_in_review(self):
        text = PUBLICATION["detalhes"].replace("quinze dias", "cinco dias")
        result = analisar_dossie([PUBLICATION], document(text))
        self.assertFalse(result["apto_para_etapa_publicacao"])
        self.assertNotEqual(result["documentos"][0]["relacao"], "REPETE_PUBLICACAO")

    def test_unextracted_file_and_other_movement_stay_visible(self):
        result = analisar_dossie(
            [PUBLICATION, {"descricao": "OUTRO ANDAMENTO", "detalhes": "Outro ato"}],
            {"items": []},
            [{"nome": "sem-texto.pdf"}],
        )
        self.assertIn("outros_andamentos_na_janela", result["motivos_revisao"])
        self.assertIn("documentos_sem_equivalencia_comprovada", result["motivos_revisao"])
        self.assertEqual(result["documentos"][0]["relacao"], "INCONCLUSIVO")
        self.assertEqual(len(result["publicacoes_para_analise_individual"]), 1)
        self.assertEqual(result["documentos_pendentes"], [0])
        self.assertEqual(result["andamentos_pendentes"], [1])

    def test_scanned_document_does_not_become_repeat(self):
        result = analisar_dossie(
            [PUBLICATION],
            document(PUBLICATION["detalhes"], ocr_required=True),
        )
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")

    def test_bb_txt_link_stays_pending_without_blocking_publication_item(self):
        txt = document(
            "Arquivos adicionais não foram acessados pelo robô.\n"
            "Link documento: https://tribunal.example/processo/123/arquivo.pdf"
        )
        txt["items"][0]["nome"] = "nao-obtido.txt"
        result = analisar_dossie([PUBLICATION], txt)
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")
        self.assertEqual(len(result["publicacoes_para_analise_individual"]), 1)
        self.assertEqual(result["documentos_pendentes"], [0])
        self.assertEqual(result["documentos"][0]["relacao"], "LINK_DOCUMENTO_PENDENTE")
        self.assertEqual(result["documentos"][0]["proxima_analise"], "OBTER_ORIGINAL_DO_LINK")
        self.assertEqual(result["documentos"][0]["link_original"], "https://tribunal.example/processo/123/arquivo.pdf")

    def test_unrelated_pdf_url_does_not_become_missing_document(self):
        pdf = document("Consulte https://tribunal.example para informações gerais.")
        result = analisar_dossie([PUBLICATION], pdf)
        self.assertNotEqual(result["documentos"][0]["relacao"], "LINK_DOCUMENTO_PENDENTE")

    def test_distinct_publications_same_day_are_not_collapsed(self):
        another = dict(PUBLICATION, detalhes=PUBLICATION["detalhes"] + " Nova decisao.")
        result = analisar_dossie([PUBLICATION, another], {"items": []})
        self.assertEqual(len(result["publicacoes"]), 2)
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_two_publications_keep_individual_pdf_match_and_residual_document(self):
        first = dict(PUBLICATION, detalhes="Processo 1234567-89.2026.8.01.0001. " + PUBLICATION["detalhes"])
        second = dict(PUBLICATION, detalhes="Processo 1234567-89.2026.8.01.0001. " + PUBLICATION["detalhes"].replace("prosseguimento", "extinção"))
        matched = document(first["detalhes"])["items"][0]
        unmatched = document("Comunicação do banco sobre comprovante de pagamento de custa judicial.")["items"][0]
        unmatched["nome"] = "comprovante.pdf"
        unmatched["sha256"] = "different"
        result = analisar_dossie([first, second], {"items": [matched, unmatched]})
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")
        self.assertEqual(len(result["publicacoes_para_analise_individual"]), 2)
        self.assertEqual(result["documentos"][0]["relacao"], "REPETE_PUBLICACAO")
        self.assertEqual(result["documentos"][0]["publicacao_ids_candidatas"], [result["publicacoes"][0]["id"]])
        self.assertEqual(result["documentos_pendentes"], [1])

    def test_same_final_act_with_pdf_header_can_be_consolidated(self):
        cnj = "1234567-89.2026.8.01.0001"
        act = " ".join(f"termo{i}" for i in range(110))
        publication = dict(PUBLICATION, detalhes=f"Processo {cnj}. Intimacao. {act}")
        pdf = f"Tribunal de Justiça. Processo {cnj}. Documento extraído do sistema. {act} Assinado digitalmente."
        result = analisar_dossie([publication], document(pdf))
        self.assertEqual(result["status"], "PUBLICACAO_COM_REPETICOES_COMPROVADAS")
        self.assertEqual(result["documentos"][0]["motivo"], "nucleo_final_identico_com_cnj_compartilhado")

    def test_opposite_decision_before_common_tail_is_not_consolidated(self):
        cnj = "1234567-89.2026.8.01.0001"
        act = " ".join(f"termo{i}" for i in range(110))
        publication = dict(PUBLICATION, detalhes=f"Processo {cnj}. Defiro o pedido. {act}")
        pdf = f"Processo {cnj}. Indefiro o pedido. {act} Assinado digitalmente."
        result = analisar_dossie([publication], document(pdf))
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_different_cnj_is_not_consolidated_by_common_tail(self):
        act = " ".join(f"termo{i}" for i in range(110))
        publication = dict(PUBLICATION, detalhes=f"Processo 1234567-89.2026.8.01.0001. {act}")
        pdf = f"Processo 1234567-89.2026.8.01.0002. {act} Assinado digitalmente."
        result = analisar_dossie([publication], document(pdf))
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_numeric_deadline_before_common_tail_is_not_consolidated(self):
        cnj = "1234567-89.2026.8.01.0001"
        act = " ".join(f"termo{i}" for i in range(110))
        publication = dict(PUBLICATION, detalhes=f"Processo {cnj}. Prazo de 15 dias. {act}")
        pdf = f"Processo {cnj}. Prazo de 5 dias. {act} Assinado digitalmente."
        result = analisar_dossie([publication], document(pdf))
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_preview_reads_existing_group_without_sending(self):
        result = build_triage_preview({
            "NPJ": "123",
            "data_notificacao": "24/09/2026",
            "ids": "1;2",
            "andamentos": json.dumps([PUBLICATION]),
            "documentos": "[]",
            "documentos_json": json.dumps({"items": []}),
        })
        self.assertEqual(result["external_group_id"], "123|24/09/2026")
        self.assertEqual(result["ids_notificacoes"], [1, 2])
        self.assertEqual(result["status"], "PUBLICACAO_ISOLADA")

    def test_document_can_contain_judicial_act_without_publication_movement(self):
        text = "Processo 1234567-89.2026.8.01.0001\nSENTENÇA\nJulgo procedente o pedido."
        result = analisar_dossie([], document(text))
        self.assertEqual(result["status"], "POSSIVEL_ATO_EM_DOCUMENTO")
        self.assertEqual(result["documentos"][0]["relacao"], "ATO_JUDICIAL_CANDIDATO")
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_internal_document_is_not_assumed_to_be_a_publication(self):
        text = "Comunicado interno do banco sobre indicação de preposto para processo administrativo."
        result = analisar_dossie([], document(text))
        self.assertEqual(result["status"], "SEM_ANDAMENTO_PUBLICACAO")
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_group_union_keeps_publication_from_another_notification_row(self):
        cnj = "1234567-89.2026.8.01.0001"
        pdf = document(f"Processo {cnj}\nSENTENÇA\nJulgo procedente o pedido.")
        rows = [
            {"id": 10, "npj": "NPJ-1", "data_notificacao": "24/09/2026",
             "tipo_notificacao": "Inclusão de Documentos no NPJ",
             "andamentos": json.dumps([{"descricao": "OUTRO", "detalhes": "movimento"}]),
             "documentos_json": json.dumps(pdf), "documentos": "[]"},
            {"id": 11, "npj": "NPJ-1", "data_notificacao": "24/09/2026",
             "tipo_notificacao": "Andamento de publicação em processo de condução terceirizada",
             "andamentos": json.dumps([PUBLICATION]),
             "documentos_json": json.dumps(pdf), "documentos": "[]"},
        ]
        merged = reunir_linhas_notificacao(rows)
        result = build_triage_preview(merged)
        self.assertEqual(len(result["publicacoes"]), 1)
        self.assertEqual(len(result["documentos"]), 1)
        self.assertEqual(result["ids_notificacoes"], [10, 11])
        self.assertEqual(result["vistos_nas_notificacoes"]["documentos"], [[10, 11]])
        self.assertEqual(result["referencias_documentos"], [[
            {"id_notificacao": 10, "indice_documento": 0},
            {"id_notificacao": 11, "indice_documento": 0},
        ]])
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")

    def test_notification_type_does_not_invent_publication_movement(self):
        rows = [{"id": 20, "npj": "NPJ-2", "data_notificacao": "24/09/2026",
                 "tipo_notificacao": "Andamento de publicação em processo de condução terceirizada",
                 "andamentos": json.dumps([{"descricao": "CONTESTACAO/DEFESA", "detalhes": "Petição juntada"}]),
                 "documentos_json": json.dumps(document("Processo 1234567-89.2026.8.01.0001\nSENTENÇA\nJulgo o pedido.")),
                 "documentos": "[]"}]
        result = build_triage_preview(reunir_linhas_notificacao(rows))
        self.assertEqual(result["status"], "POSSIVEL_ATO_EM_DOCUMENTO")
        self.assertIn("Andamento de publicação em processo de condução terceirizada", result["tipos_notificacao_recebidos"])
        self.assertFalse(result["apto_para_etapa_publicacao"])

    def test_same_file_twice_keeps_both_window_references(self):
        item = document("Texto do mesmo arquivo.")["items"][0]
        merged = reunir_linhas_notificacao([{
            "id": 30, "npj": "NPJ-3", "data_notificacao": "24/09/2026",
            "tipo_notificacao": "Inclusão de Documentos no NPJ",
            "andamentos": "[]", "documentos": "[]",
            "documentos_json": json.dumps({"items": [item, item]}),
        }])
        self.assertEqual(len(merged["documentos_json"]["items"]), 1)
        self.assertEqual(merged["referencias_documentos"], [[
            {"id_notificacao": 30, "indice_documento": 0},
            {"id_notificacao": 30, "indice_documento": 1},
        ]])

    def test_invalid_json_in_one_row_prevents_automatic_result(self):
        rows = [
            {"id": 40, "npj": "NPJ-4", "data_notificacao": "24/09/2026",
             "tipo_notificacao": "Andamento de publicação em processo de condução terceirizada",
             "andamentos": json.dumps([PUBLICATION]), "documentos": "[]",
             "documentos_json": json.dumps({"items": []})},
            {"id": 41, "npj": "NPJ-4", "data_notificacao": "24/09/2026",
             "tipo_notificacao": "Inclusão de Documentos no NPJ",
             "andamentos": "[invalid", "documentos": "[]",
             "documentos_json": json.dumps({"items": []})},
        ]
        result = build_triage_preview(reunir_linhas_notificacao(rows))
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")
        self.assertFalse(result["apto_para_etapa_publicacao"])
        self.assertEqual(result["erros_json"], [{"id_notificacao": 41, "campo": "andamentos"}])
        self.assertEqual(result["publicacoes_para_analise_individual"], [])

    def test_preview_excludes_migration_even_in_mixed_npj_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "notify.sqlite")
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE notificacoes (
                        id INTEGER PRIMARY KEY, NPJ TEXT, data_notificacao TEXT,
                        origem TEXT, status TEXT, rpa_status TEXT, flow_status TEXT,
                        tipo_notificacao TEXT, data_criacao TEXT,
                        adverso_principal TEXT, numero_processo TEXT, polo TEXT,
                        bb_ciencia_status TEXT, human_status TEXT, responsavel TEXT,
                        data_processamento TEXT, detalhes_erro TEXT,
                        andamentos TEXT, documentos TEXT, documentos_json TEXT
                    )
                """)
                rows = [
                    (1, "N1", "24/09/2026", "migracao", json.dumps([{"descricao": "OUTRO"}])),
                    (2, "N1", "24/09/2026", "onenotify", json.dumps([PUBLICATION])),
                    (3, "N2", "23/09/2026", "migracao", json.dumps([PUBLICATION])),
                ]
                conn.executemany("""
                    INSERT INTO notificacoes (
                        id, NPJ, data_notificacao, origem, andamentos,
                        status, tipo_notificacao, documentos, documentos_json
                    ) VALUES (?, ?, ?, ?, ?, 'Processado', 'Andamento', '[]', '{"items": []}')
                """, rows)
            with patch.dict(os.environ, {"SQLITE_DATABASE_PATH": db_path, "DATABASE_URL": ""}):
                self.assertEqual(len(list_candidate_groups(force=True, limit=10)), 2)
                groups = list_triage_groups(days=None, limit=10)
                self.assertEqual(len(groups), 1)
                self.assertEqual(groups[0]["ids"], "2")
                self.assertEqual(build_triage_preview(groups[0])["status"], "PUBLICACAO_ISOLADA")
                self.assertIsNone(fetch_triage_group("N2", "23/09/2026"))
                snapshot = Path(temp_dir) / "export.jsonl"
                script = Path(__file__).resolve().parents[1] / "scripts" / "preview_triagem_publicacoes.py"
                exported = subprocess.run(
                    [sys.executable, str(script), "--npj", "N1", "--data", "24/09/2026",
                     "--snapshot-out", str(snapshot)],
                    check=True, capture_output=True, text=True,
                )
                replayed = subprocess.run(
                    [sys.executable, str(script), "--input-jsonl", str(snapshot)],
                    check=True, capture_output=True, text=True,
                )
                self.assertEqual(json.loads(exported.stdout)["status"], json.loads(replayed.stdout)["status"])
                self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)

    def test_offline_replay_writes_private_case_report_without_text_or_url(self):
        txt = document("Link documento: https://tribunal.example/arquivo/123.pdf")
        txt["items"][0]["nome"] = "arquivo-nao-obtido.txt"
        group = reunir_linhas_notificacao([{
            "id": 90, "npj": "NPJ-TESTE", "data_notificacao": "24/09/2026",
            "tipo_notificacao": "Andamento de publicação em processo de condução terceirizada",
            "andamentos": json.dumps([PUBLICATION]),
            "documentos": "[]", "documentos_json": json.dumps(txt),
        }])
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "snapshot.jsonl"
            cases = Path(temp_dir) / "cases.jsonl"
            snapshot.write_text(json.dumps({
                "snapshot_schema": "onenotify.triage-snapshot.v1", "group": group,
            }) + "\n", encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "scripts" / "preview_triagem_publicacoes.py"
            completed = subprocess.run(
                [sys.executable, str(script), "--input-jsonl", str(snapshot), "--cases-out", str(cases)],
                check=True, capture_output=True, text=True,
            )
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["status"], {"REVISAO_NECESSARIA": 1})
            self.assertEqual(summary["documentos_pendentes_de_analise"], 1)
            report = cases.read_text(encoding="utf-8")
            self.assertIn("LINK_DOCUMENTO_PENDENTE", report)
            self.assertNotIn("tribunal.example", report)
            self.assertNotIn(PUBLICATION["detalhes"], report)
            self.assertEqual(cases.stat().st_mode & 0o777, 0o600)

    def test_materialized_snapshot_replays_after_source_document_disappears(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = Path(temp_dir) / "nao-obtido.txt"
            original.write_text(
                "Arquivos adicionais não foram acessados pelo robô.\n"
                "Link documento: https://tribunal.example/peca.pdf",
                encoding="utf-8",
            )
            group = reunir_linhas_notificacao([{
                "id": 91, "npj": "NPJ-TESTE", "data_notificacao": "24/09/2026",
                "tipo_notificacao": "Andamento de publicação em processo de condução terceirizada",
                "andamentos": json.dumps([PUBLICATION]),
                "documentos": json.dumps([{"caminho": str(original), "nome": original.name}]),
                "documentos_json": json.dumps({"items": []}),
            }])
            frozen = materialize_triage_group(group)
            original.unlink()
            result = build_triage_preview(frozen, refresh_documents=False)
            self.assertEqual(result["status"], "REVISAO_NECESSARIA")
            self.assertEqual(result["documentos"][0]["relacao"], "LINK_DOCUMENTO_PENDENTE")
            self.assertEqual(
                frozen["documentos_json"]["items"][0]["extraction"]["pages"][0]["text"],
                "Arquivos adicionais não foram acessados pelo robô.\n"
                "Link documento: https://tribunal.example/peca.pdf",
            )


if __name__ == "__main__":
    unittest.main()
