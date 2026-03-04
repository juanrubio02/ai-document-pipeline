import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "ai_document_pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
