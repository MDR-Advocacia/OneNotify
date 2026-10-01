import json
import sqlite3
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "painel-onenotify"))
import server  # noqa: E402


class ReviewCasesTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE notificacoes (
                id INTEGER PRIMARY KEY, NPJ TEXT, data_notificacao TEXT,
                tipo_notificacao TEXT, numero_processo TEXT,
                andamentos TEXT, documentos TEXT, documentos_json TEXT
            )"""
        )
        andamentos = json.dumps([{"data": "24/09/2026", "descricao": "PUBLICACAO DJ/DO", "detalhes": "Texto da publicação"}])
        documentos = json.dumps([{"nome": "documento.pdf", "caminho": "/app/documentos/documento.pdf"}])
        enriched = json.dumps({"items": [{"extraction": {"classification": "text_extractable", "pages": [{"text": "Texto do PDF"}]}}]})
        self.conn.executemany(
            "INSERT INTO notificacoes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (164455, "123", "24/09/2026", "Publicação", "456", andamentos, documentos, enriched),
                (167233, "123", "24/09/2026", "Documento externo", "456", andamentos, documentos, enriched),
                (168872, "123", "24/09/2026", "Inclusão de documento", "456", andamentos, documentos, enriched),
            ],
        )
        self.previous_get_db = server.get_db
        server.get_db = lambda: self.conn
        self.client = server.app.test_client()

    def tearDown(self):
        server.get_db = self.previous_get_db
        self.conn.close()

    def test_case_keeps_group_and_document_evidence(self):
        response = self.client.get("/api/revisao/casos/164455")
        self.assertEqual(response.status_code, 200)
        item = response.get_json()
        self.assertEqual(len(item["notificacoes"]), 3)
        self.assertEqual(len(item["andamentos"]), 1)
        self.assertEqual(len(item["documentos"]), 1)
        self.assertEqual(item["documentos"][0]["text_preview"], "Texto do PDF")

    def test_only_curated_cases_are_opened(self):
        self.assertEqual(self.client.get("/api/revisao/casos/167233").status_code, 404)


if __name__ == "__main__":
    unittest.main()
