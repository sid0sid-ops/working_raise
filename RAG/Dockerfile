# syntax=docker/dockerfile:1.4
# ==============================================================================
# RAISE Academic GraphRAG Studio — Production Dockerfile
# Python 3.12-slim base with non-root security and health monitoring
# ==============================================================================

FROM python:3.12-slim AS base

# System dependencies for PDF parsing, C-extensions, and container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements with layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . /app/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    TOKENIZERS_PARALLELISM=false \
    HOST=0.0.0.0 \
    PORT=8000

# Expose HTTP port
EXPOSE 8000

# Container Healthcheck against document manifest endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/documents/manifest || exit 1

# Production Entrypoint
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

