from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, select


class UploadDedupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.storage_dir = tempfile.TemporaryDirectory()
        os.environ["DB_URL"] = f"sqlite:///{cls.tmpdir.name}/test.db"
        os.environ["STORAGE_DIR"] = cls.storage_dir.name

        from app.db.models import Base, Document
        from app.db.session import SessionLocal, engine
        from app.main import app

        Base.metadata.create_all(bind=engine)

        cls.Document = Document
        cls.SessionLocal = SessionLocal
        cls.client = TestClient(app)
        cls.storage_path = Path(cls.storage_dir.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmpdir.cleanup()
        cls.storage_dir.cleanup()

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            db.execute(delete(self.Document))
            db.commit()

        for file in self.storage_path.iterdir():
            if file.is_file():
                file.unlink()

    def test_upload_new_document_returns_deduplicated_false(self) -> None:
        payload = b"same content for checksum"

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(
                "/documents",
                files={"file": ("sample.txt", payload, "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["deduplicated"])
        self.assertEqual(body["status"], "PENDING")
        send_task_mock.assert_called_once()

        with self.SessionLocal() as db:
            rows = db.execute(select(self.Document)).scalars().all()
            self.assertEqual(len(rows), 1)
            self.assertIsNotNone(rows[0].checksum)

        stored_files = [p for p in self.storage_path.iterdir() if p.is_file()]
        self.assertEqual(len(stored_files), 1)

    def test_upload_duplicate_returns_same_document_and_no_new_enqueue(self) -> None:
        payload = b"duplicate payload"

        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            first = self.client.post(
                "/documents",
                files={"file": ("first.txt", payload, "text/plain")},
            )
            second = self.client.post(
                "/documents",
                files={"file": ("second.txt", payload, "text/plain")},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_body = first.json()
        second_body = second.json()

        self.assertFalse(first_body["deduplicated"])
        self.assertTrue(second_body["deduplicated"])
        self.assertEqual(first_body["document_id"], second_body["document_id"])
        send_task_mock.assert_called_once()

        with self.SessionLocal() as db:
            rows = db.execute(select(self.Document)).scalars().all()
            self.assertEqual(len(rows), 1)

        stored_files = [p for p in self.storage_path.iterdir() if p.is_file()]
        self.assertEqual(len(stored_files), 1)

    def test_upload_empty_returns_400(self) -> None:
        with patch("app.api.documents.celery_app.send_task") as send_task_mock:
            response = self.client.post(
                "/documents",
                files={"file": ("empty.txt", b"", "text/plain")},
            )

        self.assertEqual(response.status_code, 400)
        send_task_mock.assert_not_called()

        with self.SessionLocal() as db:
            rows = db.execute(select(self.Document)).scalars().all()
            self.assertEqual(len(rows), 0)

        stored_files = [p for p in self.storage_path.iterdir() if p.is_file()]
        self.assertEqual(len(stored_files), 0)

    def test_upload_too_large_returns_413_and_no_document(self) -> None:
        payload = b"abcdef"

        with patch("app.api.documents.MAX_UPLOAD_SIZE", 5):
            with patch("app.api.documents.celery_app.send_task") as send_task_mock:
                response = self.client.post(
                    "/documents",
                    files={"file": ("big.txt", payload, "text/plain")},
                )

        self.assertEqual(response.status_code, 413)
        send_task_mock.assert_not_called()

        with self.SessionLocal() as db:
            rows = db.execute(select(self.Document)).scalars().all()
            self.assertEqual(len(rows), 0)

        stored_files = [p for p in self.storage_path.iterdir() if p.is_file()]
        self.assertEqual(len(stored_files), 0)

    def test_stats_endpoint_returns_expected_keys(self) -> None:
        payload = b"stats payload"
        with patch("app.api.documents.celery_app.send_task"):
            self.client.post(
                "/documents",
                files={"file": ("stats.txt", payload, "text/plain")},
            )

        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertIn("total_documents", body)
        self.assertIn("by_status", body)
        self.assertIn("success_rate", body)

        self.assertIn("PENDING", body["by_status"])
        self.assertIn("PROCESSING", body["by_status"])
        self.assertIn("DONE", body["by_status"])
        self.assertIn("FAILED", body["by_status"])


if __name__ == "__main__":
    unittest.main()
