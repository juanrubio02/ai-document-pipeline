from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentEmbedding
from app.db.session import get_db
from app.services.semantic_search import cosine_similarity, deserialize_embedding, generate_embedding

router = APIRouter(tags=["search"])


def search_documents_data(db: Session, q: str, limit: int = 10) -> dict[str, object]:
    q = q.strip()
    if not q:
        return {"query": q, "count": 0, "items": []}

    query_embedding = generate_embedding(q)

    rows = db.execute(
        select(Document, DocumentEmbedding.embedding)
        .join(DocumentEmbedding, DocumentEmbedding.document_id == Document.document_id)
        .where(Document.status == "DONE")
    ).all()

    scored_items: list[dict[str, object]] = []
    for doc, embedding_value in rows:
        try:
            stored_embedding = deserialize_embedding(embedding_value)
        except Exception:
            continue
        score = cosine_similarity(query_embedding, stored_embedding)
        if score <= 0:
            continue
        scored_items.append(
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "score": round(score, 4),
                "summary": doc.summary,
                "document_type": doc.document_type,
                "keywords": doc.keywords,
            }
        )

    scored_items.sort(key=lambda item: item["score"], reverse=True)
    items = scored_items[:limit]

    return {
        "query": q,
        "count": len(items),
        "items": items,
    }


@router.get("/search")
def search_documents(
    q: str = Query(..., min_length=1, description="Semantic query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return search_documents_data(db=db, q=q, limit=limit)
