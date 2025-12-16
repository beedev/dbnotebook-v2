# Query Logging & Cost Tracking Implementation

**Date**: December 11, 2025
**Status**: ✅ COMPLETED
**Phase**: Week 4 - Query Logging & Observability

---

## Overview

Implemented comprehensive query logging system for token usage tracking, cost estimation, and usage analytics. Provides both in-memory logging and optional database persistence.

---

## Implementation Summary

### Files Created

#### 1. Query Logger Service
**Location**: `rag_chatbot/core/observability/query_logger.py`

**Key Features**:
- Token usage tracking (input/output tokens)
- Cost estimation based on model pricing
- Response time monitoring
- Usage statistics and analytics
- In-memory logging with optional database persistence
- Support for OpenAI, Anthropic, Google Gemini, and Ollama models

**Core Methods**:
```python
class QueryLogger:
    def log_query(
        notebook_id, user_id, query_text, model_name,
        prompt_tokens, completion_tokens, response_time_ms
    ) -> str

    def estimate_cost(model_name, prompt_tokens, completion_tokens) -> float

    def get_usage_stats(
        notebook_id=None, user_id=None,
        start_date=None, end_date=None
    ) -> Dict

    def get_recent_logs(limit=50) -> List[Dict]

    def get_model_pricing(model_name) -> Optional[Dict]

    def list_supported_models() -> List[str]
```

#### 2. Module Initialization
**Location**: `rag_chatbot/core/observability/__init__.py`

Exports `QueryLogger` class for easy import.

---

## Model Pricing Database

Comprehensive pricing information for major LLM providers:

### OpenAI (per 1M tokens)
| Model | Input | Output |
|-------|-------|--------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-4 | $30.00 | $60.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| text-embedding-ada-002 | $0.10 | $0.00 |

### Anthropic (per 1M tokens)
| Model | Input | Output |
|-------|-------|--------|
| claude-3-5-sonnet-20241022 | $3.00 | $15.00 |
| claude-3-5-haiku-20241022 | $0.80 | $4.00 |
| claude-3-opus-20240229 | $15.00 | $75.00 |

### Google Gemini (per 1M tokens)
| Model | Input | Output |
|-------|-------|--------|
| gemini-2.0-flash-exp | $0.00 | $0.00 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gemini-1.5-flash | $0.075 | $0.30 |

### Ollama (Local Models)
All local Ollama models: **$0.00** (no API costs)

---

## Usage Examples

### Basic Logging

```python
from rag_chatbot.core.observability import QueryLogger

# Initialize logger
logger = QueryLogger()

# Log a query
log_id = logger.log_query(
    notebook_id="notebook-123",
    user_id="user-456",
    query_text="What is RAG?",
    model_name="gpt-4o",
    prompt_tokens=150,
    completion_tokens=300,
    response_time_ms=1500
)

# Output:
# Query logged | Model: gpt-4o | Tokens: 450 (150 in, 300 out) | Time: 1500ms | Cost: $0.0034
```

### Cost Estimation

```python
# Estimate cost before making API call
cost = logger.estimate_cost("claude-3-5-sonnet-20241022", 200, 500)
print(f"Estimated cost: ${cost:.4f}")  # $0.0081
```

### Usage Statistics

```python
# Get overall usage statistics
stats = logger.get_usage_stats()
print(f"Total queries: {stats['total_queries']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Total cost: ${stats['total_cost']:.2f}")
print(f"Avg response time: {stats['avg_response_time']:.0f}ms")

# Breakdown by model
for model, data in stats['queries_by_model'].items():
    print(f"{model}: {data['count']} queries, ${data['cost']:.2f}")
```

### Filtered Statistics

```python
from datetime import datetime, timedelta

# Get stats for specific notebook
notebook_stats = logger.get_usage_stats(notebook_id="notebook-123")

# Get stats for date range
week_ago = datetime.utcnow() - timedelta(days=7)
weekly_stats = logger.get_usage_stats(
    start_date=week_ago,
    end_date=datetime.utcnow()
)
```

### Recent Query History

```python
# Get last 50 queries
recent = logger.get_recent_logs(limit=50)

for log in recent:
    print(f"{log['timestamp']} | {log['model_name']} | "
          f"{log['total_tokens']} tokens | ${log['estimated_cost']:.4f}")
```

---

## Integration with Pipeline

### Step 1: Initialize QueryLogger in Pipeline

**File**: `rag_chatbot/pipeline.py`

```python
from .core.observability import QueryLogger

class LocalRAGPipeline:
    def __init__(self, ...):
        # ... existing initialization ...
        self._query_logger = QueryLogger()
```

### Step 2: Log Queries After Streaming

```python
def query(self, mode: str, message: str, chatbot: list):
    """Query with logging."""
    start_time = time.time()

    # Execute query
    response = self._query_engine.stream_chat(message)

    # Calculate metrics
    response_time_ms = int((time.time() - start_time) * 1000)

    # Extract token counts (from LLM response metadata)
    prompt_tokens = getattr(response, 'prompt_tokens', 0)
    completion_tokens = getattr(response, 'completion_tokens', 0)

    # Log query
    self._query_logger.log_query(
        notebook_id=self._current_notebook_id or "default",
        user_id="default_user",
        query_text=message,
        model_name=self._default_model.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        response_time_ms=response_time_ms
    )

    return response
```

### Step 3: Expose Usage Statistics in UI

**File**: `rag_chatbot/ui/web.py`

```python
@app.route('/usage-stats', methods=['GET'])
def get_usage_stats():
    """Get usage statistics for current session."""
    stats = pipeline._query_logger.get_usage_stats()
    return jsonify(stats)

@app.route('/recent-queries', methods=['GET'])
def get_recent_queries():
    """Get recent query history."""
    limit = request.args.get('limit', 50, type=int)
    recent = pipeline._query_logger.get_recent_logs(limit=limit)
    return jsonify(recent)
```

---

## Database Persistence (Optional)

The QueryLogger supports optional database persistence when initialized with a database manager:

```python
from rag_chatbot.core.db import DatabaseManager

# Initialize with database
db_manager = DatabaseManager(database_url="postgresql://...")
logger = QueryLogger(db_manager=db_manager)

# Logs will be automatically stored in query_logs table
```

**Database Schema** (already defined in `models.py`):
```python
class QueryLog(Base):
    __tablename__ = "query_logs"
    log_id = Column(UUID, primary_key=True)
    notebook_id = Column(UUID, ForeignKey("notebooks.notebook_id"))
    user_id = Column(UUID, ForeignKey("users.user_id"))
    query_text = Column(Text)
    model_name = Column(String(100))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    response_time_ms = Column(Integer)
    timestamp = Column(TIMESTAMP)
```

---

## Benefits

### Cost Management
- **Token Usage Tracking**: Monitor token consumption per query
- **Cost Estimation**: Calculate API costs by model in real-time
- **Budget Monitoring**: Track spending trends over time
- **Model Comparison**: Compare costs across different LLM providers

### Performance Monitoring
- **Response Time Tracking**: Identify slow queries and bottlenecks
- **Usage Patterns**: Analyze peak usage times and query frequency
- **Performance Trends**: Monitor performance improvements over time

### Observability
- **Query History**: Complete audit trail of all queries
- **Model Usage**: Track which models are used most frequently
- **User Analytics**: Per-user and per-notebook usage statistics
- **Error Detection**: Identify failed queries and error patterns

---

## Next Steps

### Integration with LangSmith
The QueryLogger complements LangSmith tracing:
- **LangSmith**: Detailed trace data, intermediate steps, retrieval context
- **QueryLogger**: Token usage, cost tracking, aggregated statistics

Both systems can run simultaneously:
- LangSmith provides deep observability for debugging
- QueryLogger provides cost management and usage analytics

### UI Dashboard (Phase 5)
Create usage dashboard in Gradio UI:
- Real-time token usage display
- Cost tracking per session
- Query history viewer
- Performance metrics graphs
- Model comparison charts

### Cost Alerts (Optional)
Implement cost threshold alerts:
```python
def check_cost_threshold(stats: Dict, threshold: float):
    """Alert if costs exceed threshold."""
    if stats['total_cost'] > threshold:
        logger.warning(f"Cost threshold exceeded: ${stats['total_cost']:.2f}")
```

### Export to CSV/Excel (Optional)
Export usage statistics for reporting:
```python
import pandas as pd

def export_usage_to_csv(logger: QueryLogger, filename: str):
    """Export query logs to CSV."""
    logs = logger.get_recent_logs(limit=1000)
    df = pd.DataFrame(logs)
    df.to_csv(filename, index=False)
```

---

## Testing

### Unit Tests

```python
import pytest
from rag_chatbot.core.observability import QueryLogger

def test_cost_estimation():
    """Test cost calculation."""
    logger = QueryLogger()

    # Test OpenAI pricing
    cost = logger.estimate_cost("gpt-4o", 1000, 2000)
    assert cost == pytest.approx(0.0225)  # (1000/1M * 2.5) + (2000/1M * 10)

    # Test Ollama (free)
    cost = logger.estimate_cost("llama3.1", 1000, 2000)
    assert cost == 0.0

def test_usage_stats():
    """Test statistics calculation."""
    logger = QueryLogger()

    # Log test queries
    logger.log_query("nb-1", "user-1", "Test query 1", "gpt-4o", 100, 200, 1000)
    logger.log_query("nb-1", "user-1", "Test query 2", "gpt-4o", 150, 250, 1200)

    # Get stats
    stats = logger.get_usage_stats()
    assert stats['total_queries'] == 2
    assert stats['total_tokens'] == 700
    assert stats['avg_response_time'] == 1100.0
```

---

## Summary

✅ **Query Logger Service**: Fully implemented with token tracking and cost estimation
✅ **Model Pricing Database**: Comprehensive pricing for OpenAI, Anthropic, Gemini, Ollama
✅ **Usage Analytics**: Statistics calculation with filtering and aggregation
✅ **In-Memory Logging**: Fast logging with session-based storage
✅ **Database Support**: Optional PostgreSQL persistence for long-term storage
✅ **Cost Management**: Real-time cost tracking and budget monitoring
✅ **Documentation**: Complete usage examples and integration guide

The query logging system is ready for integration with the RAG pipeline. Next steps include UI integration (Phase 5) and comprehensive testing (Phase 6).
