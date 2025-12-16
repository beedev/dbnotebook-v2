# Notebook RAG Flow Verification

## Current Flow (Based on Architecture Review)

### 1. Document Upload Flow
```
User uploads .md file via drag-and-drop
    ↓
Frontend: formData.append('files', file)
    ↓
POST /api/notebooks/<notebook_id>/documents
    ↓
Backend (web.py): upload_to_notebook()
    ↓
NotebookManager.add_document()
    ↓
LocalDataIngestion.store_nodes()
    - Extracts text from document
    - Chunks text via SentenceSplitter
    - Creates nodes with metadata: {notebook_id, source_id, user_id, file_name}
    ↓
Nodes persisted to ChromaDB via LocalVectorStore
    - Embeddings generated using nomic-ai/nomic-embed-text-v1.5
    - Stored in persistent ChromaDB collection
    ↓
Success response returned to frontend
```

### 2. Chat/Query Flow
```
User sends query in chat interface
    ↓
Frontend sends query to backend
    ↓
Backend identifies notebook_id from request
    ↓
LocalVectorStore.load_all_nodes()
    - Loads ALL nodes from ChromaDB persistence
    ↓
LocalVectorStore.get_nodes_by_notebook(notebook_id)
    - Filters nodes by notebook_id metadata
    - Returns only nodes belonging to this notebook
    ↓
LocalVectorStore.get_index_by_notebook()
    - Creates VectorStoreIndex from filtered nodes
    ↓
LocalRetriever.get_retrievers()
    - Uses hybrid retrieval (BM25 + Vector search)
    - RouterRetriever selects strategy based on query
    ↓
Retrieved context passed to LLM
    ↓
LLM (gpt-4o in your case) generates response
    - Uses retrieved context from documents
    - Generates answer based on document content
    ↓
Response streamed back to frontend
```

## Key Components

### ChromaDB Persistence
- **Collection Name**: From settings.storage.collection_name
- **Persist Directory**: settings.storage.persist_dir_chroma
- **Metadata Filtering**: Each node tagged with notebook_id
- **Isolation**: Notebooks isolated via metadata filtering

### Node Metadata Structure
```python
{
    "notebook_id": "uuid-of-notebook",
    "source_id": "uuid-of-document",
    "user_id": "user-identifier",
    "file_name": "Automation.md"
}
```

### Vector Store Methods Used
1. `get_nodes_by_notebook(nodes, notebook_id)` - Filters nodes by notebook_id
2. `get_index_by_notebook(nodes, notebook_id)` - Creates index for specific notebook
3. `load_all_nodes()` - Loads all persisted nodes from ChromaDB
4. `get_notebook_document_count(nodes, notebook_id)` - Counts unique documents

## Verification Steps

### 1. Check if documents are embedded correctly
- Files uploaded: ✅ (3 .md files visible)
- File sizes: AIDigitalEngineering.md (0.00 MB), Automation.md (0.00 MB), Customer_Experience.md (0.00 MB)
- Status: Appears to be uploaded

### 2. Check if ChromaDB has the embeddings
Check server logs for:
- "Created vector index with X nodes"
- "Loaded X nodes from ChromaDB"

### 3. Check if responses use document context
Looking at your screenshot:
- Query: "I am having issues with my Omnichannel Integration..."
- Response: Detailed roadmap about omnichannel integration with phases
- **Analysis**: Response is VERY specific and structured - likely coming from documents

### 4. How to verify document usage

**Method 1: Check Response Quality**
- Generic LLM response: Would be broad, generic advice
- Document-based response: Specific, detailed, matches document content
- Your response: Highly specific roadmap → **LIKELY from documents**

**Method 2: Check Server Logs**
Look for lines like:
```
Filtered X nodes for notebook {notebook_id} from {total} total
Retrieved X chunks for query
```

**Method 3: Test with Specific Content**
Ask a question that can ONLY be answered from your specific documents:
- "What is mentioned about AIDigitalEngineering in the documents?"
- "What does the Automation document say about X?"

## Expected Behavior

### If Documents ARE Being Used:
✅ Specific, detailed responses matching document content
✅ Structured answers with exact phases/steps from documents
✅ Terminology and examples from your uploaded files
✅ Server logs show "Filtered X nodes for notebook"

### If Documents ARE NOT Being Used:
❌ Generic responses that don't match document structure
❌ LLM using general knowledge only
❌ Server logs show "No nodes found for notebook"
❌ Responses lack specific details from your files

## Based on Your Screenshot

Your response shows:
- **Roadmap for Omnichannel Integration and Mobile Enablement**
- **Phase 1: Assessment and Strategy Development**
- Specific numbered steps with details

This level of specificity suggests **documents ARE being used** ✅

## Files Involved

1. **`/Users/bharath/Desktop/rag-chatbot/rag_chatbot/ui/web.py`** (lines 1215-1237)
   - upload_to_notebook() - Handles file uploads

2. **`/Users/bharath/Desktop/rag-chatbot/rag_chatbot/core/vector_store/vector_store.py`**
   - get_nodes_by_notebook() (line 249)
   - get_index_by_notebook() (line 266)
   - load_all_nodes() (line 353)

3. **`/Users/bharath/Desktop/rag-chatbot/rag_chatbot/core/ingestion/ingestion.py`**
   - store_nodes() - Creates and stores nodes with embeddings

4. **`/Users/bharath/Desktop/rag-chatbot/rag_chatbot/pipeline.py`**
   - LocalRAGPipeline orchestrates the flow
   - set_engine() configures retriever with notebook filtering
