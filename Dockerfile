FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear usuario no-root
RUN useradd -m -u 10001 appuser \
  && mkdir -p /app/storage \
  && chown -R appuser:appuser /app

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY templates ./templates
COPY static ./static

# Asegurar permisos tras copiar
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]