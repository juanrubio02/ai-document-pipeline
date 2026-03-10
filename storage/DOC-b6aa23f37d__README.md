# AI Document Pipeline

API + worker pipeline for document ingestion and background processing.

## Stack
- FastAPI
- PostgreSQL
- Redis + Celery
- Docker Compose

## Run
```bash
cp .env.example .env
docker compose up --build
