# Conversation Management Architecture

## Overview

The RAG chatbot implements a **hybrid conversation persistence system** combining:
1. **In-session memory** - LlamaIndex's `ChatMemoryBuffer` for active conversations
2. **Cross-session persistence** - PostgreSQL for long-term storage

---

## Architecture Layers

### Layer 1: In-Session Memory (LlamaIndex `ChatMemoryBuffer`)

**Location**: `rag_chatbot/core/engine/engine.py:59-62`

```python
memory = ChatMemoryBuffer(
    token_limit=self._setting.ollama.chat_token_limit,
    chat_history=chat_history or []  # Load from database on initialization
)
```

**Purpose**:
- Maintains conversation context during active session
- Automatically updated by `stream_chat()` calls
- Token-limited to prevent context overflow
- Cleared on `engine.reset()`

**Lifecycle**:
- **Created**: When `set_engine()` is called
- **Updated**: Automatically on each `stream_chat()` call
- **Preserved**: When switching notebooks (extracted → saved to PostgreSQL → reloaded)
- **Destroyed**: When engine is recreated or reset

---

### Layer 2: Database Persistence (PostgreSQL)

**Location**: `rag_chatbot/core/conversation/conversation_store.py`

**Purpose**:
- Long-term storage across sessions
- Notebook-scoped conversation isolation
- User-specific conversation tracking
- Historical conversation analysis

**Database Table**: `conversations`
```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(notebook_id),
    user_id UUID REFERENCES users(user_id),
    role VARCHAR(20),  -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Conversation Flow

### During Active Session (In-Memory)

```
User Query
    ↓
pipeline.query(mode="chat", message, chatbot)
    ↓
engine.stream_chat(message)  ← NO history parameter needed!
    ↓
ChatMemoryBuffer automatically:
  1. Adds user message to buffer
  2. Generates response with full conversation context
  3. Adds assistant response to buffer
    ↓
Streaming Response
```

**Key Point**: The `chatbot` UI list is **NOT** passed to `stream_chat()`. The engine's internal `ChatMemoryBuffer` maintains all context automatically.

---

### Notebook Switching (Memory → Database → Memory)

```
User switches to new notebook
    ↓
pipeline.switch_notebook(new_notebook_id, user_id)
    ↓
Step 1: Save Current Conversation
  - Extract from engine.memory.get_all()
  - Convert to dict format
  - conversation_store.save_messages()
    ↓
Step 2: Load New Conversation
  - conversation_store.get_conversation_history()
  - Last 50 messages from PostgreSQL
  - Convert to ChatMessage objects
    ↓
Step 3: Recreate Engine with History
  - engine.set_engine(chat_history=loaded_history)
  - New ChatMemoryBuffer initialized with history
  - Conversation context preserved
```

---

## Code Examples

### ✅ CORRECT (Implemented - Proper LlamaIndex Memory Management)

```python
def query(self, mode: str, message: str, chatbot: list[list[str]]):
    if mode == "chat":
        # ChatMemoryBuffer automatically manages conversation history
        # DO NOT pass history parameter - it replaces internal memory
        return self._query_engine.stream_chat(message)
    else:
        # Reset memory for single Q&A mode
        self._query_engine.reset()
        return self._query_engine.stream_chat(message)
```

**Location**: `rag_chatbot/pipeline.py:601-608`

**How It Works** (Verified from LlamaIndex Source):
1. `stream_chat(message)` called WITHOUT history parameter
2. Engine's internal `ChatMemoryBuffer.get()` retrieves conversation context
3. Query processed with full conversation history
4. After streaming completes, `_memory.put()` saves both user and assistant messages
5. Next query automatically has access to updated conversation history

### ❌ INCORRECT Pattern (What Was Wrong)

```python
def query(self, mode: str, message: str, chatbot: list[list[str]]):
    if mode == "chat":
        history = self.get_history(chatbot)  # ← Manual history management
        return self._query_engine.stream_chat(message, history)  # ← Passing history
    # Problem: Passing history REPLACES engine's ChatMemoryBuffer, wiping previous context
```

---

## Memory Preservation Strategy

### Scenario 1: Same Notebook, Multiple Queries

```python
# Query 1
pipeline.query("chat", "What is RAG?", chatbot=[])
# → Engine's ChatMemoryBuffer: [user: "What is RAG?", assistant: "RAG stands for..."]

# Query 2 (Follow-up)
pipeline.query("chat", "Can you elaborate?", chatbot=[...])
# → Engine's ChatMemoryBuffer: [previous messages + new exchange]
# → Context automatically maintained by LlamaIndex
```

### Scenario 2: Notebook Switch

```python
# User in Notebook A with conversation history
pipeline._current_notebook_id = "notebook-a"
# ChatMemoryBuffer: [10 messages from current session]

# User switches to Notebook B
pipeline.switch_notebook("notebook-b", user_id)
# 1. Save Notebook A's 10 messages to PostgreSQL
# 2. Load Notebook B's last 50 messages from PostgreSQL
# 3. Create new engine with Notebook B's history in ChatMemoryBuffer
# 4. Conversation context restored
```

### Scenario 3: Session End and Restart

```python
# Before session ends
# - ChatMemoryBuffer has in-memory conversation
# - UI calls: pipeline.save_conversation_exchange() after each query
# - Messages saved to PostgreSQL incrementally

# New session starts
# - Call: pipeline.switch_notebook(notebook_id, user_id)
# - Loads last 50 messages from PostgreSQL
# - ChatMemoryBuffer initialized with history
# - Conversation context restored
```

---

## Integration Points

### UI Layer (`rag_chatbot/ui/ui.py` or `web.py`)

**Current Responsibility**:
1. Send user queries to pipeline
2. **After streaming completes**, call `pipeline.save_conversation_exchange()`
3. Manage chatbot UI list for display purposes only

**Example**:
```python
# Gradio UI
def bot(message, chatbot):
    # Send query to pipeline
    response = pipeline.query("chat", message, chatbot)

    # Stream and collect full response
    full_response = ""
    for chunk in response.response_gen:
        full_response += chunk
        yield chatbot + [[message, full_response]]

    # Save to database after streaming completes
    pipeline.save_conversation_exchange(
        notebook_id=current_notebook_id,
        user_id=current_user_id,
        user_message=message,
        assistant_message=full_response
    )
```

---

## Benefits of This Architecture

1. **Single Source of Truth**: Engine's `ChatMemoryBuffer` is the authoritative source for active conversation context

2. **Automatic Context Management**: LlamaIndex handles conversation tracking natively

3. **Token-Aware**: Memory buffer respects token limits automatically

4. **Cross-Session Persistence**: PostgreSQL provides long-term storage

5. **Notebook Isolation**: Each notebook has independent conversation history

6. **Scalability**: Database can store unlimited history, while memory buffer is token-limited

---

## Testing

See `tests/test_conversation_integration.py` for comprehensive integration tests covering:
- Notebook switching with history preservation
- Multi-notebook conversation isolation
- Message persistence and retrieval
- History clearing
- Last activity tracking

All tests passing ✅
