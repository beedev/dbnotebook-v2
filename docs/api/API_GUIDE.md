# DBNotebook RAG Query API Guide

A multi-user safe REST API for querying documents using natural language with optional conversation memory.

## Quick Start

### 1. Get Your API Key

Each user has a unique API key. Get it from:
- **Admin Dashboard** → Users tab → Copy API key
- **Profile page** → API Key section

Default admin API key: `dbn_00000000000000000000000000000001`

### 2. List Available Notebooks

```bash
curl http://localhost:7007/api/query/notebooks \
  -H "X-API-Key: YOUR_API_KEY"
```

Response:
```json
{
  "success": true,
  "notebooks": [
    {
      "id": "990b1f11-fb85-4c7c-ab49-f44d0caaab7d",
      "name": "Policies",
      "document_count": 4,
      "created_at": "2026-01-11T09:01:17.738829"
    }
  ]
}
```

### 3. Execute a Stateless Query

```bash
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "notebook_id": "990b1f11-fb85-4c7c-ab49-f44d0caaab7d",
    "query": "What is the main topic of these documents?"
  }'
```

Response:
```json
{
  "success": true,
  "response": "The main topic is digital transformation...",
  "sources": [
    {
      "filename": "Automation.md",
      "snippet": "The MODERNIZE offering is...",
      "score": 0.492
    }
  ],
  "metadata": {
    "execution_time_ms": 3500,
    "model": "llama3.1:latest",
    "retrieval_strategy": "hybrid",
    "node_count": 77,
    "stateless": true,
    "history_messages_used": 0
  }
}
```

---

## Conversation Memory

The API supports multi-turn conversations with memory. **The client controls whether memory is enabled by sending a `session_id`.**

### How It Works

| Client Request | Behavior | History Saved |
|----------------|----------|---------------|
| No `session_id` | Stateless query | No |
| With `session_id` | Conversational mode | Yes |

**Important:** The server does NOT generate session IDs. If you want conversation memory, you must generate a UUID and send it from your **first** request.

### Stateless Query (No Memory)

```bash
# No session_id = stateless, no history saved
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "notebook_id": "YOUR_NOTEBOOK_ID",
    "query": "What is the policy?"
  }'
```

Response (no `session_id` in response):
```json
{
  "success": true,
  "response": "The policy states...",
  "sources": [...],
  "metadata": { "stateless": true, "history_messages_used": 0 }
}
```

### Conversational Query (With Memory)

```bash
# Generate a UUID for session_id (client-side)
SESSION_ID=$(uuidgen)  # or use any UUID generator

# First query WITH session_id = history IS saved
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{
    \"notebook_id\": \"YOUR_NOTEBOOK_ID\",
    \"query\": \"What is the policy?\",
    \"session_id\": \"$SESSION_ID\"
  }"

# Follow-up query with same session_id = has conversation context
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{
    \"notebook_id\": \"YOUR_NOTEBOOK_ID\",
    \"query\": \"Can you elaborate on that?\",
    \"session_id\": \"$SESSION_ID\"
  }"
```

Response (includes `session_id`):
```json
{
  "success": true,
  "response": "To elaborate further...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "sources": [...],
  "metadata": { "stateless": false, "history_messages_used": 2 }
}
```

### Session ID Format

Must be a valid UUID string:
```
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Examples:
- `550e8400-e29b-41d4-a716-446655440000` ✅
- `my-session-123` ❌ (not a UUID)

---

## API Reference

### Base URL

| Environment | URL |
|-------------|-----|
| Docker (default) | `http://localhost:7007` |
| Local dev | `http://localhost:7860` |
| Production | Your deployed URL |

### Authentication

All requests require an `X-API-Key` header with a valid user API key.

```bash
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"notebook_id": "...", "query": "..."}'
```

**API Key Sources:**
1. **Per-user keys** (recommended): Each user has a unique key in the database
2. **Environment variable** (legacy): `API_KEY` in docker-compose.yml

**Without a valid API key:**
```json
{"success": false, "error": "Invalid or missing API key"}
```

---

## Endpoints

### POST /api/query

Execute a RAG query against documents in a notebook.

#### Request Body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `notebook_id` | UUID | Yes | - | Notebook to query |
| `query` | string | Yes | - | Natural language query |
| `session_id` | UUID | No | - | Client-generated UUID for conversation memory |
| `max_history` | integer | No | `5` | Max history messages (1-20, only with session_id) |
| `include_sources` | boolean | No | `true` | Include source documents |
| `max_sources` | integer | No | `6` | Max sources (1-20) |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Query success status |
| `response` | string | Generated AI response |
| `session_id` | string | Only present if session_id was sent (confirms memory enabled) |
| `sources` | array | Source documents with scores |
| `metadata.execution_time_ms` | integer | Execution time in milliseconds |
| `metadata.model` | string | LLM model used |
| `metadata.stateless` | boolean | `true` if no session_id, `false` if memory enabled |
| `metadata.history_messages_used` | integer | Number of prior messages used (0 if stateless) |
| `metadata.node_count` | integer | Document chunks in notebook |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Missing required fields or invalid session_id format |
| 401 | Invalid API key |
| 403 | Access denied (RBAC) |
| 404 | Notebook not found |
| 500 | Server error |
| 503 | Pipeline not initialized |

---

### GET /api/query/notebooks

List all available notebooks.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | No | Filter by user |

#### Response

```json
{
  "success": true,
  "notebooks": [
    {
      "id": "uuid",
      "name": "Notebook Name",
      "document_count": 4,
      "created_at": "2026-01-11T09:01:17.738829"
    }
  ]
}
```

---

### GET /api/user/api-key

Get the API key for a user.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | No | User ID (defaults to admin user) |

#### Response

```json
{
  "success": true,
  "api_key": "dbn_abc123...",
  "user_id": "uuid"
}
```

---

## Code Examples

### Python - Stateless Queries

```python
import requests

BASE_URL = "http://localhost:7007"
API_KEY = "dbn_00000000000000000000000000000001"  # Your API key
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# List notebooks
response = requests.get(f"{BASE_URL}/api/query/notebooks", headers=HEADERS)
notebooks = response.json()["notebooks"]
print(f"Found {len(notebooks)} notebooks")

# Stateless query (no session_id)
notebook_id = notebooks[0]["id"]
response = requests.post(
    f"{BASE_URL}/api/query",
    headers=HEADERS,
    json={
        "notebook_id": notebook_id,
        "query": "What are the key features?",
        "max_sources": 3
    }
)

result = response.json()
print(f"Response: {result['response']}")
print(f"Stateless: {result['metadata']['stateless']}")  # True
```

### Python - Conversational Queries (With Memory)

```python
import requests
import uuid

BASE_URL = "http://localhost:7007"
API_KEY = "dbn_00000000000000000000000000000001"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

notebook_id = "your-notebook-uuid"

# Generate session_id for conversation memory
session_id = str(uuid.uuid4())

# First query - WITH session_id, history WILL be saved
response = requests.post(
    f"{BASE_URL}/api/query",
    headers=HEADERS,
    json={
        "notebook_id": notebook_id,
        "query": "What is the company policy on remote work?",
        "session_id": session_id  # Enable memory from first request
    }
)
result = response.json()
print(f"Response 1: {result['response']}")
print(f"Stateless: {result['metadata']['stateless']}")  # False

# Follow-up query - same session_id, has conversation context
response = requests.post(
    f"{BASE_URL}/api/query",
    headers=HEADERS,
    json={
        "notebook_id": notebook_id,
        "query": "What about the approval process?",  # Refers to previous context
        "session_id": session_id
    }
)
result = response.json()
print(f"Response 2: {result['response']}")
print(f"History used: {result['metadata']['history_messages_used']}")  # > 0
```

### Python - Reusable Client Class

```python
import requests
import uuid

class DBNotebookClient:
    def __init__(self, base_url="http://localhost:7007", api_key=None):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key or "dbn_00000000000000000000000000000001",
            "Content-Type": "application/json"
        }
        self.session_id = None  # For conversation memory

    def list_notebooks(self):
        response = requests.get(f"{self.base_url}/api/query/notebooks", headers=self.headers)
        return response.json()["notebooks"]

    def query(self, notebook_id, query, use_memory=False, max_sources=3):
        """Execute a query. Set use_memory=True for conversation continuity."""
        payload = {
            "notebook_id": notebook_id,
            "query": query,
            "max_sources": max_sources
        }

        if use_memory:
            if not self.session_id:
                self.session_id = str(uuid.uuid4())
            payload["session_id"] = self.session_id

        response = requests.post(
            f"{self.base_url}/api/query",
            headers=self.headers,
            json=payload
        )
        return response.json()

    def reset_conversation(self):
        """Start a new conversation."""
        self.session_id = None

# Usage
client = DBNotebookClient(api_key="your-api-key")

# Stateless queries
result = client.query("notebook-id", "What is X?")

# Conversational queries
result = client.query("notebook-id", "What is Y?", use_memory=True)
result = client.query("notebook-id", "Tell me more", use_memory=True)  # Has context

# Start fresh conversation
client.reset_conversation()
```

### JavaScript/Node.js

```javascript
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const BASE_URL = 'http://localhost:7007';
const API_KEY = 'dbn_00000000000000000000000000000001';

class DBNotebookClient {
  constructor(apiKey = API_KEY) {
    this.headers = { 'X-API-Key': apiKey, 'Content-Type': 'application/json' };
    this.sessionId = null;
  }

  async query(notebookId, query, useMemory = false) {
    const payload = { notebook_id: notebookId, query };

    if (useMemory) {
      if (!this.sessionId) this.sessionId = uuidv4();
      payload.session_id = this.sessionId;
    }

    const response = await axios.post(`${BASE_URL}/api/query`, payload, {
      headers: this.headers
    });
    return response.data;
  }

  resetConversation() {
    this.sessionId = null;
  }
}

// Usage
const client = new DBNotebookClient();

// Stateless
const result1 = await client.query('notebook-id', 'What is the policy?');

// With memory
const result2 = await client.query('notebook-id', 'What is the policy?', true);
const result3 = await client.query('notebook-id', 'Elaborate please', true); // Has context
```

### cURL

```bash
# List notebooks
curl http://localhost:7007/api/query/notebooks \
  -H "X-API-Key: YOUR_API_KEY"

# Stateless query (no session_id)
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"notebook_id": "YOUR_NOTEBOOK_ID", "query": "Your question here"}'

# Conversational query (with session_id)
SESSION_ID=$(uuidgen)
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{\"notebook_id\": \"YOUR_NOTEBOOK_ID\", \"query\": \"First question\", \"session_id\": \"$SESSION_ID\"}"

# Follow-up (same session_id)
curl -X POST http://localhost:7007/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{\"notebook_id\": \"YOUR_NOTEBOOK_ID\", \"query\": \"Follow-up question\", \"session_id\": \"$SESSION_ID\"}"
```

---

## Concurrent Usage

The API is designed for multi-user concurrent access:

- **Thread-safe**: 20+ concurrent requests supported
- **Stateless by default**: Each request without session_id is independent
- **Session isolation**: Different session_ids have separate conversation histories
- **Data isolation**: Each notebook's documents are isolated

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `notebook_id is required` | Missing notebook_id | Include notebook_id in request |
| `query is required` | Missing query | Include query in request |
| `Invalid session_id format` | session_id is not a valid UUID | Use UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `Notebook not found` | Invalid notebook_id | Check notebook exists via /api/query/notebooks |
| `Invalid or missing API key` | Bad or missing X-API-Key header | Use valid user API key |
| `Access denied` | RBAC restriction | User needs access to the notebook |

### Error Response Format

```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## RBAC (Role-Based Access Control)

When `RBAC_STRICT_MODE=true` is set, users can only query notebooks they have access to.

See [USER_RBAC_GUIDE.md](../USER_RBAC_GUIDE.md) for details on:
- User management
- Role assignments
- Notebook access control

---

## Network Access (Docker Deployment)

When DBNotebook is deployed in Docker, other servers in your network can access the API.

### Find the Host Server IP

```bash
# Linux
hostname -I | awk '{print $1}'

# macOS
ipconfig getifaddr en0
```

### Access from Other Servers

Replace `localhost` with the host server's IP address:

```bash
curl http://192.168.1.100:7007/api/query/notebooks \
  -H "X-API-Key: YOUR_API_KEY"
```

### Environment Variables for Configuration

```bash
export DBNOTEBOOK_API_URL="http://192.168.1.100:7007"
export DBNOTEBOOK_API_KEY="your-api-key"
```

```python
import os
API_BASE = os.getenv("DBNOTEBOOK_API_URL", "http://localhost:7007")
API_KEY = os.getenv("DBNOTEBOOK_API_KEY")
```

---

## Troubleshooting

### 401 Invalid or Missing API Key

```bash
# Verify your API key is correct
curl http://localhost:7007/api/query/notebooks \
  -H "X-API-Key: YOUR_API_KEY"
```

### 400 Invalid session_id format

Session ID must be a valid UUID. Generate one:
```python
import uuid
session_id = str(uuid.uuid4())  # "f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

### Conversation history not working

Make sure you:
1. Send `session_id` from the **first** request (not just follow-ups)
2. Use the **same** `session_id` for all messages in a conversation
3. Use the **same** `notebook_id` across the conversation

### 503 Pipeline Not Initialized

The server is still starting up. Wait a few seconds and retry.

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is available at:

- **File**: `docs/api/openapi.yaml`
- **Swagger UI**: Import the YAML into [Swagger Editor](https://editor.swagger.io/)
