# Asset Pulse — FastAPI backend image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System packages required by psycopg2 / healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
