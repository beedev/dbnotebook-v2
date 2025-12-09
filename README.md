# 🚀 Multimodal RAG - Sales Enablement System

![alt text](assets/demo.png)

A comprehensive Sales Enablement System built on a multimodal RAG (Retrieval-Augmented Generation) chatbot. Transform your document knowledge base into an intelligent sales assistant that generates elevator pitches, recommends offering bundles, and creates customer-specific use cases.

**Orchestrated by Bharath D and Developed by Claude**

---

## 📖 Table of Contents

- [⭐️ Key Features](#️-key-features)
- [🎯 Sales Enablement Capabilities](#-sales-enablement-capabilities)
- [💡 Architecture](#-architecture)
- [💻 Setup](#-setup)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Running the Application](#running-the-application)
- [🗺️ Roadmap](#️-roadmap)
- [🤝 Attribution](#-attribution)

---

## ⭐️ Key Features

### Core RAG Capabilities
- **Multi-Model Support**: Use any model from Huggingface, Ollama, OpenAI, Anthropic, or Google Gemini
- **Document Processing**: Handle PDFs, EPUB, TXT, DOCX, PPTX, and images (via OCR)
- **Hybrid Retrieval**: Combine BM25 and vector search with intelligent reranking
- **Persistent Storage**: ChromaDB vector store with metadata filtering
- **Modern UI**: Flask web interface with Gradio components

### Image Generation
- **Imagen Integration**: Generate images via Google Vertex AI (Imagen 3.0)
- **Text Overlays**: Add professional text overlays to generated images
- **Multiple Formats**: Support for JPG, PNG, WEBP with configurable aspect ratios

### Sales Enablement System (In Development)
- **Document Management**: Organize documents by IT Practice and Offerings
- **Query Intelligence**: Automatic classification of problem-solving vs. pitch queries
- **Offering Analysis**: AI-powered offering bundle recommendations
- **Pitch Generation**: Auto-generate elevator pitches and use cases
- **Customer Context**: Domain and customer-specific pitch customization

---

## 🎯 Sales Enablement Capabilities

### Document Organization
Group and manage sales collateral by:
- **IT Practices**: Digital, CIS, Cloud, etc. (user-defined)
- **Offerings**: Service offerings with descriptions and metadata
- **Selective Retrieval**: Query specific offerings or combinations

### Intelligent Query Modes

**Problem-Solving Mode**
```
Query: "Customer needs legacy mainframe modernization"
System: Analyzes all offerings → Recommends bundle → Generates pitch
```

**Pitch Mode**
```
Query: "Pitch Cloud Migration to ACME Corp in healthcare"
System: Uses selected offerings → Generates customer-specific pitch
```

### Automated Pitch Generation
Every response includes:
- 🎤 **Elevator Pitch**: 30-second hook (100 words)
- 📝 **Use Case**: Detailed implementation approach (500 words)
- 💡 **Talking Points**: Key value propositions
- 📊 **Implementation Strategy**: Phased approach with outcomes

---

## 💡 Architecture

```
User Query → Query Classifier → Mode Detection
                                     ↓
                    ┌────────────────┴────────────────┐
                    ↓                                 ↓
            Problem-Solving Mode              Pitch Mode
                    ↓                                 ↓
         Offering Analyzer                  Use Selected Offerings
                    ↓                                 ↓
         Recommend Bundle                   Retrieve Context
                    ↓                                 ↓
                    └────────────────┬────────────────┘
                                     ↓
                          Pitch Generator
                                     ↓
                    Elevator Pitch + Use Case
                                     ↓
                          Stream Response
```

### Tech Stack
- **LLM Framework**: LlamaIndex
- **Vector Store**: ChromaDB with metadata filtering
- **Embedding Models**: HuggingFace (nomic-embed-text-v1.5), OpenAI
- **LLM Providers**: Ollama, OpenAI, Anthropic Claude, Google Gemini
- **Image Generation**: Google Vertex AI (Imagen 3.0)
- **UI**: Flask + Gradio
- **Document Processing**: PyMuPDF, LangChain, AWS Textract (optional)

---

## 💻 Setup

### Prerequisites
- Python 3.9+
- Poetry (for dependency management)
- Ollama (for local models) - [Download](https://ollama.com/)
- Google Cloud Project with Vertex AI enabled (for image generation)
- Optional: Ngrok (for external access)

### Installation

#### 1. Clone Repository
```bash
git clone https://github.com/beedev/multimodal-rag.git
cd multimodal-rag
```

#### 2. Install Dependencies

**Using Poetry:**
```bash
poetry install
```

**Using pip:**
```bash
pip install .
```

**Using install script:**
```bash
source ./scripts/install.sh
```

#### 3. Set Up Ollama (for local models)
```bash
# macOS/Windows: Install from https://ollama.com/

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:latest
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env
```

**Key Configuration Options:**

```bash
# ============================================
# LLM Provider API Keys (optional)
# ============================================
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# ============================================
# Default Models
# ============================================
DEFAULT_LLM_MODEL=llama3.1:latest
DEFAULT_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# ============================================
# Image Generation (Imagen via Vertex AI)
# ============================================
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
IMAGE_GENERATION_PROVIDER=imagen
IMAGE_OUTPUT_DIR=outputs/images

# ============================================
# Model Provider Settings
# ============================================
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GEMINI_MODEL=gemini-2.0-flash-exp
OPENAI_MODEL=gpt-4-turbo

# ============================================
# Document Management
# ============================================
PERSIST_DOCUMENTS=true
MAX_DOCUMENTS=100
DOCUMENT_STORAGE_PATH=data/documents
```

For detailed configuration options, see `.env.example`.

### Running the Application

#### Local Development
```bash
# Using Python
python -m rag_chatbot --host localhost

# Using script
source ./scripts/run.sh
```

#### With Ngrok (External Access)
```bash
source ./scripts/run.sh --ngrok
```

#### Docker
```bash
docker compose up --build
```

**Access the application at:** `http://0.0.0.0:7860/`

---

## 🗺️ Roadmap

### Phase 1: Metadata Infrastructure (Week 1) ✅ Planned
- Create centralized metadata management system
- Design IT Practice and Offering schema
- Enhance document ingestion with metadata capture
- Update vector store for metadata filtering

### Phase 2: Retrieval & Filtering (Week 2)
- Implement offering-specific document retrieval
- ChromaDB metadata filtering integration
- Test filtered query methods

### Phase 3: Sales Intelligence (Week 3)
- Query classifier (problem-solving vs. pitch detection)
- Offering analyzer for bundle recommendations
- Test end-to-end offering analysis

### Phase 4: Pitch Generation (Week 4)
- Pitch generator with templates
- Sales orchestration workflow
- Elevator pitch + use case generation

### Phase 5: UI Implementation (Week 5)
- Upload form with IT Practice/Offering selection
- Offering library UI with multi-select
- Sales chat interface enhancements

### Phase 6: Polish & Optimization (Week 6)
- Response formatting and presentation
- Error handling and edge cases
- Performance optimization
- Comprehensive testing

### Future Enhancements
- [ ] Multilingual support for pitches
- [ ] Knowledge Graph for structured data
- [ ] MLX model support
- [ ] Advanced evaluation metrics
- [ ] Integration with CRM systems

---

## 🤝 Attribution

**Orchestrated by Bharath D**
**Developed by Claude (Anthropic)**

This project combines human vision and strategic planning with AI-powered development to create an intelligent sales enablement platform.

---

## 📚 Documentation

- **Setup Guide**: See [Environment Configuration](#environment-configuration)
- **API Documentation**: See `CLAUDE.md` for development guidance
- **Sales Enablement Plan**: See `.claude/plans/` directory

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=beedev/multimodal-rag&type=Date)](https://star-history.com/#beedev/multimodal-rag&Date)

---

## 📄 License

This project builds upon the original [rag-chatbot](https://github.com/datvodinh/rag-chatbot) project with significant enhancements for multimodal capabilities and sales enablement.
