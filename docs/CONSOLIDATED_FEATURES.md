# DBNotebook: Consolidated Feature List for Parallel Development

**Generated**: 2025-12-27
**Status**: Ready for Wave Execution

---

## Overview

This document consolidates UX Phase 3-4 agentic features with architecture P0-P3 fixes into a unified feature list organized for parallel agent development using the Wave execution model.

---

## Wave Execution Model

```
WAVE 1 (Parallel - No Dependencies)
├── Agent A: Frontend Context System     → NEW FILES (zero conflict)
├── Agent B: Backend Service Interfaces  → NEW FILES (zero conflict)
└── Agent C: Critical Pipeline Fix       → ISOLATED (single file)

WAVE 2 (Parallel - Depends on Wave 1)
├── Agent A: Frontend Hooks Refactor     → EXISTING (isolated)
├── Agent B: Service Layer Implementation → NEW FILES (zero conflict)
└── Agent C: Vector Store Interface      → NEW FILES (zero conflict)

WAVE 3 (Parallel - Depends on Wave 2)
├── Agent A: Component Context Wiring    → EXISTING (frontend isolated)
├── Agent B: Route Refactoring           → EXISTING (backend isolated)
└── Agent C: Agentic Feature Foundation  → NEW FILES (data layer)

WAVE 4 (Parallel - Depends on Wave 3)
├── Agent A: Agentic UI Components       → NEW FILES (frontend)
├── Agent B: Agentic Services            → NEW FILES (backend)
└── Agent C: Advanced Query Features     → EXISTING (pipeline)
```

---

## Wave 1: Foundation Layer (No Dependencies)

### Agent A: Frontend Context System
**Priority**: P2 | **Effort**: 4-6h | **Risk**: Low

**Files to Create**:
```
frontend/src/contexts/
├── NotebookContext.tsx     (NEW)
├── ChatContext.tsx         (NEW)
├── DocumentContext.tsx     (NEW)
└── index.ts               (NEW)
```

**Tasks**:
- [ ] Create NotebookContext with notebooks, selectedNotebook, CRUD operations
- [ ] Create ChatContext with messages, streaming state, model selection
- [ ] Create DocumentContext with documents, upload/delete/toggle operations
- [ ] Export all contexts from index.ts

**Acceptance Criteria**:
- All contexts have proper TypeScript types
- Context providers wrap App component
- No prop drilling for notebook/chat/document state

---

### Agent B: Backend Service Interfaces
**Priority**: P1 | **Effort**: 2-4h | **Risk**: Low

**Files to Create**:
```
dbnotebook/core/interfaces/
├── services.py             (NEW) - IChatService, IImageService, IDocumentService
└── __init__.py             (UPDATE)

dbnotebook/core/services/
├── __init__.py             (NEW)
└── base.py                 (NEW) - Base service class
```

**Tasks**:
- [ ] Define IChatService ABC (stream_chat, get_context, set_mode)
- [ ] Define IImageService ABC (generate, list_providers)
- [ ] Define IDocumentService ABC (upload, delete, toggle, list)
- [ ] Create base service class with common patterns

**Acceptance Criteria**:
- All interfaces use ABC with abstractmethod decorators
- Type hints for all parameters and return values
- Docstrings for all methods

---

### Agent C: Critical Pipeline Fix
**Priority**: P0 | **Effort**: 2-4h | **Risk**: Medium

**Files to Modify**:
```
dbnotebook/pipeline.py      (MODIFY) - lines 928, 971, 1001
```

**Tasks**:
- [ ] Initialize `_query_classifier` in pipeline __init__ or lazy load
- [ ] Initialize `_offering_analyzer` in pipeline __init__ or lazy load
- [ ] Add fallback behavior if classifiers unavailable
- [ ] Add tests for classifier initialization

**Acceptance Criteria**:
- No runtime crashes when using query classification
- Graceful fallback when classifiers not available
- Tests pass for all query types

---

## Wave 2: Service Implementation (Depends on Wave 1)

### Agent A: Frontend Hooks Refactor
**Priority**: P2 | **Effort**: 6-8h | **Risk**: Low

**Files to Modify**:
```
frontend/src/hooks/
├── useNotebooks.ts         (MODIFY) - use NotebookContext
├── useChat.ts              (MODIFY) - use ChatContext
└── useWebSearch.ts         (NEW) - P3 item
```

**Tasks**:
- [ ] Refactor useNotebooks to use NotebookContext
- [ ] Refactor useChat to use ChatContext
- [ ] Create useWebSearch hook (extract from WebSearchPanel)
- [ ] Ensure hooks remain backward compatible

**Acceptance Criteria**:
- All hooks work with new context system
- No breaking changes to existing components
- useWebSearch encapsulates all web search logic

---

### Agent B: Service Layer Implementation
**Priority**: P1 | **Effort**: 20-30h | **Risk**: Medium

**Files to Create**:
```
dbnotebook/core/services/
├── chat_service.py         (NEW)
├── image_service.py        (NEW)
├── document_service.py     (NEW)
└── insight_service.py      (NEW) - For agentic features
```

**Tasks**:
- [ ] Implement ChatService (delegate from web.py /chat route)
- [ ] Implement ImageService (delegate from web.py /image routes)
- [ ] Implement DocumentService (delegate from web.py /documents routes)
- [ ] Implement InsightService (foundation for proactive insights)

**Acceptance Criteria**:
- Services implement interfaces from Wave 1
- Routes become thin wrappers around services
- All existing functionality preserved

---

### Agent C: Vector Store Interface
**Priority**: P2 | **Effort**: 8-12h | **Risk**: Low

**Files to Create/Modify**:
```
dbnotebook/core/vector_store/
├── base.py                 (NEW) - IVectorStore ABC
├── pg_vector_store.py      (MODIFY) - implement interface
└── __init__.py             (MODIFY) - export interface
```

**Tasks**:
- [ ] Create IVectorStore ABC with store/query/delete methods
- [ ] Consolidate connection pools (P1: currently dual pools)
- [ ] Implement IVectorStore in PGVectorStore
- [ ] Add factory function for vector store creation

**Acceptance Criteria**:
- Single connection pool for all database operations
- PGVectorStore implements IVectorStore interface
- Can swap vector store implementations easily

---

## Wave 3: Integration & Agentic Foundation (Depends on Wave 2)

### Agent A: Component Context Wiring
**Priority**: P2 | **Effort**: 8-10h | **Risk**: Medium

**Files to Modify**:
```
frontend/src/App.tsx                    (MODIFY)
frontend/src/components/Sidebar/        (MODIFY multiple)
frontend/src/components/Chat/           (MODIFY multiple)
```

**Tasks**:
- [ ] Wrap App with context providers
- [ ] Refactor Sidebar to use contexts (reduce 24+ props)
- [ ] Refactor ChatArea to use contexts
- [ ] Update all child components

**Acceptance Criteria**:
- Sidebar receives <5 props (down from 24+)
- All components use useContext hooks
- No functionality regression

---

### Agent B: Route Refactoring
**Priority**: P1 | **Effort**: 10-15h | **Risk**: Medium

**Files to Modify**:
```
dbnotebook/ui/web.py        (MODIFY) - refactor routes to use services
```

**Tasks**:
- [ ] Refactor /chat route to use ChatService (currently 258 lines!)
- [ ] Refactor /image routes to use ImageService
- [ ] Refactor /documents routes to use DocumentService
- [ ] Remove direct pipeline access from routes

**Acceptance Criteria**:
- Routes are <50 lines each
- All business logic in services
- No direct _pipeline access from routes

---

### Agent C: Agentic Feature Foundation
**Priority**: Phase 3 | **Effort**: 15-20h | **Risk**: Low

**Files to Create**:
```
dbnotebook/core/agents/
├── __init__.py             (NEW)
├── base.py                 (NEW) - BaseAgent ABC
├── query_analyzer.py       (NEW) - Query intent analysis
└── document_analyzer.py    (NEW) - Document gap detection
```

**API Endpoints**:
```
POST /api/chat/suggest-sources      (NEW)
POST /api/documents/analyze         (NEW)
GET  /api/conversations/summary     (NEW)
POST /api/query/refine              (NEW)
```

**Tasks**:
- [ ] Create BaseAgent ABC with analyze/suggest/execute methods
- [ ] Implement QueryAnalyzer for intent classification
- [ ] Implement DocumentAnalyzer for gap detection
- [ ] Add API endpoints for agent interactions

**Acceptance Criteria**:
- Agents are stateless and composable
- API endpoints return structured suggestions
- Foundation supports all Phase 3-4 agentic features

---

## Wave 4: Agentic Features (Depends on Wave 3)

### Agent A: Agentic UI Components
**Priority**: Phase 3 | **Effort**: 15-20h | **Risk**: Low

**Files to Create**:
```
frontend/src/components/Agentic/
├── SuggestionCard.tsx      (NEW) - Proactive suggestions UI
├── QueryRefinement.tsx     (NEW) - Query improvement UI
├── InsightPanel.tsx        (NEW) - Document insights UI
├── ConversationResume.tsx  (NEW) - Session continuity UI
└── index.ts                (NEW)
```

**Tasks**:
- [ ] Create SuggestionCard for smart document suggestions
- [ ] Create QueryRefinement for query improvement prompts
- [ ] Create InsightPanel for proactive insights display
- [ ] Create ConversationResume for session continuity
- [ ] Integrate components into ChatArea

**Acceptance Criteria**:
- Components follow existing design system
- Accessible and responsive
- Smooth animations for suggestions

---

### Agent B: Agentic Services
**Priority**: Phase 3-4 | **Effort**: 25-30h | **Risk**: Medium

**Files to Create**:
```
dbnotebook/core/services/
├── suggestion_service.py   (NEW) - Smart document suggestions
├── refinement_service.py   (NEW) - Query refinement
├── continuity_service.py   (NEW) - Conversation continuity
└── organization_service.py (NEW) - Auto-notebook organization
```

**Tasks**:
- [ ] Implement SuggestionService (4.1: Smart document suggestions)
- [ ] Implement RefinementService (4.6: Smart query refinement)
- [ ] Implement ContinuityService (4.3: Conversation continuity)
- [ ] Implement OrganizationService (4.2: Auto-notebook organization)

**Acceptance Criteria**:
- Services integrate with existing RAG pipeline
- Suggestions are context-aware and relevant
- Session summaries are accurate and useful

---

### Agent C: Advanced Query Features
**Priority**: Phase 4 | **Effort**: 20-25h | **Risk**: Medium

**Files to Modify/Create**:
```
dbnotebook/pipeline.py              (MODIFY) - multi-notebook support
dbnotebook/core/retriever.py        (MODIFY) - cross-notebook retrieval
dbnotebook/core/services/
└── multi_notebook_service.py       (NEW)
```

**Tasks**:
- [ ] Add multi-notebook query support to pipeline
- [ ] Implement cross-notebook embedding search
- [ ] Add source attribution per notebook
- [ ] Implement intelligent source recommendations (4.4)

**Acceptance Criteria**:
- Queries can span multiple notebooks
- Results clearly indicate source notebook
- Recommendations improve query relevance

---

## File Ownership Matrix

| File/Directory | Wave | Agent | Conflicts With |
|----------------|------|-------|----------------|
| `frontend/src/contexts/` | W1 | A | None (new) |
| `dbnotebook/core/interfaces/services.py` | W1 | B | None (new) |
| `dbnotebook/pipeline.py` (fix) | W1 | C | None (isolated) |
| `frontend/src/hooks/useWebSearch.ts` | W2 | A | None (new) |
| `dbnotebook/core/services/chat_service.py` | W2 | B | None (new) |
| `dbnotebook/core/vector_store/base.py` | W2 | C | None (new) |
| `frontend/src/App.tsx` | W3 | A | None (isolated) |
| `dbnotebook/ui/web.py` | W3 | B | None (isolated) |
| `dbnotebook/core/agents/` | W3 | C | None (new) |
| `frontend/src/components/Agentic/` | W4 | A | None (new) |
| `dbnotebook/core/services/*_service.py` | W4 | B | None (new) |
| `dbnotebook/pipeline.py` (multi-nb) | W4 | C | None (isolated) |

---

## Verification Gates

### After Wave 1:
```bash
# No uncommitted conflicts
git status --porcelain

# Type checks
cd frontend && npm run typecheck
python -m mypy dbnotebook/core/interfaces/

# Tests
pytest tests/test_pipeline.py -v
```

### After Wave 2:
```bash
# Frontend builds
cd frontend && npm run build

# Backend tests
pytest tests/ -v --ignore=tests/integration

# Service interfaces implemented
python -c "from dbnotebook.core.services import ChatService; print('OK')"
```

### After Wave 3:
```bash
# Full test suite
pytest tests/ -v

# Frontend E2E (if available)
npm run test:e2e

# API endpoints respond
curl http://localhost:7860/api/chat/suggest-sources -X POST
```

### After Wave 4:
```bash
# Integration tests
pytest tests/integration/ -v

# Agentic feature smoke tests
python -m pytest tests/test_agentic.py -v

# Full application test
./start.sh && curl http://localhost:7860/health
```

---

## Priority Summary

| Priority | Items | Total Effort |
|----------|-------|--------------|
| P0 (Critical) | 1 | 2-4h |
| P1 (High) | 3 | 36-53h |
| P2 (Medium) | 4 | 26-36h |
| P3 (Low) | 1 | 4-6h |
| Phase 3 (Agentic) | 5 | 55-70h |
| Phase 4 (Advanced) | 3 | 40-50h |
| **Total** | **17** | **163-219h** |

---

## Execution Command

To execute with parallel agents:
```bash
# Wave 1 - Launch 3 agents simultaneously
claude --parallel --wave=1 "Execute Wave 1 tasks from CONSOLIDATED_FEATURES.md"

# Wait for completion, verify, then Wave 2...
```

Or manually with Task tool:
```
Task(subagent_type="frontend-developer", prompt="Wave 1 Agent A: Create frontend contexts...")
Task(subagent_type="backend-architect", prompt="Wave 1 Agent B: Create service interfaces...")
Task(subagent_type="backend-architect", prompt="Wave 1 Agent C: Fix pipeline dependencies...")
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Prop drilling (Sidebar) | 24+ props | <5 props |
| /chat route lines | 258 lines | <50 lines |
| Connection pools | 2 (duplicate) | 1 (unified) |
| Query success rate | Unknown | >85% |
| Feature discoverability | Low | High |
| Agentic suggestions | None | 3+ per session |
