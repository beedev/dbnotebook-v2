# DBNotebook Technical Architecture

## Overview

DBNotebook is a self-hosted document assistant that lets teams upload documents (PDFs, Word, PowerPoint, images) into organized notebooks and have intelligent conversations with their content.

**Key Capabilities:**
- **Smart Q&A**: Ask questions about your documents and get accurate, context-aware answers with source citations
- **Multiple AI Models**: Choose between local AI (privacy-first, no data leaves your network) or cloud providers (OpenAI, Anthropic, Google) based on your needs
- **Web Research**: Search the web and import relevant articles directly into your notebooks
- **Image Analysis**: Upload images, screenshots, or diagrams and the AI extracts and understands the content
- **Content Studio**: Automatically generate infographics and mind maps from your documents for presentations
- **Persistent History**: Conversations are saved per notebook, so you can pick up where you left off

**Deployment**: Single Docker command to deploy - runs entirely on your infrastructure with no external dependencies required.

---

## Core Stack

- **Backend**: Python/Flask with LlamaIndex orchestration
- **Frontend**: React 19 + Vite + Tailwind CSS
- **Database**: PostgreSQL 16 + pgvector extension
- **Containerization**: Docker Compose (multi-container)

## RAG Pipeline Architecture

```
Documents → Chunking (512 tokens) → Embeddings → PGVector Store
                                                      ↓
User Query → Hybrid Retrieval (BM25 + Vector) → Reranker → LLM → Response
```

**Retrieval Strategy (Adaptive)**:
- Small datasets (≤6 nodes): Pure vector similarity
- Large datasets: RouterRetriever selects between:
  - QueryFusionRetriever for ambiguous queries (generates 5 query variations)
  - TwoStageRetriever for clear queries (BM25 + vector → reranker)

## Strengths

| Area | Approach |
|------|----------|
| **Extensibility** | Plugin registry pattern - swap LLM/embedding/vision providers without code changes |
| **Data Isolation** | NotebookLM-style architecture - documents scoped by notebook_id, enabling multi-tenant use |
| **Hybrid Search** | Combines lexical (BM25) and semantic (vector) retrieval, avoiding pure-embedding blind spots |
| **Local-First** | Ollama integration enables fully offline operation with no data egress |
| **Persistence** | PostgreSQL for metadata + pgvector for embeddings - single database, O(log n) filtered queries |
| **Streaming** | Server-Sent Events (SSE) for real-time token streaming |

## Plugin Architecture

```
PluginRegistry
├── LLM Providers: Ollama, OpenAI, Anthropic, Gemini
├── Embedding Providers: HuggingFace (local), OpenAI
├── Vision Providers: GPT-4V, Gemini Vision
├── Image Generators: Gemini Imagen
└── Web Providers: Firecrawl (search), Jina (scraping)
```

## Key Design Decisions

1. **pgvector over ChromaDB**: Enables metadata filtering at query time without loading all vectors into memory - critical for multi-notebook isolation

2. **Reranker Stage**: Uses `mxbai-rerank-large-v1` to refine retrieval results - improves precision on top-k without increasing embedding costs

3. **Lazy Engine Initialization**: Chat engines created on-demand per notebook, preserving conversation context while managing memory

4. **Environment-Driven Configuration**: Provider selection via env vars (`LLM_PROVIDER`, `VISION_PROVIDER`) - no code deployment for model changes

## Docker Architecture

```
┌─────────────────┐     ┌─────────────────────┐
│   dbnotebook    │────▶│  postgres:pgvector  │
│  (Flask + RAG)  │     │    (embeddings +    │
│   Port 7860     │     │     metadata)       │
└────────┬────────┘     └─────────────────────┘
         │
         ▼ (host.docker.internal)
┌─────────────────┐
│  Ollama (host)  │
│   Port 11434    │
└─────────────────┘
```

---

## Code Organization

### Project Structure

```
dbnotebook/
├── __main__.py              # Application entry point, CLI argument parsing
├── pipeline.py              # Central RAG orchestrator (LLM, embeddings, retrieval)
├── logger.py                # Logging configuration
├── setting/                 # Configuration management
│   └── setting.py           # Pydantic settings from env vars + YAML
│
├── api/                     # REST API Layer
│   ├── routes/
│   │   ├── chat.py          # Chat streaming endpoints (SSE)
│   │   ├── studio.py        # Content Studio endpoints (infographics, mindmaps)
│   │   ├── vision.py        # Image analysis endpoints
│   │   └── web_content.py   # Web search/scraping endpoints
│   └── schemas/             # Pydantic request/response models
│       ├── chat.py
│       ├── document.py
│       └── notebook.py
│
├── ui/
│   └── web.py               # Flask application, route handlers, SSE streaming
│
└── core/                    # Business Logic Layer
    ├── plugins.py           # Plugin registration and discovery
    ├── registry.py          # Generic plugin registry pattern
    │
    ├── interfaces/          # Abstract Base Classes (Contracts)
    │   ├── llm.py           # LLMProvider ABC
    │   ├── embedding.py     # EmbeddingProvider ABC
    │   ├── vision.py        # VisionProvider ABC
    │   ├── image_generation.py
    │   ├── retrieval.py     # RetrievalStrategy ABC
    │   └── web_content.py   # WebSearch, WebScraper ABCs
    │
    ├── providers/           # Interface Implementations
    │   ├── ollama.py        # Local LLM via Ollama
    │   ├── openai.py        # OpenAI GPT models
    │   ├── anthropic.py     # Claude models
    │   ├── huggingface.py   # HuggingFace embeddings
    │   ├── gemini_image.py  # Imagen generation
    │   ├── gemini_vision.py # Gemini Vision
    │   ├── openai_vision.py # GPT-4V
    │   ├── firecrawl.py     # Web search provider
    │   └── jina_reader.py   # Web scraping provider
    │
    ├── strategies/          # Retrieval Strategy Implementations
    │   ├── hybrid.py        # BM25 + Vector fusion
    │   ├── semantic.py      # Pure vector similarity
    │   └── keyword.py       # BM25 lexical search
    │
    ├── model/
    │   └── model.py         # LocalRAGModel - LLM wrapper with Ollama integration
    │
    ├── embedding/
    │   └── embedding.py     # LocalEmbedding - embedding model wrapper
    │
    ├── engine/
    │   ├── engine.py        # LocalChatEngine - LlamaIndex chat engine factory
    │   └── retriever.py     # LocalRetriever - adaptive retrieval (Router/Fusion/TwoStage)
    │
    ├── vector_store/
    │   ├── vector_store.py  # Base vector store interface
    │   └── pg_vector_store.py # PostgreSQL + pgvector implementation
    │
    ├── ingestion/
    │   ├── ingestion.py     # LocalDataIngestion - document processing pipeline
    │   ├── web_ingestion.py # WebContentIngestion - URL import workflow
    │   └── synopsis_manager.py # Document summary generation
    │
    ├── db/
    │   ├── db.py            # DatabaseManager - SQLAlchemy session management
    │   └── models.py        # ORM models (User, Notebook, Source, Conversation, etc.)
    │
    ├── notebook/
    │   └── notebook_manager.py # NotebookManager - CRUD for notebooks/sources
    │
    ├── conversation/
    │   └── conversation_store.py # Persistent conversation history
    │
    ├── studio/              # Content Generation Module
    │   ├── studio_manager.py # Gallery CRUD, generator orchestration
    │   └── generators/
    │       ├── base.py      # ContentGenerator ABC
    │       ├── infographic.py # Infographic generation via Imagen
    │       └── mindmap.py   # Mind map generation via Imagen
    │
    ├── vision/
    │   └── vision_manager.py # Multi-provider vision orchestration
    │
    ├── metadata/
    │   └── metadata_manager.py # Document metadata extraction
    │
    ├── observability/
    │   ├── query_logger.py  # Query logging to database
    │   └── token_counter.py # Token usage tracking
    │
    └── prompt/              # Prompt Templates
        ├── qa_prompt.py     # RAG QA prompts
        ├── query_gen_prompt.py # Query expansion prompts
        └── select_prompt.py # Router selection prompts
```

### Supporting Structure

```
├── frontend/                # React SPA
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   └── lib/             # API client, utilities
│   └── dist/                # Production build (served by Flask)
│
├── alembic/                 # Database Migrations
│   └── versions/            # Migration scripts
│
├── config/
│   └── models.yaml          # UI model dropdown configuration
│
├── data/                    # Runtime data (mounted volume)
├── outputs/                 # Generated content (mounted volume)
├── uploads/                 # User uploads (mounted volume)
│
├── docker-compose.yml       # Multi-container orchestration
├── Dockerfile               # Multi-stage Python build
└── requirements.txt         # Python dependencies
```

## Architecture Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Plugin Registry** | `core/registry.py` | Runtime provider discovery, zero-code swapping |
| **Strategy Pattern** | `core/strategies/` | Interchangeable retrieval algorithms |
| **Abstract Factory** | `core/interfaces/` | Consistent contracts across providers |
| **Dependency Injection** | `pipeline.py` | Components receive dependencies at init |
| **Repository Pattern** | `core/db/`, `notebook_manager.py` | Data access abstraction |
| **Facade Pattern** | `pipeline.py` | Unified API over complex subsystems |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           REQUEST FLOW                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  HTTP Request                                                            │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────────────────────┐ │
│  │ web.py  │───▶│ api/routes/* │───▶│          pipeline.py            │ │
│  │ (Flask) │    │  (endpoints) │    │   (LocalRAGPipeline facade)     │ │
│  └─────────┘    └──────────────┘    └──────────────┬──────────────────┘ │
│                                                     │                    │
│                    ┌────────────────────────────────┼────────────────┐   │
│                    │                                │                │   │
│                    ▼                                ▼                ▼   │
│  ┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   core/engine/      │  │ core/ingestion/ │  │  core/providers/    │  │
│  │ ├── engine.py       │  │ (doc processing)│  │  (LLM, embedding,   │  │
│  │ └── retriever.py    │  │                 │  │   vision, search)   │  │
│  └──────────┬──────────┘  └────────┬────────┘  └──────────┬──────────┘  │
│             │                      │                      │             │
│             ▼                      ▼                      ▼             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    core/vector_store/                            │   │
│  │                    pg_vector_store.py                            │   │
│  │              (PostgreSQL + pgvector embeddings)                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Design Strengths

1. **Clean Separation**: `interfaces/` defines contracts, `providers/` implements them - easy to add new LLM providers

2. **Testable**: Each layer can be unit tested independently with mock providers

3. **Configuration-Driven**: `setting.py` centralizes all config, `models.yaml` controls UI without code changes

4. **Observable**: `observability/` provides query logging and token tracking for debugging and cost management

5. **Modular Content Generation**: `studio/generators/` pattern allows adding new content types (presentations, summaries) easily
