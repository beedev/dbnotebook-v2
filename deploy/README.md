# DBNotebook - Deployment Guide

Multimodal RAG Sales Enablement System with NotebookLM-style document organization.

## Prerequisites

- **Docker Desktop** (macOS/Windows) or Docker Engine + Compose (Linux)
- **GitHub account** with package access (provided by admin)
- **Ollama** running on host (optional - for local LLM inference)

## Quick Start

### 1. Login to GitHub Container Registry

```bash
# Using GitHub CLI (recommended)
gh auth token | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Or using personal access token
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Access

Open http://localhost:7860

## Configuration

Edit `.env` file with your settings:

```bash
# LLM Provider (ollama, openai, anthropic, gemini)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:latest

# Embedding Provider
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# Retrieval Strategy
RETRIEVAL_STRATEGY=hybrid

# API Keys (as needed for your provider)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Image Generation (for Content Studio)
IMAGE_GENERATION_PROVIDER=gemini
GEMINI_IMAGE_MODEL=imagen-4.0-generate-001

# Vision Processing
VISION_PROVIDER=gemini

# Web Search (optional)
FIRECRAWL_API_KEY=...
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| dbnotebook | 7860 | Web UI & API |
| postgres | 5432 | PostgreSQL + pgvector (internal) |

## Data Persistence

| Directory | Purpose |
|-----------|---------|
| `./data/` | Uploaded documents, embeddings |
| `./outputs/` | Generated content (infographics, mind maps) |
| `./uploads/` | Temporary upload files |
| `./config/` | Model configurations |

## Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f dbnotebook

# Stop services
docker compose down

# Update to latest image
docker compose pull
docker compose up -d

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

## Troubleshooting

### Cannot pull image
Ensure you're logged into GHCR:
```bash
gh auth token | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Ollama not connecting
- Ensure Ollama is running on host: `ollama serve`
- Check OLLAMA_HOST in .env points to `host.docker.internal:11434`

### Database connection issues
- Wait for postgres healthcheck to pass
- Check logs: `docker compose logs postgres`

## Features

- **Notebook Management**: Organize documents into notebooks
- **Multi-Provider LLM**: Ollama, OpenAI, Anthropic, Gemini
- **Content Studio**: Generate infographics and mind maps
- **Web Search**: Import content from URLs
- **Vision Processing**: Extract text from images
- **Hybrid Retrieval**: BM25 + vector search with reranking
