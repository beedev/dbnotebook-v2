# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local RAG (Retrieval-Augmented Generation) chatbot for PDF documents using LlamaIndex, Ollama, and Gradio. Supports multiple document formats (PDF, EPUB, TXT, DOCX, PPTX, images) with a hybrid retrieval system combining BM25 and vector search.

## Development Commands

```bash
# Install dependencies (requires Poetry)
pip install .
# or
source ./scripts/install.sh

# Run locally (starts Ollama server if not running)
python -m rag_chatbot --host localhost
# or
source ./scripts/run.sh

# Run with ngrok for external access
source ./scripts/run.sh --ngrok

# Run in Docker
docker compose up --build

# Run tests
pytest
```

## Architecture

### Core Pipeline Flow

```
User Input → LocalRAGPipeline → LocalChatEngine → Retriever → LLM Response
                   ↓
            LocalDataIngestion (document processing)
                   ↓
            LocalVectorStore (ChromaDB)
```

### Key Components

**`rag_chatbot/pipeline.py`** - `LocalRAGPipeline` orchestrates the entire RAG workflow:
- Manages model selection (Ollama/OpenAI), embedding models, and system prompts
- Coordinates between ingestion, vector store, and chat engine
- Handles conversation history via `ChatMessage` objects

**`rag_chatbot/core/engine/`** - Chat engine and retrieval:
- `LocalChatEngine` - Switches between `SimpleChatEngine` (no docs) and `CondensePlusContextChatEngine` (with docs)
- `LocalRetriever` - Implements hybrid retrieval strategy:
  - Uses `RouterRetriever` to select between query fusion and two-stage retrieval based on document count
  - `TwoStageRetriever` combines BM25 + vector retrieval with reranking

**`rag_chatbot/core/ingestion/ingestion.py`** - `LocalDataIngestion` handles document processing:
- Supports PDF, EPUB, TXT, DOCX, PPTX, images (via AWS Textract)
- Uses `SentenceSplitter` for chunking with configurable overlap
- Caches processed nodes by filename

**`rag_chatbot/core/model/model.py`** - `LocalRAGModel` wraps LLM providers:
- Ollama models via `llama_index.llms.ollama.Ollama`
- OpenAI models (gpt-3.5-turbo, gpt-4) via `llama_index.llms.openai.OpenAI`

**`rag_chatbot/core/embedding/embedding.py`** - `LocalEmbedding` wraps embedding models:
- HuggingFace embeddings (default: `nomic-ai/nomic-embed-text-v1.5`)
- OpenAI embeddings (`text-embedding-ada-002`)

**`rag_chatbot/setting/setting.py`** - Pydantic settings classes:
- `RAGSettings` aggregates `OllamaSettings`, `RetrieverSettings`, `IngestionSettings`, `StorageSettings`
- Default LLM: `llama3.1:latest`, default embedding: `nomic-ai/nomic-embed-text-v1.5`

**`rag_chatbot/ui/ui.py`** - `LocalChatbotUI` Gradio interface:
- Multi-tab interface (Interface, Setting, Output)
- Handles document upload, model selection, chat modes (chat/QA)
- Streaming responses via `LLMResponse.stream_response()`

### Data Flow for Document Processing

1. Files uploaded via Gradio → moved to `data/data/`
2. `LocalDataIngestion.store_nodes()` extracts text (pymupdf for PDFs, langchain loaders for DOCX/PPTX)
3. Text filtered and chunked via `SentenceSplitter`
4. Embeddings generated and cached in `_node_store`
5. `LocalRetriever.get_retrievers()` builds retriever based on node count:
   - ≤6 nodes: `VectorIndexRetriever`
   - >6 nodes: `RouterRetriever` with fusion/two-stage options

### Retrieval Strategy

The retriever uses a router pattern with two strategies:
- **Fusion Retriever**: For ambiguous queries - generates multiple query variations, fuses BM25 + vector results
- **Two-Stage Retriever**: For clear queries - BM25 + vector retrieval followed by reranking (`mixedbread-ai/mxbai-rerank-large-v1`)

### Host Configuration

- `localhost` - Local development, auto-starts Ollama server
- `host.docker.internal` - Docker container (default), connects to host Ollama

## Key Defaults

- Ollama port: 11434
- Gradio UI: http://0.0.0.0:7860
- Chunk size: 512 tokens, overlap: 32
- Context window: 8000 tokens
- Similarity top-k: 20, rerank top-k: 6
