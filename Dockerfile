FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY dbnotebook/ dbnotebook/
COPY frontend/dist/ frontend/dist/
COPY data/config/ data/config/
COPY alembic/ alembic/
COPY alembic.ini .

# Create directories
RUN mkdir -p data outputs/studio uploads

EXPOSE 7860

# Use environment variable for host configuration
ENV OLLAMA_HOST=host.docker.internal
ENV OLLAMA_PORT=11434

CMD ["python", "-m", "dbnotebook", "--host", "0.0.0.0"]
