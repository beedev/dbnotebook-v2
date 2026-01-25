# DBNotebook Query & Chat Flows - Detailed Architecture

This document provides comprehensive step-by-step diagrams for the three main query flows in DBNotebook:

1. **API Query** (`/api/query`) - Programmatic RAG access
2. **RAG Chat** (`/api/chat`) - Interactive document chat with intelligent routing
3. **SQL Chat** (`/api/sql-chat/query`) - Natural language to SQL

---

## Table of Contents

- [1. API Query Flow](#1-api-query-flow)
- [2. RAG Chat Flow](#2-rag-chat-flow)
- [3. SQL Chat Flow](#3-sql-chat-flow)
- [4. Comparative Summary](#4-comparative-summary)
- [5. Key Components](#5-key-components)

---

## 1. API Query Flow

**Endpoint:** `POST /api/query`
**Purpose:** Programmatic RAG access for scripts, automation, and API integrations
**Source:** `dbnotebook/api/routes/query.py`

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           API QUERY FLOW (Programmatic RAG)                              │
│                              POST /api/query                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌───────────────────────────────────────────────────────────────────┐
│   Client     │      │                        Flask Backend                               │
│  (Script/    │      │                                                                   │
│   Automation)│      │  ┌─────────────────────────────────────────────────────────────┐ │
└──────┬───────┘      │  │                  require_api_key Decorator                   │ │
       │              │  │  1. Check X-API-Key header                                   │ │
       │ POST         │  │  2. Validate against users.api_key (DB) or API_KEY (env)    │ │
       │ /api/query   │  │  3. Store user_id in request context                        │ │
       ▼              │  └─────────────────────────┬───────────────────────────────────┘ │
┌──────────────┐      │                            │                                      │
│  Request     │──────┼────────────────────────────▼                                      │
│  {           │      │  ┌─────────────────────────────────────────────────────────────┐ │
│   notebook_id│      │  │              STEP 1: Notebook Validation                    │ │
│   query      │      │  │  • notebook_manager.get_notebook(notebook_id)              │ │
│   session_id?│      │  │  • RBAC check: check_notebook_access(user, AccessLevel)    │ │
│   model?     │      │  │  • ~4ms                                                     │ │
│   top_k?     │      │  └─────────────────────────┬───────────────────────────────────┘ │
│   skip_raptor│      │                            │                                      │
│  }           │      │                            ▼                                      │
└──────────────┘      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 1.5: Load Conversation History            │ │
                      │  │  • If session_id provided:                                  │ │
                      │  │    - Load from _query_sessions (in-memory, ephemeral)       │ │
                      │  │    - Get last N message pairs (max_history * 2)             │ │
                      │  │  • Isolated from RAG Chat DB history                        │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 2: Node Cache Lookup                      │ │
                      │  │  • pipeline._get_cached_nodes(notebook_id)                  │ │
                      │  │  • Thread-safe with RLock                                   │ │
                      │  │  • 5-minute TTL cache                                       │ │
                      │  │  • ~0-50ms (cache hit) / ~300ms (cache miss)                │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 3: Create Hybrid Retriever                │ │
                      │  │  • LocalRetriever.get_retrievers()                          │ │
                      │  │  • If ≤6 nodes: VectorIndexRetriever (pure semantic)        │ │
                      │  │  • If >6 nodes: RouterRetriever selecting:                  │ │
                      │  │    - QueryFusionRetriever (ambiguous queries)               │ │
                      │  │    - TwoStageRetriever (clear queries)                      │ │
                      │  │  • ~0-50ms                                                  │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 4: Chunk Retrieval                        │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │                 Hybrid Retrieval                     │   │ │
                      │  │  │  ┌────────────┐   ┌────────────┐   ┌────────────┐  │   │ │
                      │  │  │  │   BM25     │ + │  Vector    │ → │  Reranker  │  │   │ │
                      │  │  │  │ (Keyword)  │   │ (Semantic) │   │ (mxbai)    │  │   │ │
                      │  │  │  └────────────┘   └────────────┘   └────────────┘  │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  • QueryBundle(query_str=query)                            │ │
                      │  │  • retriever.retrieve(query_bundle)                        │ │
                      │  │  • Returns top_k nodes with scores                         │ │
                      │  │  • ~200-500ms                                              │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 5: Format Sources                         │ │
                      │  │  • Extract top max_sources (default 6)                      │ │
                      │  │  • Include: filename, snippet (200 chars), score            │ │
                      │  │  • ~0ms                                                     │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 6: RAPTOR Summaries (Optional)            │ │
                      │  │  • If skip_raptor=false (default: true)                     │ │
                      │  │  • Get query embedding                                      │ │
                      │  │  • vector_store.get_top_raptor_summaries()                  │ │
                      │  │  • Filter by relevance threshold (≥0.3)                     │ │
                      │  │  • Max 5 summaries from tree_level ≥1                       │ │
                      │  │  • ~100-200ms (when enabled)                                │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 7: Build Hierarchical Context             │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  ## HIGH-LEVEL CONTEXT (RAPTOR summaries)           │   │ │
                      │  │  │  [Summary 1] [Summary 2] [Summary 3]                 │   │ │
                      │  │  ├─────────────────────────────────────────────────────┤   │ │
                      │  │  │  ## DETAILED EVIDENCE (Retrieved chunks)            │   │ │
                      │  │  │  [Source: doc1.pdf] chunk text...                   │   │ │
                      │  │  │  [Source: doc2.pdf] chunk text...                   │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  • ~0ms                                                    │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 8: LLM Completion                         │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  Prompt Construction:                                │   │ │
                      │  │  │  ┌─────────────────────────────────────────────┐    │   │ │
                      │  │  │  │ System Prompt (RAG-optimized)               │    │   │ │
                      │  │  │  ├─────────────────────────────────────────────┤    │   │ │
                      │  │  │  │ Context (RAPTOR + Chunks)                   │    │   │ │
                      │  │  │  ├─────────────────────────────────────────────┤    │   │ │
                      │  │  │  │ Conversation History (if session_id)        │    │   │ │
                      │  │  │  ├─────────────────────────────────────────────┤    │   │ │
                      │  │  │  │ User Question                               │    │   │ │
                      │  │  │  └─────────────────────────────────────────────┘    │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  • llm.complete(prompt)                                    │ │
                      │  │  • Uses Settings.llm or model override                     │ │
                      │  │  • ~2,000-15,000ms (depends on provider)                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              STEP 9: Save Conversation (Optional)           │ │
                      │  │  • If session_id provided:                                  │ │
                      │  │    - Append {role: "user", content: query}                  │ │
                      │  │    - Append {role: "assistant", content: response}          │ │
                      │  │  • Stored in _query_sessions (in-memory, ephemeral)         │ │
                      │  │  • NOT persisted to database (isolated from RAG Chat)       │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              RESPONSE                                       │ │
                      │  │  {                                                          │ │
                      │  │    "success": true,                                         │ │
                      │  │    "response": "LLM response text...",                      │ │
                      │  │    "session_id": "uuid" (only if memory enabled),           │ │
                      │  │    "sources": [{filename, snippet, score}, ...],            │ │
                      │  │    "metadata": {                                            │ │
                      │  │      "execution_time_ms": 5234,                             │ │
                      │  │      "model": "gpt-4.1-mini",                               │ │
                      │  │      "retrieval_strategy": "queryfusion",                   │ │
                      │  │      "node_count": 45,                                      │ │
                      │  │      "raptor_summaries_used": 2,                            │ │
                      │  │      "timings": {...per-stage breakdown...}                 │ │
                      │  │    }                                                        │ │
                      │  │  }                                                          │ │
                      │  └─────────────────────────────────────────────────────────────┘ │
                      └───────────────────────────────────────────────────────────────────┘
```

### API Query Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `notebook_id` | UUID | Yes | - | Target notebook for retrieval |
| `query` | string | Yes | - | Natural language query |
| `session_id` | UUID | No | - | Client-generated UUID for conversation memory |
| `model` | string | No | Pipeline default | LLM model override |
| `max_sources` | int | No | 6 | Maximum sources to return (max 20) |
| `max_history` | int | No | 5 | Max conversation history pairs (max 20) |
| `skip_raptor` | bool | No | true | Skip RAPTOR hierarchical summaries |
| `reranker_enabled` | bool | No | global | Enable/disable reranking |
| `top_k` | int | No | 6 | Retrieval top-k override |

### Timing Breakdown (Typical)

| Stage | Duration | Notes |
|-------|----------|-------|
| 1. Notebook Lookup | ~4ms | RBAC validation |
| 2. Node Cache | 0-300ms | 5-min TTL cache |
| 3. Create Retriever | 0-50ms | Cached per notebook |
| 4. Chunk Retrieval | 200-500ms | Hybrid BM25+Vector+Rerank |
| 5. Format Sources | ~0ms | String formatting |
| 6. RAPTOR (optional) | 100-200ms | Only if skip_raptor=false |
| 7. Context Building | ~0ms | String concatenation |
| 8. LLM Completion | 2,000-15,000ms | **Bottleneck** (~95% of time) |
| 9. Save History | ~0ms | In-memory operation |
| **Total** | **3,000-15,000ms** | Varies by LLM provider |

---

## 2. RAG Chat Flow

**Endpoint:** `POST /api/chat`
**Purpose:** Interactive document chat with two-stage intelligent routing
**Source:** `dbnotebook/api/routes/chat.py`

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           RAG CHAT FLOW (Two-Stage Intelligent Routing)                  │
│                              POST /api/chat                                              │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌───────────────────────────────────────────────────────────────────┐
│   React      │      │                        Flask Backend                               │
│   Frontend   │      │                                                                   │
└──────┬───────┘      │                                                                   │
       │              │                                                                   │
       │ POST         │  ┌─────────────────────────────────────────────────────────────┐ │
       │ /api/chat    │  │              REQUEST VALIDATION                              │ │
       ▼              │  │  • Parse: message, notebook_ids, mode, fast_mode, model      │ │
┌──────────────┐      │  │  • fast_mode → Skip to Fast Path (4-8x faster)               │ │
│  Request     │──────┼──┤                                                              │ │
│  {           │      │  └─────────────────────────┬───────────────────────────────────┘ │
│   message    │      │                            │                                      │
│   notebook_id│      │            ┌───────────────┴───────────────┐                     │
│   mode       │      │            │                               │                     │
│   fast_mode  │      │            ▼                               ▼                     │
│   model?     │      │  ┌─────────────────────┐     ┌─────────────────────────────────┐ │
│  }           │      │  │    FAST MODE PATH   │     │    STANDARD TWO-STAGE PATH      │ │
└──────────────┘      │  │  (fast_mode=true)   │     │    (fast_mode=false)            │ │
                      │  │                     │     │                                  │ │
                      │  │  Uses:              │     │                                  │ │
                      │  │  stateless_query()  │     │                                  │ │
                      │  │  or                 │     │                                  │ │
                      │  │  stateless_query_   │     │                                  │ │
                      │  │  streaming()        │     │                                  │ │
                      │  │                     │     │                                  │ │
                      │  │  • No routing       │     │                                  │ │
                      │  │  • Direct retrieval │     │                                  │ │
                      │  │  • 4-8x faster      │     │                                  │ │
                      │  └──────────┬──────────┘     │                                  │ │
                      │             │                │                                  │ │
                      │             │                ▼                                  │ │
                      │             │   ┌───────────────────────────────────────────┐  │ │
                      │             │   │  STAGE 1: DOCUMENT ROUTING ANALYSIS       │  │ │
                      │             │   │  (DocumentRoutingService)                 │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  1. Get document summaries from notebook  │  │ │
                      │             │   │  2. LLM analyzes query vs summaries       │  │ │
                      │             │   │  3. Determines routing strategy:          │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  ┌─────────────────────────────────────┐ │  │ │
                      │             │   │  │ DIRECT_SYNTHESIS                    │ │  │ │
                      │             │   │  │ Answer from summaries only          │ │  │ │
                      │             │   │  │ → Return immediately (no retrieval) │ │  │ │
                      │             │   │  ├─────────────────────────────────────┤ │  │ │
                      │             │   │  │ DEEP_DIVE                           │ │  │ │
                      │             │   │  │ Deep analysis of specific documents │ │  │ │
                      │             │   │  │ → Filter to selected docs only      │ │  │ │
                      │             │   │  ├─────────────────────────────────────┤ │  │ │
                      │             │   │  │ MULTI_DOC_ANALYSIS                  │ │  │ │
                      │             │   │  │ Cross-document comparison           │ │  │ │
                      │             │   │  │ → Use all selected documents        │ │  │ │
                      │             │   │  └─────────────────────────────────────┘ │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  ~1000-3000ms                             │  │ │
                      │             │   └───────────────────────────────────────────┘  │ │
                      │             │                      │                            │ │
                      │             │                      ▼                            │ │
                      │             │   ┌───────────────────────────────────────────┐  │ │
                      │             │   │  STAGE 2: FOCUSED RETRIEVAL               │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  Step 2a: Configure Engine                │  │ │
                      │             │   │  • set_engine(offering_filter=notebooks)  │  │ │
                      │             │   │  • Force reset for fresh context          │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  Step 2b: Get Cached Nodes                │  │ │
                      │             │   │  • _get_cached_nodes() for each notebook  │  │ │
                      │             │   │  • Filter by selected_document_ids        │  │ │
                      │             │   │    (from routing)                         │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  Step 2c: Create Retriever                │  │ │
                      │             │   │  • Same hybrid retriever as API Query     │  │ │
                      │             │   │  • BM25 + Vector + Reranker               │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  Step 2d: Retrieve Chunks                 │  │ │
                      │             │   │  • QueryBundle(message)                   │  │ │
                      │             │   │  • Top 6 sources with scores              │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  ~200-500ms                               │  │ │
                      │             │   └───────────────────────────────────────────┘  │ │
                      │             │                      │                            │ │
                      │             │                      ▼                            │ │
                      │             │   ┌───────────────────────────────────────────┐  │ │
                      │             │   │  STAGE 3: LLM RESPONSE GENERATION         │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  • pipeline.query(mode, message, chatbot) │  │ │
                      │             │   │  • Returns StreamingAgentChatResponse     │  │ │
                      │             │   │  • Collect all chunks into response_text  │  │ │
                      │             │   │  • Uses chat memory for context           │  │ │
                      │             │   │                                           │  │ │
                      │             │   │  ~2000-15000ms                            │  │ │
                      │             │   └───────────────────────────────────────────┘  │ │
                      │             │                      │                            │ │
                      │             └──────────────────────┼────────────────────────────┘ │
                      │                                    │                              │
                      │                                    ▼                              │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              RESPONSE                                       │ │
                      │  │  {                                                          │ │
                      │  │    "success": true,                                         │ │
                      │  │    "response": "LLM response text...",                      │ │
                      │  │    "sources": [                                             │ │
                      │  │      {document_name, chunk_location, relevance_score,       │ │
                      │  │       excerpt, notebook_id, source_id}                      │ │
                      │  │    ],                                                       │ │
                      │  │    "notebook_ids": ["uuid1"],                               │ │
                      │  │    "retrieval_strategy": "deep_dive+queryfusion",           │ │
                      │  │    "routing": {                                             │ │
                      │  │      "strategy": "DEEP_DIVE",                               │ │
                      │  │      "reasoning": "Query focuses on specific policy...",    │ │
                      │  │      "confidence": 0.85,                                    │ │
                      │  │      "selected_documents": ["source-uuid-1"]                │ │
                      │  │    },                                                       │ │
                      │  │    "metadata": { execution_time_ms, timings }               │ │
                      │  │  }                                                          │ │
                      │  └─────────────────────────────────────────────────────────────┘ │
                      └───────────────────────────────────────────────────────────────────┘
```

### Routing Strategies

| Strategy | Description | When Used |
|----------|-------------|-----------|
| `DIRECT_SYNTHESIS` | Answer from document summaries only | General questions, overview requests |
| `DEEP_DIVE` | Deep analysis of specific documents | Detailed questions about specific topics |
| `MULTI_DOC_ANALYSIS` | Cross-document comparison | Comparative questions, synthesis across docs |

### Fast Mode vs Standard Mode

| Aspect | Fast Mode | Standard Mode |
|--------|-----------|---------------|
| Latency | ~3-5s | ~5-15s |
| Routing | No routing analysis | Two-stage LLM routing |
| Method | `stateless_query()` | Full pipeline with routing |
| Memory | Stateless | Uses chat memory |
| Best For | Quick responses, production | Complex analysis, document selection |

### UI Configuration Status

**Default Mode**: **Standard Mode** (`fast_mode: false` or omitted)

**Current UI Status**: Fast mode is **NOT currently exposed** in the frontend UI.

| Component | Endpoint | fast_mode Parameter |
|-----------|----------|---------------------|
| `useChat.ts` (v1) | `/chat` | Not passed |
| `useChatV2.ts` (v2) | `/api/v2/chat/stream` | Not passed |
| `api.ts` service | Both endpoints | Not included |

**Backend Support**: The backend fully supports `fast_mode` via the API:
```json
POST /api/chat
{
  "message": "What is this document about?",
  "notebook_id": "uuid",
  "fast_mode": true  // Enables 4-8x faster responses
}
```

**To Enable Fast Mode via UI**: A toggle would need to be added to the chat interface that passes `fast_mode: true` to the backend. This would provide 4-8x faster responses at the cost of:
- Skipping two-stage document routing
- Skipping RAPTOR hierarchical summaries
- Using simpler stateless retrieval

---

## 3. SQL Chat Flow

**Endpoint:** `POST /api/sql-chat/query/<session_id>`
**Purpose:** Natural language to SQL with multi-database support
**Source:** `dbnotebook/api/routes/sql_chat.py`, `dbnotebook/core/sql_chat/service.py`

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SQL CHAT FLOW (Natural Language to SQL)                        │
│                         POST /api/sql-chat/query/<session_id>                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌───────────────────────────────────────────────────────────────────┐
│   React      │      │                    SQLChatService                                  │
│   Frontend   │      │            (dbnotebook/core/sql_chat/service.py)                   │
└──────┬───────┘      │                                                                   │
       │              │  ┌────────────────────────────────────────────────────────────┐  │
       │ POST         │  │                     COMPONENT REGISTRY                      │  │
       │ /api/sql-chat│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│  │
       │ /query/{id}  │  │  │ Connection   │ │ Schema       │ │ Intent Classifier    ││  │
       ▼              │  │  │ Manager      │ │ Introspector │ │ (classify query type)││  │
┌──────────────┐      │  │  └──────────────┘ └──────────────┘ └──────────────────────┘│  │
│  Request     │──────┼──┤  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│  │
│  {           │      │  │  │ Schema       │ │ Few-Shot     │ │ TextToSQL Engine     ││  │
│   query:     │      │  │  │ Linker       │ │ Retriever    │ │ (LlamaIndex NL2SQL)  ││  │
│   "Show top  │      │  │  └──────────────┘ └──────────────┘ └──────────────────────┘│  │
│    10 sales" │      │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│  │
│  }           │      │  │  │ Cost         │ │ Safe Query   │ │ Confidence           ││  │
└──────────────┘      │  │  │ Estimator    │ │ Executor     │ │ Scorer               ││  │
                      │  │  └──────────────┘ └──────────────┘ └──────────────────────┘│  │
                      │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│  │
                      │  │  │ Data Masker  │ │ Result       │ │ Telemetry            ││  │
                      │  │  │              │ │ Validator    │ │ Logger               ││  │
                      │  │  └──────────────┘ └──────────────┘ └──────────────────────┘│  │
                      │  └────────────────────────────────────────────────────────────┘  │
                      │                                                                   │
                      │  ═══════════════════════════════════════════════════════════════ │
                      │                      EXECUTION PIPELINE                           │
                      │  ═══════════════════════════════════════════════════════════════ │
                      │                                                                   │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 1: SESSION & INPUT VALIDATION                         │ │
                      │  │  • Validate session_id exists                               │ │
                      │  │  • Get user_id from request (multi-user safe)               │ │
                      │  │  • Validate user owns session                               │ │
                      │  │  • Security: sanitize input, check for injection patterns   │ │
                      │  │  ~5-10ms                                                    │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 2: REFINEMENT CHECK                                   │ │
                      │  │  • Check if this is a follow-up to previous query           │ │
                      │  │  • Load conversation context from SQLChatMemory             │ │
                      │  │  • Detect pronouns ("Show that again", "Filter those")      │ │
                      │  │  ~10-20ms                                                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 3: INTENT CLASSIFICATION                              │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  IntentClassifier.classify()                        │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Intent Types:                                       │   │ │
                      │  │  │  • TOP_K     → "top 10", "first 5"                  │   │ │
                      │  │  │  • JOIN      → multiple tables                       │   │ │
                      │  │  │  • FILTER    → "where", "with"                       │   │ │
                      │  │  │  • AGGREGATE → "total", "sum", "average"             │   │ │
                      │  │  │  • GROUP_BY  → "by region", "per month"              │   │ │
                      │  │  │  • COMPARE   → "vs", "compare"                       │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Returns: {intent, confidence, prompt_hints}         │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~20-50ms                                                  │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 4: SCHEMA FINGERPRINT CHECK                           │ │
                      │  │  • Fast fingerprint comparison (~10ms vs 500-2000ms full)   │ │
                      │  │  • If fingerprint matches → use cached schema               │ │
                      │  │  • If changed → re-introspect full schema                   │ │
                      │  │  ~10-2000ms (depends on cache hit)                          │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 5: SCHEMA LINKING (Table Pre-filtering)               │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  SchemaLinker.link()                                │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Query: "Show top 10 customers by revenue"           │   │ │
                      │  │  │              ↓                                       │   │ │
                      │  │  │  1. Embed query text                                 │   │ │
                      │  │  │  2. Compare to table/column embeddings               │   │ │
                      │  │  │  3. Score each table by relevance                    │   │ │
                      │  │  │              ↓                                       │   │ │
                      │  │  │  Selected: customers (0.92), orders (0.85)           │   │ │
                      │  │  │  Excluded: logs (0.12), audit (0.08)                 │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  → 80% context reduction for LLM                     │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~100-200ms                                                │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 6: DICTIONARY CONTEXT RETRIEVAL (RAG)                 │ │
                      │  │  • Query notebook "SQL: <connection_name>"                  │ │
                      │  │  • Retrieve relevant schema descriptions                    │ │
                      │  │  • Include sample values and business context               │ │
                      │  │  ~200-500ms                                                 │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 7: FEW-SHOT EXAMPLE RETRIEVAL                         │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  FewShotRetriever.retrieve()                        │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  • Vector search in Gretel dataset (~100K examples) │   │ │
                      │  │  │  • Find similar NL→SQL pairs                        │   │ │
                      │  │  │  • Return top-k examples for prompt                 │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Example:                                            │   │ │
                      │  │  │  NL: "Show top 5 products by sales"                  │   │ │
                      │  │  │  SQL: SELECT p.name, SUM(s.amount)...               │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~100-300ms                                                │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 8: SQL GENERATION (GPT-4.1)                           │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  TextToSQLEngine (LlamaIndex NLSQLTableQueryEngine)  │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Prompt:                                             │   │ │
                      │  │  │  ┌────────────────────────────────────────────────┐ │   │ │
                      │  │  │  │ Schema (filtered by SchemaLinker):             │ │   │ │
                      │  │  │  │ - customers (id, name, email, created_at)      │ │   │ │
                      │  │  │  │ - orders (id, customer_id, amount, date)       │ │   │ │
                      │  │  │  │                                                │ │   │ │
                      │  │  │  │ Intent hints: TOP_K query                      │ │   │ │
                      │  │  │  │                                                │ │   │ │
                      │  │  │  │ Few-shot examples:                             │ │   │ │
                      │  │  │  │ [Example 1] [Example 2] [Example 3]            │ │   │ │
                      │  │  │  │                                                │ │   │ │
                      │  │  │  │ Dictionary context: (from RAG)                 │ │   │ │
                      │  │  │  │                                                │ │   │ │
                      │  │  │  │ Query: "Show top 10 customers by revenue"      │ │   │ │
                      │  │  │  └────────────────────────────────────────────────┘ │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  → Uses dedicated GPT-4.1 (not pipeline LLM)         │   │ │
                      │  │  │  → Temperature: 0.0 (deterministic)                  │   │ │
                      │  │  │  → Context window: 1,000,000 tokens                  │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~1000-3000ms                                              │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 9: COST ESTIMATION & SAFETY CHECK                     │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  QueryCostEstimator.estimate()                      │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  • EXPLAIN ANALYZE on generated SQL                 │   │ │
                      │  │  │  • Check for:                                        │   │ │
                      │  │  │    - Sequential scans on large tables               │   │ │
                      │  │  │    - Cartesian products (missing JOINs)             │   │ │
                      │  │  │    - Excessive estimated rows                       │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Returns: {total_cost, estimated_rows, warnings}    │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~50-200ms                                                 │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 10: SEMANTIC EXECUTION WITH ERROR CORRECTION          │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  SafeQueryExecutor.execute() + SemanticInspector     │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  1. Execute SQL with READ-ONLY enforcement           │   │ │
                      │  │  │  2. If error:                                        │   │ │
                      │  │  │     a. SemanticInspector analyzes error              │   │ │
                      │  │  │     b. LLM generates corrected SQL                   │   │ │
                      │  │  │     c. Retry (max 3 attempts)                        │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Read-only check:                                    │   │ │
                      │  │  │  - Blocks: INSERT, UPDATE, DELETE, DROP, ALTER      │   │ │
                      │  │  │  - Uses PostgreSQL SET TRANSACTION READ ONLY        │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~50-500ms (depends on query complexity)                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 11: DATA MASKING                                      │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  DataMasker.mask()                                  │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Based on MaskingPolicy:                            │   │ │
                      │  │  │  • mask_columns: ["email"] → john***@***.com        │   │ │
                      │  │  │  • redact_columns: ["ssn"] → [REDACTED]             │   │ │
                      │  │  │  • hash_columns: ["user_id"] → a1b2c3...            │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~10-50ms                                                  │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 12: RESULT VALIDATION                                 │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  ResultValidator.validate()                         │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  • Check for empty results (may indicate bad query) │   │ │
                      │  │  │  • Verify column types match expectations           │   │ │
                      │  │  │  • Check for NULL-heavy results                     │   │ │
                      │  │  │  • Validate aggregation results                     │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  → Generate warnings (not errors)                   │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~5-20ms                                                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 13: CONFIDENCE SCORING                                │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  ConfidenceScorer.score()                           │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Factors:                                            │   │ │
                      │  │  │  • Query complexity (JOINs, subqueries)              │   │ │
                      │  │  │  • Intent match confidence                          │   │ │
                      │  │  │  • Schema coverage (all tables found?)              │   │ │
                      │  │  │  • Few-shot similarity                              │   │ │
                      │  │  │  • Execution success                                │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Returns: {score: 0.85, level: "high", factors}     │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~5-10ms                                                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 14: QUERY LEARNING                                    │ │
                      │  │  ┌─────────────────────────────────────────────────────┐   │ │
                      │  │  │  QueryLearner.learn()                               │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  If query successful:                                │   │ │
                      │  │  │  • Extract JOIN patterns from SQL                   │   │ │
                      │  │  │  • Store in learned_joins cache                     │   │ │
                      │  │  │  • Increment usage_count for existing patterns      │   │ │
                      │  │  │                                                      │   │ │
                      │  │  │  Future queries use learned patterns                │   │ │
                      │  │  └─────────────────────────────────────────────────────┘   │ │
                      │  │  ~5-20ms                                                   │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │  STEP 15: TELEMETRY LOGGING                                 │ │
                      │  │  • Log to sql_query_history table                           │ │
                      │  │  • Track: query, SQL, success, latency, confidence          │ │
                      │  │  • Used for accuracy metrics dashboard                      │ │
                      │  │  ~5-10ms                                                    │ │
                      │  └─────────────────────────┬───────────────────────────────────┘ │
                      │                            │                                      │
                      │                            ▼                                      │
                      │  ┌─────────────────────────────────────────────────────────────┐ │
                      │  │              RESPONSE                                       │ │
                      │  │  {                                                          │ │
                      │  │    "success": true,                                         │ │
                      │  │    "result": {                                              │ │
                      │  │      "sqlGenerated": "SELECT c.name, SUM(o.amount)...",     │ │
                      │  │      "data": [[...], [...], ...],                           │ │
                      │  │      "columns": [{name, type}, ...],                        │ │
                      │  │      "rowCount": 10,                                        │ │
                      │  │      "executionTimeMs": 3245,                               │ │
                      │  │      "confidence": {score: 0.85, level: "high"},            │ │
                      │  │      "intent": {type: "top_k", confidence: 0.9},            │ │
                      │  │      "costEstimate": {totalCost, estimatedRows},            │ │
                      │  │      "validationWarnings": [],                              │ │
                      │  │      "timings": {...per-stage breakdown...}                 │ │
                      │  │    }                                                        │ │
                      │  │  }                                                          │ │
                      │  └─────────────────────────────────────────────────────────────┘ │
                      └───────────────────────────────────────────────────────────────────┘
```

### SQL Chat Components

| Component | Purpose | File |
|-----------|---------|------|
| `DatabaseConnectionManager` | Connection CRUD, credential encryption | `connection.py` |
| `SchemaIntrospector` | Schema discovery, caching, fingerprinting | `schema.py` |
| `SchemaLinker` | Table pre-filtering via embeddings | `schema_linker.py` |
| `IntentClassifier` | Query intent detection (TOP_K, JOIN, etc.) | `intent_classifier.py` |
| `FewShotRetriever` | RAG over Gretel SQL examples | `few_shot_retriever.py` |
| `TextToSQLEngine` | LlamaIndex NLSQLTableQueryEngine | `query_engine.py` |
| `QueryCostEstimator` | EXPLAIN ANALYZE for safety | `cost_estimator.py` |
| `SafeQueryExecutor` | Read-only enforcement | `executor.py` |
| `DataMasker` | PII masking, redaction | `data_masker.py` |
| `ResultValidator` | Result quality checks | `result_validator.py` |
| `ConfidenceScorer` | Multi-factor confidence scoring | `confidence_scorer.py` |
| `QueryLearner` | Learn JOIN patterns from success | `query_learner.py` |
| `TelemetryLogger` | Query metrics tracking | `telemetry.py` |

### SQL Chat Timing Breakdown (Typical)

| Stage | Duration | Notes |
|-------|----------|-------|
| 1. Session Validation | ~5-10ms | User/session checks |
| 2. Refinement Check | ~10-20ms | Follow-up detection |
| 3. Intent Classification | ~20-50ms | Pattern matching |
| 4. Schema Fingerprint | 10-2000ms | Cache hit vs full introspection |
| 5. Schema Linking | ~100-200ms | Embedding similarity |
| 6. Dictionary RAG | ~200-500ms | Notebook query |
| 7. Few-Shot Retrieval | ~100-300ms | Vector search |
| 8. SQL Generation | ~1000-3000ms | **GPT-4.1 LLM call** |
| 9. Cost Estimation | ~50-200ms | EXPLAIN ANALYZE |
| 10. Query Execution | ~50-500ms | Actual SQL run |
| 11. Data Masking | ~10-50ms | PII handling |
| 12. Result Validation | ~5-20ms | Quality checks |
| 13. Confidence Scoring | ~5-10ms | Multi-factor score |
| 14. Query Learning | ~5-20ms | Pattern extraction |
| 15. Telemetry | ~5-10ms | Async logging |
| **Total** | **~2000-5000ms** | Varies by complexity |

---

## 4. Comparative Summary

| Feature | API Query | RAG Chat | SQL Chat |
|---------|-----------|----------|----------|
| **Purpose** | Programmatic RAG access | Interactive chat with docs | Natural language → SQL |
| **Entry Point** | `/api/query` | `/api/chat` | `/api/sql-chat/query/{id}` |
| **Auth** | API Key (X-API-Key) | None (session-based) | Session + User ID |
| **Memory** | Ephemeral (in-memory) | Persistent (DB) | Session-based (DB) |
| **Routing** | None | Two-stage LLM routing | Intent classification |
| **Retrieval** | Hybrid (BM25+Vector+Rerank) | Same + doc filtering | Schema linking + RAG |
| **LLM** | Configurable per-request | Pipeline default | Dedicated GPT-4.1 |
| **Typical Latency** | 5-15s | 5-15s (3s fast mode) | 3-5s |
| **RAPTOR Support** | Yes (optional) | Via routing | N/A |
| **Streaming** | No | Yes (fast mode) | SSE streaming |
| **Multi-User Safe** | Yes (thread-safe) | Yes | Yes (session isolation) |

---

## 5. Key Components

### Hybrid Retrieval Pipeline

```
┌───────────────────────────────────────────────────────────────────────┐
│                     HYBRID RETRIEVAL ARCHITECTURE                      │
│                    (Used by API Query and RAG Chat)                    │
└───────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   Query     │
                              │   Text      │
                              └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
           ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
           │    BM25       │ │   Vector      │ │   RAPTOR      │
           │   Retriever   │ │   Retriever   │ │   Retriever   │
           │  (Keyword)    │ │  (Semantic)   │ │ (Hierarchical)│
           └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                   │                 │                 │
                   └────────────┬────┴─────────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Query Fusion /       │
                   │   Result Merging       │
                   │   (Reciprocal Rank)    │
                   └───────────┬────────────┘
                               │
                               ▼
                   ┌────────────────────────┐
                   │      Reranker          │
                   │  (mxbai-rerank-large)  │
                   │   Cross-encoder        │
                   └───────────┬────────────┘
                               │
                               ▼
                   ┌────────────────────────┐
                   │   Top-K Results        │
                   │   with Scores          │
                   └────────────────────────┘
```

### RAPTOR Tree Structure

```
┌───────────────────────────────────────────────────────────────────────┐
│                     RAPTOR HIERARCHICAL SUMMARIES                      │
│                  (Built during document ingestion)                     │
└───────────────────────────────────────────────────────────────────────┘

                    Level 3: Root Summary
                         ┌───────┐
                         │ Root  │  ← Highest abstraction
                         └───┬───┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
Level 2: │ Summary │    │ Summary │    │ Summary │
         │   A     │    │   B     │    │   C     │
         └────┬────┘    └────┬────┘    └────┬────┘
              │              │              │
    ┌────┬────┘    ┌────┬────┘    ┌────┬────┘
    │    │    │    │    │    │    │    │    │
   ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐
Level 1: Cluster Summaries (semantic groupings)
   └┬┘  └┬┘  └┬┘  └┬┘  └┬┘  └┬┘  └┬┘  └┬┘  └┬┘
    │    │    │    │    │    │    │    │    │
Level 0: Original Document Chunks (512 tokens each)
   ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐  ┌┴┐
   │C1│ │C2│ │C3│ │C4│ │C5│ │C6│ │C7│ │C8│ │C9│
   └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘

Retrieval Strategy:
- Query RAPTOR summaries for high-level context
- Query original chunks for detailed evidence
- Combine for hierarchical understanding
```

### Document Routing Decision Tree

```
┌───────────────────────────────────────────────────────────────────────┐
│                     DOCUMENT ROUTING DECISION TREE                     │
│                  (DocumentRoutingService in RAG Chat)                  │
└───────────────────────────────────────────────────────────────────────┘

                         ┌─────────────┐
                         │   Query     │
                         └──────┬──────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Analyze query against │
                    │  document summaries   │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │   General    │     │  Specific    │     │ Comparative  │
   │   Overview   │     │  Deep Dive   │     │   Analysis   │
   │   Question   │     │   Question   │     │   Question   │
   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │   DIRECT_    │     │   DEEP_      │     │  MULTI_DOC_  │
   │  SYNTHESIS   │     │    DIVE      │     │   ANALYSIS   │
   │              │     │              │     │              │
   │ Answer from  │     │ Filter to    │     │ Query across │
   │ summaries    │     │ selected     │     │ multiple     │
   │ only         │     │ documents    │     │ documents    │
   └──────────────┘     └──────────────┘     └──────────────┘
          │                    │                    │
          │                    ▼                    ▼
          │             ┌──────────────────────────────┐
          │             │    Hybrid Retrieval          │
          │             │    (BM25 + Vector + Rerank)  │
          │             └──────────────────────────────┘
          │                           │
          └───────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ LLM Response │
                  │ Generation   │
                  └──────────────┘
```

---

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md) - System architecture and components
- [RAG Chat](features/rag-chat.md) - Hybrid retrieval and chat implementation
- [SQL Chat](features/sql-chat.md) - Natural language to SQL queries
- [RAPTOR Retrieval](features/raptor.md) - Hierarchical tree building and retrieval
