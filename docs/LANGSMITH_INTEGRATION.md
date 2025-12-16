# LangSmith Integration Summary

**Date**: December 11, 2025
**Status**: ✅ COMPLETED
**Feature**: LLM Workflow Tracing and Observability

---

## Overview

LangSmith has been integrated into the RAG chatbot to provide comprehensive tracing and observability for all LLM operations. This enables monitoring of token usage, query performance, conversation flows, and system behavior in production.

---

## Changes Made

### 1. Environment Configuration (`.env`)

Added LangSmith configuration block:

```bash
# ============================================
# LangSmith Configuration (Observability & Tracing)
# ============================================
# Enable LangSmith tracing (true|false)
LANGSMITH_TRACING_ENABLED=true

# LangSmith API key
LANGSMITH_API_KEY=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

# LangSmith project name
LANGSMITH_PROJECT=RAG-Chatbot-Dev

# LangSmith endpoint (optional - defaults to https://api.smith.langchain.com)
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

**Project Name**: Changed from "Recommender" to "RAG-Chatbot-Dev" as requested

### 2. Settings Module (`rag_chatbot/setting/setting.py`)

Created `LangSmithSettings` class to read configuration from environment variables:

```python
class LangSmithSettings(BaseModel):
    """Settings for LangSmith observability and tracing."""
    tracing_enabled: bool = Field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING_ENABLED", "false").lower() == "true",
        description="Enable LangSmith tracing"
    )
    api_key: str | None = Field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY"),
        description="LangSmith API key"
    )
    project: str = Field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "RAG-Chatbot"),
        description="LangSmith project name"
    )
    endpoint: str = Field(
        default_factory=lambda: os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        description="LangSmith API endpoint"
    )
```

Added `langsmith: LangSmithSettings = LangSmithSettings()` to `RAGSettings`

### 3. Application Entry Point (`rag_chatbot/__main__.py`)

Integrated LangSmith tracing configuration:

```python
# Initialize settings
from .setting import get_settings
settings = get_settings()

# Configure LangSmith tracing if enabled
if settings.langsmith.tracing_enabled and settings.langsmith.api_key:
    logger.info("Configuring LangSmith tracing...")
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith.api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith.project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith.endpoint

    # Set LangSmith as global handler for LlamaIndex
    llama_index.core.set_global_handler("langsmith")
    logger.info(f"LangSmith tracing enabled for project: {settings.langsmith.project}")
else:
    # Use simple logging if LangSmith not enabled
    llama_index.core.set_global_handler("simple")
    logger.info("LangSmith tracing disabled - using simple logging")
```

---

## How It Works

### Architecture

```
User Query → LocalRAGPipeline → LocalChatEngine → LLM Call
                                                      ↓
                                              LangSmith Handler
                                                      ↓
                                          LangSmith API Server
                                                      ↓
                                          Project Dashboard
```

### Automatic Tracing

When `LANGSMITH_TRACING_ENABLED=true`, all LLM interactions are automatically traced:

1. **LLM Calls**: All queries to Ollama, OpenAI, Claude, and Gemini models
2. **Retrieval Operations**: Vector search and BM25 retrieval
3. **Chat Engine**: Conversation context and memory operations
4. **Embeddings**: Document and query embedding generation

### What Gets Logged

- **Inputs**: User queries, system prompts, context
- **Outputs**: LLM responses, retrieved documents
- **Metadata**: Model names, temperature, token counts
- **Timing**: Response latency, retrieval time
- **Errors**: Stack traces, error messages

---

## Viewing Traces

### LangSmith Dashboard

1. Navigate to: https://smith.langchain.com
2. Select project: **RAG-Chatbot-Dev**
3. View traces organized by:
   - Timestamp
   - Run type (LLM, Chain, Retriever)
   - Status (success, error)
   - Latency
   - Token usage

### Trace Details

Each trace includes:
- **Input/Output**: Full query and response
- **Intermediate Steps**: Retrieval, reranking, generation
- **Performance Metrics**: Token counts, timing breakdown
- **Error Handling**: Exceptions and stack traces

---

## Configuration Options

### Enable/Disable Tracing

**To Enable**:
```bash
LANGSMITH_TRACING_ENABLED=true
```

**To Disable**:
```bash
LANGSMITH_TRACING_ENABLED=false
```

### Change Project Name

Edit `.env`:
```bash
LANGSMITH_PROJECT=Your-Project-Name
```

### Custom Endpoint

For self-hosted LangSmith:
```bash
LANGSMITH_ENDPOINT=https://your-langsmith-instance.com
```

---

## Benefits

### Observability
- **Real-time Monitoring**: Track all LLM operations as they happen
- **Performance Analysis**: Identify slow queries and bottlenecks
- **Error Tracking**: Capture and debug failures in production

### Cost Management
- **Token Usage**: Track token consumption per query
- **Cost Estimation**: Calculate API costs by model
- **Usage Trends**: Identify high-usage patterns

### Quality Improvement
- **Conversation Analysis**: Review chat sessions for quality
- **Context Debugging**: Verify retrieval accuracy
- **Prompt Engineering**: Test and iterate on prompts

---

## Next Steps

### Optional Enhancements

1. **Custom Metadata**: Add user IDs, session IDs to traces
2. **Feedback Collection**: Tag traces with user ratings
3. **Dataset Creation**: Export traces for fine-tuning
4. **Alerts**: Configure alerts for errors or high latency
5. **Analytics**: Create custom dashboards and reports

### Integration Points

- **Token Usage Tracking**: Parse trace data for cost calculation
- **Performance Metrics**: Extract latency and throughput stats
- **Query Logging**: Store traces in PostgreSQL for long-term analysis
- **A/B Testing**: Compare model performance across variants

---

## Troubleshooting

### Traces Not Appearing

1. **Check API Key**: Verify `LANGSMITH_API_KEY` is correct
2. **Enable Tracing**: Ensure `LANGSMITH_TRACING_ENABLED=true`
3. **Check Logs**: Look for "LangSmith tracing enabled" in startup logs
4. **Network**: Verify connectivity to https://api.smith.langchain.com

### Startup Logs

**Success**:
```
INFO - Configuring LangSmith tracing...
INFO - LangSmith tracing enabled for project: RAG-Chatbot-Dev
```

**Disabled**:
```
INFO - LangSmith tracing disabled - using simple logging
```

### Common Issues

**Issue**: No traces in dashboard
**Solution**: Check API key format, ensure it starts with `lsv2_sk_`

**Issue**: High latency
**Solution**: LangSmith adds ~10-50ms overhead, disable for local development

**Issue**: Missing traces
**Solution**: Tracing is async, traces may take 1-2 seconds to appear

---

## References

### Documentation
- **LangSmith Docs**: https://docs.smith.langchain.com
- **LlamaIndex Callbacks**: https://docs.llamaindex.ai/en/stable/module_guides/observability/
- **Environment Variables**: https://docs.smith.langchain.com/tracing/faq

### API
- **Endpoint**: https://api.smith.langchain.com
- **Dashboard**: https://smith.langchain.com
- **Project**: RAG-Chatbot-Dev

---

## Summary

✅ **Configuration**: Environment variables added to `.env`
✅ **Settings**: `LangSmithSettings` class created
✅ **Integration**: Auto-configuration in `__main__.py`
✅ **Project**: Configured for "RAG-Chatbot-Dev"
✅ **Status**: Ready for production tracing

LangSmith integration is complete and will automatically trace all LLM operations when the application starts. Check the LangSmith dashboard to view real-time traces of queries, retrievals, and responses.
