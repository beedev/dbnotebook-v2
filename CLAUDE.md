# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DBNotebook** - A multimodal RAG (Retrieval-Augmented Generation) Sales Enablement System using LlamaIndex, PostgreSQL/pgvector, and Flask. Features NotebookLM-style document organization, persistent conversations, hybrid retrieval (BM25 + vector), multi-provider LLM support (Ollama, OpenAI, Anthropic, Gemini), web search integration (Firecrawl + Jina), vision-based image understanding (OpenAI GPT-4V, Gemini Vision), and Content Studio for multimodal content generation.

## Development Commands

```bash
# Start application (handles venv, deps, Ollama automatically)
./start.sh                    # Flask UI (default port 7860)
./start.sh 8080 localhost     # Custom port/host
./start_gradio.sh             # Original Gradio UI

# Manual execution
source venv/bin/activate
python -m dbnotebook --host localhost --port 7860

# Frontend development (React + Vite)
cd frontend
npm install
npm run dev                   # Dev server with HMR
npm run build                 # Production build
npm run lint                  # ESLint

# Database migrations (Alembic)
alembic upgrade head          # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Docker
docker compose up --build

# Tests
pytest
pytest tests/test_metadata.py  # Specific test
```

## Architecture

### Core Data Flow

```
User Input → Flask UI (web.py) → LocalRAGPipeline (pipeline.py)
                                        ↓
                    ┌───────────────────┴───────────────────┐
                    ↓                                       ↓
           LocalDataIngestion                        LocalChatEngine
           (document processing)                    (chat/retrieval)
                    ↓                                       ↓
           PGVectorStore ←─────────────────────── LocalRetriever
           (PostgreSQL + pgvector)                 (hybrid BM25 + vector)
                    ↓
           LLM Response (streaming via SSE)
```

### Key Components

**`dbnotebook/pipeline.py`** - Central orchestrator:
- Manages LLM providers, embedding models, notebook context
- Tracks `_current_notebook_id` and `_current_user_id` for document isolation
- Coordinates vector store, chat engine, conversation history
- Key methods: `switch_notebook()`, `store_nodes()`, `stream_chat()`, `set_chat_mode()`

**`dbnotebook/ui/web.py`** - Flask web interface:
- REST API endpoints for chat, upload, notebooks, image generation
- Streaming responses via Server-Sent Events (SSE)
- Integrates with NotebookManager, MetadataManager, ImageProvider

**`dbnotebook/core/vector_store/pg_vector_store.py`** - PGVectorStore (replaces ChromaDB):
- PostgreSQL + pgvector for O(log n) metadata filtering
- Stores embeddings with `notebook_id`, `file_hash`, `it_practice`, `offering_id` metadata
- Table: `data_embeddings` with JSONB metadata column
- Duplicate prevention via md5(text) + notebook_id unique index

**`dbnotebook/core/engine/retriever.py`** - LocalRetriever:
- ≤6 nodes: VectorIndexRetriever (pure semantic)
- \>6 nodes: RouterRetriever selecting:
  - QueryFusionRetriever (ambiguous queries): generates 5 variations, fuses BM25 + vector
  - TwoStageRetriever (clear queries): BM25 + vector → reranker (`mixedbread-ai/mxbai-rerank-large-v1`)

**`dbnotebook/core/notebook/notebook_manager.py`** - NotebookManager:
- CRUD for notebooks (NotebookLM-style document organization)
- Document tracking with MD5 hash duplicate detection
- Multi-user support via `user_id`

**`dbnotebook/core/conversation/conversation_store.py`** - ConversationStore:
- Persistent conversation history per notebook
- Cross-session context preservation

### Plugin Architecture

```
PluginRegistry (core/registry.py)
├── LLM Providers: Ollama, OpenAI, Anthropic, Gemini
├── Embedding Providers: HuggingFace, OpenAI
├── Retrieval Strategies: Hybrid, Semantic, Keyword
├── Image Providers: Gemini/Imagen
├── Vision Providers: OpenAI GPT-4V, Gemini Vision
├── Web Search Providers: Firecrawl
└── Web Scraper Providers: Jina Reader
```

Providers are registered at startup and selected via environment variables (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `RETRIEVAL_STRATEGY`, `VISION_PROVIDER`).

### Web Search Integration

**`dbnotebook/core/providers/firecrawl.py`** - FirecrawlSearchProvider:
- Web search via Firecrawl API
- Returns structured results with URL, title, description

**`dbnotebook/core/providers/jina_reader.py`** - JinaReaderProvider:
- Content scraping via Jina Reader (r.jina.ai/{url})
- Extracts clean markdown content from web pages

**`dbnotebook/core/ingestion/web_ingestion.py`** - WebContentIngestion:
- Orchestrates search → preview → scrape → embed workflow
- User selects URLs to import after search results displayed

**API Endpoints**:
- `POST /api/web/search` - Search web for URLs
- `POST /api/web/scrape-preview` - Preview content before import
- `POST /api/notebooks/{id}/web-sources` - Add selected URLs to notebook

### Vision Processing

**`dbnotebook/core/interfaces/vision.py`** - VisionProvider ABC:
- Abstract interface for image understanding providers
- Methods: `analyze_image()`, `extract_text()`, `validate()`

**`dbnotebook/core/providers/gemini_vision.py`** - GeminiVisionProvider:
- Uses Gemini Pro Vision for image understanding
- Supports image analysis and OCR-like text extraction

**`dbnotebook/core/providers/openai_vision.py`** - OpenAIVisionProvider:
- Uses GPT-4V/GPT-4o for image understanding
- High accuracy text extraction and visual analysis

**API Endpoints**:
- `POST /api/vision/analyze` - Analyze image with optional prompt
- `GET /api/vision/providers` - List available vision providers

### Content Studio

**`dbnotebook/core/studio/`** - Multimodal content generation:
- `StudioManager` - CRUD for generated content, gallery management
- `ContentGenerator` (base) - Abstract class for generators
- `InfographicGenerator` - Creates infographics using Gemini/Imagen
- `MindMapGenerator` - Creates mind maps using Gemini/Imagen

**`dbnotebook/api/routes/studio.py`** - Studio API endpoints:
- `GET /api/studio/gallery` - List generated content with filters
- `POST /api/studio/generate` - Generate new content from notebook
- `GET /api/studio/content/{id}` - Get content details
- `GET /api/studio/content/{id}/file` - Serve generated file
- `GET /api/studio/content/{id}/thumbnail` - Serve thumbnail
- `DELETE /api/studio/content/{id}` - Delete content
- `GET /api/studio/generators` - List available generators

**Database**: `generated_content` table stores metadata, file paths, source notebook reference.

### Database Layer

- **ORM**: SQLAlchemy 2.0 with models in `core/db/models.py`
- **Migrations**: Alembic in `/alembic/`
- **Tables**:
  - `users` - User accounts
  - `notebooks` - NotebookLM-style document collections
  - `notebook_sources` - Documents within notebooks (has `active` toggle for RAG inclusion)
  - `conversations` - Persistent chat history per notebook
  - `query_logs` - Query logging for observability
  - `data_embeddings` - pgvector embeddings storage
  - `generated_content` - Content Studio outputs (infographics, mind maps)

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Core providers
LLM_PROVIDER=ollama              # ollama|openai|anthropic|gemini
LLM_MODEL=llama3.1:latest
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
RETRIEVAL_STRATEGY=hybrid        # hybrid|semantic|keyword

# Database (required for persistence)
DATABASE_URL=postgresql://user:pass@localhost:5433/dbnotebook_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=dbnotebook_dev

# API keys (as needed)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...

# Image generation
IMAGE_GENERATION_PROVIDER=gemini
GEMINI_IMAGE_MODEL=imagen-4.0-generate-001

# Web Search (optional)
FIRECRAWL_API_KEY=...           # Required for web search
JINA_API_KEY=...                # Optional (for higher rate limits)

# Vision processing
VISION_PROVIDER=gemini          # gemini|openai
GEMINI_VISION_MODEL=gemini-2.0-flash-exp
OPENAI_VISION_MODEL=gpt-4o
```

## Frontend (React + TypeScript)

Located in `/frontend/`:
- **Stack**: React 19, Vite, Tailwind CSS 4, TypeScript
- **Theme**: Deep Space Terminal (dark theme)
- **Dev server**: `npm run dev` (proxies to Flask backend)

## Key Defaults

- Flask UI: http://localhost:7860
- Ollama: localhost:11434
- PostgreSQL: localhost:5433 (Docker) or 5432 (local)
- Chunk size: 512 tokens, overlap: 32
- Context window: 8000 tokens
- Similarity top-k: 20, rerank top-k: 6
- Embedding dimension: 768 (nomic) or 1536 (OpenAI)

## Document Processing

Supported formats: PDF, EPUB, TXT, DOCX, PPTX, images (via Vision AI)

Pipeline:
1. Format-specific readers (PyMuPDF for PDFs, LangChain for Office docs)
2. Vision providers for images (Gemini Vision, OpenAI GPT-4V)
3. MD5 hash for duplicate detection
4. SentenceSplitter (512 tokens, 32 overlap)
5. HuggingFace embeddings (batch size 8)
6. Store in PGVectorStore with metadata

## Docker Deployment

```bash
# Start with Docker (external Ollama required)
docker compose up --build

# External Ollama must be running on host
ollama serve
```

Docker Compose configuration:
- `dbnotebook` service: Flask app + RAG pipeline
- `postgres` service: PostgreSQL 16 + pgvector
- External Ollama: Connects via `host.docker.internal:11434`
