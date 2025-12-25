# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install dependencies
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# OCI labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/beedev/dbnotebook"
LABEL org.opencontainers.image.description="Multimodal RAG Sales Enablement System"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.version="1.0.0"

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
COPY frontend/dist/ frontend/dist/
COPY data/config/ data/config/
COPY alembic/ alembic/
COPY alembic.ini .

# Create mount point directories
RUN mkdir -p config data outputs/studio uploads

EXPOSE 7860

ENV OLLAMA_HOST=host.docker.internal
ENV OLLAMA_PORT=11434

CMD ["python", "-m", "dbnotebook", "--host", "0.0.0.0", "--port", "7860"]
