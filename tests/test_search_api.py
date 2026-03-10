from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import delete


class SearchApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        os.environ["DB_URL"] = f"sqlite:///{cls.tmpdir.name}/test.db"

        from app.db.models import Base, Document, DocumentEmbedding
        from app.db.session import SessionLocal, engine
        from app.main import app
        from app.services.semantic_search import generate_embedding, serialize_embedding

        Base.metadata.create_all(bind=engine)

        cls.Document = Document
        cls.DocumentEmbedding = DocumentEmbedding
        cls.SessionLocal = SessionLocal
        cls.client = TestClient(app)
        cls.generate_embedding = generate_embedding
        cls.serialize_embedding = serialize_embedding

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmpdir.cleanup()

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            db.execute(delete(self.DocumentEmbedding))
            db.execute(delete(self.Document))
            db.commit()

    def test_search_returns_ranked_results(self) -> None:
        with self.SessionLocal() as db:
            python_doc = self.Document(
                document_id="DOC-python",
                filename="python.txt",
                checksum="a" * 64,
                storage_path="/tmp/python.txt",
                content_type="text/plain",
                status="DONE",
                created_at=self._dt(),
                processed_at=self._dt(),
                text="python backend docker api service",
                summary="python backend profile",
                document_type="generic",
                keywords="python, backend, docker",
                error=None,
            )
            invoice_doc = self.Document(
                document_id="DOC-invoice",
                filename="invoice.txt",
                checksum="b" * 64,
                storage_path="/tmp/invoice.txt",
                content_type="text/plain",
                status="DONE",
                created_at=self._dt(),
                processed_at=self._dt(),
                text="invoice subtotal vat payment amount",
                summary="invoice summary",
                document_type="invoice",
                keywords="invoice, vat, payment",
                error=None,
            )
            db.add(python_doc)
            db.add(invoice_doc)
            db.add(
                self.DocumentEmbedding(
                    document_id="DOC-python",
                    embedding=self.serialize_embedding(self.generate_embedding(python_doc.text or "")),
                )
            )
            db.add(
                self.DocumentEmbedding(
                    document_id="DOC-invoice",
                    embedding=self.serialize_embedding(self.generate_embedding(invoice_doc.text or "")),
                )
            )
            db.commit()

        response = self.client.get("/search", params={"q": "python backend docker"})
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["query"], "python backend docker")
        self.assertGreaterEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["document_id"], "DOC-python")
        self.assertIn("score", body["items"][0])
        self.assertIn("summary", body["items"][0])
        self.assertIn("document_type", body["items"][0])
        self.assertIn("keywords", body["items"][0])

    @staticmethod
    def _dt():
        from datetime import datetime

        return datetime(2026, 3, 10, 12, 0, 0)


if __name__ == "__main__":
    unittest.main()
