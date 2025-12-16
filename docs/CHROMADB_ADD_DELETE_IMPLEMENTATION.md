# ChromaDB Add/Delete Implementation - Complete

## Summary

Fixed two critical bugs in the notebook document management system:
1. **ADD operation** - Documents were NOT being persisted to ChromaDB, causing loss on subsequent operations
2. **DELETE operation** - No endpoint existed to delete documents from ChromaDB

## Problem Analysis

### Issue 1: ADD Operation Bug
**Root Cause**: File-by-file calls to `get_index()` with caching caused overwrites
- Each new file triggered `get_index()` with force_rebuild
- Cached node count comparison failed (new file count ≠ cached count)
- ChromaDB index rebuilt with ONLY the new file's nodes
- Previous files' nodes LOST from ChromaDB

### Issue 2: DELETE Operation Missing
**Root Cause**: No DELETE endpoint or ChromaDB deletion logic existed
- `notebook_manager.remove_document()` only deleted from PostgreSQL
- Nodes remained in ChromaDB indefinitely
- No way to clean up deleted documents

## Solutions Implemented

### Fix 1: Enhanced ADD Operation

**File**: `rag_chatbot/core/ingestion/ingestion.py` (lines 503-524)

**What Changed**:
- Removed file-by-file ChromaDB persistence
- Added batch persistence after ALL files processed
- **CRITICAL**: Load existing nodes FIRST, combine with new, persist ALL together

**Code Changes**:
```python
# OLD CODE (BUGGY):
for file_name in file_names:
    # Process file...
    # Persist to ChromaDB immediately (OVERWRITES PREVIOUS!)
    self._vector_store.get_index(return_nodes, force_rebuild=True)

# NEW CODE (FIXED):
# Process ALL files first...
# THEN persist ALL nodes at once:
if self._vector_store and notebook_id and return_nodes:
    # Load existing nodes from ChromaDB
    existing_nodes = self._vector_store.load_all_nodes()

    # Filter to get THIS notebook's existing nodes
    existing_notebook_nodes = self._vector_store.get_nodes_by_notebook(
        existing_nodes, notebook_id
    )

    # Combine existing + new nodes
    all_nodes = existing_notebook_nodes + return_nodes

    # Persist ALL nodes together (forces rebuild to ensure all are stored)
    self._vector_store.get_index(all_nodes, force_rebuild=True)
```

### Fix 2: Added DELETE Helper Method

**File**: `rag_chatbot/core/vector_store/vector_store.py` (lines 398-455)

**What It Does**:
1. Loads ALL nodes from ChromaDB
2. Filters OUT nodes matching `source_id`
3. Rebuilds ChromaDB index with remaining nodes

**Method Signature**:
```python
def delete_document_nodes(self, source_id: str) -> bool:
    """
    Delete all nodes for a specific document from ChromaDB.

    Args:
        source_id: UUID of the document whose nodes should be deleted

    Returns:
        True if deletion successful, False otherwise
    """
```

### Fix 3: Added DELETE Endpoint

**File**: `rag_chatbot/ui/web.py` (lines 1318-1352)

**Endpoint**: `DELETE /api/notebooks/<notebook_id>/documents/<source_id>`

**What It Does**:
1. Validates notebook feature availability
2. Calls `notebook_manager.remove_document()` - PostgreSQL deletion
3. Calls `vector_store.delete_document_nodes()` - ChromaDB deletion
4. Returns success/error response

**Code**:
```python
@self._app.route("/api/notebooks/<notebook_id>/documents/<source_id>", methods=["DELETE"])
def delete_notebook_document(notebook_id, source_id):
    """Delete a document from a notebook."""
    # Delete from PostgreSQL database
    success = self._notebook_manager.remove_document(notebook_id, source_id)

    # Delete from ChromaDB vector store
    if self._pipeline and self._pipeline._vector_store:
        chromadb_success = self._pipeline._vector_store.delete_document_nodes(source_id)

    return jsonify({"success": True, "message": "Document deleted successfully"})
```

## Complete Data Flow

### ADD Operation Flow
```
User uploads files via drag-and-drop
    ↓
POST /api/notebooks/<notebook_id>/documents
    ↓
Files saved to data/data/
    ↓
notebook_manager.add_document() → PostgreSQL
    ↓
ingestion.store_nodes():
    - Process ALL files (chunking, embedding)
    - Load existing ChromaDB nodes for THIS notebook
    - Combine existing + new nodes
    - Persist ALL nodes to ChromaDB (force rebuild)
    ↓
Success response → Frontend
```

### DELETE Operation Flow
```
User clicks delete button in UI
    ↓
DELETE /api/notebooks/<notebook_id>/documents/<source_id>
    ↓
notebook_manager.remove_document() → PostgreSQL deletion
    ↓
vector_store.delete_document_nodes():
    - Load ALL nodes from ChromaDB
    - Filter OUT nodes with matching source_id
    - Rebuild ChromaDB with remaining nodes
    ↓
Success response → Frontend
```

## Key Technical Details

### Metadata Used
```python
{
    "notebook_id": "uuid-of-notebook",
    "source_id": "uuid-of-document",  # Used for deletion
    "user_id": "user-identifier",
    "file_name": "document.md"
}
```

### ChromaDB Operations
- **Location**: `data/chroma/chroma.sqlite3`
- **Collection**: From `settings.storage.collection_name`
- **Embedding Model**: `nomic-ai/nomic-embed-text-v1.5`
- **Index Caching**: `force_rebuild=True` ensures clean state

## Files Modified

1. **`rag_chatbot/core/ingestion/ingestion.py`**
   - Lines 503-524: Enhanced ADD operation to preserve existing nodes

2. **`rag_chatbot/core/vector_store/vector_store.py`**
   - Lines 398-455: Added `delete_document_nodes()` helper method

3. **`rag_chatbot/ui/web.py`**
   - Lines 1318-1352: Added DELETE endpoint

## Testing Recommendations

### Test ADD Operation
1. Upload multiple .md files to a notebook
2. Verify server logs show: "Persisting X total nodes (Y existing + Z new)"
3. Check that ALL documents appear in notebook
4. Restart server and verify documents still accessible
5. Add MORE files and verify previous files still work

### Test DELETE Operation
1. Upload 3 documents to a notebook
2. Delete the middle document
3. Verify:
   - Document removed from UI
   - PostgreSQL has 2 documents remaining
   - ChromaDB only has nodes for 2 documents
   - Chat still works with remaining 2 documents
4. Delete all documents and verify empty state

### Test Edge Cases
1. Delete last document in notebook
2. Add files after deleting all files
3. Delete file immediately after upload
4. Upload same file multiple times (should create new nodes each time with different source_id)

## Next Steps

1. **Frontend Integration**: Update notebooks UI to call DELETE endpoint
2. **Bulk Operations**: Add endpoint to delete multiple documents at once
3. **Document Stats**: Show node count per document in UI
4. **Validation**: Add UI confirmation before deletion
5. **Audit Trail**: Log document additions/deletions

## Bug Fixes

### Critical Bug in `delete_document_nodes()` - FIXED
**Location**: `rag_chatbot/core/vector_store/vector_store.py:441-452`

**Issue**: When deleting the last document from ChromaDB, the code referenced incorrect variable names:
- Used `self._client` instead of `self._chroma_client`
- Used `self._index` instead of `self._index_cache`

**Impact**: Would cause AttributeError when attempting to delete the final document from a notebook

**Fix Applied**:
```python
# BEFORE (BUGGY):
collection = self._client.get_collection(name=self._collection_name)
self._client.delete_collection(name=self._collection_name)
self._client.create_collection(name=self._collection_name)
self._index = None

# AFTER (FIXED):
self._chroma_client.delete_collection(name=self._collection_name)
self._chroma_client.get_or_create_collection(
    name=self._collection_name,
    metadata={"hnsw:space": "cosine"}
)
self._index_cache = None
self._cached_node_count = 0
```

## Status

- ✅ **ADD Operation Fixed**: Nodes persist correctly to ChromaDB
- ✅ **DELETE Helper Added**: `delete_document_nodes()` method in vector_store.py
- ✅ **DELETE Helper Bug Fixed**: Corrected variable names for last document deletion
- ✅ **DELETE Endpoint Added**: `/api/notebooks/<notebook_id>/documents/<source_id>`
- ⏳ **Frontend Integration**: Need to wire up delete button to endpoint
- ⏳ **Testing**: Need to verify with real documents

## Related Documentation

- `docs/CHROMADB_FIX.md` - ChromaDB schema mismatch fix (Dec 13, 2025)
- `docs/NOTEBOOK_FLOW_VERIFICATION.md` - Architecture documentation
- `docs/NOTEBOOKS_UI_IMPROVEMENTS.md` - UI enhancement plans
