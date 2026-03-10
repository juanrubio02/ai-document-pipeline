from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document
from app.db.session import get_db

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Document.status, func.count())
        .group_by(Document.status)
    ).all()

    by_status = {
        "PENDING": 0,
        "PROCESSING": 0,
        "DONE": 0,
        "FAILED": 0,
    }

    for status, count in rows:
        if status in by_status:
            by_status[status] = int(count)

    total_documents = sum(by_status.values())
    success_rate = (by_status["DONE"] / total_documents) if total_documents else 0.0

    return {
        "total_documents": total_documents,
        "by_status": by_status,
        "success_rate": success_rate,
    }
