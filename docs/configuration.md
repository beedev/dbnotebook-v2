# Configuration Reference

Complete reference for all DBNotebook configuration options.

---

## Environment Variables

### Core Settings

```bash
# Application
FLASK_ENV=development          # development|production
FLASK_SECRET_KEY=your-secret   # Required for sessions
DEBUG=false                    # Enable debug mode

# Server
HOST=0.0.0.0
PORT=7860
```

---

## LLM Configuration

### Provider Selection

```bash
# Primary LLM provider
LLM_PROVIDER=ollama            # ollama|openai|anthropic|gemini|groq

# Model selection (provider-specific)
LLM_MODEL=llama3.1:latest      # Ollama
LLM_MODEL=gpt-4.1-mini           # OpenAI
LLM_MODEL=claude-sonnet-4-20250514     # Anthropic
LLM_MODEL=gemini-2.0-flash     # Google
LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct  # Groq
```

### Provider-Specific Settings

=== "Ollama"

    ```bash
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_TIMEOUT=300
    ```

=== "OpenAI"

    ```bash
    OPENAI_API_KEY=sk-...
    OPENAI_API_BASE=https://api.openai.com/v1  # Optional
    ```

=== "Anthropic"

    ```bash
    ANTHROPIC_API_KEY=sk-ant-...
    ```

=== "Google Gemini"

    ```bash
    GOOGLE_API_KEY=...
    GEMINI_MODEL=gemini-2.0-flash
    ```

=== "Groq"

    ```bash
    GROQ_API_KEY=gsk_...
    GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
    ```

### Context Window

```bash
CONTEXT_WINDOW=128000          # Model's max context (128K for llama3.1)
CHAT_TOKEN_LIMIT=32000         # Chat memory buffer limit
```

---

## Embedding Configuration

```bash
# Provider
EMBEDDING_PROVIDER=openai      # openai|huggingface

# Model
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5  # HuggingFace

# Dimension (must match model output)
PGVECTOR_EMBED_DIM=1536        # OpenAI: 1536, nomic: 768
```

### Common Embedding Models

| Provider | Model | Dimension |
|----------|-------|-----------|
| OpenAI | text-embedding-3-small | 1536 |
| OpenAI | text-embedding-3-large | 3072 |
| HuggingFace | nomic-ai/nomic-embed-text-v1.5 | 768 |
| HuggingFace | BAAI/bge-small-en-v1.5 | 384 |

---

## Database Configuration

### PostgreSQL

```bash
# Connection URL (preferred)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbnotebook_dev

# Or individual settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dbnotebook_dev
POSTGRES_USER=dbnotebook
POSTGRES_PASSWORD=dbnotebook
```

### pgvector Settings

```bash
PGVECTOR_EMBED_DIM=1536        # Must match embedding model
PGVECTOR_DISTANCE=cosine       # cosine|l2|inner_product
```

---

## Retrieval Configuration

### Strategy Selection

```bash
RETRIEVAL_STRATEGY=hybrid      # hybrid|semantic|keyword
```

| Strategy | Description | Best For |
|----------|-------------|----------|
| `hybrid` | BM25 + Vector fusion | General use (recommended) |
| `semantic` | Pure vector similarity | Conceptual queries |
| `keyword` | BM25 only | Exact term matching |

### Retrieval Parameters

Configured in `config/dbnotebook.yaml`:

```yaml
retrieval:
  similarity_top_k: 20         # Initial candidates
  retriever_weights: [0.5, 0.5]  # [BM25, Vector]
  fusion_mode: "dist_based_score"
  num_queries: 3               # Query expansion count
```

### Reranker Settings

```yaml
reranker:
  enabled: true
  model: "large"               # xsmall|base|large
  top_k: 10                    # Final results after reranking
```

| Model | Speed | Quality | Memory |
|-------|-------|---------|--------|
| `xsmall` | Fastest | Good | ~100MB |
| `base` | Medium | Better | ~300MB |
| `large` | Slowest | Best | ~1.2GB |

---

## RAPTOR Configuration

Configured in `config/dbnotebook.yaml` under the `raptor:` section:

### Tree Building

```yaml
tree_building:
  max_tree_depth: 4            # Maximum levels
  min_nodes_to_cluster: 5      # Min nodes to create level
  batch_size: 50               # Nodes per batch
  max_concurrent_summaries: 3  # Parallel summarization
```

### Clustering

```yaml
clustering:
  min_cluster_size: 3
  max_cluster_size: 10
  max_clusters: 50
  gmm_probability_threshold: 0.3
```

### Summarization

```yaml
summarization:
  max_input_tokens: 6000
  summary_max_tokens: 500
  max_chunks_per_summary: 10
```

### Level Retrieval

```yaml
level_retrieval:
  summary_query_levels: [0, 1, 2, 3]
  detail_query_levels: [0, 1]
  top_k_per_level: 6
  min_similarity_threshold: 0.3
```

### Quick Presets

```yaml
presets:
  fast:
    tree_building:
      max_tree_depth: 2
    summarization:
      summary_max_tokens: 300

  thorough:
    tree_building:
      max_tree_depth: 5
    summarization:
      summary_max_tokens: 800
```

---

## Document Processing

Configured in `config/dbnotebook.yaml` under the `ingestion:` section:

### Chunking

```yaml
chunking:
  chunk_size: 512              # Tokens per chunk
  chunk_overlap: 32            # Overlap between chunks
  chunking_regex: "[^,.;]+[,.;]?"
  paragraph_sep: "\n \n"
```

### Embedding

```yaml
embedding:
  batch_size: 8                # Embeddings per batch
  cache_folder: "data/huggingface"
```

---

## Vision & Image Generation

### Vision Provider

```bash
VISION_PROVIDER=gemini         # gemini|openai

# Gemini Vision
GEMINI_VISION_MODEL=gemini-2.0-flash-exp

# OpenAI Vision
OPENAI_VISION_MODEL=gpt-4o
```

### Image Generation

```bash
IMAGE_GENERATION_PROVIDER=gemini

# Gemini Imagen
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
# Alternative: imagen-4.0-generate-001

# Output settings
IMAGE_OUTPUT_DIR=outputs/images
MAX_IMAGE_SIZE_MB=10
SUPPORTED_IMAGE_FORMATS=jpg,jpeg,png,webp
```

---

## Web Search & Scraping

```bash
# Firecrawl (web search)
FIRECRAWL_API_KEY=fc-...

# Jina Reader (scraping) - optional
JINA_API_KEY=jina_...         # Higher rate limits
```

---

## SQL Chat Configuration

### Connection Security

```bash
# Encryption key for stored credentials
SQL_CHAT_ENCRYPTION_KEY=your-fernet-key

# Skip read-only check (dev only!)
SQL_CHAT_SKIP_READONLY_CHECK=false
```

### Few-Shot Learning

```bash
FEW_SHOT_MAX_EXAMPLES=100000   # Max SQL examples
```

### Query Limits

Configured in `config/dbnotebook.yaml` under the `sql_chat:` section:

```yaml
query:
  max_rows: 10000              # Max result rows
  timeout_seconds: 30          # Query timeout
  max_correction_attempts: 3   # Auto-correction retries
```

---

## Excel Analytics

```bash
# File limits
MAX_ANALYTICS_FILE_SIZE_MB=50
MAX_ANALYTICS_ROWS=100000
```

---

## Authentication

```bash
# Session management
FLASK_SECRET_KEY=your-secret-key  # Required!

# RBAC
RBAC_STRICT_MODE=false         # Enable strict access control

# API authentication
API_KEY=your-api-key           # For /api/query endpoint
```

### Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

!!! warning "Change Default Password"
    Always change the default admin password in production.

---

## Logging

```bash
LOG_LEVEL=INFO                 # DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json                # json|text
LOG_FILE=logs/dbnotebook.log
```

---

## Docker Configuration

### docker-compose.yml

```yaml
services:
  dbnotebook:
    environment:
      - DATABASE_URL=postgresql://dbnotebook:dbnotebook@db:5432/dbnotebook
      - OLLAMA_HOST=http://host.docker.internal:11434
    ports:
      - "7007:7860"
    volumes:
      - ./dbnotebook:/app/dbnotebook    # Hot reload
      - ./config:/app/config            # Config files
```

### Volume Mounts

| Mount | Purpose |
|-------|---------|
| `./dbnotebook:/app/dbnotebook` | Backend hot reload |
| `./config:/app/config` | Configuration files |
| `./uploads:/app/uploads` | Uploaded documents |
| `./outputs:/app/outputs` | Generated content |

---

## Configuration Files

### File Locations

| File | Purpose |
|------|---------|
| `.env` | Environment variables |
| `config/dbnotebook.yaml` | Unified configuration (ingestion, retrieval, RAPTOR, SQL Chat) |
| `config/models.yaml` | Model configurations for UI dropdown |

### Loading Configuration

```python
from dbnotebook.core.config import get_config_value

# Get nested value with default
chunk_size = get_config_value(
    'ingestion', 'chunking', 'chunk_size',
    default=512
)
```

---

## Performance Tuning

### High-Traffic Deployments

```bash
# Increase connection pool
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=20

# Enable caching
CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

### Memory Optimization

```bash
# Reduce embedding batch size
EMBEDDING_BATCH_SIZE=4

# Use smaller reranker
RERANKER_MODEL=xsmall

# Limit context
CHAT_TOKEN_LIMIT=16000
```

### GPU Acceleration

```bash
# For HuggingFace embeddings
CUDA_VISIBLE_DEVICES=0
HF_DEVICE=cuda
```

---

## Example Configurations

### Minimal (Local Development)

```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:latest
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://dbnotebook:dbnotebook@localhost:5432/dbnotebook_dev
```

### Production (Cloud)

```bash
FLASK_ENV=production
FLASK_SECRET_KEY=<strong-random-key>
LLM_PROVIDER=groq
LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_API_KEY=gsk_...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@db.example.com:5432/dbnotebook
RBAC_STRICT_MODE=true
```

### High-Quality RAG

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1
RETRIEVAL_STRATEGY=hybrid
RERANKER_MODEL=large
RAPTOR_ENABLED=true
```
