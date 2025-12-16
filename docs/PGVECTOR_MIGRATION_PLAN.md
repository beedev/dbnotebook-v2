# pgvector Migration Plan - Clean Slate Architecture

> **Bharath Persona Active**: "We're not here to write code. We're here to make a dent in the universe."

## Quick Start for New Session

**Full plan file**: `/Users/bharath/.claude/plans/magical-jumping-wave.md`

**Approach**: Clean slate - replace ChromaDB with pgvector. No data migration (documents will be re-added later).

---

## Implementation Phases

### Phase 0: Database Setup (30 min)
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
```bash
pip install llama-index-vector-stores-postgres psycopg2-binary asyncpg
```

### Phase 1: Create PGVectorStore Wrapper (2 hrs)
- **File**: `rag_chatbot/core/vector_store/pg_vector_store.py`
- Same interface as LocalVectorStore for drop-in replacement
- Methods: `get_index()`, `get_index_by_notebook()`, `add_nodes()`, `delete_document_nodes()`

### Phase 2: Database Schema Migration (1 hr)
- **File**: `alembic/versions/xxx_add_pgvector_embeddings.py`
- Create `embeddings` table with `vector(768)` column
- HNSW index for cosine similarity
- B-tree indexes on `notebook_id`, `source_id`
- tsvector for hybrid search

### Phase 3: Pipeline Integration (2 hrs)
- Update `rag_chatbot/pipeline.py` to use PGVectorStore
- Update `rag_chatbot/core/ingestion/ingestion.py` for incremental adds
- Update `rag_chatbot/core/engine/retriever.py` for notebook-filtered index

### Phase 4: Cleanup & Testing (1 hr)
- Remove ChromaDB from `pyproject.toml`
- Delete `rag_chatbot/core/vector_store/vector_store.py`
- Run integration tests

---

## Critical Files

| File | Action |
|------|--------|
| `pyproject.toml` | Add pgvector deps, remove chromadb |
| `rag_chatbot/core/vector_store/pg_vector_store.py` | **CREATE** |
| `rag_chatbot/core/vector_store/vector_store.py` | **DELETE** |
| `rag_chatbot/pipeline.py` | Modify |
| `rag_chatbot/core/ingestion/ingestion.py` | Modify |
| `rag_chatbot/core/engine/retriever.py` | Modify |
| `alembic/versions/xxx_add_pgvector.py` | **CREATE** |

---

## LlamaIndex PGVectorStore Pattern

```python
from llama_index.vector_stores.postgres import PGVectorStore

vector_store = PGVectorStore.from_params(
    database=db_name,
    host=host,
    password=password,
    port=port,
    user=user,
    table_name="embeddings",
    embed_dim=768,  # nomic-embed-text-v1.5
    hnsw_kwargs={
        "hnsw_m": 16,
        "hnsw_ef_construction": 64,
        "hnsw_ef_search": 40,
        "hnsw_dist_method": "vector_cosine_ops",
    },
    hybrid_search=True,
    text_search_config="english",
)
```

---

## Future Phases (After pgvector)

### MVP 5: Plugin Architecture (1-2 days)
- Abstract interfaces: `RetrievalStrategy`, `LLMProvider`, `ContentProcessor`
- Plugin registry for configuration-driven component swapping
- Files: `rag_chatbot/core/interfaces/`, `rag_chatbot/core/strategies/`, `rag_chatbot/core/providers/`

### MVP 6: Polish & Production (1-2 days)
- Document list in notebook view
- Loading states, error messages
- Keyboard shortcuts, search, sorting
- Health check endpoint `/api/health`

---

## Benefits of pgvector

- O(log n) metadata filtering via SQL indexes (vs O(n) client-side)
- Native hybrid search (BM25 + vector in single query)
- ACID transactions across metadata + vectors
- Single backup/restore strategy
- Incremental vector updates (no index rebuild)
- Production-ready scaling (millions of vectors)

---

## Command to Start

```bash
# In new session, tell Claude:
"Implement pgvector migration using Bharath persona. Plan is at docs/PGVECTOR_MIGRATION_PLAN.md"
```
