from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete


class ReprocessFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        os.environ["DB_URL"] = f"sqlite:///{cls.tmpdir.name}/test.db"

        from app.db.models import Base, Document
        from app.db.session import SessionLocal, engine
        from app.main import app

        Base.metadata.create_all(bind=engine)

        cls.Document = Document
        cls.SessionLocal = SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmpdir.cleanup()

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            db.execute(delete(self.Document))
            db.commit()

    def _insert_document(
        self,
        *,
        document_id: str,
        status: str,
        processed_at: datetime | None,
    ) -> None:
        with self.SessionLocal() as db:
            doc = self.Document(
                document_id=document_id,
                filename="doc.txt",
                storage_path="/tmp/doc.txt",
                content_type="text/plain",
                status=status,
                created_at=datetime(2026, 1, 1, 10, 0, 0),
                processed_at=processed_at,
                text="hello",
                error="old error",
            )
            db.add(doc)
            db.commit()

    def _get_document(self, document_id: str):
        with self.SessionLocal() as db:
            return db.get(self.Document, document_id)

    def test_api_reprocess_requeues_and_clears_processed_at(self) -> None:
        doc_id = "DOC-api-requeue"
        self._insert_document(
            document_id=doc_id,
            status="DONE",
            processed_at=datetime(2026, 1, 2, 12, 0, 0),
        )

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(f"/documents/{doc_id}/reprocess")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"document_id": doc_id, "status": "PENDING", "message": "Re-queued"},
        )
        send_task_mock.assert_called_once_with("app.worker.process_document", args=[doc_id])

        doc = self._get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, "PENDING")
        self.assertIsNone(doc.processed_at)
        self.assertIsNone(doc.error)

    def test_api_reprocess_failed_document_requeues_and_clears_error(self) -> None:
        doc_id = "DOC-api-failed"
        self._insert_document(
            document_id=doc_id,
            status="FAILED",
            processed_at=datetime(2026, 1, 6, 11, 0, 0),
        )

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(f"/documents/{doc_id}/reprocess")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"document_id": doc_id, "status": "PENDING", "message": "Re-queued"},
        )
        send_task_mock.assert_called_once_with("app.worker.process_document", args=[doc_id])

        doc = self._get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, "PENDING")
        self.assertIsNone(doc.processed_at)
        self.assertIsNone(doc.error)

    def test_api_reprocess_already_processing_is_idempotent(self) -> None:
        doc_id = "DOC-api-processing"
        original_processed_at = datetime(2026, 1, 3, 9, 30, 0)
        self._insert_document(
            document_id=doc_id,
            status="PROCESSING",
            processed_at=original_processed_at,
        )

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(f"/documents/{doc_id}/reprocess")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"document_id": doc_id, "status": "PROCESSING", "message": "Already processing"},
        )
        send_task_mock.assert_not_called()

        doc = self._get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, "PROCESSING")
        self.assertEqual(doc.processed_at, original_processed_at)

    def test_api_reprocess_nonexistent_document_returns_404(self) -> None:
        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post("/documents/DOC-not-found/reprocess")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Document not found"})
        send_task_mock.assert_not_called()

    def test_ui_reprocess_requeues_and_redirects(self) -> None:
        doc_id = "DOC-ui-requeue"
        self._insert_document(
            document_id=doc_id,
            status="DONE",
            processed_at=datetime(2026, 1, 4, 8, 0, 0),
        )

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(
                f"/ui/documents/{doc_id}/reprocess",
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], f"/ui/documents/{doc_id}?msg=requeued")
        send_task_mock.assert_called_once_with("app.worker.process_document", args=[doc_id])

        doc = self._get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, "PENDING")
        self.assertIsNone(doc.processed_at)
        self.assertIsNone(doc.error)

    def test_ui_reprocess_processing_redirects_without_enqueue(self) -> None:
        doc_id = "DOC-ui-processing"
        self._insert_document(
            document_id=doc_id,
            status="PROCESSING",
            processed_at=datetime(2026, 1, 5, 7, 0, 0),
        )

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(
                f"/ui/documents/{doc_id}/reprocess",
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], f"/ui/documents/{doc_id}?msg=already_processing")
        send_task_mock.assert_not_called()

        doc = self._get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, "PROCESSING")


if __name__ == "__main__":
    unittest.main()
