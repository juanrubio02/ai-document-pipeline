from __future__ import annotations

import os
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Document
from app.services.extractors import extract_text_from_file

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "ai_document_pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.task_routes = {"app.worker.process_document": {"queue": "default"}}
celery_app.conf.broker_connection_retry_on_startup = True  # quita el warning futuro


def now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@celery_app.task(name="app.worker.process_document")
def process_document(document_id: str) -> None:
    db: Session = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            return

        doc.status = "PROCESSING"
        doc.error = None
        db.commit()

        if not doc.storage_path:
            raise ValueError("storage_path is empty")

        path = doc.storage_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"storage_path not found: {path}")

        text = extract_text_from_file(
            path=path,
            filename=doc.filename,
            content_type=doc.content_type,
        )

        doc.text = text
        doc.status = "DONE"
        doc.processed_at = now_utc_naive()
        db.commit()

    except Exception as e:
        try:
            doc = db.get(Document, document_id)
            if doc:
                doc.status = "FAILED"
                doc.error = str(e)
                doc.processed_at = now_utc_naive()
                db.commit()
        finally:
            pass
    finally:
        db.close()
