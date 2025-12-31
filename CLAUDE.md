# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DBNotebook** - A multimodal RAG system using LlamaIndex, PostgreSQL/pgvector, and Flask. Features NotebookLM-style document organization, persistent conversations, RAPTOR hierarchical retrieval, hybrid BM25+vector search, multi-provider LLM support (Ollama, OpenAI, Anthropic, Gemini), vision-based image understanding, Content Studio for multimodal content generation, and Excel Analytics with AI-powered dashboard generation.

## Development Commands

```bash
# Start application (handles venv, deps, Ollama automatically)
./start.sh                    # Flask UI (default port 7860)
./start.sh 8080 localhost     # Custom port/host

# Manual execution
source venv/bin/activate
python -m dbnotebook --host localhost --port 7860

# Frontend development (React + Vite)
cd frontend
npm install
npm run dev                   # Dev server on :3000 (proxies to Flask :7860)
npm run build                 # Production build (tsc + vite)
npm run lint                  # ESLint
npm run typecheck             # TypeScript check (tsc -b)

# Database migrations (Alembic)
alembic upgrade head          # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Tests
pytest                        # All tests
pytest tests/test_notebook_integration.py  # Specific test
pytest tests/raptor/          # RAPTOR module tests

# Docker
docker compose up --build     # External Ollama required on host
```

## Architecture

### Core Data Flow

```
React Frontend (:3000) → Flask API (:7860) → LocalRAGPipeline
                                                    ↓
                              ┌─────────────────────┴─────────────────────┐
                              ↓                                           ↓
                    LocalDataIngestion                             LocalChatEngine
                    (document processing)                          (chat/retrieval)
                              ↓                                           ↓
                    RAPTOR TreeBuilder ←──────────────────────── LocalRetriever
                    (hierarchical summaries)                     (hybrid BM25+vector)
                              ↓                                           ↓
                    PGVectorStore ─────────────────────────────────────────
                    (PostgreSQL + pgvector)
                              ↓
                    LLM Response (SSE streaming)
```

### Key Components

**`dbnotebook/pipeline.py`** - Central orchestrator:
- Manages LLM/embedding providers, notebook context (`_current_notebook_id`, `_current_user_id`)
- Key methods: `switch_notebook()`, `store_nodes()`, `stream_chat()`, `set_chat_mode()`

**`dbnotebook/ui/web.py`** - Flask web interface:
- REST API + SSE streaming endpoints
- Integrates NotebookManager, MetadataManager, all providers

**`dbnotebook/core/services/`** - Service layer (inherit from `BaseService`):
- `chat_service.py` - Chat orchestration with refinement and suggestions
- `document_service.py` - Document upload and processing
- `multi_notebook_service.py` - Cross-notebook queries
- `continuity_service.py` - Session continuity
- All services receive `pipeline`, `db_manager`, `notebook_manager` via constructor

**`dbnotebook/core/vector_store/pg_vector_store.py`** - PGVectorStore:
- PostgreSQL + pgvector with JSONB metadata
- Duplicate prevention via md5(text) + notebook_id unique index
- Table: `data_embeddings`

**`dbnotebook/core/engine/retriever.py`** - LocalRetriever:
- ≤6 nodes: VectorIndexRetriever (pure semantic)
- \>6 nodes: RouterRetriever selecting:
  - QueryFusionRetriever (ambiguous): 5 query variations, fuses BM25+vector
  - TwoStageRetriever (clear): BM25+vector → reranker (`mixedbread-ai/mxbai-rerank-large-v1`)

### RAPTOR Hierarchical Retrieval

**`dbnotebook/core/raptor/`** - Implementation of [RAPTOR paper](https://arxiv.org/abs/2401.18059):
- `tree_builder.py` - Builds hierarchical summary trees bottom-up
- `clustering.py` - Semantic clustering of document chunks
- `summarizer.py` - LLM-based cluster summarization
- `retriever.py` - Multi-level retrieval across tree levels
- `worker.py` - Background RAPTOR tree building

Tree building flow: Document chunks (level 0) → Cluster by similarity → Summarize clusters (level 1) → Repeat until root

### AI Transformations

**`dbnotebook/core/transformations/`** - Document transformation service:
- `transformation_service.py` - Generates dense summaries, key insights, reflection questions
- Uses chunked processing for long documents (>10K chars)
- Async with sync wrapper for Flask routes

### Excel Analytics & AI Dashboards

Complete Excel/CSV analysis pipeline with LLM-powered dashboard generation.

**Backend** (`dbnotebook/core/analytics/`):
- `service.py` - AnalyticsService: Session management, file handling, orchestration
- `profiler.py` - DataProfiler: ydata-profiling integration for statistical analysis
- `dashboard_generator.py` - DashboardConfigGenerator: LLM-powered dashboard config generation
- `types.py` - Type definitions (ParsedData, ProfilingResult, DashboardConfig, KPIConfig, ChartConfig, FilterConfig)

**API Flow**:
1. `POST /api/analytics/upload` - Upload Excel/CSV file, create session
2. `POST /api/analytics/parse/{session_id}` - Parse with pandas, extract column metadata
3. `POST /api/analytics/profile/{session_id}` - Run ydata-profiling, generate quality score
4. `POST /api/analytics/analyze/{session_id}` - LLM generates dashboard config (KPIs, charts, filters)
5. `GET /api/analytics/sessions/{session_id}/data` - Get complete dashboard data

**Frontend** (`frontend/src/components/Analytics/`):
- `ExcelUploader.tsx` - Drag-and-drop file upload
- `DashboardView.tsx` - Main dashboard with tabs (Dashboard, Data Profile)
- `KPICardGrid.tsx` - Renders KPI metric cards with aggregations
- `ChartGrid.tsx` - Renders bar/line/pie/scatter/area charts
- `FilterBar.tsx` - Interactive categorical/range/date filters

**State Management** (`frontend/src/contexts/AnalyticsContext.tsx`):
- `useAnalytics()` hook for session state, data, filters
- `useCrossFilter()` hook for cross-chart filtering
- Actions: `uploadFile()`, `parseFile()`, `profileData()`, `analyzeDashboard()`, `runFullAnalysis()`

**Types** (`frontend/src/types/analytics.ts`):
- `AnalysisState`: idle → uploading → parsing → profiling → analyzing → complete
- `DashboardConfig`: KPIs, charts, filters, metadata
- `FilterState`, `CrossFilterEvent` for interactive filtering

### Plugin Architecture

**`dbnotebook/core/registry.py`** - PluginRegistry:
```
├── LLM Providers: Ollama, OpenAI, Anthropic, Gemini
├── Embedding Providers: HuggingFace, OpenAI
├── Retrieval Strategies: Hybrid, Semantic, Keyword
├── Image Providers: Gemini/Imagen
├── Vision Providers: OpenAI GPT-4V, Gemini Vision
├── Web Search: Firecrawl
└── Web Scraper: Jina Reader
```

Providers selected via env vars: `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `RETRIEVAL_STRATEGY`, `VISION_PROVIDER`

### Configuration System

**`config/*.yaml`** - YAML configuration files:
- `raptor.yaml` - Clustering, summarization, tree building params
- `ingestion.yaml` - Chunking, embedding, retrieval settings
- `models.yaml` - Model configurations

**`dbnotebook/core/config/config_loader.py`** - Loads and caches YAML configs:
```python
from dbnotebook.core.config import get_config_value
value = get_config_value('raptor', 'clustering', 'min_cluster_size', default=3)
```

### API Routes

Routes in `dbnotebook/api/routes/`:
- `chat.py` - `/chat`, `/api/chat/*` - Chat and streaming
- `studio.py` - `/api/studio/*` - Content generation gallery
- `vision.py` - `/api/vision/*` - Image analysis
- `web_content.py` - `/api/web/*` - Web search and scraping
- `transformations.py` - `/api/transformations/*` - AI document transformations
- `multi_notebook.py` - `/api/multi-notebook/*` - Cross-notebook queries
- `analytics.py` - `/api/analytics/*` - Excel profiling and AI dashboard generation

Routes follow pattern: `create_*_routes(app, pipeline, db_manager, notebook_manager)`

### Database Layer

**ORM**: SQLAlchemy 2.0 (`core/db/models.py`)
**Migrations**: Alembic (`/alembic/`)

**Tables**:
- `notebooks` - Document collections with `user_id`
- `notebook_sources` - Documents with `active` toggle for RAG inclusion
- `conversations` - Persistent chat history per notebook
- `data_embeddings` - pgvector embeddings with JSONB metadata
- `generated_content` - Content Studio outputs

## Environment Configuration

Copy `.env.example` to `.env`. Key variables:

```bash
# Core providers
LLM_PROVIDER=ollama              # ollama|openai|anthropic|gemini
LLM_MODEL=llama3.1:latest
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
RETRIEVAL_STRATEGY=hybrid        # hybrid|semantic|keyword

# Database
DATABASE_URL=postgresql://user:pass@localhost:5433/dbnotebook_dev

# Vision & Image Generation
VISION_PROVIDER=gemini           # gemini|openai
IMAGE_GENERATION_PROVIDER=gemini
GEMINI_IMAGE_MODEL=imagen-4.0-generate-001

# Web Search (optional)
FIRECRAWL_API_KEY=...           # Required for web search
JINA_API_KEY=...                # Optional (higher rate limits)

# Contextual Retrieval (optional, enriches chunks with LLM context)
CONTEXTUAL_RETRIEVAL_ENABLED=false
```

## Frontend

Located in `/frontend/`:
- **Stack**: React 19, Vite 7, Tailwind CSS 4, TypeScript
- **Theme**: Deep Space Terminal (dark theme)
- **Proxy**: Vite proxies `/api`, `/chat`, `/upload`, `/image` to Flask :7860
- **State**: `AnalyticsContext` for analytics, React Context for app state

## Key Defaults

- Flask: http://localhost:7860
- Frontend dev: http://localhost:3000
- PostgreSQL: localhost:5433 (Docker) or 5432 (local)
- Chunk size: 512 tokens, overlap: 32
- Similarity top-k: 20, rerank top-k: 6
- Embedding dimension: 768 (nomic) or 1536 (OpenAI)

## Document Processing Pipeline

1. Format-specific readers (PyMuPDF for PDFs, LangChain for Office docs)
2. Vision providers for images (Gemini/OpenAI)
3. MD5 hash duplicate detection
4. SentenceSplitter (512 tokens, 32 overlap)
5. HuggingFace embeddings (batch size 8)
6. Store in PGVectorStore with metadata
7. Optional: RAPTOR tree building for hierarchical summaries
