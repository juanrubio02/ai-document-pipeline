from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document

router = APIRouter()

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_doc_id() -> str:
    return f"DOC-{secrets.token_hex(5)}"  # 10 hex chars


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    document_id = new_doc_id()

    # Leer contenido (esto TIENE que estar dentro del async endpoint)
    content = await file.read()

    # Guardar a disco
    safe_name = Path(file.filename).name  # evita paths raros
    storage_path = STORAGE_DIR / f"{document_id}__{safe_name}"
    storage_path.write_bytes(content)

    # Guardar registro en DB
    doc = Document(
        document_id=document_id,
        filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        status="PENDING",
        created_at=now_utc(),
        processed_at=None,
        text=None,
        error=None,
    )
    db.add(doc)
    db.commit()

    return {"document_id": document_id, "status": doc.status, "created_at": doc.created_at.isoformat()}