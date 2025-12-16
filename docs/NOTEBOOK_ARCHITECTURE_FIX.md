# Notebook Architecture Fix - ChromaDB Persistence

## Problem
Documents uploaded to notebooks are not persisting across sessions. Embeddings are created but stored only in memory, lost on server restart.

## Root Cause
1. `store_nodes()` creates nodes with embeddings and stores them in memory dictionaries (`_node_store`, `_ingested_file`)
2. Nodes are NOT persisted to ChromaDB during upload
3. When a notebook is selected for chat, `get_ingested_nodes()` returns empty list (memory is cleared)
4. Chat engine is created with 0 nodes, causing LLM to use general knowledge instead of notebook documents

## Solution Architecture

### Phase 1: Persist During Upload
When documents are uploaded to a notebook:
1. `store_nodes()` creates nodes with `notebook_id` metadata
2. Nodes are immediately persisted to ChromaDB via `LocalVectorStore`
3. Metadata includes: `notebook_id`, `source_id`, `user_id`, `file_name`

### Phase 2: Load During Chat
When a notebook is selected for chat:
1. Query ChromaDB for all nodes (load from persistent storage)
2. Filter nodes by `notebook_id` using metadata
3. Create retriever with filtered nodes
4. No need to re-load documents from disk

## Implementation Changes

### 1. Modify LocalDataIngestion
- Add `vector_store` parameter to `__init__`
- After nodes are created with metadata, persist to ChromaDB
- Method: `vector_store.get_index(nodes)` - automatically persists when `persist=True`

### 2. Modify LocalRAGPipeline
- Pass `vector_store` to `LocalDataIngestion` during initialization
- In `set_engine()`:
  - Load ALL nodes from ChromaDB (persistent storage)
  - Use `vector_store.get_nodes_by_notebook()` to filter by `notebook_id`
  - Create retriever with filtered nodes

### 3. Add ChromaDB Query Method
- `LocalVectorStore.load_all_nodes()` - loads all persisted nodes from ChromaDB
- Uses the existing ChromaDB collection
- Returns List[BaseNode] with all stored embeddings

## Benefits
1. **Persistence**: Embeddings survive server restarts
2. **Efficiency**: No re-loading documents from disk
3. **Scalability**: ChromaDB handles large collections efficiently
4. **Isolation**: Notebooks are isolated by metadata filtering

## Implementation Steps
1. Add `load_all_nodes()` method to `LocalVectorStore`
2. Modify `LocalDataIngestion.__init__()` to accept vector_store
3. Modify `LocalDataIngestion.store_nodes()` to persist to ChromaDB after creating nodes
4. Modify `LocalRAGPipeline.__init__()` to pass vector_store to ingestion
5. Modify `LocalRAGPipeline.set_engine()` to load from ChromaDB instead of disk
6. Test: Upload document, restart server, verify chat uses document content
