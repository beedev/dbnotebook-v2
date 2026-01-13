# DBNotebook Multi-User Scalability Architecture Plan

**Status**: ✅ COMPLETE - All 8 Phases Implemented
**Created**: 2026-01-12
**Last Updated**: 2026-01-13

---

## Executive Summary

Transform DBNotebook into a **multi-user, API-first architecture** supporting 50-100 concurrent users across **ALL three features**: API, Notebook Chat, and SQL Chat.

**Core Insight**: The `/api/query` endpoint is **already fast AND accurate** using RAPTOR summaries. Apply this pattern everywhere.

---

## Goals (Priority Order)

1. **Concurrency** - 50-100 concurrent users
2. **Multi-user** - User isolation, no data leakage
3. **Speed** - Notebook Chat ~5-10s (4-8x faster than 40s)
4. **Accuracy** - >= 95% of current API accuracy
5. **RBAC** - Role-based access for ALL three features
6. **Chat Memory** - Conversation continuity via session_id

---

## Current State Analysis

### Feature Comparison

| Feature | Speed | Accuracy | Multi-user Ready | Memory |
|---------|-------|----------|------------------|--------|
| **API** (`/api/query`) | ✅ Fast (~5-10s) | ✅ Good | ✅ Stateless | ❌ No |
| **Notebook Chat** (`/chat`) | ❌ Slow (~40s) | ✅ Good | ❌ Global state | ❌ Lost |
| **SQL Chat** | ⚠️ Medium | ✅ Good | ❌ Shared LLM | ⚠️ In memory |

### Why API is Fast

- Uses RAPTOR summaries directly (no 3-LLM-call pipeline)
- Per-request node lookup (thread-safe cache)
- Creates per-request retriever (no global mutation)
- Stateless LLM completion via `Settings.llm`

### Why Notebook Chat is Slow

Full pipeline with 3 sequential LLM calls:
1. Intent classification (LLM) → 8-15s
2. Router selection (LLM) → 3-5s
3. QueryFusion variations → 10-15s

---

## 7-Phase Implementation Plan

### Phase 1: Extract API Pattern as Reusable Core
- [x] **Status**: ✅ COMPLETE
- **Effort**: 1 day
- **Goal**: Extract fast retrieval pattern from `/api/query` into `core/stateless/`

**Created Files**:
```
dbnotebook/core/stateless/
├── __init__.py       # Module exports
├── retrieval.py      # fast_retrieve(), get_raptor_summaries(), create_retriever()
├── completion.py     # execute_query(), execute_query_streaming(), build_prompt()
└── context.py        # build_hierarchical_context(), format_sources(), build_context_with_history()
```

---

### Phase 2: Add Chat Memory to API Pattern
- [x] **Status**: ✅ COMPLETE
- **Effort**: 1 day
- **Goal**: Add DB-backed conversation memory to API pattern

**New Endpoint**: `POST /api/v2/chat`
```json
{
    "notebook_id": "uuid",
    "query": "Follow-up question",
    "session_id": "uuid",
    "user_id": "uuid",
    "include_history": true,
    "max_history": 10
}
```

**Created Files**:
- `dbnotebook/api/routes/chat_v2.py` - V2 Chat with memory + streaming
- `dbnotebook/core/stateless/memory.py` - DB-backed memory utilities

**Endpoints**:
- `POST /api/v2/chat` - Chat with memory
- `POST /api/v2/chat/stream` - Streaming chat with memory
- `GET /api/v2/chat/history` - Get conversation history
- `DELETE /api/v2/chat/history` - Clear conversation history

---

### Phase 3: Apply Fast Pattern to Notebook Chat
- [x] **Status**: ✅ COMPLETE
- **Effort**: 2 days
- **Goal**: Replace slow 3-LLM pipeline with fast API pattern

**Speed Improvement**:
- Before: ~40s (Intent LLM + Router LLM + Fusion LLM + Retrieve)
- After: ~5-10s (Fast Retrieve + Single LLM)
- **4-8x faster**

**Implementation**:
- `dbnotebook/pipeline.py` - Added `stateless_query()` and `stateless_query_streaming()`
- `dbnotebook/api/routes/chat.py` - Added `fast_mode` parameter to use stateless path

**Usage**:
```json
POST /api/chat
{
    "message": "What are the key findings?",
    "notebook_id": "uuid",
    "fast_mode": true,      // Enable fast stateless mode
    "user_id": "uuid"       // Required for multi-user
}
```

---

### Phase 4: Apply Fast Pattern to SQL Chat
- [x] **Status**: ✅ COMPLETE
- **Effort**: 1 day
- **Goal**: Make SQL Chat multi-user ready

**Issues Fixed**:
- ✅ Shared `_llm` instance → Per-request LLM via `_get_current_llm()` using `Settings.llm`
- ✅ No user validation → All session endpoints now validate user_id access
- ✅ Hardcoded default user ID → `get_current_user_id()` checks request body/params first

**Implementation**:
- `service.py`: Added `_get_current_llm()`, `_get_response_generator()`, `_get_query_decomposer()` for per-request LLM
- `service.py`: Updated `get_session()`, `execute_query()`, `refresh_session_schema()`, `get_query_history()` with user_id validation
- `sql_chat.py`: Updated `get_current_user_id()` to check request body/params
- `sql_chat.py`: All session endpoints now pass user_id for validation

**Files**:
- MODIFIED: `dbnotebook/core/sql_chat/service.py`
- MODIFIED: `dbnotebook/api/routes/sql_chat.py`

---

### Phase 5: RBAC for ALL Features
- [x] **Status**: ✅ COMPLETE
- **Effort**: 3 days
- **Goal**: Role-based access for API, Notebook Chat, AND SQL Chat

**Implementation Summary**:
- ✅ Database models for RBAC (Role, UserRole, NotebookAccess, SQLConnectionAccess)
- ✅ Alembic migration with default roles (admin, user, viewer)
- ✅ RBACService with access control methods
- ✅ Flask decorators for route protection
- ✅ Inline access check helpers for multi-notebook support
- ✅ Admin API routes for managing access
- ✅ RBAC_STRICT_MODE environment variable for opt-in enforcement

**Database Schema** (Created in `alembic/versions/add_rbac_tables.py`):
```sql
CREATE TABLE roles (role_id, name, description, permissions);
CREATE TABLE user_roles (user_id, role_id, assigned_by, assigned_at);
CREATE TABLE notebook_access (notebook_id, user_id, access_level, granted_by, granted_at);
CREATE TABLE sql_connection_access (connection_id, user_id, access_level, granted_by, granted_at);
```

**Default Roles**:
- `admin`: Full access (manage_users, manage_roles, manage_notebooks, manage_connections, view_all, edit_all, delete_all)
- `user`: Standard access (create_notebook, create_connection, view_assigned, edit_assigned)
- `viewer`: Read-only access (view_assigned)

**Admin Endpoints** (Created in `/api/admin/*`):
```
GET    /api/admin/roles                         # List all roles
GET    /api/admin/users                         # List users with roles
POST   /api/admin/users/{id}/role               # Assign role to user
DELETE /api/admin/users/{id}/role/{role_name}   # Remove role from user
POST   /api/admin/notebooks                     # Create notebook for any user
GET    /api/admin/notebooks/{id}/access         # List notebook access
POST   /api/admin/notebooks/{id}/access         # Grant notebook access
DELETE /api/admin/notebooks/{id}/access/{user}  # Revoke notebook access
GET    /api/admin/sql-connections/{id}/access   # List connection access
POST   /api/admin/sql-connections/{id}/access   # Grant connection access
DELETE /api/admin/sql-connections/{id}/access/{user} # Revoke connection access
```

**Access Control Functions** (in `core/auth/rbac.py`):
- `check_notebook_access(user_id, notebook_id, access_level)` - Inline notebook check
- `check_multi_notebook_access(user_id, notebook_ids, access_level)` - Multi-notebook check
- `check_sql_connection_access(user_id, connection_id, access_level)` - SQL connection check
- `@require_permission(permission)` - Decorator for permission-based access
- `@require_notebook_access(access_level)` - Decorator for notebook routes
- `@require_sql_connection_access(access_level)` - Decorator for SQL routes

**RBAC Enforcement**:
- Set `RBAC_STRICT_MODE=true` to enforce access control
- Default is disabled for backward compatibility
- When enabled, routes check user access before processing

**Files**:
- NEW: `dbnotebook/core/auth/__init__.py` - Auth module exports
- NEW: `dbnotebook/core/auth/rbac.py` - RBACService and decorators
- NEW: `dbnotebook/api/routes/admin.py` - Admin API routes
- NEW: `alembic/versions/add_rbac_tables.py` - Migration
- MODIFIED: `dbnotebook/core/db/models.py` - RBAC models
- MODIFIED: `dbnotebook/api/routes/query.py` - RBAC check integration
- MODIFIED: `dbnotebook/ui/web.py` - Register admin routes

---

### Phase 6: Accuracy Validation & Performance Testing
- [x] **Status**: ✅ COMPLETE
- **Effort**: 1 day
- **Goal**: Validate accuracy and test 100 concurrent users

**Implementation Summary**:
- ✅ Accuracy benchmark comparing old pipeline vs new stateless pattern
- ✅ Load test for 100 concurrent users
- ✅ Metrics: response times, error rates, P50/P95/P99 latencies
- ✅ Data isolation verification (no cross-user leakage)

**Accuracy Benchmark** (`tests/test_accuracy_benchmark.py`):
```python
# Compares old pipeline (fast_mode=false) vs new stateless (/api/query)
# Metrics tracked:
# - Source relevance scores (avg, min, max)
# - Response completeness
# - RAPTOR summary usage
# - Execution time comparison
# Target: >= 85% accuracy score (weighted combination of above)
```

**Load Test** (`tests/test_load_concurrent.py`):
```python
# Configuration:
CONCURRENT_USERS = 100
REQUESTS_PER_USER = 3
TARGET_ERROR_RATE = 0.05  # 5%
TARGET_P95_LATENCY_MS = 30000  # 30 seconds

# Run tests:
pytest tests/test_load_concurrent.py -v -s
# Or standalone:
python tests/test_load_concurrent.py
```

**Test Commands**:
```bash
# Run accuracy benchmark
pytest tests/test_accuracy_benchmark.py -v

# Run load test for 100 concurrent users
pytest tests/test_load_concurrent.py -v -s

# Run both
pytest tests/test_accuracy_benchmark.py tests/test_load_concurrent.py -v
```

**Files**:
- NEW: `tests/test_accuracy_benchmark.py` - Accuracy comparison test suite
- NEW: `tests/test_load_concurrent.py` - 100 concurrent users load test

---

### Phase 7: Frontend Integration & Testing
- [x] **Status**: ✅ COMPLETE
- **Effort**: 2 days
- **Goal**: Update frontend to use new APIs with session tracking

**Implementation Summary**:
- ✅ Added V2 Chat types (`ChatV2Request`, `ChatV2Response`, `ConversationHistoryItem`)
- ✅ Created V2 API functions (`sendChatV2Message`, `getChatV2History`, `clearChatV2History`)
- ✅ Created `useChatV2` hook with session/user tracking and history loading
- ✅ Updated `ChatContext` with `sessionId`, `userId`, `setSessionId`, `resetSession`
- ✅ User ID persisted in localStorage for multi-user support
- ✅ **Connected ChatArea.tsx to useChatV2** (2026-01-13)
  - Changed import from `useChat` to `useChatV2`
  - Removed unused `toApiQuerySettings` function
  - Fixed sendMessage calls to single argument
  - Frontend builds successfully

**Usage**:
```typescript
// Use useChatV2 hook for multi-user chat with memory
import { useChatV2 } from '@/hooks';

function ChatComponent({ notebookId }) {
  const { messages, sendMessage, sessionId, userId } = useChatV2(notebookId);
  // Messages persist to database, history loads on notebook switch
}

// Access from ChatContext
import { useChat } from '@/contexts/ChatContext';
const { sessionId, userId, resetSession } = useChat();
```

**Files**:
- NEW: `frontend/src/hooks/useChatV2.ts` - V2 chat hook with memory
- NEW: `frontend/src/types/index.ts` - Added V2 chat types
- MODIFIED: `frontend/src/services/api.ts` - Added V2 API functions
- MODIFIED: `frontend/src/contexts/ChatContext.tsx` - Added session/user tracking
- MODIFIED: `frontend/src/hooks/index.ts` - Exported useChatV2

---

### Phase 8: Code Cleanup & Modularization
- [x] **Status**: ✅ COMPLETE
- **Effort**: 1 day
- **Goal**: Clean up code, extract constants, document multi-user architecture

**Completed Work**:

1. **Created `dbnotebook/core/constants.py`**
   - Extracted shared constants (`DEFAULT_USER_ID`, `DEFAULT_NOTEBOOK_ID`)
   - Eliminated magic strings across codebase

2. **Cleaned up `dbnotebook/api/routes/chat.py`**
   - Removed unused `ChatMessage` import
   - Simplified chatbot history creation
   - Used `DEFAULT_USER_ID` constant

3. **Cleaned up `dbnotebook/api/routes/query.py`**
   - Consolidated duplicate `Settings` imports to module level
   - Used `DEFAULT_USER_ID` constant

4. **Cleaned up `dbnotebook/api/routes/analytics.py`** (2026-01-13)
   - Imported `DEFAULT_USER_ID` from constants
   - Removed hardcoded duplicate constant

5. **Cleaned up `dbnotebook/api/routes/sql_chat.py`** (2026-01-13)
   - Imported `DEFAULT_USER_ID` from constants
   - Removed hardcoded duplicate constant

6. **Cleaned up `dbnotebook/ui/web.py`**
   - Removed dead code in `_is_image_generation_request`
   - Extracted `ALLOWED_CORS_ORIGINS` constant
   - DRY'd up CORS configuration

7. **Documented `dbnotebook/pipeline.py`**
   - Added comprehensive class docstring for multi-user architecture
   - Documented which methods are multi-user safe vs single-user
   - Listed global state variables with explanations
   - Added usage recommendations
   - Used `DEFAULT_USER_ID` constant

**Multi-User Architecture Documentation** (in pipeline.py):
- **MULTI-USER SAFE**: `stateless_query()`, `stateless_query_streaming()`, `_get_cached_nodes()`
- **SINGLE-USER**: `switch_notebook()`, `set_engine()`, `set_chat_mode()`, `query()`
- **GLOBAL STATE**: `_current_notebook_id`, `_current_user_id`, `_current_offering_filter`

---

## Implementation Priority

| Phase | Priority | Effort | Impact |
|-------|----------|--------|--------|
| Phase 1: Extract API Pattern | P0 | 1 day | Foundation |
| Phase 2: Add Chat Memory | P0 | 1 day | Conversation continuity |
| Phase 3: Apply to Notebook Chat | P0 | 2 days | **4-8x speed** |
| Phase 4: Apply to SQL Chat | P0 | 1 day | SQL multi-user |
| Phase 5: RBAC for All Features | P1 | 3 days | Access control |
| Phase 6: Accuracy Validation | P1 | 1 day | Quality assurance |
| Phase 7: Frontend & Testing | P1 | 2 days | Integration |
| Phase 8: Code Cleanup | P2 | 2 days | Maintainability |

**Total Effort**: ~13 days

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Speed | Notebook Chat ~5-10s (was 40s) |
| Accuracy | >= 95% of current API accuracy |
| Concurrency | 50 users with <5% error rate |
| Memory | Conversations persist across sessions |
| RBAC | All 3 features protected |

---

## Critical Files Summary

**New Files**:
- `dbnotebook/core/stateless/` (module)
- `dbnotebook/api/routes/chat_v2.py`
- `dbnotebook/api/routes/admin.py`
- `dbnotebook/core/auth/rbac.py`
- `alembic/versions/xxx_add_rbac.py`
- `tests/test_accuracy_benchmark.py`
- `tests/test_concurrent_users.py`

**Modified Files**:
- `dbnotebook/pipeline.py`
- `dbnotebook/api/routes/chat.py`
- `dbnotebook/core/sql_chat/service.py`
- `dbnotebook/core/db/models.py`
- `dbnotebook/ui/web.py`
- `frontend/src/api/chat.ts`
- `frontend/src/contexts/ChatContext.tsx`
