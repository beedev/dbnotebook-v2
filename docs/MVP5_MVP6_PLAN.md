# MVP 5 & 6 Implementation Plan

> **Bharath Persona Active**: Quality-driven development with approval gates

---

## MVP 5: Plugin Architecture (1-2 days)

### Objective
Create abstract interfaces for swappable components, enabling configuration-driven architecture.

### New Directory Structure
```
rag_chatbot/core/
├── interfaces/           # Abstract base classes
│   ├── __init__.py
│   ├── retrieval.py      # RetrievalStrategy interface
│   ├── llm.py            # LLMProvider interface
│   ├── embedding.py      # EmbeddingProvider interface
│   └── processor.py      # ContentProcessor interface
├── strategies/           # Retrieval implementations
│   ├── __init__.py
│   ├── hybrid.py         # Hybrid BM25 + Vector
│   ├── semantic.py       # Pure vector search
│   └── keyword.py        # Pure BM25/keyword
├── providers/            # LLM provider implementations
│   ├── __init__.py
│   ├── ollama.py         # Ollama local models
│   ├── openai.py         # OpenAI API
│   ├── anthropic.py      # Claude API
│   └── gemini.py         # Google Gemini
└── registry.py           # Plugin registry & factory
```

### Interface Definitions

#### 1. RetrievalStrategy
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from llama_index.core.schema import NodeWithScore

class RetrievalStrategy(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> List[NodeWithScore]:
        """Retrieve relevant nodes for a query."""
        pass

    @abstractmethod
    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        pass
```

#### 2. LLMProvider
```python
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion for prompt."""
        pass

    @abstractmethod
    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """Stream completion tokens."""
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """Return model name, context window, pricing."""
        pass
```

#### 3. EmbeddingProvider
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass
```

#### 4. ContentProcessor
```python
class ContentProcessor(ABC):
    @abstractmethod
    def process(self, content: bytes, filename: str) -> List[Document]:
        """Process file content into documents."""
        pass

    @abstractmethod
    def supported_types(self) -> List[str]:
        """Return list of supported file extensions."""
        pass
```

### Plugin Registry
```python
class PluginRegistry:
    _strategies: Dict[str, Type[RetrievalStrategy]] = {}
    _providers: Dict[str, Type[LLMProvider]] = {}
    _embeddings: Dict[str, Type[EmbeddingProvider]] = {}
    _processors: Dict[str, Type[ContentProcessor]] = {}

    @classmethod
    def register_strategy(cls, name: str, strategy: Type[RetrievalStrategy]):
        cls._strategies[name] = strategy

    @classmethod
    def get_strategy(cls, name: str, **kwargs) -> RetrievalStrategy:
        return cls._strategies[name](**kwargs)

    # Similar for providers, embeddings, processors
```

### Configuration Example (.env)
```
# Retrieval Strategy
RETRIEVAL_STRATEGY=hybrid  # hybrid|semantic|keyword

# LLM Provider
LLM_PROVIDER=openai        # ollama|openai|anthropic|gemini
LLM_MODEL=gpt-4-turbo

# Embedding Provider
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
```

---

## MVP 6: UI/UX Polish & Production (1-2 days)

### Objective
Professional, polished interface with excellent UX and production-ready features.

### UI/UX Improvements

#### 1. Notebook Management Panel (Left Sidebar)
```
┌─────────────────────────────────┐
│ 📓 Notebooks            [+ New] │
├─────────────────────────────────┤
│ 🔍 Search notebooks...          │
├─────────────────────────────────┤
│ ● Sales Playbook         (5) 📄 │
│   Marketing Docs         (3) 📄 │
│   Product Specs          (8) 📄 │
│   Customer Cases         (2) 📄 │
└─────────────────────────────────┘
│ Selected: Sales Playbook        │
│ ┌─────────────────────────────┐ │
│ │ Documents:                  │ │
│ │ • pitch_deck.pdf      [🗑️]  │ │
│ │ • objections.docx     [🗑️]  │ │
│ │ • pricing.xlsx        [🗑️]  │ │
│ │ • case_study_1.pdf    [🗑️]  │ │
│ │ • case_study_2.pdf    [🗑️]  │ │
│ └─────────────────────────────┘ │
│ [+ Add Documents]               │
└─────────────────────────────────┘
```

#### 2. Chat Interface (Main Panel)
```
┌─────────────────────────────────────────────────────────┐
│ 💬 Chat with: Sales Playbook                    [Clear] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 👤 What are the main objection handling tips?   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🤖 Based on the documents, here are the key     │   │
│  │    objection handling strategies:               │   │
│  │                                                 │   │
│  │    1. **Price Objections**: Focus on value...  │   │
│  │    2. **Competition**: Highlight unique...     │   │
│  │                                                 │   │
│  │    **Sources:**                                 │   │
│  │    - [objections.docx] - Section 3             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ [📎] Type your message...                      [Send ➤] │
└─────────────────────────────────────────────────────────┘
```

#### 3. Loading States
- **Document upload**: Progress bar with percentage
- **Processing**: Animated spinner with "Processing documents..."
- **Chat response**: Typing indicator with streaming text
- **Notebook switching**: Skeleton loader

#### 4. Error Handling UI
- Toast notifications for errors (top-right, auto-dismiss)
- Inline validation for forms
- Retry buttons for failed operations
- Friendly error messages (not technical jargon)

#### 5. Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Send message |
| `Ctrl+N` | New notebook |
| `Ctrl+U` | Upload documents |
| `Ctrl+K` | Focus search |
| `Escape` | Close modals |
| `↑` / `↓` | Navigate chat history |

#### 6. Search & Sorting
- **Notebook search**: Filter notebooks by name
- **Document search**: Search within notebook documents
- **Sort options**: Name, Date added, Size, Type
- **Filter by type**: PDF, DOCX, TXT, etc.

#### 7. Responsive Design
- Mobile-friendly sidebar (collapsible)
- Touch-friendly buttons (44px min)
- Readable text on all screen sizes

### Production Features

#### 1. Health Check Endpoint
```python
@app.route("/api/health")
def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": check_db_connection(),
        "ollama": check_ollama_status(),
        "uptime": get_uptime()
    }
```

#### 2. API Improvements
- Rate limiting (100 req/min)
- Request validation
- Consistent error responses
- API versioning (/api/v1/)

#### 3. Performance
- Lazy loading for document lists
- Debounced search input
- Cached notebook list
- Optimistic UI updates

---

## Implementation Order

### Day 1: MVP 5 - Plugin Architecture
1. Create interface definitions (2 hrs)
2. Implement plugin registry (1 hr)
3. Migrate existing code to use interfaces (2 hrs)
4. Add configuration loading (1 hr)
5. Test with different providers (1 hr)

### Day 2: MVP 6 - UI/UX
1. Redesign sidebar with document list (2 hrs)
2. Add loading states & error handling (1.5 hrs)
3. Implement keyboard shortcuts (1 hr)
4. Add search & sorting (1.5 hrs)
5. Health check & API polish (1 hr)
6. Responsive design fixes (1 hr)

---

## Files to Create/Modify

### MVP 5 (New Files)
- `rag_chatbot/core/interfaces/__init__.py`
- `rag_chatbot/core/interfaces/retrieval.py`
- `rag_chatbot/core/interfaces/llm.py`
- `rag_chatbot/core/interfaces/embedding.py`
- `rag_chatbot/core/interfaces/processor.py`
- `rag_chatbot/core/strategies/__init__.py`
- `rag_chatbot/core/strategies/hybrid.py`
- `rag_chatbot/core/providers/__init__.py`
- `rag_chatbot/core/providers/openai.py`
- `rag_chatbot/core/providers/ollama.py`
- `rag_chatbot/core/registry.py`

### MVP 6 (Modify)
- `rag_chatbot/templates/index.html` - Major UI overhaul
- `rag_chatbot/ui/web.py` - New endpoints, health check
- `rag_chatbot/static/css/` - New styles (if separated)
- `rag_chatbot/static/js/` - New JS modules (if separated)

---

## Approval Required

Please review this plan and confirm:
1. ✅ MVP 5 scope is correct?
2. ✅ MVP 6 UI/UX covers your needs?
3. ✅ Implementation order is acceptable?
4. ✅ Any additional requirements?

Once approved, I'll proceed with implementation.
