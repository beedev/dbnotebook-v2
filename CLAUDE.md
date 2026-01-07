# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DBNotebook** - A multimodal RAG system using LlamaIndex, PostgreSQL/pgvector, and Flask. Features NotebookLM-style document organization, persistent conversations, RAPTOR hierarchical retrieval, hybrid BM25+vector search, multi-provider LLM support (Ollama, OpenAI, Anthropic, Gemini), vision-based image understanding, Content Studio for multimodal content generation, Excel Analytics with AI-powered dashboard generation, and agentic query analysis with document routing.

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
pytest -v -x                  # Verbose, stop on first failure

# Docker
docker compose up --build     # External Ollama required on host
```

## Quick Reference

**Add new provider**: Create class in `core/providers/`, register in `core/plugins.py`
**Add new route**: Create in `api/routes/`, register in `ui/web.py` via `create_*_routes()`
**Add new service**: Inherit `BaseService` in `core/services/`, inject via constructor
**Modify DB schema**: Edit `core/db/models.py`, then `alembic revision --autogenerate`
**Frontend component**: Add to `frontend/src/components/`, types in `frontend/src/types/`

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
- `refinement_service.py` - Query refinement suggestions
- `document_routing_service.py` - Intelligent document routing
- `image_service.py` - Image generation orchestration
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

### Agents Module

**`dbnotebook/core/agents/`** - Agentic analysis components:
- `base.py` - Base agent interface
- `query_analyzer.py` - Analyzes queries to determine retrieval strategy
- `document_analyzer.py` - Analyzes document content for routing decisions

### Excel Analytics & AI Dashboards

Complete Excel/CSV analysis pipeline with LLM-powered dashboard generation.

**Backend** (`dbnotebook/core/analytics/`):
- `service.py` - AnalyticsService: Session management, file handling, orchestration
- `profiler.py` - DataProfiler: ydata-profiling integration for statistical analysis
- `dashboard_generator.py` - DashboardConfigGenerator: LLM-powered dashboard config generation
- `dashboard_modifier.py` - DashboardModifier: NLP-based dashboard modification agent
- `types.py` - Type definitions (ParsedData, ProfilingResult, DashboardConfig, ModificationResult)

**API Flow**:
1. `POST /api/analytics/upload` - Upload Excel/CSV file, create session
2. `POST /api/analytics/parse/{session_id}` - Parse with pandas, extract column metadata
3. `POST /api/analytics/profile/{session_id}` - Run ydata-profiling, generate quality score
4. `POST /api/analytics/analyze/{session_id}` - LLM generates dashboard config (KPIs, charts, filters)
5. `GET /api/analytics/sessions/{session_id}/data` - Get complete dashboard data
6. `POST /api/analytics/sessions/{session_id}/modify` - NLP-based dashboard modification
7. `POST /api/analytics/sessions/{session_id}/undo` - Undo last modification
8. `POST /api/analytics/sessions/{session_id}/redo` - Redo undone modification

**Frontend** (`frontend/src/components/Analytics/`):
- `ExcelUploader.tsx` - Drag-and-drop file upload
- `DashboardView.tsx` - Main dashboard with tabs (Dashboard, Data Profile), PDF export
- `DashboardModifier.tsx` - NLP modification input with undo/redo
- `KPICardGrid.tsx` - Renders KPI metric cards with aggregations
- `ChartGrid.tsx` - Bar/line/pie/scatter/area charts with cross-filtering, top 10 + "Others" grouping
- `FilterBar.tsx` - Interactive categorical/range/date filters
- `FilteredDataTable.tsx` - Displays filtered raw data with CSV download
- `ColumnProfileTable.tsx` - Sortable column statistics table
- `ColumnDetailPanel.tsx` - Detailed column statistics (numeric/categorical)

**State Management** (`frontend/src/contexts/AnalyticsContext.tsx`):
- `useAnalytics()` hook for session state, data, filters, modification history
- `useCrossFilter()` hook for cross-chart filtering
- Actions: `uploadFile()`, `runFullAnalysis()`, `modifyDashboard()`, `undoModification()`, `redoModification()`

**Types** (`frontend/src/types/analytics.ts`):
- `AnalysisState`: idle → uploading → parsing → profiling → analyzing → complete
- `DashboardConfig`: KPIs, charts, filters, metadata
- `FilterState`, `CrossFilterEvent` for interactive filtering
- `ModificationState` for undo/redo history

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
- `agents.py` - `/api/agents/*` - Agentic query analysis endpoints

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
# Or individual settings:
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=dbnotebook_dev

# Context Window
CONTEXT_WINDOW=128000            # Model context window (llama3.1 supports 128K)
CHAT_TOKEN_LIMIT=32000           # Chat memory buffer limit

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
- **State**: React Context pattern - `AnalyticsContext`, `ChatContext`, `NotebookContext`, `DocumentContext`
- **v2 Components**: Alternative UI in `components/v2/` (NotebookLM-style layout)

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

## Common Patterns

### Adding a New LLM Provider
```python
# 1. core/providers/my_provider.py
class MyProvider(LLMProvider):
    def get_llm(self, **kwargs) -> LLM: ...
    def validate(self) -> bool: ...

# 2. core/plugins.py
PluginRegistry.register_llm_provider("my_provider", MyProvider)

# 3. .env
LLM_PROVIDER=my_provider
```

### Adding a New API Route
```python
# 1. api/routes/my_feature.py
def create_my_feature_routes(app, pipeline, db_manager, notebook_manager):
    @app.route('/api/my-feature', methods=['POST'])
    def my_endpoint(): ...

# 2. ui/web.py (in create_app)
from dbnotebook.api.routes.my_feature import create_my_feature_routes
create_my_feature_routes(app, pipeline, db_manager, notebook_manager)
```

### Service Layer Pattern
```python
# All services in core/services/ inherit BaseService
class MyService(BaseService):
    def __init__(self, pipeline, db_manager, notebook_manager):
        super().__init__(pipeline, db_manager, notebook_manager)
```

## Debugging Tips

- **Chat not retrieving**: Check `_current_notebook_id` is set in pipeline
- **Embeddings failing**: Verify `EMBEDDING_MODEL` and vector dimension match
- **RAPTOR tree not building**: Check `raptor_status` in `notebook_sources` table
- **Frontend proxy issues**: Ensure Flask running on :7860 before `npm run dev`
- **Migration conflicts**: Run `alembic heads` to check for multiple heads
- **LLM connection issues**: Check `OLLAMA_HOST` (default: localhost:11434)
- **Context overflow**: Reduce `CHAT_TOKEN_LIMIT` or increase `CONTEXT_WINDOW`
