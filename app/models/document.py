from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class DocumentCreateOut(BaseModel):
    document_id: str
    status: str
    created_at: datetime


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    content_type: str
    status: str
    created_at: datetime
    processed_at: datetime | None
    text: str | None
    error: str | None
