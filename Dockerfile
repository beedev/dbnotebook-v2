# Frontend build stage
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Python build stage
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install dependencies
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install CPU-only PyTorch first (much smaller than CUDA version)
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies (without torch)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Runtime stage
FROM python:3.11-slim

# OCI labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/beedev/dbnotebook"
LABEL org.opencontainers.image.description="Multimodal RAG Sales Enablement System"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.version="1.1.0"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy application code
COPY dbnotebook/ dbnotebook/
COPY --from=frontend-builder /app/frontend/dist frontend/dist/
COPY alembic/ alembic/
COPY alembic.ini .

# Create mount point directories (config files created at runtime)
RUN mkdir -p config data/config outputs/studio uploads

EXPOSE 7860

ENV OLLAMA_HOST=host.docker.internal
ENV OLLAMA_PORT=11434

CMD ["python", "-m", "dbnotebook", "--host", "0.0.0.0", "--port", "7860"]
