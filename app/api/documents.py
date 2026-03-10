from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Document
from app.db.session import get_db
from app.worker import celery_app

router = APIRouter(tags=["documents"])

# Where files are stored inside the container
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB

DocStatus = Literal["PENDING", "PROCESSING", "DONE", "FAILED"]


def now_utc_naive() -> datetime:
    """DB stores timestamp WITHOUT timezone, so we persist naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_doc_id() -> str:
    """Short readable id."""
    return f"DOC-{secrets.token_hex(5)}"  # 10 hex chars


def to_dict(doc: Document) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "status": doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        "error": doc.error,
        "text": doc.text,
    }


def upload_response_payload(doc: Document, deduplicated: bool) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "status": doc.status,
        "created_at": doc.created_at.isoformat(),
        "deduplicated": deduplicated,
    }


def reprocess_document_record(db: Session, document_id: str) -> tuple[Document, bool]:
    """
    Re-queue a document for processing.
    Returns (doc, already_processing).
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status == "PROCESSING":
        return doc, True

    doc.status = "PENDING"
    doc.error = None
    doc.processed_at = None
    db.commit()

    celery_app.send_task("app.worker.process_document", args=[document_id])
    return doc, False


@router.post("/documents")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Uploads a file:
    - stores it on disk (/app/storage)
    - creates DB row
    - enqueues Celery task to process it
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    document_id = new_doc_id()

    # Stream upload to temp file while computing checksum to avoid loading all file in memory.
    tmp_storage_path = STORAGE_DIR / f".upload-{document_id}.tmp"
    hasher = hashlib.sha256()
    has_content = False
    total_bytes = 0
    upload_too_large = False
    try:
        with open(tmp_storage_path, "wb") as tmp_file:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                has_content = True
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE:
                    upload_too_large = True
                    break
                hasher.update(chunk)
                tmp_file.write(chunk)
    except PermissionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Storage permission error: {e}",
        ) from e

    if upload_too_large:
        tmp_storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {MAX_UPLOAD_SIZE} bytes",
        )

    if not has_content:
        tmp_storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = hasher.hexdigest()

    existing = db.execute(
        select(Document).where(Document.checksum == checksum)
    ).scalar_one_or_none()
    if existing:
        tmp_storage_path.unlink(missing_ok=True)
        accept_existing = request.headers.get("accept", "")
        if "text/html" in accept_existing:
            return RedirectResponse(url=f"/ui/documents/{existing.document_id}", status_code=303)
        return upload_response_payload(existing, deduplicated=True)

    # Store on disk (sanitize filename to avoid weird paths)
    safe_name = Path(file.filename).name
    storage_path = STORAGE_DIR / f"{document_id}__{safe_name}"

    # DB row
    doc = Document(
        document_id=document_id,
        filename=safe_name,
        checksum=checksum,
        content_type=file.content_type or "application/octet-stream",
        storage_path=str(storage_path),
        status="PENDING",
        created_at=now_utc_naive(),
        processed_at=None,
        text=None,
        error=None,
    )
    db.add(doc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        tmp_storage_path.unlink(missing_ok=True)
        existing = db.execute(
            select(Document).where(Document.checksum == checksum)
        ).scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=409, detail="Duplicate checksum conflict")

        accept_existing = request.headers.get("accept", "")
        if "text/html" in accept_existing:
            return RedirectResponse(url=f"/ui/documents/{existing.document_id}", status_code=303)
        return upload_response_payload(existing, deduplicated=True)

    try:
        tmp_storage_path.replace(storage_path)
    except PermissionError as e:
        doc.status = "FAILED"
        doc.error = f"Storage permission error: {e}"
        doc.processed_at = now_utc_naive()
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Storage permission error: {e}",
        ) from e

    # Enqueue processing
    try:
        celery_app.send_task("app.worker.process_document", args=[document_id])
    except Exception as e:
        doc.status = "FAILED"
        doc.error = f"Enqueue failed: {e}"
        doc.processed_at = now_utc_naive()
        db.commit()
        raise HTTPException(status_code=503, detail="Processing queue unavailable") from e

    # If upload comes from UI form, redirect to detail page
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url=f"/ui/documents/{document_id}", status_code=303)

    return upload_response_payload(doc, deduplicated=False)


@router.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return to_dict(doc)


@router.get("/documents/{document_id}/text")
def get_document_text(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status == "FAILED":
        raise HTTPException(status_code=409, detail=f"Processing failed: {doc.error}")

    if doc.status != "DONE":
        raise HTTPException(status_code=409, detail=f"Not ready (status={doc.status})")

    return {"document_id": doc.document_id, "text": doc.text or ""}


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = doc.storage_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Stored file not found")

    return FileResponse(
        path,
        media_type=doc.content_type or "application/octet-stream",
        filename=doc.filename,
    )


@router.post("/documents/{document_id}/reprocess")
def reprocess_document(document_id: str, db: Session = Depends(get_db)):
    """
    Re-queue processing (simple idempotency: if already PROCESSING, we don't enqueue again).
    """
    doc, already_processing = reprocess_document_record(db, document_id)
    if already_processing:
        return {"document_id": doc.document_id, "status": doc.status, "message": "Already processing"}

    return {"document_id": doc.document_id, "status": doc.status, "message": "Re-queued"}


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: DocStatus | None = Query(None, description="Filter by status"),
    q: str | None = Query(None, description="Search by filename contains"),
):
    stmt = select(Document).order_by(Document.created_at.desc())

    if status:
        stmt = stmt.where(Document.status == status)

    if q:
        stmt = stmt.where(Document.filename.ilike(f"%{q}%"))

    rows = db.execute(stmt.limit(limit).offset(offset)).scalars().all()

    return {
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "items": [to_dict(d) for d in rows],
    }
