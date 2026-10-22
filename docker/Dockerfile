FROM python:3.13-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH=/opt/venv/bin:${PATH} \
    HOME=/home/appuser \
    XDG_CACHE_HOME=/home/appuser/.cache

COPY --from=builder /opt/venv /opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        tzdata \
        libgomp1 \
        fonts-liberation \
        fonts-dejavu-core \
        fonts-noto-color-emoji \
        fonts-unifont \
    && /opt/venv/bin/python -m playwright install-deps firefox \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash appuser \
    && mkdir -p /app/output/logs /app/artifacts /app/assets \
    && chown -R appuser:appuser /app /home/appuser \
    && chown -R appuser:appuser /opt/venv/lib/python3.13/site-packages/camoufox

WORKDIR /app

USER appuser
RUN python -m camoufox fetch

# psycopg v3 (langgraph-checkpoint-postgres) requires libpq at runtime
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/health" || exit 1

CMD ["python", "launcher.py", "api"]

