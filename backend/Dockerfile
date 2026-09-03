FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 curl && rm -rf /var/lib/apt/lists/*
RUN if [ "$(uname -m)" = "x86_64" ] || [ "$(uname -m)" = "amd64" ]; then \
        pip install --default-timeout=1000 --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt; \
    else \
        pip install --default-timeout=1000 --no-cache-dir -r requirements.txt; \
    fi

COPY . .

# Gunicorn with 1 worker by default — required because the BM25 SQLite store uses
# file-level locking that is unsafe across multiple processes.
# Multi-worker is safe when using the PostgreSQL sparse backend (SPARSE_BACKEND=postgres),
# and the worker count can be configured via the GUNICORN_WORKERS environment variable.
CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${GUNICORN_WORKERS:-1} --bind 0.0.0.0:8000 --timeout 300"]
