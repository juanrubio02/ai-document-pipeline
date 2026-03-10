# AI Document Pipeline

Asynchronous document ingestion, enrichment, and semantic retrieval pipeline built with FastAPI, Celery, PostgreSQL, Redis, and Docker.

This project is designed as a production-style backend portfolio piece: it accepts document uploads, processes them in the background, enriches them with lightweight offline AI features, and exposes both API and SSR UI flows for inspection and search.

## What It Does

- Streams uploads to disk without loading the full file into memory
- Applies SHA-256 deduplication to avoid duplicate processing
- Processes documents asynchronously with Celery workers
- Extracts text from `.txt`, `.md`, `.pdf`, and `.docx`
- Generates a short summary offline
- Infers `document_type` and extracts `keywords`
- Indexes processed documents for semantic search
- Exposes operational stats and document lifecycle endpoints
- Includes a simple server-rendered UI built with Jinja2

## Architecture

The system is intentionally small, explicit, and backend-first.

```text
Client / SSR UI
      |
      v
 FastAPI API  ---> PostgreSQL
      |
      v
 Redis queue
      |
      v
 Celery worker ---> Storage (/app/storage)
      |
      v
 Text extraction -> summary -> enrichment -> embedding
```

### Main components

- `app/api`
  FastAPI routes for documents, stats, and semantic search
- `app/ui`
  Server-rendered UI routes for home and document detail views
- `app/services`
  Focused business logic modules for extraction, summary, enrichment, and search
- `app/db`
  SQLAlchemy models and session management
- `app/worker.py`
  Celery worker responsible for asynchronous document processing
- `alembic/`
  Database migrations

## Processing Flow

1. `POST /documents` receives an upload.
2. The file is streamed to a temporary file while computing SHA-256.
3. If the checksum already exists, the API returns the existing document.
4. If it is new, metadata is stored in PostgreSQL and the worker task is enqueued.
5. The Celery worker extracts text, generates summary and enrichment, computes an embedding, and marks the document as `DONE`.
6. Processed documents become searchable through `GET /search`.

## AI Features

All AI-style features in this version run locally and offline.

- Summary generation
  heuristic sentence-based summarization with length limits
- Document enrichment
  lightweight `document_type` detection and keyword extraction
- Semantic search
  deterministic local embeddings with cosine similarity for small-scale document retrieval

No external LLM or hosted API is required.

## API Surface

Core endpoints:

- `POST /documents`
- `GET /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/text`
- `GET /documents/{document_id}/download`
- `POST /documents/{document_id}/reprocess`
- `GET /stats`
- `GET /search?q=...`
- `GET /health`

## Tech Stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- Jinja2
- Docker Compose
- PyMuPDF
- python-docx

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8001`
- Home UI: `http://localhost:8001/`
- Health check: `http://localhost:8001/health`

## Example Use Cases

- Upload documents and inspect processing status
- Reprocess failed or completed documents
- Search processed documents by semantic similarity
- Explore extracted text, summaries, keywords, and inferred type
- Use the SSR UI as a lightweight operational console

## Testing

The repository includes focused tests for:

- upload behavior and deduplication
- reprocess flow
- summary generation
- enrichment logic
- extractors
- semantic search service

## Why This Project

This repository demonstrates practical backend engineering beyond CRUD:

- async pipeline design
- safe file handling and deduplication
- background processing with failure isolation
- database-backed search indexing
- incremental AI enrichment without external dependencies
- clean separation between API, worker, services, and UI
