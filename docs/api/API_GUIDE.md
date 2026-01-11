# DBNotebook RAG Query API Guide

A multi-user safe REST API for querying documents using natural language.

## Quick Start

### 1. List Available Notebooks

```bash
curl http://localhost:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"
```

Response:
```json
{
  "success": true,
  "notebooks": [
    {
      "id": "990b1f11-fb85-4c7c-ab49-f44d0caaab7d",
      "name": "Digital",
      "document_count": 4,
      "created_at": "2026-01-11T09:01:17.738829"
    }
  ]
}
```

### 2. Execute a Query

```bash
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
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
      "document": "Automation.md",
      "excerpt": "The MODERNIZE offering is...",
      "score": 0.492
    }
  ],
  "metadata": {
    "execution_time_ms": 3500,
    "model": "gpt-4.1",
    "retrieval_strategy": "hybrid",
    "node_count": 77
  }
}
```

---

## API Reference

### Base URL

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:7860` |
| Docker | `http://localhost:7860` |
| Production | Your deployed URL |

### Authentication

Authentication is **enabled** by default in the Docker deployment.

**API Key**: `dbnotebook-secure-api-key-2026`

All requests must include the `X-API-Key` header:

```bash
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
  -d '{"notebook_id": "...", "query": "..."}'
```

**Without the API key**, requests will be rejected with:
```json
{"success": false, "error": "Invalid or missing API key"}
```

**To change the API key**, edit `docker-compose.yml`:
```yaml
environment:
  - API_KEY=your-new-api-key-here
```

**To disable authentication**, remove the `API_KEY` line from `docker-compose.yml`.

---

## Endpoints

### POST /api/query

Execute a RAG query against documents in a notebook.

#### Request Body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `notebook_id` | UUID | Yes | - | Notebook to query |
| `query` | string | Yes | - | Natural language query |
| `include_sources` | boolean | No | `true` | Include source documents |
| `max_sources` | integer | No | `6` | Max sources (1-20) |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Query success status |
| `response` | string | Generated AI response |
| `sources` | array | Source documents with scores |
| `metadata.execution_time_ms` | integer | Execution time |
| `metadata.model` | string | LLM model used |
| `metadata.node_count` | integer | Document chunks in notebook |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Missing required fields |
| 401 | Invalid API key |
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

## Code Examples

### Python

```python
import requests

BASE_URL = "http://localhost:7860"
API_KEY = "dbnotebook-secure-api-key-2026"
HEADERS = {"X-API-Key": API_KEY}

# List notebooks
response = requests.get(f"{BASE_URL}/api/query/notebooks", headers=HEADERS)
notebooks = response.json()["notebooks"]
print(f"Found {len(notebooks)} notebooks")

# Query a notebook
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
print(f"Sources: {len(result['sources'])}")
print(f"Time: {result['metadata']['execution_time_ms']}ms")
```

### Python - Reusable Client Class

```python
import requests

class DBNotebookClient:
    def __init__(self, base_url="http://localhost:7860", api_key="dbnotebook-secure-api-key-2026"):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    def list_notebooks(self):
        response = requests.get(f"{self.base_url}/api/query/notebooks", headers=self.headers)
        return response.json()["notebooks"]

    def query(self, notebook_id, query, max_sources=3):
        response = requests.post(
            f"{self.base_url}/api/query",
            headers=self.headers,
            json={"notebook_id": notebook_id, "query": query, "max_sources": max_sources}
        )
        return response.json()

# Usage
client = DBNotebookClient()
notebooks = client.list_notebooks()
result = client.query(notebooks[0]["id"], "Create a sales pitch for Retail industry")
print(result["response"])
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:7860';
const API_KEY = 'dbnotebook-secure-api-key-2026';

async function queryNotebook(notebookId, query) {
  const response = await axios.post(`${BASE_URL}/api/query`, {
    notebook_id: notebookId,
    query: query,
    max_sources: 3
  }, {
    headers: { 'X-API-Key': API_KEY }
  });

  return response.data;
}

// Usage
const result = await queryNotebook(
  '990b1f11-fb85-4c7c-ab49-f44d0caaab7d',
  'What is the main topic?'
);
console.log(result.response);
```

### JavaScript Fetch

```javascript
const API_KEY = 'dbnotebook-secure-api-key-2026';

async function queryAPI(notebookId, query) {
  const response = await fetch('http://localhost:7860/api/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify({
      notebook_id: notebookId,
      query: query
    })
  });

  return response.json();
}
```

### cURL

```bash
# List notebooks
curl http://localhost:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"

# Simple query
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
  -d '{"notebook_id": "YOUR_NOTEBOOK_ID", "query": "Your question here"}'

# With all options
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
  -d '{
    "notebook_id": "990b1f11-fb85-4c7c-ab49-f44d0caaab7d",
    "query": "Create a detailed sales pitch for Healthcare industry",
    "include_sources": true,
    "max_sources": 5
  }'

# Pretty print response
curl -s -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
  -d '{"notebook_id": "YOUR_ID", "query": "Summary"}' | python -m json.tool
```

### PowerShell

```powershell
$apiKey = "dbnotebook-secure-api-key-2026"
$headers = @{ "X-API-Key" = $apiKey }

$body = @{
    notebook_id = "990b1f11-fb85-4c7c-ab49-f44d0caaab7d"
    query = "What are the key features?"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:7860/api/query" `
    -Method Post `
    -ContentType "application/json" `
    -Headers $headers `
    -Body $body

Write-Host $response.response
```

---

## Concurrent Usage

The API is designed for multi-user concurrent access:

- **Thread-safe**: 20+ concurrent requests supported
- **Stateless**: No session state, each request is independent
- **Data isolation**: Each notebook's documents are isolated

### Example: Batch Queries (Python)

```python
import concurrent.futures
import requests

API_KEY = "dbnotebook-secure-api-key-2026"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def query_notebook(notebook_id, query):
    response = requests.post(
        "http://localhost:7860/api/query",
        headers=HEADERS,
        json={"notebook_id": notebook_id, "query": query}
    )
    return response.json()

# Execute multiple queries concurrently
queries = [
    ("notebook-1", "Query 1"),
    ("notebook-1", "Query 2"),
    ("notebook-2", "Query 3"),
]

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(query_notebook, nb_id, q)
        for nb_id, q in queries
    ]

    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        print(f"Success: {result['success']}")
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `notebook_id is required` | Missing notebook_id | Include notebook_id in request |
| `query is required` | Missing query | Include query in request |
| `Notebook not found` | Invalid notebook_id | Check notebook exists via /api/query/notebooks |
| `Invalid or missing API key` | Auth enabled, bad key | Check X-API-Key header |

### Error Response Format

```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is available at:

- **File**: `docs/api/openapi.yaml`
- **Swagger UI**: Import the YAML into [Swagger Editor](https://editor.swagger.io/)

---

## Performance Tips

1. **Limit sources**: Use `max_sources: 3-5` for faster responses
2. **Batch queries**: Use concurrent requests for multiple queries
3. **Cache notebook IDs**: Fetch notebooks list once, reuse IDs
4. **Monitor timing**: Check `metadata.execution_time_ms` for performance

---

## Network Access (Docker Deployment)

When DBNotebook is deployed in Docker, other servers in your network can access the API.

### 1. Find the Host Server IP

On the server running Docker:

```bash
# Linux
hostname -I | awk '{print $1}'

# macOS
ipconfig getifaddr en0

# Windows
ipconfig | findstr /i "IPv4"
```

Example: `192.168.1.100`

### 2. Verify Port is Accessible

The current `docker-compose.yml` exposes port `7860` on all interfaces:

```yaml
ports:
  - "7860:7860"  # Binds to 0.0.0.0:7860
```

### 3. Access from Other Servers

Replace `localhost` with the host server's IP address:

```bash
# From another server in the network
curl http://192.168.1.100:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"

# Execute a query
curl -X POST http://192.168.1.100:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbnotebook-secure-api-key-2026" \
  -d '{
    "notebook_id": "YOUR_NOTEBOOK_ID",
    "query": "What is the summary?"
  }'
```

### 4. Python Client from Remote Server

```python
import requests

# Use the Docker host's IP address
API_BASE = "http://192.168.1.100:7860"
API_KEY = "dbnotebook-secure-api-key-2026"

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def list_notebooks():
    response = requests.get(f"{API_BASE}/api/query/notebooks", headers=HEADERS)
    return response.json()

def query_notebook(notebook_id, query, max_sources=3):
    response = requests.post(
        f"{API_BASE}/api/query",
        headers=HEADERS,
        json={
            "notebook_id": notebook_id,
            "query": query,
            "max_sources": max_sources
        }
    )
    return response.json()

# Usage
notebooks = list_notebooks()
print(f"Available notebooks: {notebooks['notebooks']}")

result = query_notebook(
    notebook_id="990b1f11-fb85-4c7c-ab49-f44d0caaab7d",
    query="Create a sales pitch for Retail industry"
)
print(f"Response: {result['response']}")
```

### 5. Environment Variables for Configuration

For applications that need to call the API, set environment variables:

```bash
# On the client server
export DBNOTEBOOK_API_URL="http://192.168.1.100:7860"
export DBNOTEBOOK_API_KEY="dbnotebook-secure-api-key-2026"
```

```python
import os
import requests

API_BASE = os.getenv("DBNOTEBOOK_API_URL", "http://localhost:7860")
API_KEY = os.getenv("DBNOTEBOOK_API_KEY", "dbnotebook-secure-api-key-2026")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

response = requests.post(f"{API_BASE}/api/query", headers=HEADERS, json={...})
```

### 6. Firewall Configuration

If the API is not accessible, check firewall rules on the Docker host:

```bash
# Linux (UFW)
sudo ufw allow 7860/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=7860/tcp --permanent
sudo firewall-cmd --reload

# Check if port is listening
sudo netstat -tlnp | grep 7860
# or
sudo ss -tlnp | grep 7860
```

### 7. Docker Network Binding (Advanced)

To bind to a specific interface (more secure):

```yaml
# docker-compose.yml
ports:
  - "192.168.1.100:7860:7860"  # Only accessible via this IP
```

Or bind to all interfaces explicitly:

```yaml
ports:
  - "0.0.0.0:7860:7860"  # Accessible from any network interface
```

### 8. Using DNS/Hostname

If your network has DNS:

```bash
# Access via hostname
curl http://dbnotebook-server.internal:7860/api/query/notebooks
```

### 9. Reverse Proxy (Production)

For production, use a reverse proxy like Nginx:

```nginx
# /etc/nginx/sites-available/dbnotebook
server {
    listen 80;
    server_name dbnotebook.yourcompany.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;  # For long LLM responses
    }
}
```

Then access via: `http://dbnotebook.yourcompany.com/api/query`

### 10. Testing Network Connectivity

```bash
# From client server, test connectivity
ping 192.168.1.100

# Test port is open
nc -zv 192.168.1.100 7860

# Test API endpoint (without key - should return 401)
curl -v http://192.168.1.100:7860/api/query/notebooks

# Test API endpoint (with key - should succeed)
curl http://192.168.1.100:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"
```

---

## Troubleshooting

### API Not Responding

```bash
# Check if server is running (include API key)
curl http://localhost:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"

# Check Docker logs
docker compose logs dbnotebook
```

### 401 Invalid or Missing API Key

```bash
# Verify you're using the correct API key
curl http://localhost:7860/api/query/notebooks \
  -H "X-API-Key: dbnotebook-secure-api-key-2026"

# Check the configured API key in docker-compose.yml
grep API_KEY docker-compose.yml
```

### Cannot Access from Remote Server

1. **Check host IP**: `hostname -I`
2. **Check port is listening**: `netstat -tlnp | grep 7860`
3. **Check firewall**: `sudo ufw status` or `sudo firewall-cmd --list-ports`
4. **Check Docker binding**: `docker port dbnotebook`
5. **Test locally first**: `curl http://localhost:7860/api/query/notebooks -H "X-API-Key: dbnotebook-secure-api-key-2026"`
6. **Verify API key**: Ensure `X-API-Key` header is included in all requests

### Slow Responses

- Check LLM provider status (OpenAI, Ollama)
- Reduce `max_sources` parameter
- Check `execution_time_ms` in response metadata

### 503 Pipeline Not Initialized

The server is still starting up. Wait a few seconds and retry.

### Connection Refused from Remote

- Verify Docker is exposing on `0.0.0.0`, not `127.0.0.1`
- Check firewall rules on Docker host
- Ensure no VPN/network restrictions blocking the port
