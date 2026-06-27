FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN if [ "$(uname -m)" = "x86_64" ] || [ "$(uname -m)" = "amd64" ]; then \
        pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

# CRITICAL FIX: Use gunicorn with 4 uvicorn workers for multicore concurrency
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "--bind", "0.0.0.0:8000", "--timeout", "300"]
