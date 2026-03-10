from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.stats import router as stats_router
from app.ui.routes import router as ui_router

app = FastAPI(title="AI Document Pipeline", version="0.1.0")

# API
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(stats_router)

# UI
app.include_router(ui_router)

# Static (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
