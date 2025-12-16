# Phase 5 & 6 Implementation Progress

**Date**: December 12, 2025
**Status**: IN PROGRESS - Phase 5 partially complete, Phase 6 pending

---

## Phase 5: UI Transformation

### ✅ COMPLETED ITEMS

1. **Sales-Specific Backend Code Removed**
   - ✅ Deleted `rag_chatbot/core/sales/` directory (query_classifier.py, offering_analyzer.py)
   - ✅ Deleted `rag_chatbot/core/metadata/` directory (MetadataManager)

### ⏳ PENDING ITEMS

2. **web.py Simplification** - CRITICAL (IN PROGRESS)

   **File**: `rag_chatbot/ui/web.py` (1093 lines)

   **Lines to Remove**:
   - Lines 14, 38-43: MetadataManager import and initialization
   - Lines 42-173: Document metadata file management methods
   - Lines 370, 405-409: Sales mode query selection logic
   - Lines 398-496: Image generation request detection and dual-approach generation
   - Lines 520-572: Upload endpoint with IT practice/offering metadata
   - Lines 796-1009: All sales/practice/offering metadata endpoints

   **Lines to Keep**:
   - Document upload/deletion (simplified - no metadata)
   - Chat endpoint (simplified - no sales mode)
   - Model management
   - Query logger endpoints (1011-1083)
   - Image generation endpoints (simplified)
   - Health check

   **Simplified web.py Structure** (target ~400 lines):
   ```python
   class FlaskChatbotUI:
       def __init__(self, pipeline, host, data_dir, upload_dir):
           self._pipeline = pipeline
           self._image_generator = ImageGenerator(pipeline._settings)
           # Remove: MetadataManager
           # Remove: Document metadata tracking

       # Simplified routes:
       @app.route("/") -> index page
       @app.route("/chat", POST) -> Simple RAG query (no sales mode)
       @app.route("/upload", POST) -> Upload without metadata
       @app.route("/clear", POST) -> Clear conversation
       @app.route("/reset", POST) -> Reset documents
       @app.route("/model", POST) -> Set model

       # Keep: Query logging endpoints
       @app.route("/api/usage-stats", GET)
       @app.route("/api/recent-queries", GET)
       @app.route("/api/model-pricing", GET)

       # Keep: Document management
       @app.route("/api/documents/list", GET)
       @app.route("/api/documents/<filename>", DELETE)

       # Keep: Image generation (simplified)
       @app.route("/generate-image", POST)
       @app.route("/image/<filename>", GET)

       # Remove: All /api/practices, /api/offerings, /api/metadata endpoints
   ```

3. **Pipeline Simplification** - REQUIRED

   **File**: `rag_chatbot/pipeline.py`

   **Changes Needed**:
   - Remove imports: `from .core.sales import QueryClassifier, OfferingAnalyzer`
   - Remove `query_sales_mode()` method entirely
   - Simplify `query()` method - remove offering filter logic
   - Remove `_query_classifier` and `_offering_analyzer` initialization
   - Keep: QueryLogger integration (already working)

4. **Template Updates** - MODERATE EFFORT

   **Files**:
   - `rag_chatbot/templates/index.html`
   - `rag_chatbot/templates/documents.html`

   **Changes Needed**:
   - Remove: IT Practice/Offering selection UI
   - Remove: Offering checkboxes
   - Simplify: Upload form (just file upload, no metadata)
   - Add: Usage statistics display section
   - Add: Model selector dropdown
   - Keep: Chat interface (already good)

   **New Sections to Add**:
   ```html
   <!-- Usage Statistics Card -->
   <div id="usage-stats">
     <h3>Usage Statistics</h3>
     <div>Total Queries: <span id="total-queries">0</span></div>
     <div>Total Tokens: <span id="total-tokens">0</span></div>
     <div>Est. Cost: $<span id="total-cost">0.00</span></div>
     <div>Avg Response Time: <span id="avg-response">0</span>ms</div>
   </div>

   <!-- Recent Queries List -->
   <div id="recent-queries">
     <h3>Recent Queries</h3>
     <ul id="query-list"></ul>
   </div>
   ```

5. **Notebook UI Addition** - NEW FEATURE (HIGH PRIORITY)

   **What's Needed**: Add notebook management UI to replace sales offerings UI

   **Backend Already Exists**:
   - ✅ `rag_chatbot/core/notebook/notebook_manager.py` (fully implemented)
   - ✅ `rag_chatbot/core/db/models.py` (Notebook, NotebookSource tables)

   **New API Endpoints Needed in web.py**:
   ```python
   @app.route("/api/notebooks", GET) -> List all notebooks
   @app.route("/api/notebooks", POST) -> Create notebook
   @app.route("/api/notebooks/<notebook_id>", GET) -> Get notebook details
   @app.route("/api/notebooks/<notebook_id>", DELETE) -> Delete notebook
   @app.route("/api/notebooks/<notebook_id>/switch", POST) -> Switch to notebook
   @app.route("/api/notebooks/<notebook_id>/documents", GET) -> Get notebook docs
   @app.route("/api/notebooks/<notebook_id>/documents", POST) -> Upload to notebook
   ```

   **New UI Components Needed**:
   - Notebook sidebar (left panel)
   - "Create Notebook" button
   - Active notebook indicator
   - Notebook switcher dropdown
   - Per-notebook document list

---

## Phase 6: Testing & Optimization

### ⏳ ALL PENDING

1. **Unit Tests** - NOT STARTED

   **Files to Create**:
   - `tests/test_notebook_manager.py` - Test notebook CRUD
   - `tests/test_conversation_store.py` - Test conversation persistence
   - `tests/test_query_logger.py` - Test usage tracking
   - `tests/test_web_api.py` - Test Flask endpoints

   **Coverage Target**: ≥80% for core modules

2. **Integration Tests** - NOT STARTED

   **Scenarios**:
   - Create notebook → Upload docs → Query → Switch notebook → Verify isolation
   - Upload → Query → Check query logger → Verify cost calculation
   - Conversation persistence across notebook switches
   - Document duplicate detection

   **File**: `tests/test_integration.py`

3. **Performance Optimization** - NOT STARTED

   **Areas to Profile**:
   - Query response time (target: <3s)
   - Memory usage (target: <500MB)
   - Database query optimization
   - Vector store query performance

   **Tools**: pytest-benchmark, memory_profiler

---

## Critical Path to Completion

### IMMEDIATE (Next 2-3 hours):

1. **Simplify web.py** (1-2 hours)
   - Remove sales endpoints
   - Simplify chat route
   - Keep query logger endpoints
   - Test basic functionality

2. **Simplify pipeline.py** (30 minutes)
   - Remove sales mode imports
   - Remove query_sales_mode method
   - Test queries work

3. **Update templates** (30 minutes)
   - Remove IT practice/offering UI
   - Add usage stats display
   - Test UI loads

### SHORT-TERM (Next 4-6 hours):

4. **Add Notebook API Endpoints** (2 hours)
   - Implement 7 new routes
   - Connect to NotebookManager
   - Test CRUD operations

5. **Add Notebook UI Components** (2-3 hours)
   - Create notebook sidebar
   - Add switcher UI
   - Connect to backend APIs

6. **Basic Testing** (1-2 hours)
   - Manual end-to-end testing
   - Fix critical bugs
   - Verify query logger works

### MEDIUM-TERM (Next 8-12 hours):

7. **Write Unit Tests** (4-6 hours)
   - Test all new components
   - Achieve ≥80% coverage
   - CI/CD integration

8. **Integration Testing** (2-3 hours)
   - Full workflow tests
   - Cross-notebook isolation
   - Conversation persistence

9. **Performance Optimization** (2-3 hours)
   - Profile bottlenecks
   - Optimize queries
   - Reduce memory usage

---

## What's Working RIGHT NOW

✅ Query Logger API endpoints functional at http://localhost:7860:
- `/api/usage-stats` - Returns usage statistics
- `/api/recent-queries` - Returns query history
- `/api/model-pricing` - Returns model pricing for 16 models

✅ Database infrastructure ready:
- PostgreSQL tables created
- NotebookManager implemented
- ConversationStore implemented

✅ Application running successfully:
- Flask server operational
- RAG pipeline working
- Conversation memory fixed

---

## Quick Start Guide for Next Session

### Option 1: Continue with web.py Simplification

```bash
# 1. Create backup
cp rag_chatbot/ui/web.py rag_chatbot/ui/web.py.backup

# 2. Create simplified web.py
# See "Simplified web.py Structure" section above

# 3. Test
./venv/bin/python -m rag_chatbot --host localhost --port 7860
curl http://localhost:7860/health
curl http://localhost:7860/api/usage-stats
```

### Option 2: Add Notebook Endpoints First

```python
# Add to web.py after line 1083 (after model-pricing endpoint):

@self._app.route("/api/notebooks", methods=["GET"])
def list_notebooks():
    """Get all notebooks for current user."""
    try:
        from .core.notebook import NotebookManager
        from .core.db import DatabaseManager

        db = DatabaseManager(database_url=os.getenv("DATABASE_URL"))
        notebook_mgr = NotebookManager(db_manager=db)

        notebooks = notebook_mgr.list_notebooks(user_id="default_user")
        return jsonify({"success": True, "notebooks": notebooks})
    except Exception as e:
        logger.error(f"Error listing notebooks: {e}")
        return jsonify({"success": False, "error": str(e)})

# Add remaining 6 endpoints similarly...
```

### Option 3: Focus on Testing First

```bash
# Create test structure
mkdir -p tests
touch tests/__init__.py
touch tests/test_query_logger.py

# Write basic test
pytest tests/test_query_logger.py -v
```

---

## Files Modified in This Session

### Deleted:
- `rag_chatbot/core/sales/` (entire directory)
- `rag_chatbot/core/metadata/` (entire directory)

### To Modify (Next):
- `rag_chatbot/ui/web.py` - Simplify (remove sales endpoints)
- `rag_chatbot/pipeline.py` - Remove sales mode
- `rag_chatbot/templates/index.html` - Update UI
- `rag_chatbot/templates/documents.html` - Simplify

### To Create (Next):
- `tests/test_notebook_manager.py`
- `tests/test_conversation_store.py`
- `tests/test_query_logger.py`
- `tests/test_web_api.py`
- `tests/test_integration.py`

---

## Estimated Remaining Effort

**Phase 5 Completion**: 6-8 hours
**Phase 6 Completion**: 8-12 hours
**Total**: 14-20 hours

**Priority Order**:
1. web.py simplification (blocking)
2. pipeline.py simplification (blocking)
3. Template updates (high visibility)
4. Notebook API endpoints (new feature)
5. Notebook UI (new feature)
6. Testing (quality assurance)
7. Optimization (performance)

---

## Success Criteria

### Phase 5 Complete When:
- ✅ All sales-specific code removed
- ✅ UI simplified (no IT practice/offering)
- ✅ Notebook management UI functional
- ✅ Usage statistics displayed in UI
- ✅ Application runs without errors

### Phase 6 Complete When:
- ✅ Unit test coverage ≥80%
- ✅ Integration tests pass
- ✅ Performance targets met (<3s queries, <500MB memory)
- ✅ No critical bugs
- ✅ Documentation updated

---

## Notes for Future Sessions

1. **Database Setup**: PostgreSQL must be running for full notebook functionality
   ```bash
   # macOS
   brew services start postgresql@15
   createdb rag_chatbot
   ```

2. **Environment Variables**: Ensure DATABASE_URL is set in .env:
   ```bash
   DATABASE_URL=postgresql://localhost/rag_chatbot
   ```

3. **Migrations**: Run Alembic migrations if database schema changes
   ```bash
   alembic upgrade head
   ```

4. **Testing**: Always test after major changes
   ```bash
   # Test API endpoints
   ./scripts/test_api.sh

   # Test UI
   open http://localhost:7860
   ```
