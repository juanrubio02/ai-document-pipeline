from __future__ import annotations

import os
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Document

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "ai_document_pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.task_routes = {
    "app.worker.process_document": {"queue": "default"},
}


def now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@celery_app.task(name="app.worker.process_document")
def process_document(document_id: str) -> None:
    db: Session = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if not doc:
            return

        # Marcar PROCESSING
        doc.status = "PROCESSING"
        doc.error = None
        db.commit()

        # Leer fichero
        path = doc.storage_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"storage_path not found: {path}")

        text: str | None = None
        lower = (doc.filename or "").lower()

        if lower.endswith(".txt") or lower.endswith(".md"):
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", errors="replace")
        else:
            text = f"[no extractor yet] stored file {doc.filename} ({doc.content_type})"

        doc.text = text
        doc.status = "DONE"
        doc.processed_at = now_utc_naive()
        db.commit()

    except Exception as e:
        # FAILED
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
