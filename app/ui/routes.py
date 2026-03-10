from __future__ import annotations

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.documents import reprocess_document_record
from app.api.search import search_documents_data
from app.db.session import get_db
from app.db.models import Document

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def ui_index(request: Request, db: Session = Depends(get_db)):
    search_query = request.query_params.get("q", "").strip()
    docs = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .limit(50)
        .all()
    )

    rows = db.execute(
        select(Document.status, func.count()).group_by(Document.status)
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
    search_results = search_documents_data(db=db, q=search_query, limit=8) if search_query else None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "docs": docs,
            "search_query": search_query,
            "search_results": search_results,
            "stats": {
                "total_documents": total_documents,
                "by_status": by_status,
                "success_rate": success_rate,
            },
        },
    )


@router.get("/ui/documents/{document_id}", response_class=HTMLResponse)
def ui_detail(document_id: str, request: Request, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    text_preview = None
    if doc.text:
        # preview corto para no reventar la página
        text_preview = doc.text[:4000]

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "doc": doc,
            "text_preview": text_preview,
        },
    )


@router.post("/ui/upload")
async def ui_upload(file: UploadFile = File(...)):
    # Compatibility shim: keep old path and delegate to the real upload endpoint.
    return RedirectResponse(url="/documents", status_code=307)


@router.post("/ui/documents/{document_id}/reprocess")
def ui_reprocess(document_id: str, db: Session = Depends(get_db)):
    doc, already_processing = reprocess_document_record(db, document_id)
    if already_processing:
        return RedirectResponse(url=f"/ui/documents/{document_id}?msg=already_processing", status_code=303)

    return RedirectResponse(url=f"/ui/documents/{document_id}?msg=requeued", status_code=303)
