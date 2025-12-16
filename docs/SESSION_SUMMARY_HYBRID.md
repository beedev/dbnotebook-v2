# Hybrid Architecture Implementation - Session Summary

**Date**: December 12, 2025
**Status**: In Progress - Design Complete, Implementation Starting

---

## What Was Accomplished

### 1. User Decision: Hybrid Approach Confirmed ✅

User confirmed they want to **preserve sales features** while adding notebook management:
- Keep problem solving mode (offering bundle recommendations)
- Keep pitch generation (elevator pitch + use cases)
- Add notebook-based document organization
- Add persistent conversation history

### 2. Sales Directories Restored ✅

Restored deleted directories from git:
```bash
rag_chatbot/core/sales/
  - query_classifier.py
  - offering_analyzer.py
rag_chatbot/core/metadata/
  - metadata_manager.py
```

### 3. Comprehensive Hybrid Architecture Designed ✅

Created `/docs/HYBRID_ARCHITECTURE.md` with:

**Architecture Layers**:
1. **Notebook Layer** (Organization):
   - NotebookManager for CRUD
   - ConversationStore for persistent history
   - QueryLogger for observability
   - Document isolation by notebook_id

2. **Sales Intelligence Layer** (Analysis):
   - QueryClassifier (problem solving vs. pitch modes)
   - OfferingAnalyzer (bundle recommendations)
   - Works with notebook-based filtering

3. **RAG Retrieval Layer** (Execution):
   - ChromaDB with notebook metadata
   - Hybrid retrieval (BM25 + vector)
   - LLM with sales prompts

**Key Design Decisions**:
- Each notebook = one IT Practice or Offering
- MetadataManager replaced by NotebookManager
- Notebooks provide offering context automatically
- No manual metadata entry required

### 4. Implementation Plan Created ✅

**4 Steps**:
1. Modify Sales Components (offering_analyzer.py, query_classifier.py) - 2-3h
2. Update Pipeline (pipeline.py) - 1-2h
3. Update Web UI (web.py, templates) - 2-3h
4. Integration Testing - 1-2h

---

## Current Understanding

### OfferingAnalyzer.py Structure

**Current Implementation**:
- Takes pre-generated `offering_synopses` as input
- Scores each offering against problem description
- Returns top N offerings based on relevance scores
- Generates bundle strategy and implementation plan

**Hybrid Modification Needed**:
- Add `NotebookManager` dependency
- Query notebooks to generate synopses (or pipeline generates them)
- Replace `offering_names` with `notebook_ids` in returns
- Keep scoring and bundle generation logic intact

### Conversation History Solution

The hybrid approach solves the original conversation history issue:
- **Before**: In-memory patches, history lost on notebook switch
- **After**: ConversationStore with PostgreSQL persistence
- **Scoped**: Conversation history per notebook
- **Loading**: Automatic when switching notebooks

---

## Next Steps (Priority Order)

### Step 1: Modify OfferingAnalyzer ✅ (COMPLETED)

**File**: `rag_chatbot/core/sales/offering_analyzer.py`

**Changes Required**:
1. Add `NotebookManager` to `__init__`:
   ```python
   def __init__(self, llm: LLM, notebook_manager: NotebookManager):
       self._llm = llm
       self._notebook_manager = notebook_manager
   ```

2. Modify `analyze_problem()` signature:
   ```python
   def analyze_problem(
       self,
       problem_description: str,
       user_id: str = "default_user",  # NEW
       customer_name: Optional[str] = None,
       industry: Optional[str] = None,
       top_n: int = 3,
       min_score_threshold: float = 0.70
   ) -> Dict:
   ```

3. Replace offering synopses with notebook synopses:
   ```python
   # Get all notebooks for user
   notebooks = self._notebook_manager.list_notebooks(user_id)

   # Generate synopsis for each notebook by querying its documents
   notebook_synopses = {}
   for notebook in notebooks:
       synopsis = self._generate_notebook_synopsis(notebook["notebook_id"])
       notebook_synopses[notebook["notebook_id"]] = synopsis
   ```

4. Update returns to use `notebook_ids` instead of `offering_names`:
   ```python
   return {
       "recommended_notebooks": recommended_notebooks,  # Changed from recommended_offerings
       "notebook_scores": notebook_scores,
       "notebook_explanations": notebook_explanations,
       "bundle_strategy": bundle_strategy
   }
   ```

5. Add `_generate_notebook_synopsis()` method:
   ```python
   def _generate_notebook_synopsis(
       self,
       notebook_id: str,
       max_docs: int = 5
   ) -> str:
       """
       Generate synopsis from notebook documents.

       Strategy:
       1. Query top documents from notebook
       2. Summarize key capabilities and value propositions
       3. Return concise synopsis (200-300 words)
       """
   ```

### Step 2: Modify QueryClassifier

**File**: `rag_chatbot/core/sales/query_classifier.py`

**Changes Required**:
1. Add `selected_notebooks` parameter
2. Add conversation history awareness
3. Return `use_all_notebooks` flag

### Step 3: Update Pipeline

**File**: `rag_chatbot/pipeline.py`

**Changes Required**:
1. Add NotebookManager and ConversationStore initialization
2. Modify `query_sales_mode()` for notebook-based filtering
3. Load/save conversation history from ConversationStore
4. Remove MetadataManager dependency

### Step 4: Update Web UI

**File**: `rag_chatbot/ui/web.py`

**Changes Required**:
1. Update `/chat` endpoint with mode parameter
2. Route to appropriate pipeline method
3. Keep notebook management endpoints (already exist)
4. Keep query logger endpoints (already working)

**File**: `rag_chatbot/templates/index.html`

**Changes Required**:
1. Add notebook sidebar
2. Add sales mode toggle (normal, problem_solving, pitch)
3. Add notebook selection for pitch mode
4. Keep usage statistics display

---

## Files Modified So Far

### Created:
- `/docs/HYBRID_ARCHITECTURE.md` - Comprehensive design document
- `/docs/SESSION_SUMMARY_HYBRID.md` - This file

### Restored (from git):
- `rag_chatbot/core/sales/query_classifier.py`
- `rag_chatbot/core/sales/offering_analyzer.py`
- `rag_chatbot/core/sales/__init__.py`
- `rag_chatbot/core/metadata/metadata_manager.py`
- `rag_chatbot/core/metadata/__init__.py`

### To Modify (Next):
- `rag_chatbot/core/sales/offering_analyzer.py` ⏳
- `rag_chatbot/core/sales/query_classifier.py`
- `rag_chatbot/pipeline.py`
- `rag_chatbot/ui/web.py`
- `rag_chatbot/templates/index.html`

---

## Key Integration Points

### 1. Notebook → Offering Mapping

```python
# Each notebook represents an offering
notebook = {
    "notebook_id": str(uuid),
    "name": "AI Digital Engineering",  # Offering name
    "description": "AI and ML solutions for digital transformation"  # Offering description
}
```

### 2. Problem Solving Flow

```
User: "Need to modernize legacy systems"
       ↓
QueryClassifier → mode="problem_solving"
       ↓
OfferingAnalyzer:
  - Get all notebooks for user
  - Generate synopsis for each notebook
  - Score relevance to problem
  - Recommend top 3 notebooks
       ↓
Pipeline:
  - Query recommended notebooks only
  - Generate bundle pitch + use case
  - Stream formatted response
```

### 3. Pitch Flow

```
User: "Pitch Cloud Migration to ACME Corp"
       ↓
QueryClassifier → mode="pitch_specific"
       ↓
User selects notebook: "Cloud Migration"
       ↓
Pipeline:
  - Query selected notebook
  - Generate customer/industry-specific pitch
  - Stream formatted response
```

### 4. Conversation Persistence

```
On notebook switch:
  1. Save current conversation to PostgreSQL (ConversationStore)
  2. Load new notebook's conversation history
  3. Recreate engine with new notebook context
  4. Continue conversation seamlessly
```

---

## Database Infrastructure (Already Implemented)

From Phase 4, we have:
- **NotebookManager**: CRUD operations for notebooks
- **ConversationStore**: Persistent conversation history
- **QueryLogger**: Usage tracking and cost estimation
- **PostgreSQL**: Database with tables for notebooks, conversations, query logs

**Tables**:
```sql
notebooks (notebook_id, user_id, name, description, created_at, document_count)
notebook_sources (source_id, notebook_id, file_name, file_hash, upload_timestamp)
conversations (conversation_id, notebook_id, user_id, role, content, timestamp)
query_logs (log_id, notebook_id, user_id, query_text, model_name, tokens, timestamp)
```

---

## Testing Strategy

### Test Scenarios

**1. Problem Solving Mode**:
```
Query: "We need to modernize our legacy mainframe system"
Expected:
  - OfferingAnalyzer queries all notebooks
  - Recommends top 3 notebooks (e.g., "Cloud Migration", "AI Digital Engineering", "Automation")
  - Generates bundle strategy
  - Creates implementation plan
  - Streams formatted response with pitch
```

**2. Pitch Mode (Customer-Specific)**:
```
Query: "Pitch Cloud Migration to ACME Corp in manufacturing"
User Action: Select "Cloud Migration" notebook
Expected:
  - QueryClassifier detects pitch_specific mode
  - Query selected notebook only
  - Generate customer/industry-tailored pitch
  - Stream formatted response
```

**3. Normal Chat Mode**:
```
Query: "What are the benefits of cloud migration?"
Context: User is in "Cloud Migration" notebook
Expected:
  - Query current notebook
  - Normal RAG response (no sales formatting)
```

**4. Conversation Persistence**:
```
Action: Switch from "AI Digital Engineering" to "Cloud Migration" notebook
Expected:
  - Save current conversation to PostgreSQL
  - Load "Cloud Migration" conversation history
  - Context switches seamlessly
  - No conversation loss
```

---

## Timeline Estimate

**Total Remaining**: 6-9 hours

- **Step 1**: Modify Sales Components (2-3h)
  - OfferingAnalyzer notebook integration (1-2h)
  - QueryClassifier enhancements (1h)

- **Step 2**: Update Pipeline (1-2h)
  - Add NotebookManager/ConversationStore (30min)
  - Modify query_sales_mode() (30min-1h)
  - Integration testing (30min)

- **Step 3**: Update Web UI (2-3h)
  - Modify /chat endpoint (1h)
  - Update templates (1-2h)

- **Step 4**: Integration Testing (1-2h)
  - End-to-end testing (1h)
  - Bug fixes (1h)

**Completion Target**: Within 2 working days

---

## Success Criteria

### Functional:
- ✅ Sales features preserved (problem solving, pitch generation)
- ✅ Notebook organization working
- ✅ Conversation history persistent
- ✅ Mode switching seamless

### Technical:
- ✅ OfferingAnalyzer uses NotebookManager
- ✅ Pipeline integrates ConversationStore
- ✅ No MetadataManager dependencies
- ✅ Clean error handling

### Performance:
- ✅ Response time < 3s
- ✅ Conversation history loads < 500ms
- ✅ No memory leaks

---

## Open Questions / Decisions Made

### Q: Should we pre-generate notebook synopses or generate on-demand?

**Decision**: Generate on-demand but cache for session
- **Rationale**: Simpler implementation, no stale data
- **Optimization**: Add caching if performance becomes an issue
- **Fallback**: Use notebook description if synopsis generation fails

### Q: How to handle notebooks without documents?

**Decision**: Skip empty notebooks in offering analysis
- **Rationale**: Can't generate meaningful synopsis without documents
- **UI**: Show warning when creating empty notebooks
- **Validation**: Require at least 1 document before using in sales mode

### Q: Should MetadataManager be deleted or kept?

**Decision**: Keep for now, mark as deprecated
- **Rationale**: May be useful for future features
- **Action**: Remove imports but don't delete files
- **Cleanup**: Delete in future refactoring sprint

---

## Notes for Next Session

1. **Continue with OfferingAnalyzer modification**
   - Implement notebook synopsis generation
   - Test with NotebookManager integration
   - Update return types

2. **Watch for token limits**
   - May need to break into multiple sessions
   - Save progress frequently
   - Use incremental testing

3. **Background processes cleanup**
   - Many start.sh processes still running
   - Run `pkill -9 -f "start.sh"` at start of session

4. **Git commit strategy**
   - Commit after each major component modification
   - Create feature branch: `feature/hybrid-architecture`
   - Merge to main after all testing complete

---

## Reference Documents

- `/docs/HYBRID_ARCHITECTURE.md` - Full architectural design
- `/docs/PHASE_5_6_PROGRESS.md` - Original transformation plan (now superseded by hybrid approach)
- `/Users/bharath/.claude/plans/modular-crunching-pancake.md` - Original plan file with sales enablement system
