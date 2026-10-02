import unittest
import json

from flow_sync import build_triage_preview
from triagem_publicacoes import analisar_dossie


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

    def test_scanned_document_does_not_become_repeat(self):
        result = analisar_dossie(
            [PUBLICATION],
            document(PUBLICATION["detalhes"], ocr_required=True),
        )
        self.assertEqual(result["status"], "REVISAO_NECESSARIA")

    def test_distinct_publications_same_day_are_not_collapsed(self):
        another = dict(PUBLICATION, detalhes=PUBLICATION["detalhes"] + " Nova decisao.")
        result = analisar_dossie([PUBLICATION, another], {"items": []})
        self.assertEqual(len(result["publicacoes"]), 2)
        self.assertFalse(result["apto_para_etapa_publicacao"])

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


if __name__ == "__main__":
    unittest.main()
