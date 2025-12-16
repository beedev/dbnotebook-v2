# Hybrid Architecture: Notebooks + Sales Intelligence

**Date**: December 12, 2025
**Status**: Design Phase
**Approach**: Best of Both Worlds

---

## Executive Summary

This hybrid architecture combines:
- **Notebook Management** (organization, conversation persistence) from Phase 4
- **Sales Intelligence** (problem solving, pitch generation) from original sales system

**Result**: A chatbot that organizes documents in notebooks while providing intelligent sales analysis and pitch generation capabilities.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (Flask)                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Notebook        │  │  Sales Mode      │  │  Document      │ │
│  │ Management UI   │  │  Toggle          │  │  Upload UI     │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        HYBRID PIPELINE                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              NOTEBOOK LAYER (Organization)                │  │
│  │  • NotebookManager (CRUD operations)                      │  │
│  │  • ConversationStore (persistent history per notebook)    │  │
│  │  • QueryLogger (usage tracking)                           │  │
│  │  • Document isolation by notebook_id                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                 │                                │
│                                 ▼                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          SALES INTELLIGENCE LAYER (Analysis)              │  │
│  │  • QueryClassifier (problem solving vs. pitch)            │  │
│  │  • OfferingAnalyzer (offering bundle recommendation)      │  │
│  │  • PitchGenerator (elevator pitch + use case generation)  │  │
│  │  • Works with notebook-based document filtering          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                 │                                │
│                                 ▼                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          RAG RETRIEVAL LAYER (Execution)                  │  │
│  │  • VectorStore (ChromaDB with notebook_id metadata)       │  │
│  │  • Hybrid Retrieval (BM25 + vector with reranking)       │  │
│  │  • LLM (Ollama/OpenAI with sales prompts)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components Integration

### 1. Notebooks as Offering Containers

**Concept**: Each notebook represents an IT Practice or Offering.

**Notebook Metadata**:
```python
{
    "notebook_id": str(uuid),
    "user_id": str(uuid),
    "name": str,  # e.g., "AI Digital Engineering", "Cloud Migration", "Automation"
    "description": str,  # Offering description
    "offering_type": str,  # "it_practice" or "offering"
    "created_at": datetime,
    "document_count": int
}
```

**Benefits**:
- Clean separation of concerns (each offering = one notebook)
- Persistent conversation history per offering
- Easy document management (upload/delete per notebook)
- No need for complex metadata system

### 2. Sales Modes with Notebooks

**Problem Solving Mode**:
```python
User Query: "We need to modernize our legacy mainframe system"

Workflow:
1. QueryClassifier detects "problem_solving" mode
2. OfferingAnalyzer.analyze_problem():
   - Queries ALL notebooks (all offerings)
   - Scores relevance of each offering
   - Recommends top 5 offerings as bundle
3. Retrieval:
   - Use recommended notebook IDs as filter
   - Query documents from recommended notebooks only
4. PitchGenerator.generate_pitch():
   - Creates elevator pitch for bundle
   - Generates use case with implementation approach
5. Stream response with formatted pitch
```

**Pitch Mode** (Customer/Domain-Specific):
```python
User Query: "Pitch Cloud Migration to ACME Corp in manufacturing"

Workflow:
1. QueryClassifier detects "pitch_specific" mode
2. User selects notebook (e.g., "Cloud Migration")
3. Retrieval:
   - Query documents from selected notebook only
   - Extract offering context
4. PitchGenerator.generate_pitch():
   - Creates customer-specific elevator pitch
   - Generates use case tailored to ACME Corp + manufacturing
   - Includes implementation approach
5. Stream formatted pitch response
```

**Pitch Mode** (Generic):
```python
User Query: "Pitch Automation to healthcare industry"

Workflow:
1. QueryClassifier detects "pitch_generic" mode
2. User selects notebook (e.g., "Automation")
3. Retrieval:
   - Query documents from selected notebook
   - Extract offering capabilities
4. PitchGenerator.generate_pitch():
   - Creates industry-specific pitch (healthcare focus)
   - Generates use case with healthcare examples
5. Stream formatted pitch response
```

### 3. Persistent Conversation History

**Implementation** (already done in Phase 4):
```python
class ConversationStore:
    def save_message(
        self,
        notebook_id: str,
        user_id: str,
        role: str,
        content: str
    ) -> str:
        """Save message to PostgreSQL conversations table."""

    def get_conversation_history(
        self,
        notebook_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Load conversation history for notebook."""
```

**Integration**:
- Conversations scoped to notebook_id
- Load history when switching notebooks
- Save after each query response
- Solves original conversation history issue

### 4. Document Management

**Upload with Notebook Selection**:
```python
@app.route('/notebooks/<notebook_id>/documents', methods=['POST'])
def upload_documents(notebook_id):
    """
    Upload documents to specific notebook (offering).

    Workflow:
    1. Validate notebook exists
    2. Process uploaded files
    3. Store nodes with metadata:
       {
           "notebook_id": notebook_id,
           "file_name": file_name,
           "file_hash": hash_value,
           "source_id": source_id
       }
    4. Update notebook document_count
    5. Return success
    """
```

**Benefits**:
- No manual metadata entry (practice/offering dropdown)
- Notebook provides context automatically
- Duplicate detection by file_hash per notebook
- Clean document isolation

---

## Modified Sales Intelligence Components

### Modified QueryClassifier

**Original**: Classified queries based on keywords only.

**Enhanced**: Includes notebook context.

```python
class QueryClassifier:
    def classify(
        self,
        query: str,
        selected_notebooks: Optional[List[str]] = None,
        conversation_history: Optional[List] = None
    ) -> Dict:
        """
        Classify query mode with notebook awareness.

        Returns:
        {
            "mode": "problem_solving" | "pitch_specific" | "pitch_generic",
            "customer_name": str | None,
            "industry": str | None,
            "problem_description": str | None,
            "use_all_notebooks": bool  # True for problem solving
        }
        """
```

**Changes**:
- Add `selected_notebooks` parameter for pitch mode
- Add conversation history awareness for follow-up detection
- Return `use_all_notebooks` flag for retrieval filtering

### Modified OfferingAnalyzer

**Original**: Analyzed offerings from metadata system.

**Enhanced**: Analyzes offerings from notebooks.

```python
class OfferingAnalyzer:
    def __init__(self, notebook_manager: NotebookManager):
        self._notebook_manager = notebook_manager

    def analyze_problem(
        self,
        problem_description: str,
        customer_name: Optional[str] = None,
        industry: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Dict:
        """
        Analyze problem and recommend offering bundle.

        Workflow:
        1. Get all notebooks for user
        2. Query each notebook with problem context
        3. Score relevance of each offering
        4. Recommend top 5 as bundle
        5. Generate implementation approach

        Returns:
        {
            "recommended_notebooks": [notebook_id_1, ...],  # Top 5
            "relevance_scores": {notebook_id: score},
            "bundle_strategy": str,
            "implementation_approach": str
        }
        """
```

**Changes**:
- Replace `offering_ids` with `notebook_ids`
- Use `NotebookManager` instead of `MetadataManager`
- Query notebooks instead of metadata-filtered documents
- Return notebook IDs instead of offering IDs

### Modified Pipeline

**Original**: `query_sales_mode()` used metadata filters.

**Enhanced**: Uses notebook-based filtering.

```python
class LocalRAGPipeline:
    def query_sales_mode(
        self,
        message: str,
        selected_notebooks: Optional[List[str]] = None,
        current_notebook_id: Optional[str] = None,
        chatbot: List = []
    ) -> StreamingAgentChatResponse:
        """
        Query in sales mode with notebook-based filtering.

        Workflow:
        1. Classify query (problem solving vs. pitch)

        2a. PROBLEM SOLVING:
            - OfferingAnalyzer.analyze_problem() → recommended_notebooks
            - Retrieve from recommended notebooks
            - Generate bundle pitch + use case

        2b. PITCH MODE:
            - Use selected_notebooks OR current_notebook_id
            - Retrieve from selected notebooks
            - Generate customer/industry-specific pitch

        3. Load conversation history from ConversationStore

        4. Stream response with pitch formatting

        5. Save conversation to ConversationStore
        """
```

**Changes**:
- Add `current_notebook_id` parameter for context
- Use notebook-based retrieval instead of metadata filters
- Integrate with ConversationStore for persistent history
- Preserve conversation context across queries

---

## UI Changes for Hybrid System

### New Notebook Management UI

**Notebook Sidebar** (Left Panel):
```html
<div id="notebook-sidebar">
  <!-- Create Notebook Button -->
  <button onclick="createNotebook()">+ New Notebook (Offering)</button>

  <!-- Notebook List -->
  <div id="notebook-list">
    <div class="notebook-item active" data-id="uuid1">
      <span class="notebook-name">AI Digital Engineering</span>
      <span class="doc-count">12 docs</span>
    </div>
    <div class="notebook-item" data-id="uuid2">
      <span class="notebook-name">Cloud Migration</span>
      <span class="doc-count">8 docs</span>
    </div>
    <!-- ... more notebooks ... -->
  </div>
</div>
```

**Document Upload** (Enhanced):
```html
<div id="upload-section">
  <h3>Upload to: <span id="current-notebook">AI Digital Engineering</span></h3>
  <input type="file" multiple id="file-upload">
  <button onclick="uploadToNotebook()">Upload Documents</button>
  <div id="document-list">
    <!-- List of documents in current notebook -->
  </div>
</div>
```

### Sales Mode UI

**Mode Toggle**:
```html
<div id="sales-mode-toggle">
  <label>
    <input type="radio" name="chat-mode" value="normal" checked>
    Normal Chat
  </label>
  <label>
    <input type="radio" name="chat-mode" value="problem_solving">
    Problem Solving (All Offerings)
  </label>
  <label>
    <input type="radio" name="chat-mode" value="pitch">
    Pitch (Selected Offering)
  </label>
</div>
```

**Notebook Selection for Pitch Mode**:
```html
<div id="pitch-notebook-selection" style="display:none;">
  <h4>Select Offering for Pitch:</h4>
  <select id="pitch-notebook-select">
    <option value="uuid1">AI Digital Engineering</option>
    <option value="uuid2">Cloud Migration</option>
    <!-- ... -->
  </select>
</div>
```

**Usage Statistics** (Already Working):
```html
<div id="usage-stats">
  <h3>Usage Statistics</h3>
  <div>Total Queries: <span id="total-queries">0</span></div>
  <div>Total Tokens: <span id="total-tokens">0</span></div>
  <div>Est. Cost: $<span id="total-cost">0.00</span></div>
  <div>Avg Response Time: <span id="avg-response">0</span>ms</div>
</div>
```

---

## API Endpoints (web.py)

### Notebook Management Endpoints (Already Implemented in Phase 4)

```python
@app.route('/api/notebooks', methods=['GET'])
def list_notebooks():
    """Get all notebooks for user."""

@app.route('/api/notebooks', methods=['POST'])
def create_notebook():
    """Create new notebook (offering)."""

@app.route('/api/notebooks/<notebook_id>', methods=['DELETE'])
def delete_notebook(notebook_id):
    """Delete notebook and all documents."""

@app.route('/api/notebooks/<notebook_id>/switch', methods=['POST'])
def switch_notebook(notebook_id):
    """Switch to different notebook, load conversation history."""

@app.route('/api/notebooks/<notebook_id>/documents', methods=['GET'])
def get_notebook_documents(notebook_id):
    """List documents in notebook."""

@app.route('/api/notebooks/<notebook_id>/documents', methods=['POST'])
def upload_documents(notebook_id):
    """Upload documents to notebook."""
```

### Sales Mode Endpoints (Keep from Original)

```python
@app.route('/chat', methods=['POST'])
def chat():
    """
    Unified chat endpoint.

    Request:
    {
        "message": str,
        "mode": "normal" | "problem_solving" | "pitch",
        "selected_notebooks": [notebook_id_1, ...] (for pitch mode),
        "current_notebook_id": notebook_id (for context),
        "chatbot": [...]  # Conversation history
    }

    Response:
    - Streaming response for all modes
    - Problem solving: Formatted with bundle recommendations
    - Pitch: Formatted with elevator pitch + use case
    """
    mode = request.json.get('mode', 'normal')

    if mode == 'normal':
        # Use normal pipeline query
        response = pipeline.query(message, chatbot, current_notebook_id)
    else:
        # Use sales mode pipeline
        response = pipeline.query_sales_mode(
            message,
            selected_notebooks=selected_notebooks,
            current_notebook_id=current_notebook_id,
            chatbot=chatbot
        )

    # Stream response
    return stream_response(response)
```

### Query Logger Endpoints (Keep from Phase 4)

```python
@app.route('/api/usage-stats', methods=['GET'])
def get_usage_stats():
    """Get usage statistics."""

@app.route('/api/recent-queries', methods=['GET'])
def get_recent_queries():
    """Get recent query history."""

@app.route('/api/model-pricing', methods=['GET'])
def get_model_pricing():
    """Get model pricing information."""
```

---

## Implementation Plan

### Step 1: Modify Sales Intelligence Components (2-3 hours)

**File**: `rag_chatbot/core/sales/offering_analyzer.py`

**Changes**:
1. Add `NotebookManager` dependency
2. Replace `MetadataManager` calls with `NotebookManager` calls
3. Replace `offering_ids` with `notebook_ids`
4. Update `analyze_problem()` to query notebooks instead of metadata-filtered documents

**File**: `rag_chatbot/core/sales/query_classifier.py`

**Changes**:
1. Add `selected_notebooks` parameter to `classify()`
2. Add conversation history awareness
3. Return `use_all_notebooks` flag

### Step 2: Modify Pipeline (1-2 hours)

**File**: `rag_chatbot/pipeline.py`

**Changes**:
1. Add `NotebookManager` and `ConversationStore` initialization
2. Modify `query_sales_mode()`:
   - Add `current_notebook_id` parameter
   - Use notebook-based filtering instead of metadata
   - Load conversation history from ConversationStore
   - Save conversation after response
3. Remove `MetadataManager` dependency

### Step 3: Update Web UI (2-3 hours)

**File**: `rag_chatbot/ui/web.py`

**Changes**:
1. Keep notebook management endpoints (already implemented)
2. Update `/chat` endpoint:
   - Add `mode` parameter (normal, problem_solving, pitch)
   - Route to appropriate pipeline method
   - Pass notebook context
3. Keep query logger endpoints (already working)
4. Remove old metadata endpoints (if any)

**File**: `rag_chatbot/templates/index.html`

**Changes**:
1. Add notebook sidebar UI
2. Add sales mode toggle
3. Add notebook selection for pitch mode
4. Keep usage statistics display

### Step 4: Integration Testing (1-2 hours)

**Test Scenarios**:
1. **Problem Solving Mode**:
   - Query: "Need to modernize legacy systems"
   - Verify: Analyzes all notebooks, recommends bundle, generates pitch

2. **Pitch Mode (Customer-Specific)**:
   - Query: "Pitch Cloud Migration to ACME Corp in manufacturing"
   - Verify: Queries selected notebook, generates customer/industry pitch

3. **Normal Mode**:
   - Query: "What are the benefits of automation?"
   - Verify: Queries current notebook, normal RAG response

4. **Conversation Persistence**:
   - Query 1: "Tell me about AI capabilities"
   - Query 2: "Can you provide more details?"
   - Verify: Follow-up references previous query, history preserved

5. **Notebook Switching**:
   - Switch from "AI Digital Engineering" to "Cloud Migration"
   - Verify: Conversation history loads correctly, context switches

---

## Migration from Current State

### What Stays

1. **Notebook Infrastructure** (Phase 4):
   - NotebookManager
   - ConversationStore
   - QueryLogger
   - Database models

2. **Sales Intelligence** (Restored):
   - QueryClassifier
   - OfferingAnalyzer
   - PitchGenerator (if exists, else integrate into pipeline)

3. **RAG Pipeline**:
   - VectorStore with ChromaDB
   - Hybrid retrieval
   - LLM integration

### What Changes

1. **MetadataManager** → **NotebookManager**:
   - Replace metadata filtering with notebook filtering
   - Remove IT Practice/Offering manual metadata entry
   - Use notebooks as offering containers

2. **Pipeline**:
   - Add notebook context to all queries
   - Integrate ConversationStore for persistent history
   - Modify `query_sales_mode()` for notebook-based filtering

3. **UI**:
   - Add notebook management sidebar
   - Add sales mode toggle
   - Remove metadata entry forms

### What's Removed

1. **MetadataManager** (replaced by NotebookManager)
2. **Document metadata file management** (replaced by database)
3. **Manual IT Practice/Offering selection on upload** (use notebooks)

---

## Benefits of Hybrid Approach

### Technical Benefits

1. **Clean Separation of Concerns**:
   - Notebooks = Organization layer
   - Sales Intelligence = Analysis layer
   - RAG = Execution layer

2. **Persistent Conversation History**:
   - Solves original conversation memory issue
   - Scoped to notebooks for context
   - No more in-memory patches

3. **Scalable Architecture**:
   - Easy to add new offerings (create new notebook)
   - Clean document isolation
   - Database-backed persistence

### User Experience Benefits

1. **Sales Features Preserved**:
   - Problem solving mode with offering bundle recommendations
   - Pitch generation (elevator pitch + use case)
   - Customer/industry-specific pitches

2. **Better Organization**:
   - Notebooks provide clear offering boundaries
   - Easy document management per offering
   - Clean conversation history per offering

3. **Flexibility**:
   - Normal chat mode for general queries
   - Problem solving mode for recommendation
   - Pitch mode for sales presentations

---

## Success Criteria

### Functional Requirements

- ✅ Users can create notebooks for different offerings
- ✅ Users can upload documents to specific notebooks
- ✅ Problem solving mode recommends offering bundles
- ✅ Pitch mode generates customer-specific pitches
- ✅ Conversation history persists across sessions
- ✅ Conversations scoped to notebooks
- ✅ Normal chat mode works within notebook context

### Technical Requirements

- ✅ QueryClassifier works with notebook context
- ✅ OfferingAnalyzer uses NotebookManager
- ✅ Pipeline integrates ConversationStore
- ✅ No metadata system dependencies
- ✅ All Phase 4 infrastructure utilized

### Quality Requirements

- ✅ Response time < 3s for all modes
- ✅ Conversation history loads < 500ms
- ✅ No memory leaks or context loss
- ✅ Clean error handling
- ✅ Comprehensive logging

---

## Next Steps

1. **Complete Design** ✅
2. **Modify Sales Components** (offering_analyzer.py, query_classifier.py)
3. **Update Pipeline** (pipeline.py)
4. **Update Web UI** (web.py, templates)
5. **Integration Testing**
6. **Phase 6: Unit Tests & Optimization**

---

## Timeline Estimate

**Total**: 6-9 hours

- Step 1: Modify Sales Components (2-3h)
- Step 2: Modify Pipeline (1-2h)
- Step 3: Update Web UI (2-3h)
- Step 4: Integration Testing (1-2h)
- Phase 6: Testing & Optimization (4-6h)

**Completion Target**: Within 2 working days
