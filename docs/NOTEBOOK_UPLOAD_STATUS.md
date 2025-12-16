# Notebook Upload Feature - Implementation Status

**Last Updated**: December 12, 2025
**Status**: IN PROGRESS - Backend complete, API routes needed

---

## ✅ Completed Components

### 1. Database Infrastructure (COMPLETE)
- **File**: `rag_chatbot/core/db/db.py`
  - DatabaseManager class with SQLAlchemy
  - Connection pooling and session management
  - Context manager for transactions

- **File**: `rag_chatbot/core/db/models.py`
  - User model
  - Notebook model
  - NotebookSource model (document tracking)
  - Conversation model (for future conversation persistence)
  - All relationships and constraints defined

### 2. Notebook Manager (COMPLETE)
- **File**: `rag_chatbot/core/notebook/notebook_manager.py`
  - ✅ `create_notebook(user_id, name, description)` - Create new notebook
  - ✅ `get_notebook(notebook_id)` - Get notebook details
  - ✅ `list_notebooks(user_id)` - List all user notebooks
  - ✅ `update_notebook(notebook_id, **kwargs)` - Update notebook
  - ✅ `delete_notebook(notebook_id)` - Delete notebook
  - ✅ `add_document(notebook_id, file_info)` - Add document to notebook
  - ✅ `get_documents(notebook_id)` - List documents in notebook
  - ✅ `remove_document(notebook_id, source_id)` - Remove document
  - ✅ `get_notebook_stats(notebook_id)` - Get statistics
  - ✅ `ensure_default_user()` - Create default user if not exists

### 3. Migration Utility (COMPLETE - User Declined)
- **Files**:
  - `scripts/migrate_offerings_to_notebooks.py`
  - `rag_chatbot/core/migration/offering_to_notebook_migration.py`
  - `docs/OFFERING_TO_NOTEBOOK_MIGRATION.md`
  - `docs/MIGRATION_SUMMARY.md`

- **User Decision**: "Not necessary, I can upload them to notebook"
- **Action**: No migration needed - user will upload documents directly

---

## ❌ Not Done - Remaining Work

### 1. Initialize Database in Application (NOT STARTED)

**File**: `rag_chatbot/__main__.py` or `rag_chatbot/ui/web.py`

**What's needed**:
```python
# In __main__.py or web.py
from rag_chatbot.core.db.db import DatabaseManager
from rag_chatbot.core.notebook.notebook_manager import NotebookManager
import os

# Get DATABASE_URL from environment
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Fallback or raise error
    database_url = "postgresql://localhost/rag_chatbot"

# Initialize DatabaseManager
db_manager = DatabaseManager(database_url=database_url)

# Initialize database schema
db_manager.init_db()

# Create NotebookManager
notebook_manager = NotebookManager(db_manager=db_manager)

# Ensure default user exists
notebook_manager.ensure_default_user()

# Pass to FlaskChatbotUI
ui = FlaskChatbotUI(
    pipeline=pipeline,
    db_manager=db_manager,
    notebook_manager=notebook_manager
)
```

**Environment Configuration**:
- DATABASE_URL must be set in `.env`
- Example: `DATABASE_URL=postgresql://localhost/rag_chatbot`

### 2. Add Notebook API Routes to web.py (IN PROGRESS)

**File**: `rag_chatbot/ui/web.py`

**Current State**:
- Line 58: FlaskChatbotUI class exists
- Line 82-87: `_setup_routes()` method exists
- Line 370-379: Hybrid support for `selected_notebooks` already present in chat route

**Missing Routes** (need to add in `_setup_routes()` method):

```python
# GET /api/notebooks - List all notebooks for user
@self._app.route('/api/notebooks', methods=['GET'])
def list_notebooks():
    try:
        user_id = "default_user"  # For now, hardcoded
        notebooks = self._notebook_manager.list_notebooks(user_id)
        return jsonify({"success": True, "notebooks": notebooks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# POST /api/notebooks - Create new notebook
@self._app.route('/api/notebooks', methods=['POST'])
def create_notebook():
    try:
        data = request.json
        user_id = "default_user"
        name = data.get("name")
        description = data.get("description", "")

        notebook_id = self._notebook_manager.create_notebook(
            user_id=user_id,
            name=name,
            description=description
        )
        return jsonify({"success": True, "notebook_id": notebook_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# DELETE /api/notebooks/<notebook_id> - Delete notebook
@self._app.route('/api/notebooks/<notebook_id>', methods=['DELETE'])
def delete_notebook(notebook_id):
    try:
        success = self._notebook_manager.delete_notebook(notebook_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# POST /api/notebooks/<notebook_id>/documents - Upload documents to notebook
@self._app.route('/api/notebooks/<notebook_id>/documents', methods=['POST'])
def upload_to_notebook(notebook_id):
    try:
        # Get uploaded files
        files = request.files.getlist('files')

        # Process each file
        for file in files:
            # Save file to data/data/
            file_path = os.path.join("data/data", file.filename)
            file.save(file_path)

            # Calculate file hash
            import hashlib
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            # Get file stats
            file_size = os.path.getsize(file_path)
            file_type = file.filename.split('.')[-1] if '.' in file.filename else 'unknown'

            # Add to notebook
            file_info = {
                "file_name": file.filename,
                "file_hash": file_hash,
                "file_size": file_size,
                "file_type": file_type,
                "chunk_count": 0  # Will be updated after ingestion
            }

            source_id = self._notebook_manager.add_document(
                notebook_id=notebook_id,
                file_info=file_info
            )

            # Ingest document (existing pipeline logic)
            # TODO: Update ingestion to include notebook_id metadata

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# GET /api/notebooks/<notebook_id>/documents - List documents in notebook
@self._app.route('/api/notebooks/<notebook_id>/documents', methods=['GET'])
def list_notebook_documents(notebook_id):
    try:
        documents = self._notebook_manager.get_documents(notebook_id)
        return jsonify({"success": True, "documents": documents})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

### 3. Update UI Templates (NOT STARTED)

**File**: `rag_chatbot/ui/ui.py` or template files

**What's needed**:
1. **Notebook Selector Dropdown**
   - Add to upload interface
   - Fetch notebooks from `/api/notebooks`
   - Allow user to select notebook before upload

2. **Notebook Management UI**
   - "Create Notebook" button
   - Notebook list with delete option
   - Notebook name/description input form

3. **Chat Interface Update**
   - Notebook selector for querying
   - Display current notebook context

### 4. Update Ingestion to Include Notebook Metadata (NOT STARTED)

**File**: `rag_chatbot/core/ingestion/ingestion.py`

**What's needed**:
- Add `notebook_id` parameter to `store_nodes()` method
- Include `notebook_id` in ChromaDB metadata for all nodes
- Example:
```python
metadata = {
    "file_name": file_name,
    "notebook_id": notebook_id,  # NEW
    "user_id": user_id,           # NEW
    "source_id": source_id,       # NEW
    "file_hash": file_hash,
    # ... existing metadata
}
```

### 5. Update Pipeline to Use Notebook Filter (NOT STARTED)

**File**: `rag_chatbot/pipeline.py`

**What's needed**:
- Modify `query_sales_mode()` or chat methods to accept `selected_notebooks`
- Pass notebook filter to vector store retrieval
- Example:
```python
# Get nodes filtered by notebook_id
nodes = self._vector_store.get_nodes_by_notebook(notebook_id)
```

---

## 🎯 Next Steps (Priority Order)

1. **Step 1**: Initialize DatabaseManager in `__main__.py`
   - Import DatabaseManager and NotebookManager
   - Get DATABASE_URL from environment
   - Initialize db_manager and notebook_manager
   - Pass to FlaskChatbotUI constructor

2. **Step 2**: Update `FlaskChatbotUI.__init__()` to accept db_manager and notebook_manager
   - Add parameters to constructor
   - Store as instance variables

3. **Step 3**: Add notebook API routes to `web.py`
   - Add 5 routes listed above in `_setup_routes()` method

4. **Step 4**: Update ingestion to include notebook_id metadata
   - Modify `store_nodes()` in `ingestion.py`

5. **Step 5**: Update UI templates for notebook management
   - Add notebook selector
   - Add create/delete notebook UI

6. **Step 6**: Test end-to-end workflow
   - Create notebook via API
   - Upload document to notebook
   - Query with notebook filter
   - Verify ChromaDB metadata filtering works

---

## 📋 Database Setup Required

Before running, ensure PostgreSQL is set up:

```bash
# macOS
brew services start postgresql@15
createdb rag_chatbot

# Linux
sudo systemctl start postgresql
sudo -u postgres createdb rag_chatbot

# Set environment variable
echo "DATABASE_URL=postgresql://localhost/rag_chatbot" >> .env
```

---

## 🔧 Key Configuration

**Environment Variables** (`.env`):
```
DATABASE_URL=postgresql://localhost/rag_chatbot
```

**Default User**:
- user_id: "default_user" (hardcoded for single-user mode)
- Created automatically by `notebook_manager.ensure_default_user()`

---

## 📝 Important Notes

1. **Migration NOT needed**: User will upload documents directly to notebooks
2. **Single-user mode**: Using hardcoded `user_id = "default_user"` for now
3. **Hybrid support exists**: Current code already handles `selected_notebooks` parameter in chat route
4. **Database schema ready**: All tables defined, just need to initialize

---

## 🔗 Related Files

**Backend (Complete)**:
- `rag_chatbot/core/db/db.py`
- `rag_chatbot/core/db/models.py`
- `rag_chatbot/core/notebook/notebook_manager.py`

**Frontend/API (Needs Work)**:
- `rag_chatbot/__main__.py` - Need db initialization
- `rag_chatbot/ui/web.py` - Need API routes
- `rag_chatbot/ui/ui.py` - Need UI updates

**Pipeline (Needs Updates)**:
- `rag_chatbot/core/ingestion/ingestion.py` - Add notebook_id to metadata
- `rag_chatbot/pipeline.py` - Use notebook filtering

**Migration (Complete - Not Using)**:
- `scripts/migrate_offerings_to_notebooks.py`
- `rag_chatbot/core/migration/offering_to_notebook_migration.py`
- `docs/OFFERING_TO_NOTEBOOK_MIGRATION.md`
- `docs/MIGRATION_SUMMARY.md`
