# DBNotebook - Product Requirements Document

## Overview

**Product**: DBNotebook - Multimodal RAG Sales Enablement System
**Version**: 1.2.0
**Last Updated**: 2025-12-27

A NotebookLM-style document intelligence platform combining:
- Document collection management (Notebooks)
- Multi-provider AI chat (Ollama, OpenAI, Anthropic, Gemini)
- Advanced hybrid retrieval (BM25 + Vector + Reranking)
- Visual content generation (Infographics, Mind Maps)
- Web content integration (Search + Scraping)
- Image understanding (Vision AI)

---

## Core Features

### 1. Notebook Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Create Notebook | Create named notebooks with optional description | P0 |
| List Notebooks | View all notebooks with document counts | P0 |
| Select Notebook | Switch between notebooks, isolate context | P0 |
| Update Notebook | Edit name and description | P1 |
| Delete Notebook | Remove notebook and associated data | P1 |
| Document Isolation | Each notebook has isolated embeddings | P0 |

### 2. Document Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Upload Documents | PDF, DOCX, PPTX, TXT, MD, EPUB, Images | P0 |
| Drag-and-Drop | Drop files onto upload area | P1 |
| Document Toggle | Enable/disable from RAG without deletion | P0 |
| Delete Document | Remove document and embeddings | P1 |
| Duplicate Detection | MD5 hash-based per notebook | P1 |
| Metadata Display | Filename, type, chunk count, upload time | P1 |

**Supported Formats**:
- Text: PDF, DOCX, DOC, TXT, MD, EPUB
- Presentations: PPTX, PPT
- Spreadsheets: XLSX, XLS, CSV
- Images: PNG, JPG, JPEG, WEBP (via Vision AI)

### 3. Chat & Conversation

| Feature | Description | Priority |
|---------|-------------|----------|
| Multi-turn Chat | Contextual conversation with history | P0 |
| Streaming Responses | Real-time token streaming | P0 |
| Source Attribution | Show document sources for answers | P0 |
| Persistent History | Save/load conversation per notebook | P1 |
| Edit Message | Edit and resend previous messages | P2 |
| Remove Message | Delete messages from history | P2 |
| Copy Response | Copy assistant response to clipboard | P1 |
| Clear Chat | Reset conversation | P1 |
| Stop Generation | Cancel mid-stream responses | P1 |

### 4. Multi-Provider Model Selection

| Provider | Models | API Key Required |
|----------|--------|-----------------|
| Ollama | llama3.1, mistral, neural-chat | No (local) |
| OpenAI | GPT-4, GPT-4o, GPT-3.5 | Yes |
| Anthropic | Claude 3 Opus/Sonnet/Haiku | Yes |
| Google | Gemini Pro, Gemini Vision | Yes |

### 5. Retrieval Strategies

| Strategy | Description | When Used |
|----------|-------------|-----------|
| Vector Only | Pure semantic search | ≤6 documents |
| Hybrid (BM25 + Vector) | Keyword + semantic | >6 documents |
| Query Fusion | 5 query variations + fusion | Ambiguous queries |
| Two-Stage + Rerank | BM25 + Vector → Reranker | Clear queries |

**Reranker**: mixedbread-ai/mxbai-rerank-large-v1

### 6. Web Search & Content Integration

| Feature | Description | Service |
|---------|-------------|---------|
| Web Search | Search web for content | Firecrawl API |
| URL Preview | Preview before importing | Jina Reader |
| Batch Import | Add multiple URLs | Jina Reader |
| Web Sources | Track as documents | Internal |

### 7. Image Understanding (Vision)

| Feature | Description | Providers |
|---------|-------------|-----------|
| Image Analysis | Analyze uploaded images | Gemini Vision, GPT-4V |
| Text Extraction | OCR-like extraction | Gemini Vision, GPT-4V |
| Brand Extraction | Colors, style from reference | Gemini Vision |

### 8. Content Studio (Generation)

| Generator | Output | Input |
|-----------|--------|-------|
| Infographic | Visual infographic PNG | Notebook content + prompt |
| Mind Map | Visual mind map PNG | Notebook content + prompt |

**Features**:
- Gallery browsing with thumbnails
- Download generated content
- Brand reference image support
- Custom prompts

### 9. Document Transformations

| Transformation | Description |
|----------------|-------------|
| Dense Summary | 300-500 word AI summary |
| Key Insights | 5-10 extracted insights |
| Reflection Questions | 5-7 study questions |

**Status Tracking**: pending → processing → completed/failed

---

## Data Models

### Notebook
```
- id: UUID
- name: string (required)
- description: string (optional)
- source_count: integer
- created_at: timestamp
- updated_at: timestamp
```

### Document (NotebookSource)
```
- source_id: UUID
- notebook_id: UUID (FK)
- filename: string
- file_hash: SHA256
- file_size: bigint
- file_type: string
- chunk_count: integer
- active: boolean (default true)
- upload_timestamp: timestamp
- transformation_status: enum
- dense_summary: text
- key_insights: JSONB
- reflection_questions: JSONB
```

### Message
```
- id: UUID
- role: 'user' | 'assistant'
- content: text
- timestamp: timestamp
- images: string[] (optional)
- sources: SourceCitation[] (optional)
```

### SourceCitation
```
- filename: string
- page: number (optional)
- score: number (optional)
- snippet: string (optional)
```

### GeneratedContent
```
- content_id: UUID
- content_type: 'infographic' | 'mindmap'
- title: string
- file_path: string
- thumbnail_path: string
- source_notebook_id: UUID (optional)
- created_at: timestamp
```

---

## User Flows

### Flow 1: First-Time User
1. Open app → See welcome empty state
2. Create first notebook → Enter name
3. Upload documents → Drag or click
4. Wait for processing → See progress
5. Ask first question → Get AI response
6. View sources → See citations

### Flow 2: Returning User
1. Open app → See notebook list
2. Select notebook → Load history
3. Continue conversation → Context preserved
4. Add more documents → Expand knowledge

### Flow 3: Web Research
1. Open web search panel
2. Search topic → Get results
3. Preview URLs → Check content
4. Add selected → Import content
5. Ask questions → Include web sources

### Flow 4: Content Creation
1. Open Content Studio
2. Select generator type
3. Optionally upload brand reference
4. Generate content
5. Preview in gallery
6. Download or delete

### Flow 5: Document Management
1. View document list
2. Toggle active status (eye icon)
3. Delete unwanted documents
4. Upload additional files
5. See updated chunk counts

---

## API Endpoints

### Chat
- `POST /api/chat` - Send message (streaming)

### Notebooks
- `GET /api/notebooks` - List notebooks
- `POST /api/notebooks` - Create notebook
- `GET /api/notebooks/{id}` - Get notebook
- `PUT /api/notebooks/{id}` - Update notebook
- `DELETE /api/notebooks/{id}` - Delete notebook

### Documents
- `GET /api/notebooks/{id}/sources` - List documents
- `POST /api/notebooks/{id}/sources` - Upload document
- `PUT /api/notebooks/{id}/sources/{source_id}` - Toggle active
- `DELETE /api/notebooks/{id}/sources/{source_id}` - Delete

### Web Content
- `POST /api/web/search` - Search web
- `POST /api/web/scrape-preview` - Preview URL
- `POST /api/notebooks/{id}/web-sources` - Add URLs

### Vision
- `GET /api/vision/providers` - List providers
- `POST /api/vision/analyze` - Analyze image

### Studio
- `GET /api/studio/gallery` - List content
- `POST /api/studio/generate` - Generate content
- `GET /api/studio/content/{id}` - Get content
- `GET /api/studio/content/{id}/file` - Download
- `DELETE /api/studio/content/{id}` - Delete

### Models
- `GET /api/models` - List models
- `POST /api/models/select` - Select model

---

## UI Components

### Layout
- Sidebar (280px fixed)
- Main content area (flex)
- Mobile responsive (collapsible sidebar)

### Sidebar Sections
1. Logo/Brand
2. Model Selector (dropdown)
3. Notebooks (list with cards)
4. Sources/Documents (list with toggle)
5. Web Search Panel (expandable)
6. Footer (settings, version)

### Chat Area
1. Header (notebook name, actions)
2. Message List (scrollable)
3. Input Box (textarea + actions)
4. Empty State (when no messages)

### Message Components
- User message (right-aligned or neutral)
- Assistant message (with sources)
- Source citations (expandable)
- Generated images (grid)
- Streaming indicator

---

## Technical Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://...
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB

# LLM
LLM_PROVIDER=ollama|openai|anthropic|gemini
LLM_MODEL=llama3.1:latest

# Embedding
EMBEDDING_PROVIDER=huggingface|openai
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# Retrieval
RETRIEVAL_STRATEGY=hybrid|semantic|keyword

# API Keys
OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
FIRECRAWL_API_KEY, JINA_API_KEY

# Vision
VISION_PROVIDER=gemini|openai
IMAGE_GENERATION_PROVIDER=gemini
```

### Defaults
- Chunk size: 512 tokens
- Chunk overlap: 32 tokens
- Context window: 8000 tokens
- Top-K retrieval: 20
- Rerank Top-K: 6
- Embedding dimension: 768 (nomic) or 1536 (OpenAI)

---

## Current UI Theme

**Name**: Deep Space Terminal
**Style**: Dark, neon accents, techy/gamified

| Element | Value |
|---------|-------|
| Background | #0a0a0f (void) |
| Surface | #12121a, #1a1a24, #222230 |
| Accent Primary | #00e5cc (cyan glow) |
| Accent Secondary | #7c3aed (purple nebula) |
| Text | #e2e8f0, #94a3b8, #64748b |
| Typography | JetBrains Mono (headers), DM Sans (body) |
| Effects | Glow shadows, gradients, noise overlay |

---

## Deployment

### Docker
- Multi-stage build (frontend + backend)
- PostgreSQL with pgvector
- External Ollama support
- GitHub Container Registry (ghcr.io)

### Ports
- App: 7860 (default)
- PostgreSQL: 5433 (Docker) or 5432 (local)
- Ollama: 11434

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-25 | Initial release |
| 1.1.0 | 2025-12-26 | Multi-file upload, eye toggle fix |
| 1.2.0 | 2025-12-26 | AI transformations, GHCR support |
