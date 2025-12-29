# DBNotebook Technical Architecture

## Overview

DBNotebook is a multimodal RAG (Retrieval-Augmented Generation) system designed for Sales Enablement with a NotebookLM-style document organization. It provides intelligent document retrieval, persistent conversations, and multi-provider LLM support.

**Key Capabilities:**
- **Smart Q&A**: Ask questions about your documents and get accurate, context-aware answers with source citations
- **Multiple AI Models**: Choose between local AI (privacy-first, no data leaves your network) or cloud providers (OpenAI, Anthropic, Google) based on your needs
- **Web Research**: Search the web and import relevant articles directly into your notebooks
- **Image Analysis**: Upload images, screenshots, or diagrams and the AI extracts and understands the content
- **Content Studio**: Automatically generate infographics and mind maps from your documents for presentations
- **Persistent History**: Conversations are saved per notebook, so you can pick up where you left off
- **RAPTOR Hierarchical Retrieval**: Advanced tree-based retrieval for better summary and detail queries
- **Hybrid BM25 + Vector Search**: Combines keyword matching with semantic similarity for structured content

**Deployment**: Single Docker command to deploy - runs entirely on your infrastructure with no external dependencies required.

---

## System Architecture

```
                               ┌─────────────────────────────────────────────────────────────┐
                               │                      DBNOTEBOOK SYSTEM                       │
                               └─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              PRESENTATION LAYER                                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                  │
│    ┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐                            │
│    │   React Frontend    │      │   Flask REST API    │      │  Streaming SSE      │                            │
│    │  (Vite + Tailwind)  │ ───▶ │   (7860 port)       │ ───▶ │  (Chat Responses)   │                            │
│    └─────────────────────┘      └─────────────────────┘      └─────────────────────┘                            │
│                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              ORCHESTRATION LAYER                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐          │
│    │                              LocalRAGPipeline (pipeline.py)                                      │          │
│    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │          │
│    │  │ NotebookManager │  │ConversationStore│  │ VectorStore     │  │  ChatEngine     │            │          │
│    │  │ (context mgmt)  │  │ (history)       │  │ (pgvector)      │  │ (LlamaIndex)    │            │          │
│    │  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘            │          │
│    └─────────────────────────────────────────────────────────────────────────────────────────────────┘          │
│                                                                                                                  │
│    ┌──────────────────────────────┐    ┌──────────────────────────────┐                                         │
│    │   TransformationWorker       │    │       RAPTORWorker           │                                         │
│    │   (AI transformations)       │    │   (hierarchical trees)       │                                         │
│    └──────────────────────────────┘    └──────────────────────────────┘                                         │
│                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                 CORE LAYER                                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                  │
│    ┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐                           │
│    │           INGESTION                  │    │            RETRIEVAL                │                           │
│    │  ┌─────────────────────────────────┐ │    │  ┌─────────────────────────────────┐│                           │
│    │  │ LocalDataIngestion              │ │    │  │ LocalRetriever                  ││                           │
│    │  │ • PDF, DOCX, PPTX, TXT, EPUB   │ │    │  │ • RouterRetriever               ││                           │
│    │  │ • Image (via Vision)           │ │    │  │ • QueryFusionRetriever          ││                           │
│    │  │ • SentenceSplitter chunking    │ │    │  │ • TwoStageRetriever             ││                           │
│    │  │ • Contextual enrichment        │ │    │  │ • RAPTORRetriever               ││                           │
│    │  └─────────────────────────────────┘ │    │  └─────────────────────────────────┘│                           │
│    │  ┌─────────────────────────────────┐ │    │  ┌─────────────────────────────────┐│                           │
│    │  │ WebContentIngestion             │ │    │  │ Hybrid BM25 + Vector            ││                           │
│    │  │ • Firecrawl search             │ │    │  │ • BM25 keyword matching (50%)   ││                           │
│    │  │ • Jina Reader scraping         │ │    │  │ • Vector semantic (50%)         ││                           │
│    │  └─────────────────────────────────┘ │    │  │ • Query expansion (3 queries)   ││                           │
│    └─────────────────────────────────────┘    │  └─────────────────────────────────┘│                           │
│                                                │  ┌─────────────────────────────────┐│                           │
│                                                │  │ Reranking                       ││                           │
│                                                │  │ • mxbai-rerank-large-v1        ││                           │
│                                                │  └─────────────────────────────────┘│                           │
│                                                └─────────────────────────────────────┘                           │
│                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              PROVIDER LAYER                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                  │
│    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐       │
│    │    LLM Providers     │  │ Embedding Providers  │  │   Vision Providers   │  │   Image Providers    │       │
│    │  ┌────────────────┐  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │       │
│    │  │ Ollama         │  │  │  │ HuggingFace    │  │  │  │ Gemini Vision  │  │  │  │ Gemini/Imagen  │  │       │
│    │  │ OpenAI         │  │  │  │ OpenAI         │  │  │  │ OpenAI GPT-4V  │  │  │  │                │  │       │
│    │  │ Anthropic      │  │  │  └────────────────┘  │  │  └────────────────┘  │  │  └────────────────┘  │       │
│    │  │ Gemini         │  │  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘       │
│    │  └────────────────┘  │                                                                                      │
│    └──────────────────────┘                                                                                      │
│                                                                                                                  │
│    ┌──────────────────────┐  ┌──────────────────────┐                                                           │
│    │   Web Providers      │  │ Retrieval Strategies │                                                           │
│    │  ┌────────────────┐  │  │  ┌────────────────┐  │                                                           │
│    │  │ Firecrawl      │  │  │  │ Hybrid         │  │                                                           │
│    │  │ Jina Reader    │  │  │  │ Semantic       │  │                                                           │
│    │  └────────────────┘  │  │  │ Keyword        │  │                                                           │
│    └──────────────────────┘  │  └────────────────┘  │                                                           │
│                              └──────────────────────┘                                                           │
│                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              STORAGE LAYER                                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐          │
│    │                             PostgreSQL 16 + pgvector                                             │          │
│    │                                                                                                  │          │
│    │    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │          │
│    │    │     users       │  │   notebooks     │  │notebook_sources │  │  conversations  │          │          │
│    │    │   (accounts)    │  │  (collections)  │  │   (documents)   │  │   (history)     │          │          │
│    │    └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘          │          │
│    │                                                                                                  │          │
│    │    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                               │          │
│    │    │  query_logs     │  │data_embeddings  │  │generated_content│                               │          │
│    │    │ (observability) │  │   (pgvector)    │  │  (studio)       │                               │          │
│    │    └─────────────────┘  └─────────────────┘  └─────────────────┘                               │          │
│    │                                                                                                  │          │
│    └─────────────────────────────────────────────────────────────────────────────────────────────────┘          │
│                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Stack

- **Backend**: Python/Flask with LlamaIndex orchestration
- **Frontend**: React 19 + Vite + Tailwind CSS
- **Database**: PostgreSQL 16 + pgvector extension
- **Containerization**: Docker Compose (multi-container)

---

## 1. Core Pipeline (`pipeline.py`)

The `LocalRAGPipeline` is the central orchestrator that manages:

| Component | Purpose |
|-----------|---------|
| `NotebookManager` | CRUD operations for notebooks (document collections) |
| `ConversationStore` | Persistent conversation history per notebook |
| `PGVectorStore` | Vector embeddings storage with pgvector |
| `LocalChatEngine` | LlamaIndex chat engine factory |
| `LocalDataIngestion` | Document processing and chunking |
| `TransformationWorker` | Background AI transformations (summaries, insights) |
| `RAPTORWorker` | Background hierarchical tree building |

**Initialization Flow:**
```python
LocalRAGPipeline(host, database_url)
    ├── DatabaseManager.init_db()
    ├── NotebookManager(db_manager)
    ├── ConversationStore(db_manager)
    ├── PGVectorStore(host, setting)
    ├── LocalChatEngine(setting, host)
    ├── LocalDataIngestion(setting, vector_store)
    ├── TransformationWorker.start()
    └── RAPTORWorker.start()
```

---

## 2. Plugin Architecture (`core/registry.py`)

The `PluginRegistry` provides swappable components:

```
PluginRegistry
├── LLM Providers       (ollama, openai, anthropic, gemini)
├── Embedding Providers (huggingface, openai)
├── Retrieval Strategies (hybrid, semantic, keyword)
├── Image Providers     (gemini/imagen)
├── Vision Providers    (gemini, openai)
├── Web Search          (firecrawl)
└── Web Scraper         (jina)
```

**Configuration via Environment:**
```bash
LLM_PROVIDER=ollama           # or openai, anthropic, gemini
EMBEDDING_PROVIDER=huggingface
RETRIEVAL_STRATEGY=hybrid     # or semantic, keyword
VISION_PROVIDER=gemini        # or openai
```

---

## 3. Storage Architecture

### 3.1 PostgreSQL + pgvector

**Why PostgreSQL over ChromaDB:**
- O(log n) metadata filtering via SQL indexes (vs O(n) client-side)
- Native hybrid search (BM25 + vector in single query)
- ACID transactions across metadata + vectors
- Incremental vector updates without index rebuild
- Unified backend for all data

### 3.2 Database Schema

```sql
-- Core Tables
users                    -- Multi-user accounts
notebooks               -- Document collections (NotebookLM-style)
notebook_sources        -- Files with metadata and transformation status
conversations          -- Persistent chat history per notebook
query_logs             -- Observability and cost tracking
generated_content      -- Content Studio outputs
embedding_config       -- Active embedding model tracking

-- Vector Storage (via LlamaIndex PGVectorStore)
data_embeddings        -- pgvector embeddings with JSONB metadata
```

**Key Table: `notebook_sources`**
```sql
source_id              UUID PRIMARY KEY
notebook_id            UUID FOREIGN KEY → notebooks
file_name              VARCHAR(500)
file_hash              VARCHAR(64)      -- SHA256 for duplicate detection
active                 BOOLEAN          -- Toggle for RAG inclusion

-- AI Transformations
dense_summary          TEXT             -- 300-500 word summary
key_insights           JSONB            -- ["insight1", "insight2", ...]
reflection_questions   JSONB            -- ["q1", "q2", ...]
transformation_status  VARCHAR(20)      -- pending|processing|completed|failed

-- RAPTOR Status
raptor_status          VARCHAR(20)      -- pending|building|completed|failed
raptor_built_at        TIMESTAMP
```

**Key Table: `data_embeddings`**
```sql
id                     UUID PRIMARY KEY
node_id                VARCHAR(255)
text                   TEXT             -- Original chunk text
embedding              VECTOR(768)      -- pgvector embedding (dimension configurable)
metadata_              JSONB            -- Includes:
                                        --   notebook_id, source_id
                                        --   file_name, tree_level
                                        --   has_context, context_prefix
```

---

## 4. Document Ingestion Pipeline

### 4.1 Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              DOCUMENT INGESTION PIPELINE                                  │
└──────────────────────────────────────────────────────────────────────────────────────────┘

  Document Upload                    Processing                           Storage
       │                                 │                                    │
       ▼                                 ▼                                    ▼
┌──────────────┐    ┌──────────────────────────────────────────────────────────────┐
│  File Input  │    │                    LocalDataIngestion                        │
│              │    │                                                              │
│  • PDF       │───▶│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  • DOCX      │    │  │   Reader    │──▶│  Chunking   │──▶│  Contextual     │   │
│  • PPTX      │    │  │ (format-    │   │(Sentence-   │   │  Enrichment     │   │
│  • TXT       │    │  │  specific)  │   │ Splitter)   │   │  (optional)     │   │
│  • EPUB      │    │  └─────────────┘   └─────────────┘   └─────────────────┘   │
│  • Images    │    │         │                │                   │              │
└──────────────┘    │         ▼                ▼                   ▼              │
                    │  ┌─────────────────────────────────────────────────────┐    │
                    │  │                   Embedding                          │    │
                    │  │  HuggingFace (nomic-embed-text-v1.5)                │    │
                    │  │  or OpenAI (text-embedding-3-small)                 │    │
                    │  └─────────────────────────────────────────────────────┘    │
                    └──────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                    ┌──────────────────────────────────────────────────────────────┐
                    │                    PGVectorStore                             │
                    │   • Store embeddings in data_embeddings table               │
                    │   • Metadata: notebook_id, source_id, tree_level            │
                    │   • Duplicate detection via MD5 hash                        │
                    └──────────────────────────────────────────────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
          ┌─────────────────────┐                       ┌─────────────────────┐
          │TransformationWorker │                       │    RAPTORWorker     │
          │   (Background)      │                       │    (Background)     │
          │                     │                       │                     │
          │ • Dense Summary     │                       │ • Cluster chunks    │
          │ • Key Insights      │                       │ • Generate summaries│
          │ • Reflection Q's    │                       │ • Build tree levels │
          └─────────────────────┘                       └─────────────────────┘
```

### 4.2 Chunking Configuration

```python
# Default Settings (setting.py)
chunk_size = 512        # Tokens per chunk
chunk_overlap = 32      # Overlap between chunks
embed_batch_size = 8    # Embeddings per batch
```

### 4.3 Contextual Retrieval (Optional)

When enabled (`CONTEXTUAL_RETRIEVAL_ENABLED=true`), chunks are enriched with LLM-generated context during ingestion:

```python
# Original Chunk
"Fire Chakra, Color: White, Location: Upper left..."

# Enriched Chunk (prepended context)
"This table lists chakra properties including colors and locations.
The Fire Chakra has color White and is located in the upper left chest.

Fire Chakra, Color: White, Location: Upper left..."
```

**Configuration:**
```bash
CONTEXTUAL_RETRIEVAL_ENABLED=false  # Enable for better structured content retrieval
CONTEXTUAL_BATCH_SIZE=5             # Chunks to process in parallel
CONTEXTUAL_MAX_CONCURRENCY=3        # Concurrent LLM calls
CONTEXTUAL_MAX_CHUNK_CHARS=2000     # Max chunk size for context generation
```

---

## 5. Retrieval Architecture

### 5.1 Multi-Strategy Retrieval Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               RETRIEVAL ARCHITECTURE                                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    User Query
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │     Intent Classification   │
                          │   (LLM-based detection)     │
                          │   • SUMMARY: overview       │
                          │   • DETAIL: specific facts  │
                          └─────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │   RAPTOR Retriever    │               │  Standard Retriever   │
        │   (if tree exists)    │               │  (fallback)           │
        └───────────────────────┘               └───────────────────────┘
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────────────────────────────────────────────────────┐
        │                     HYBRID RETRIEVAL                              │
        │                                                                   │
        │   ┌─────────────────────┐     ┌─────────────────────┐           │
        │   │   BM25 Retriever    │     │   Vector Retriever   │           │
        │   │  (keyword match)    │     │  (semantic search)   │           │
        │   │      50% weight     │     │      50% weight      │           │
        │   └─────────────────────┘     └─────────────────────┘           │
        │              │                          │                        │
        │              └────────────┬─────────────┘                        │
        │                           ▼                                      │
        │              ┌─────────────────────────┐                         │
        │              │   QueryFusionRetriever  │                         │
        │              │  • 3 query variations   │                         │
        │              │  • Score fusion         │                         │
        │              └─────────────────────────┘                         │
        │                           │                                      │
        └───────────────────────────┼──────────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────────┐
                          │       Reranker          │
                          │ mixedbread-ai/mxbai-    │
                          │   rerank-large-v1       │
                          │   top_k_rerank: 10      │
                          └─────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────────┐
                          │    Top-K Results        │
                          │   (sent to LLM)         │
                          └─────────────────────────┘
```

### 5.2 RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval

RAPTOR builds hierarchical summary trees for better retrieval of both high-level concepts and specific details.

**Reference**: https://arxiv.org/abs/2401.18059

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RAPTOR TREE STRUCTURE                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                         Level 3: Document Summary (Root)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
              Level 2: Section Summaries            Level 2: Section Summaries
                    │                                       │
        ┌───────────┼───────────┐               ┌───────────┼───────────┐
        ▼           ▼           ▼               ▼           ▼           ▼
     Level 1:   Level 1:   Level 1:         Level 1:   Level 1:   Level 1:
     Cluster    Cluster    Cluster          Cluster    Cluster    Cluster
     Summary    Summary    Summary          Summary    Summary    Summary
        │           │           │               │           │           │
     ┌──┴──┐     ┌──┴──┐     ┌──┴──┐        ┌──┴──┐     ┌──┴──┐     ┌──┴──┐
     ▼     ▼     ▼     ▼     ▼     ▼        ▼     ▼     ▼     ▼     ▼     ▼
   Level 0: Original Document Chunks (Leaf Nodes)


BUILD PROCESS:
1. Start with L0 chunks (original document)
2. Cluster by semantic similarity (GMM + UMAP)
3. Summarize each cluster → L1 nodes
4. Repeat until root reached

QUERY ROUTING:
• SUMMARY queries → Search L0-L3 (boost higher levels)
• DETAIL queries  → Search L0-L1 (boost L0)
```

**RAPTOR Configuration (`core/raptor/config.py`):**

```python
# Clustering
umap_n_components = 10          # UMAP dimensionality
umap_n_neighbors = 15           # Local neighborhood size
gmm_probability_threshold = 0.3 # Soft cluster membership
min_cluster_size = 3            # Minimum nodes per cluster
max_cluster_size = 10           # Maximum nodes per cluster

# Tree Building
max_tree_depth = 4              # Maximum levels (0=chunks, 1-3=summaries)
min_nodes_to_cluster = 5        # Min nodes for new level
max_concurrent_summaries = 3    # Parallel LLM calls

# Retrieval
summary_query_levels = [0, 1, 2, 3]  # Levels for summary queries
detail_query_levels = [0, 1]         # Levels for detail queries
summary_level_boost = 1.5            # Boost for higher levels
detail_level_boost = 1.3             # Boost for L0 chunks

# Hybrid Retrieval (BM25 + Vector fusion)
use_hybrid_retrieval = True
bm25_weight = 0.5                    # BM25 keyword weight
vector_weight = 0.5                  # Vector semantic weight
num_query_variations = 3             # Query expansion
```

### 5.3 Hybrid BM25 + Vector Retrieval

The hybrid approach combines keyword matching (BM25) with semantic similarity (vector) for optimal retrieval of both structured content (tables, lists) and narrative text.

```python
# How Hybrid Retrieval Works
QueryFusionRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    retriever_weights=[0.5, 0.5],    # Equal weighting
    similarity_top_k=20,              # Initial retrieval
    num_queries=3,                    # Query variations for expansion
    mode="dist_based_score"           # Score fusion method
)
```

**Why Hybrid is Better for Structured Content:**

| Content Type | BM25 Score | Vector Score | Result |
|-------------|------------|--------------|--------|
| "Fourth Chakra, Color: Black" | HIGH (exact match) | Medium | Retrieved |
| "The chakra system represents..." | Low | HIGH (semantic) | Retrieved |
| "Fire element is associated with..." | Medium | HIGH | Retrieved |

**Key Improvement**: Pure vector search often fails for structured content (tables, lists) because embeddings are optimized for prose. BM25 provides exact keyword matching that catches structured data.

### 5.4 Retrieval Strategy Selection

```python
# Adaptive Retrieval (LocalRetriever)
if node_count <= 6:
    # Small datasets: Pure vector similarity
    VectorIndexRetriever

elif node_count > 6:
    # Large datasets: Router selects strategy
    RouterRetriever
    ├── QueryFusionRetriever  # For ambiguous queries
    │   └── Generates 5 query variations
    │   └── Fuses BM25 + Vector results
    │
    └── TwoStageRetriever     # For clear queries
        └── Stage 1: BM25 + Vector retrieval
        └── Stage 2: Cross-encoder reranking
```

---

## 6. AI Transformations

### 6.1 TransformationWorker

Background worker that generates AI-powered document transformations:

```python
# Transformation Types
TransformationJob
├── dense_summary          # 300-500 word comprehensive summary
├── key_insights           # 5-10 actionable takeaways (JSON array)
└── reflection_questions   # 5-7 thought-provoking questions (JSON array)
```

**Status Tracking:**
```
pending → processing → completed
                   └→ failed (with error message)
```

### 6.2 RAPTORWorker

Background worker that builds hierarchical trees:

```python
RAPTORJob
├── source_id      # Document to process
├── notebook_id    # Parent notebook
└── priority       # Job priority (higher = sooner)

# Status: pending → building → completed/failed
```

---

## 7. Chat Engine Architecture

### 7.1 Engine Types

```python
LocalChatEngine.set_engine(llm, nodes, ...)
    │
    ├── SimpleChatEngine           # No documents (general chat)
    │   └── memory: ChatMemoryBuffer
    │
    └── CondensePlusContextChatEngine  # RAG with retrieval
        ├── retriever: RAPTORRetriever or StandardRetriever
        ├── memory: ChatMemoryBuffer
        └── condense_prompt: CustomerContextCondensePrompt
```

### 7.2 Memory Management

```python
# Token Allocation
CHAT_TOKEN_LIMIT = 32000  # Total memory budget

# Memory Distribution
├── System Prompt:     ~500 tokens
├── Context Prompt:   ~1000 tokens
├── Chat History:     ~15000 tokens (50% reserve)
└── Response Budget:  ~15500 tokens
```

### 7.3 Two-Stage Document Routing

```
Query → DocumentRoutingService
            │
            ▼
    ┌───────────────────────┐
    │  Stage 1: Analyze     │
    │  Query vs. Summaries  │
    │  (fast, cheap LLM)    │
    └───────────────────────┘
            │
            ▼
    ┌───────────────────────┐
    │  Routing Decision:    │
    │  • all_documents      │
    │  • deep_dive          │
    │  • skip_retrieval     │
    │  • specific_documents │
    └───────────────────────┘
            │
            ▼
    ┌───────────────────────┐
    │  Stage 2: Execute     │
    │  Appropriate Strategy │
    └───────────────────────┘
```

---

## 8. Web Content Integration

### 8.1 Search → Scrape → Embed Pipeline

```
User Search Query
        │
        ▼
┌───────────────────┐
│ FirecrawlProvider │
│  (Web Search)     │
│  Returns: URLs    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ User Selection    │
│ (Preview URLs)    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ JinaReaderProvider│
│  (Content Scrape) │
│  Returns: Markdown│
└───────────────────┘
        │
        ▼
┌───────────────────┐
│LocalDataIngestion │
│  (Chunk + Embed)  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   PGVectorStore   │
└───────────────────┘
```

### 8.2 API Endpoints

```
POST /api/web/search           # Search for URLs
POST /api/web/scrape-preview   # Preview content
POST /api/notebooks/{id}/web-sources  # Add to notebook
```

---

## 9. Vision Processing

### 9.1 Image Understanding Flow

```
Image Upload
      │
      ▼
┌─────────────────────┐
│   VisionManager     │
│   ┌───────────────┐ │
│   │GeminiVision   │ │
│   │ or            │ │
│   │OpenAIVision   │ │
│   └───────────────┘ │
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│ Text Extraction +   │
│ Visual Analysis     │
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│ Chunk + Embed       │
│ (like documents)    │
└─────────────────────┘
```

**Configuration:**
```bash
VISION_PROVIDER=gemini           # or openai
GEMINI_VISION_MODEL=gemini-2.0-flash-exp
OPENAI_VISION_MODEL=gpt-4o
USE_VISION_FOR_IMAGES=true       # Enable vision processing
```

---

## 10. Content Studio

### 10.1 Generator Architecture

```python
StudioManager
├── InfographicGenerator
│   └── Gemini/Imagen API → PNG/JPEG
├── MindMapGenerator
│   └── Gemini/Imagen API → PNG/JPEG
└── (Extensible for more generators)

# Storage
generated_content table
├── content_id
├── content_type      # 'infographic', 'mindmap'
├── file_path         # outputs/studio/xxx.png
├── thumbnail_path    # Cached preview
└── content_metadata  # Generation params
```

### 10.2 API Endpoints

```
GET  /api/studio/gallery              # List generated content
POST /api/studio/generate             # Create new content
GET  /api/studio/content/{id}         # Get content details
GET  /api/studio/content/{id}/file    # Serve file
GET  /api/studio/generators           # List available generators
```

---

## 11. REST API Reference

### 11.1 Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message, get response with sources |
| POST | `/api/chat/stream` | Streaming SSE response |
| POST | `/api/multi-notebook/query` | Query across multiple notebooks |

### 11.2 Notebook Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notebooks` | List all notebooks |
| POST | `/api/notebooks` | Create notebook |
| GET | `/api/notebooks/{id}` | Get notebook details |
| DELETE | `/api/notebooks/{id}` | Delete notebook |
| POST | `/api/notebooks/{id}/sources` | Upload document |

### 11.3 Document Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sources/{id}` | Get source details |
| DELETE | `/api/sources/{id}` | Delete source |
| PATCH | `/api/sources/{id}/toggle` | Toggle active state |
| GET | `/api/sources/{id}/transformations` | Get AI transformations |

### 11.4 Special Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vision/providers` | List vision providers |
| POST | `/api/vision/analyze` | Analyze image |
| GET | `/api/transformations/{id}/status` | Transformation status |
| POST | `/api/transformations/{id}/retry` | Retry failed transformation |

---

## 12. Configuration Reference

### 12.1 Environment Variables

```bash
# ============================================
# Core Providers
# ============================================
LLM_PROVIDER=ollama                    # ollama|openai|anthropic|gemini
LLM_MODEL=llama3.1:latest
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
RETRIEVAL_STRATEGY=hybrid              # hybrid|semantic|keyword

# ============================================
# Database
# ============================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=dbnotebook_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root

# ============================================
# Context & Memory
# ============================================
CONTEXT_WINDOW=128000                  # LLM context window
CHAT_TOKEN_LIMIT=32000                 # Chat memory budget

# ============================================
# Advanced Retrieval Configuration
# ============================================
# Contextual Retrieval (Anthropic approach)
CONTEXTUAL_RETRIEVAL_ENABLED=false     # Chunk enrichment during ingestion
CONTEXTUAL_BATCH_SIZE=5
CONTEXTUAL_MAX_CONCURRENCY=3
CONTEXTUAL_MAX_CHUNK_CHARS=2000

# Hybrid Retrieval (BM25 + Vector)
# Configured in core/raptor/config.py:
# bm25_weight=0.5, vector_weight=0.5, num_query_variations=3

# ============================================
# API Keys (as needed)
# ============================================
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
FIRECRAWL_API_KEY=...
JINA_API_KEY=...

# ============================================
# Vision Configuration
# ============================================
VISION_PROVIDER=gemini
GEMINI_VISION_MODEL=gemini-2.0-flash-exp
OPENAI_VISION_MODEL=gpt-4o
USE_VISION_FOR_IMAGES=true

# ============================================
# Image Generation
# ============================================
IMAGE_GENERATION_PROVIDER=gemini
GEMINI_IMAGE_MODEL=imagen-4.0-generate-001
```

### 12.2 Default Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `chunk_size` | 512 | Tokens per chunk |
| `chunk_overlap` | 32 | Overlap between chunks |
| `similarity_top_k` | 20 | Initial retrieval count |
| `top_k_rerank` | 10 | Final results after reranking |
| `bm25_weight` | 0.5 | BM25 keyword matching weight |
| `vector_weight` | 0.5 | Vector semantic weight |
| `num_query_variations` | 3 | Query expansion count |

---

## 13. Docker Architecture

```yaml
services:
  dbnotebook:
    build: .
    ports: ["7860:7860"]
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      - OLLAMA_HOST=host.docker.internal
      - DATABASE_URL=postgresql://...

  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5433:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
```

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

**Startup Flow:**
```
1. PostgreSQL container starts
2. Health check passes (pgvector extension ready)
3. DBNotebook container starts
4. Alembic migrations run
5. Flask app initializes
6. Background workers start (Transformation, RAPTOR)
7. Ready for requests on :7860
```

---

## 14. Code Organization

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
│   │   ├── studio.py        # Content Studio endpoints
│   │   ├── vision.py        # Image analysis endpoints
│   │   ├── transformations.py  # AI transformation endpoints
│   │   ├── agents.py        # Agent endpoints
│   │   ├── multi_notebook.py   # Cross-notebook query
│   │   └── web_content.py   # Web search/scraping endpoints
│   └── schemas/             # Pydantic request/response models
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
    │   ├── routing.py       # RoutingStrategy ABC
    │   ├── services.py      # Service ABCs
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
    ├── raptor/              # RAPTOR Tree Building
    │   ├── config.py        # RAPTOR configuration
    │   ├── clustering.py    # GMM + UMAP clustering
    │   ├── summarizer.py    # Cluster summarization
    │   ├── tree_builder.py  # Tree construction
    │   ├── retriever.py     # RAPTOR-aware retrieval
    │   └── worker.py        # Background tree building
    │
    ├── transformations/     # AI Transformations
    │   ├── context_service.py    # Contextual Retrieval enrichment
    │   ├── transformation_service.py  # Document transformations
    │   ├── prompts.py       # Transformation prompts
    │   └── worker.py        # Background worker
    │
    ├── services/            # Business Logic Services
    │   ├── chat_service.py
    │   ├── document_service.py
    │   ├── document_routing_service.py
    │   ├── multi_notebook_service.py
    │   └── ...
    │
    ├── engine/
    │   ├── engine.py        # LocalChatEngine - LlamaIndex chat engine factory
    │   └── retriever.py     # LocalRetriever - adaptive retrieval
    │
    ├── vector_store/
    │   ├── base.py          # IVectorStore interface
    │   └── pg_vector_store.py # PostgreSQL + pgvector implementation
    │
    ├── ingestion/
    │   ├── ingestion.py     # LocalDataIngestion - document processing
    │   ├── web_ingestion.py # WebContentIngestion - URL import
    │   └── synopsis_manager.py # Document summary generation
    │
    ├── db/
    │   ├── db.py            # DatabaseManager - SQLAlchemy session management
    │   └── models.py        # ORM models
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
    │       ├── infographic.py
    │       └── mindmap.py
    │
    ├── vision/
    │   └── vision_manager.py # Multi-provider vision orchestration
    │
    ├── agents/              # AI Agents
    │   ├── base.py
    │   ├── query_analyzer.py
    │   └── document_analyzer.py
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

---

## 15. Architecture Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Plugin Registry** | `core/registry.py` | Runtime provider discovery, zero-code swapping |
| **Strategy Pattern** | `core/strategies/` | Interchangeable retrieval algorithms |
| **Abstract Factory** | `core/interfaces/` | Consistent contracts across providers |
| **Dependency Injection** | `pipeline.py` | Components receive dependencies at init |
| **Repository Pattern** | `core/db/`, `notebook_manager.py` | Data access abstraction |
| **Facade Pattern** | `pipeline.py` | Unified API over complex subsystems |
| **Background Workers** | `TransformationWorker`, `RAPTORWorker` | Async processing |

---

## 16. Key Design Decisions

1. **pgvector over ChromaDB**: Enables metadata filtering at query time without loading all vectors into memory - critical for multi-notebook isolation

2. **Hybrid BM25 + Vector**: Combines lexical and semantic search to handle both structured content (tables, lists) and narrative text effectively

3. **RAPTOR Hierarchical Trees**: Enables better retrieval for both summary queries (high-level) and detail queries (specific facts)

4. **Reranker Stage**: Uses `mxbai-rerank-large-v1` to refine retrieval results - improves precision on top-k without increasing embedding costs

5. **Lazy Engine Initialization**: Chat engines created on-demand per notebook, preserving conversation context while managing memory

6. **Environment-Driven Configuration**: Provider selection via env vars (`LLM_PROVIDER`, `VISION_PROVIDER`) - no code deployment for model changes

7. **Background Workers**: Heavy processing (transformations, RAPTOR trees) runs asynchronously to keep UI responsive

8. **Query Expansion**: Generates 3 query variations to improve recall for ambiguous queries

---

## 17. Extending the System

### 17.1 Adding a New LLM Provider

```python
# 1. Create provider class in core/providers/
class MyProvider(LLMProvider):
    def get_llm(self, **kwargs) -> LLM:
        return MyLLM(...)

    def validate(self) -> bool:
        return self._api_key is not None

# 2. Register in core/plugins.py
PluginRegistry.register_llm_provider("my_provider", MyProvider)

# 3. Configure via environment
LLM_PROVIDER=my_provider
```

### 17.2 Adding a New Generator

```python
# 1. Create generator class in core/studio/generators/
class MyGenerator(ContentGenerator):
    def generate(self, prompt, context) -> GenerationResult:
        ...

# 2. Register in studio/__init__.py
GENERATORS = {
    "my_type": MyGenerator,
    ...
}
```

### 17.3 Adding a New Retrieval Strategy

```python
# 1. Create strategy in core/strategies/
class MyStrategy(RetrievalStrategy):
    def create_retriever(self, nodes, **kwargs):
        ...

# 2. Register in core/plugins.py
PluginRegistry.register_strategy("my_strategy", MyStrategy)

# 3. Configure via environment
RETRIEVAL_STRATEGY=my_strategy
```

---

*Document Version: 2.0*
*Last Updated: December 2024*
