from __future__ import annotations

import os
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentEmbedding
from app.db.session import SessionLocal
from app.services.ai_enrichment import detect_document_type, extract_keywords
from app.services.ai_summary import generate_summary
from app.services.extractors import extract_text_from_file
from app.services.semantic_search import generate_embedding, serialize_embedding

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
        summary: str | None = None
        document_type: str | None = None
        keywords: str | None = None
        serialized_embedding: str | None = None
        if text:
            try:
                summary = generate_summary(text)
            except Exception:
                # Summary generation must not break the pipeline.
                summary = None
            try:
                document_type = detect_document_type(doc.filename, doc.content_type, text)
                extracted_keywords = extract_keywords(text)
                keywords = ", ".join(extracted_keywords) if extracted_keywords else None
            except Exception:
                # Enrichment must not break the pipeline.
                document_type = None
                keywords = None
            try:
                serialized_embedding = serialize_embedding(generate_embedding(text))
            except Exception:
                # Embedding generation must not break the pipeline.
                serialized_embedding = None

        doc.text = text
        doc.summary = summary
        doc.document_type = document_type
        doc.keywords = keywords
        embedding_row = db.get(DocumentEmbedding, doc.document_id)
        if serialized_embedding:
            if embedding_row:
                embedding_row.embedding = serialized_embedding
            else:
                db.add(
                    DocumentEmbedding(
                        document_id=doc.document_id,
                        embedding=serialized_embedding,
                    )
                )
        elif embedding_row:
            db.delete(embedding_row)
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
