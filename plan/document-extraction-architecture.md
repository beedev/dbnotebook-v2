# DocuAgent - Intelligent Document Processing (IDP)

## Standalone Agentic Document Extraction Application

---

## 1. Executive Summary

**Project Name**: DocuAgent (working title)

**Goal**: Build a **standalone** Intelligent Document Processing (IDP) application using agentic architecture - autonomous agents with tool use, planning, and reasoning that extract structured data from documents with high accuracy.

**Project Type**: New standalone application (not a DBNotebook module)

**Base Code**: Fork relevant components from DBNotebook (LLM providers, Vision providers, settings management)

**Core Requirements**:
- R1: Intuitive UI with minimal user friction
- R2: Full API access for programmatic use
- R3: Support PDF, JPG, and scanned documents
- R4: High accuracy extraction (~98%+) via agentic reasoning
- R5: Extensible document types via schema management
- R6: **Autonomous schema detection** (agent can identify document type)
- R7: **Transparent reasoning** (visible chain-of-thought for debugging)
- R8: **Standalone deployment** (independent of any other application)

---

## 2. Project Setup

### 2.1 New Project Structure

```
docuagent/                          # New project root
├── README.md
├── pyproject.toml                  # Python project config
├── requirements.txt
├── .env.example
├── alembic/                        # Database migrations
│   ├── alembic.ini
│   └── versions/
├── config/
│   └── schemas.yaml                # Default schema definitions
├── docuagent/                      # Main package
│   ├── __init__.py
│   ├── __main__.py                 # Entry point
│   ├── settings.py                 # Configuration (from DBNotebook)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── model/                  # LLM providers (copy from DBNotebook)
│   │   │   ├── __init__.py
│   │   │   └── model.py            # LocalRAGModel adapted
│   │   ├── vision/                 # Vision providers (copy from DBNotebook)
│   │   │   ├── __init__.py
│   │   │   └── vision_manager.py
│   │   ├── db/                     # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── models.py           # SQLAlchemy models
│   │   ├── auth/                   # Authentication (simplified from DBNotebook)
│   │   │   ├── __init__.py
│   │   │   └── auth_service.py
│   │   └── extraction/             # NEW: Agentic extraction
│   │       ├── __init__.py
│   │       ├── service.py          # ExtractionService
│   │       ├── agents/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── orchestrator.py
│   │       │   ├── analyzer.py
│   │       │   ├── extractor.py
│   │       │   └── validator.py
│   │       ├── tools/
│   │       │   ├── __init__.py
│   │       │   ├── document_tools.py
│   │       │   ├── table_tools.py
│   │       │   ├── ocr_tools.py
│   │       │   ├── parsing_tools.py
│   │       │   ├── validation_tools.py
│   │       │   ├── schema_tools.py
│   │       │   └── storage_tools.py
│   │       ├── document_processor.py
│   │       ├── schema_manager.py
│   │       └── types.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── extraction.py       # /api/extraction/*
│   │       ├── schemas.py          # /api/schemas/*
│   │       └── auth.py             # /api/auth/*
│   └── ui/
│       ├── __init__.py
│       └── web.py                  # Flask app factory
├── frontend/                       # React frontend (new)
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Upload/
│   │   │   ├── Review/
│   │   │   ├── Manage/
│   │   │   └── SchemaEditor/
│   │   ├── contexts/
│   │   └── types/
│   └── public/
├── tests/
│   ├── test_agents/
│   ├── test_tools/
│   └── test_api/
└── scripts/
    └── init_schemas.py             # Initialize default schemas
```

### 2.2 Files to Copy from DBNotebook

**Complete file paths for copying to new project:**

```
# ===========================================
# SETTINGS & CONFIG
# ===========================================
/Users/bharath/Desktop/dbn-v2/dbnotebook/setting/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/setting/setting.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/config/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/config/config_loader.py
/Users/bharath/Desktop/dbn-v2/config/models.yaml

# ===========================================
# LLM MODEL MANAGER
# ===========================================
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/model/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/model/model.py

# ===========================================
# VISION PROVIDERS (for OCR)
# ===========================================
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/vision/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/vision/vision_manager.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/providers/gemini_vision.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/providers/openai_vision.py

# ===========================================
# AUTH SERVICE
# ===========================================
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/auth/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/auth/auth_service.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/auth/rbac.py

# ===========================================
# DATABASE BASE
# ===========================================
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/db/__init__.py
/Users/bharath/Desktop/dbn-v2/dbnotebook/core/db/db.py

# ===========================================
# ALEMBIC TEMPLATE (structure only)
# ===========================================
/Users/bharath/Desktop/dbn-v2/alembic.ini
/Users/bharath/Desktop/dbn-v2/alembic/env.py
/Users/bharath/Desktop/dbn-v2/alembic/script.py.mako
/Users/bharath/Desktop/dbn-v2/alembic/README

# ===========================================
# PROJECT FILES
# ===========================================
/Users/bharath/Desktop/dbn-v2/.env.example
/Users/bharath/Desktop/dbn-v2/requirements.txt

# ===========================================
# ARCHITECTURE PLAN
# ===========================================
/Users/bharath/Desktop/dbn-v2/plan/document-extraction-architecture.md
```

### 2.3 File Modifications After Copy

| Component | Source Path | Modifications |
|-----------|-------------|---------------|
| **Settings** | `setting/setting.py` | Remove RAG-specific settings (ollama, raptor, etc.), add extraction settings |
| **LLM Model** | `core/model/model.py` | Keep as-is (multi-provider support works) |
| **Vision Manager** | `core/vision/vision_manager.py` | Keep as-is |
| **Database** | `core/db/db.py` | Remove notebook-specific pool settings, simplify |
| **Auth Service** | `core/auth/auth_service.py` | Keep as-is |
| **Config Loader** | `core/config/config_loader.py` | Update paths for new project structure |
| **models.yaml** | `config/models.yaml` | Remove reranker section, keep LLM providers |
| **alembic.ini** | `alembic.ini` | Update database name to `docuagent` |
| **alembic/env.py** | `alembic/env.py` | Update imports for new package name |
| **.env.example** | `.env.example` | Simplify to extraction-only settings |
| **requirements.txt** | `requirements.txt` | Remove RAG deps, add `pymupdf4llm` |

### 2.3 New Code to Write

| Component | Description |
|-----------|-------------|
| **Agents** | All 4 agents (Orchestrator, Analyzer, Extractor, Validator) |
| **Tools** | All 15+ tools in the tool registry |
| **ExtractionService** | Main orchestration service |
| **SchemaManager** | Schema CRUD and validation |
| **DocumentProcessor** | PyMuPDF4LLM wrapper |
| **API Routes** | `/api/extraction/*`, `/api/schemas/*` |
| **Frontend** | New React UI for 3-step workflow |
| **Database Models** | `extraction_schemas`, `extractions`, `extraction_edits` |

### 2.4 Dependencies

```toml
# pyproject.toml
[project]
name = "docuagent"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # LLM Providers (from DBNotebook)
    "llama-index>=0.10.0",
    "llama-index-llms-openai",
    "llama-index-llms-anthropic",
    "llama-index-llms-gemini",
    "llama-index-llms-groq",
    "llama-index-llms-ollama",

    # Vision
    "google-generativeai",
    "openai",

    # Document Processing
    "pymupdf4llm>=0.0.10",
    "pymupdf>=1.24.0",
    "Pillow",

    # Web Framework
    "flask>=3.0.0",
    "flask-cors",

    # Database
    "sqlalchemy>=2.0.0",
    "psycopg2-binary",
    "alembic",

    # Auth
    "bcrypt",
    "pyjwt",

    # Utilities
    "python-dotenv",
    "pydantic>=2.0.0",
    "pyyaml",
    "backoff",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "black",
    "ruff",
]
```

---

## 3. Architecture Overview

### 3.1 Agentic vs Pipeline Architecture

### Why Agentic?

| Aspect | Pipeline (Previous) | Agentic (New) |
|--------|---------------------|---------------|
| **Decision Making** | Deterministic routing | LLM decides strategy |
| **Schema Selection** | User must specify | Agent auto-detects |
| **Tool Use** | None | Agent calls tools |
| **Error Handling** | Fixed retry logic | Agent reasons about errors |
| **Complex Documents** | Struggles | Agent adapts strategy |
| **Accuracy** | ~95% | ~98% |
| **Cost** | 1x | 3-5x |
| **Transparency** | Black box | Visible reasoning trace |

### Agentic Architecture Principles

1. **ReAct Pattern**: Reasoning + Acting in iterative loops
2. **Tool Use**: LLM calls functions to interact with documents
3. **Planning**: Agent creates extraction plan before executing
4. **Self-Reflection**: Agent validates own work and corrects errors
5. **Autonomy**: Minimal human intervention required

---

### 3.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENTIC EXTRACTION SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATOR AGENT                           │   │
│  │           Coordinates workflow, manages agent handoffs            │   │
│  └─────────────────────────────┬────────────────────────────────────┘   │
│                                │                                         │
│          ┌─────────────────────┼─────────────────────┐                  │
│          │                     │                     │                  │
│          ▼                     ▼                     ▼                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   ANALYZER   │     │  EXTRACTOR   │     │  VALIDATOR   │            │
│  │    AGENT     │     │    AGENT     │     │    AGENT     │            │
│  │              │     │              │     │              │            │
│  │ • Classify   │     │ • Extract    │     │ • Validate   │            │
│  │ • Plan       │     │ • Use tools  │     │ • Cross-check│            │
│  │ • Route      │     │ • Reason     │     │ • Correct    │            │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘            │
│         │                    │                    │                     │
│         └────────────────────┼────────────────────┘                     │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         TOOL LAYER                                │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │   │
│  │  │read_page│ │extract_ │ │  ocr_   │ │validate_│ │ lookup_ │    │   │
│  │  │         │ │ table   │ │ region  │ │  math   │ │ schema  │    │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │   │
│  │  │ get_    │ │ check_  │ │compare_ │ │ flag_   │ │ store_  │    │   │
│  │  │metadata │ │ format  │ │ values  │ │ review  │ │ result  │    │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    SHARED INFRASTRUCTURE                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │ PostgreSQL │  │   LLM      │  │   Vision   │  │ PyMuPDF4LLM│  │   │
│  │  │ (schemas,  │  │ Providers  │  │ Providers  │  │  (tables)  │  │   │
│  │  │  results)  │  │ (existing) │  │ (existing) │  │            │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Agentic Components

### 4.1 Agent Definitions

### 4.1 Orchestrator Agent

**Role**: Workflow coordinator, manages agent handoffs and overall extraction lifecycle.

**Responsibilities**:
- Receive document and optional schema hint from user
- Dispatch to Analyzer Agent for classification
- Route to Extractor Agent with plan
- Trigger Validator Agent for quality check
- Handle retries and escalations
- Return final result or flag for human review

**System Prompt**:
```
You are the Orchestrator Agent for document extraction. Your job is to:
1. Coordinate the extraction workflow between specialized agents
2. Ensure each agent completes its task before proceeding
3. Handle errors gracefully and retry with adjusted strategies
4. Track the overall confidence and flag documents needing human review

You have access to these agents:
- analyzer: Classifies documents and creates extraction plans
- extractor: Extracts data using tools
- validator: Validates extracted data for accuracy

Always maintain a reasoning trace explaining your decisions.
```

---

### 4.2 Analyzer Agent

**Role**: Document classifier, extraction planner, strategy selector.

**Responsibilities**:
- Analyze document structure (pages, tables, images, text regions)
- Classify document type (invoice, resume, contract, PO, SOW, or unknown)
- Select or suggest appropriate schema
- Create extraction plan (which pages, what strategy per section)
- Identify potential challenges (scanned, handwritten, complex tables)

**Tools Available**:
- `get_document_metadata()` - Page count, file type, dimensions
- `read_page(page_num)` - Get text/markdown from specific page
- `detect_tables(page_num)` - Find tables and their structure
- `lookup_schema(name)` - Get schema definition
- `list_schemas()` - List available schemas

**System Prompt**:
```
You are the Analyzer Agent. Your job is to understand documents before extraction.

For each document:
1. First, call get_document_metadata() to understand structure
2. Read the first page to identify document type
3. Look for key indicators:
   - Invoice: "Invoice", "Bill To", "Total Due", line items
   - Resume: Name at top, "Experience", "Education", contact info
   - Contract: "Agreement", parties, signatures, legal language
   - Purchase Order: "PO Number", "Ship To", item quantities
   - SOW: "Scope of Work", deliverables, milestones
4. If confident, lookup_schema() for that type
5. If uncertain, explain what you see and suggest best match

Create an extraction plan:
{
  "document_type": "invoice",
  "confidence": 0.95,
  "schema": "invoice",
  "plan": [
    {"page": 1, "strategy": "header_extraction", "fields": ["invoice_number", "date", "vendor"]},
    {"page": 1-2, "strategy": "table_extraction", "fields": ["line_items"]},
    {"page": 2, "strategy": "footer_extraction", "fields": ["subtotal", "tax", "total"]}
  ],
  "challenges": ["complex multi-page table", "handwritten notes in margin"],
  "reasoning": "Document has clear invoice header with 'INVOICE' title, vendor logo, and line item table..."
}
```

**ReAct Example**:
```
Thought: I need to understand this document before extraction. Let me check metadata first.
Action: get_document_metadata()
Observation: {"pages": 3, "file_type": "pdf", "has_images": true, "text_extractable": true}

Thought: 3 pages with extractable text. Let me read the first page to classify.
Action: read_page(1)
Observation: "INVOICE\n\nFrom: Acme Corp\n123 Business St...\n\nInvoice #: INV-2024-001\nDate: January 15, 2024\n\nBill To:\nWidget Inc..."

Thought: Clear invoice format with standard fields. Let me check for tables.
Action: detect_tables(1)
Observation: {"tables": [{"rows": 5, "columns": 4, "bbox": [100, 400, 500, 600], "headers": ["Description", "Qty", "Price", "Amount"]}]}

Thought: Found a line item table. This is definitely an invoice. Let me get the invoice schema.
Action: lookup_schema("invoice")
Observation: {"name": "invoice", "fields": [...]}

Final Answer: {
  "document_type": "invoice",
  "confidence": 0.98,
  "schema": "invoice",
  "plan": [...],
  "reasoning": "Document clearly labeled 'INVOICE' with standard fields and line item table."
}
```

---

### 4.3 Extractor Agent

**Role**: Data extractor, tool user, field populator.

**Responsibilities**:
- Execute extraction plan from Analyzer
- Use tools to extract specific fields
- Handle tables, dates, currencies with appropriate tools
- Reason about ambiguous values
- Track confidence per field

**Tools Available**:
- `read_page(page_num)` - Get full page text
- `read_section(page_num, bbox)` - Get text from specific region
- `extract_table(page_num, table_index)` - Get structured table data
- `ocr_region(page_num, bbox)` - OCR specific image region
- `parse_date(text)` - Normalize date formats
- `parse_currency(text)` - Extract currency values
- `extract_field(page_num, field_name, hints)` - Targeted field extraction

**System Prompt**:
```
You are the Extractor Agent. Your job is to extract structured data from documents.

You receive an extraction plan from the Analyzer. For each field:
1. Use the appropriate tool to locate the value
2. Parse and normalize the value (dates, currencies, etc.)
3. Record your confidence (0.0-1.0) for each field
4. If uncertain, explain why in the reasoning trace

For tables:
- Use extract_table() to get structured data
- Map columns to schema fields
- Handle merged cells and multi-row values

For ambiguous fields:
- Look for alternative labels (e.g., "Invoice #" vs "Inv No" vs "Reference")
- Check multiple locations (header, footer, margins)
- Use context clues to disambiguate

Output format:
{
  "extracted_data": {
    "invoice_number": {"value": "INV-2024-001", "confidence": 0.99, "source": "page 1, line 5"},
    "total_amount": {"value": 1234.56, "confidence": 0.95, "source": "page 2, table footer"},
    ...
  },
  "reasoning_trace": [
    "Found 'Invoice #: INV-2024-001' on page 1",
    "Table total shows $1,234.56, cross-referenced with 'Total Due' field",
    ...
  ]
}
```

**ReAct Example**:
```
Thought: Plan says extract invoice_number from page 1 header. Let me read the page.
Action: read_page(1)
Observation: "INVOICE\n\nInvoice #: INV-2024-001\nDate: January 15, 2024..."

Thought: Found invoice number clearly labeled. Now extract line items from table.
Action: extract_table(1, 0)
Observation: {
  "headers": ["Description", "Qty", "Unit Price", "Amount"],
  "rows": [
    ["Widget A", "10", "$50.00", "$500.00"],
    ["Service B", "5", "$100.00", "$500.00"]
  ]
}

Thought: Table extracted successfully. Let me map to schema line_items format.
Action: parse_currency("$500.00")
Observation: {"value": 500.00, "currency": "USD"}

Thought: Now I need to find the total. Plan says page 2 footer.
Action: read_page(2)
Observation: "...Subtotal: $1,000.00\nTax (10%): $100.00\nTotal Due: $1,100.00"

Thought: Found all totals. Let me verify: 500 + 500 = 1000 subtotal ✓, 1000 * 0.10 = 100 tax ✓, 1000 + 100 = 1100 total ✓

Final Answer: {
  "extracted_data": {
    "invoice_number": {"value": "INV-2024-001", "confidence": 0.99},
    "line_items": [...],
    "subtotal": {"value": 1000.00, "confidence": 0.98},
    "tax_amount": {"value": 100.00, "confidence": 0.98},
    "total_amount": {"value": 1100.00, "confidence": 0.99}
  },
  "reasoning_trace": ["Math verified: subtotal + tax = total ✓"]
}
```

---

### 4.4 Validator Agent

**Role**: Quality checker, error detector, correction suggester.

**Responsibilities**:
- Validate extracted data against schema rules
- Cross-check mathematical relationships
- Verify format compliance (dates, emails, currencies)
- Flag inconsistencies for human review
- Suggest corrections with reasoning

**Tools Available**:
- `validate_math(expression)` - Check arithmetic relationships
- `validate_format(value, format_type)` - Check format compliance
- `compare_values(extracted, expected)` - Compare against expectations
- `cross_reference(field1, field2, rule)` - Check field relationships
- `flag_for_review(field, reason)` - Mark for human review
- `suggest_correction(field, current, suggested, reason)` - Propose fix

**System Prompt**:
```
You are the Validator Agent. Your job is to ensure extraction accuracy.

Validation checks:
1. **Schema Compliance**: All required fields present? Types correct?
2. **Mathematical Consistency**: Do numbers add up? (line items = subtotal, subtotal + tax = total)
3. **Format Validation**: Dates parseable? Emails valid? Currencies consistent?
4. **Cross-Field Logic**: Does ship_to make sense with vendor? Does end_date > start_date?
5. **Confidence Review**: Any fields with confidence < 0.90?

For each issue found:
- Explain the problem clearly
- Attempt to correct if possible
- Flag for human review if uncertain

Output format:
{
  "validation_passed": false,
  "overall_confidence": 0.94,
  "issues": [
    {
      "field": "total_amount",
      "type": "math_error",
      "message": "Line items sum to $1,000 but total shows $1,100",
      "severity": "high",
      "suggested_correction": null,
      "needs_human_review": true
    }
  ],
  "corrections_applied": [
    {
      "field": "invoice_date",
      "original": "1/15/24",
      "corrected": "2024-01-15",
      "reason": "Normalized to ISO format"
    }
  ],
  "reasoning_trace": [...]
}
```

**ReAct Example**:
```
Thought: Let me verify the math first. Checking if line items sum to subtotal.
Action: validate_math("500.00 + 500.00 == 1000.00")
Observation: {"valid": true, "result": 1000.00}

Thought: Subtotal matches. Now check subtotal + tax = total.
Action: validate_math("1000.00 + 100.00 == 1100.00")
Observation: {"valid": true, "result": 1100.00}

Thought: Math checks out. Let me verify the date format.
Action: validate_format("January 15, 2024", "date")
Observation: {"valid": true, "parsed": "2024-01-15", "format": "MMMM DD, YYYY"}

Thought: All validations passed. Let me check field confidence levels.
Observation: All fields have confidence >= 0.95

Final Answer: {
  "validation_passed": true,
  "overall_confidence": 0.97,
  "issues": [],
  "corrections_applied": [],
  "reasoning_trace": ["Math verified ✓", "Dates valid ✓", "All confidence levels acceptable ✓"]
}
```

---

### 4.2 Tool Definitions

### 5.1 Document Reading Tools

```python
@tool
def get_document_metadata(document_id: str) -> dict:
    """Get document structure information.

    Returns:
        {
            "pages": int,
            "file_type": "pdf" | "jpg" | "png",
            "file_size_kb": int,
            "has_images": bool,
            "text_extractable": bool,  # False for scanned PDFs
            "dimensions": {"width": int, "height": int}
        }
    """

@tool
def read_page(document_id: str, page_num: int) -> str:
    """Extract text/markdown from a specific page using PyMuPDF4LLM.

    Args:
        document_id: Document identifier
        page_num: 1-indexed page number

    Returns:
        Markdown-formatted text content
    """

@tool
def read_section(document_id: str, page_num: int, bbox: list[float]) -> str:
    """Extract text from a specific region of a page.

    Args:
        document_id: Document identifier
        page_num: 1-indexed page number
        bbox: [x0, y0, x1, y1] coordinates

    Returns:
        Text content from region
    """

@tool
def ocr_region(document_id: str, page_num: int, bbox: list[float] | None = None) -> str:
    """OCR a specific region or full page using Vision provider.

    Args:
        document_id: Document identifier
        page_num: 1-indexed page number
        bbox: Optional region to OCR, None for full page

    Returns:
        OCR'd text content
    """
```

### 5.2 Table Extraction Tools

```python
@tool
def detect_tables(document_id: str, page_num: int) -> list[dict]:
    """Detect all tables on a page.

    Returns:
        [
            {
                "table_index": 0,
                "bbox": [x0, y0, x1, y1],
                "rows": int,
                "columns": int,
                "headers": ["col1", "col2", ...] | None
            }
        ]
    """

@tool
def extract_table(
    document_id: str,
    page_num: int,
    table_index: int,
    table_strategy: str = "lines_strict"
) -> dict:
    """Extract structured table data using PyMuPDF4LLM.

    Args:
        document_id: Document identifier
        page_num: 1-indexed page number
        table_index: 0-indexed table on page
        table_strategy: "lines_strict" | "lines" | "text" | "explicit"

    Returns:
        {
            "headers": ["Description", "Qty", "Price", "Amount"],
            "rows": [
                ["Widget A", "10", "$50.00", "$500.00"],
                ...
            ],
            "footer": ["", "", "Total:", "$1,100.00"] | None
        }
    """
```

### 5.3 Schema Tools

```python
@tool
def list_schemas() -> list[dict]:
    """List all available extraction schemas.

    Returns:
        [
            {"name": "invoice", "display_name": "Invoice", "is_system": True},
            {"name": "resume", "display_name": "Resume / CV", "is_system": True},
            ...
        ]
    """

@tool
def lookup_schema(name: str) -> dict | None:
    """Get full schema definition.

    Returns:
        {
            "name": "invoice",
            "display_name": "Invoice",
            "fields": [
                {"name": "invoice_number", "type": "string", "required": True},
                ...
            ]
        }
    """

@tool
def suggest_schema(document_summary: str) -> dict:
    """Suggest best matching schema for a document.

    Args:
        document_summary: Brief description of document content

    Returns:
        {
            "suggested_schema": "invoice",
            "confidence": 0.85,
            "reasoning": "Document contains invoice number, line items, and total amount"
        }
    """
```

### 5.4 Parsing Tools

```python
@tool
def parse_date(text: str) -> dict:
    """Parse and normalize date from various formats.

    Args:
        text: Date string (e.g., "1/15/24", "January 15, 2024", "15-Jan-2024")

    Returns:
        {
            "value": "2024-01-15",  # ISO format
            "original": "January 15, 2024",
            "confidence": 0.95
        }
    """

@tool
def parse_currency(text: str) -> dict:
    """Parse currency value.

    Args:
        text: Currency string (e.g., "$1,234.56", "USD 1234.56", "1.234,56 EUR")

    Returns:
        {
            "value": 1234.56,
            "currency": "USD",
            "original": "$1,234.56",
            "confidence": 0.98
        }
    """

@tool
def extract_field(
    document_id: str,
    page_num: int,
    field_name: str,
    field_type: str,
    hints: list[str] | None = None
) -> dict:
    """Extract a specific field using LLM with targeted prompting.

    Args:
        document_id: Document identifier
        page_num: Page to search
        field_name: Name of field to extract
        field_type: Expected type (string, date, currency, etc.)
        hints: Alternative labels to look for

    Returns:
        {
            "value": "INV-2024-001",
            "confidence": 0.95,
            "source": {"page": 1, "bbox": [100, 50, 200, 70]},
            "reasoning": "Found 'Invoice #: INV-2024-001' on line 5"
        }
    """
```

### 5.5 Validation Tools

```python
@tool
def validate_math(expression: str) -> dict:
    """Validate mathematical expression.

    Args:
        expression: Math expression (e.g., "500 + 500 == 1000")

    Returns:
        {
            "valid": True,
            "result": 1000.0,
            "expression": "500 + 500 == 1000"
        }
    """

@tool
def validate_format(value: str, format_type: str) -> dict:
    """Validate value against expected format.

    Args:
        value: Value to validate
        format_type: "date" | "email" | "phone" | "url" | "currency"

    Returns:
        {
            "valid": True,
            "parsed": "2024-01-15",
            "format_detected": "MMMM DD, YYYY"
        }
    """

@tool
def cross_reference(field1: dict, field2: dict, rule: str) -> dict:
    """Check relationship between two fields.

    Args:
        field1: {"name": "start_date", "value": "2024-01-01"}
        field2: {"name": "end_date", "value": "2024-12-31"}
        rule: "field2 > field1" | "field1 == field2" | custom

    Returns:
        {
            "valid": True,
            "reasoning": "end_date (2024-12-31) is after start_date (2024-01-01)"
        }
    """

@tool
def flag_for_review(field_name: str, reason: str, severity: str = "medium") -> dict:
    """Flag a field for human review.

    Args:
        field_name: Field that needs review
        reason: Why review is needed
        severity: "low" | "medium" | "high"

    Returns:
        {"flagged": True, "field": field_name, "reason": reason}
    """
```

### 5.6 Storage Tools

```python
@tool
def store_result(
    document_id: str,
    schema_name: str,
    extracted_data: dict,
    confidence: float,
    reasoning_trace: list[str]
) -> dict:
    """Store extraction result to database.

    Returns:
        {
            "extraction_id": "uuid",
            "stored": True,
            "needs_review": confidence < 0.95
        }
    """

@tool
def update_field(extraction_id: str, field_name: str, new_value: any, reason: str) -> dict:
    """Update a specific field in stored extraction.

    Returns:
        {"updated": True, "field": field_name, "old_value": ..., "new_value": ...}
    """
```

---

### 4.3 Agentic Workflow

### 6.1 Complete Extraction Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENTIC EXTRACTION WORKFLOW                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER INPUT                                                              │
│  ──────────                                                              │
│  • Document (PDF/JPG)                                                    │
│  • Schema hint (optional)                                                │
│                                                                          │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ORCHESTRATOR: Initialize extraction                             │    │
│  │  • Generate document_id                                          │    │
│  │  • Store document to configured path                             │    │
│  │  • Start reasoning trace                                         │    │
│  └───────────────────────────┬─────────────────────────────────────┘    │
│                              │                                          │
│       ┌──────────────────────┴──────────────────────┐                   │
│       │                                              │                   │
│       ▼                                              │                   │
│  ┌─────────────────────────────────────────────┐    │                   │
│  │  ANALYZER AGENT                              │    │                   │
│  │  ─────────────                               │    │                   │
│  │  Thought: Analyze document structure         │    │                   │
│  │  Action: get_document_metadata()             │    │                   │
│  │  Action: read_page(1)                        │    │                   │
│  │  Action: detect_tables(1)                    │    │                   │
│  │  Thought: Classify and plan                  │    │                   │
│  │  Action: lookup_schema("invoice")            │    │                   │
│  │                                              │    │                   │
│  │  Output: {                                   │    │                   │
│  │    document_type: "invoice",                 │    │                   │
│  │    schema: "invoice",                        │    │                   │
│  │    confidence: 0.95,                         │    │                   │
│  │    plan: [...],                              │    │                   │
│  │    reasoning: "..."                          │    │                   │
│  │  }                                           │    │                   │
│  └───────────────────────────┬─────────────────┘    │                   │
│                              │                       │                   │
│       ┌──────────────────────┘                       │                   │
│       │                                              │                   │
│       ▼                                              │                   │
│  ┌─────────────────────────────────────────────┐    │                   │
│  │  EXTRACTOR AGENT                             │    │                   │
│  │  ───────────────                             │    │                   │
│  │  For each field in plan:                     │    │                   │
│  │    Thought: Extract invoice_number           │    │                   │
│  │    Action: extract_field(1, "invoice_num")   │    │                   │
│  │    Thought: Extract line items               │    │                   │
│  │    Action: extract_table(1, 0)               │    │                   │
│  │    Action: parse_currency("$500.00")         │    │                   │
│  │    Thought: Extract totals                   │    │                   │
│  │    Action: read_section(2, footer_bbox)      │    │                   │
│  │                                              │    │ Retry with        │
│  │  Output: {                                   │    │ adjusted          │
│  │    extracted_data: {...},                    │    │ strategy          │
│  │    field_confidences: {...},                 │    │ (max 3)           │
│  │    reasoning_trace: [...]                    │    │                   │
│  │  }                                           │    │                   │
│  └───────────────────────────┬─────────────────┘    │                   │
│                              │                       │                   │
│       ┌──────────────────────┘                       │                   │
│       │                                              │                   │
│       ▼                                              │                   │
│  ┌─────────────────────────────────────────────┐    │                   │
│  │  VALIDATOR AGENT                             │    │                   │
│  │  ───────────────                             │    │                   │
│  │  Thought: Check required fields              │    │                   │
│  │  Thought: Validate math                      │    │                   │
│  │  Action: validate_math("500+500==1000")      │    │                   │
│  │  Thought: Verify formats                     │    │                   │
│  │  Action: validate_format(date, "date")       │    │                   │
│  │  Thought: Cross-reference fields             │    │                   │
│  │  Action: cross_reference(subtotal, total)    │    │                   │
│  │                                              │    │                   │
│  │  Output: {                                   │    │                   │
│  │    validation_passed: true/false,            │    │                   │
│  │    overall_confidence: 0.97,                 │◄───┘                   │
│  │    issues: [...],                            │  (if validation       │
│  │    corrections: [...]                        │   failed)             │
│  │  }                                           │                       │
│  └───────────────────────────┬─────────────────┘                        │
│                              │                                          │
│       ┌──────────────────────┴──────────────────────┐                   │
│       │                                              │                   │
│       ▼                                              ▼                   │
│  ┌─────────────────────┐                 ┌─────────────────────┐        │
│  │  CONFIDENCE ≥ 95%   │                 │  CONFIDENCE < 95%   │        │
│  │  ─────────────────  │                 │  ─────────────────  │        │
│  │  store_result()     │                 │  flag_for_review()  │        │
│  │  Return success     │                 │  store_result()     │        │
│  │                     │                 │  Return with flags  │        │
│  └─────────────────────┘                 └─────────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Auto-Schema Detection Flow

When user doesn't specify a schema:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AUTO-SCHEMA DETECTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ANALYZER AGENT                                                          │
│  ─────────────                                                          │
│                                                                          │
│  Thought: No schema provided. Need to classify document.                │
│                                                                          │
│  Action: get_document_metadata()                                        │
│  Observation: {pages: 2, file_type: "pdf", text_extractable: true}      │
│                                                                          │
│  Action: read_page(1)                                                   │
│  Observation: "John Smith\njohnsmith@email.com\n(555) 123-4567\n        │
│                PROFESSIONAL EXPERIENCE\nSoftware Engineer at Acme..."   │
│                                                                          │
│  Thought: This looks like a resume - has name, contact info, and        │
│           "PROFESSIONAL EXPERIENCE" section. Let me verify.             │
│                                                                          │
│  Action: list_schemas()                                                 │
│  Observation: [invoice, resume, contract, purchase_order, sow]          │
│                                                                          │
│  Thought: Checking for resume indicators:                               │
│           ✓ Person name at top                                          │
│           ✓ Contact information (email, phone)                          │
│           ✓ "EXPERIENCE" keyword                                        │
│           ✗ No "Invoice", "PO", "Agreement" keywords                    │
│                                                                          │
│  Action: lookup_schema("resume")                                        │
│  Observation: {name: "resume", fields: [full_name, email, ...]}         │
│                                                                          │
│  Final Answer: {                                                        │
│    "document_type": "resume",                                           │
│    "confidence": 0.92,                                                  │
│    "schema": "resume",                                                  │
│    "reasoning": "Document contains person name, contact info, and       │
│                  experience section typical of a resume/CV",            │
│    "alternative_schemas": [                                             │
│      {"name": "contract", "confidence": 0.15, "reason": "Has names"}    │
│    ]                                                                    │
│  }                                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Error Recovery Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ERROR RECOVERY                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SCENARIO: Scanned PDF detected (text not extractable)                  │
│  ────────────────────────────────────────────────────                   │
│                                                                          │
│  ANALYZER AGENT                                                          │
│                                                                          │
│  Action: get_document_metadata()                                        │
│  Observation: {pages: 1, text_extractable: false, has_images: true}     │
│                                                                          │
│  Thought: This is a scanned document. Text extraction won't work.       │
│           I need to use OCR via the Vision provider.                    │
│                                                                          │
│  Action: ocr_region(doc_id, page=1, bbox=None)  # Full page OCR         │
│  Observation: "INVOICE\nInvoice #: INV-2024-001\nDate: Jan 15, 2024..." │
│                                                                          │
│  Thought: OCR successful. Document is an invoice. Proceeding with       │
│           adjusted strategy using OCR for all text extraction.          │
│                                                                          │
│  Output: {                                                              │
│    "document_type": "invoice",                                          │
│    "schema": "invoice",                                                 │
│    "plan": [...],                                                       │
│    "strategy_adjustment": "Using OCR for all text extraction",          │
│    "challenges": ["Scanned document - OCR quality may vary"]            │
│  }                                                                      │
│                                                                          │
│  ────────────────────────────────────────────────────                   │
│  SCENARIO: Math validation fails                                        │
│  ────────────────────────────────────────────────────                   │
│                                                                          │
│  VALIDATOR AGENT                                                         │
│                                                                          │
│  Action: validate_math("500 + 500 == 1200")                             │
│  Observation: {valid: false, expected: 1000, actual: 1200}              │
│                                                                          │
│  Thought: Line items don't sum to total. Possible causes:               │
│           1. Missed a line item                                         │
│           2. OCR error in numbers                                       │
│           3. Document has error                                         │
│                                                                          │
│  Action: [Notify Orchestrator of validation failure]                    │
│                                                                          │
│  ORCHESTRATOR                                                            │
│                                                                          │
│  Thought: Validation failed. Retry extraction with more careful         │
│           table reading. Attempt 2 of 3.                                │
│                                                                          │
│  Action: [Re-invoke Extractor with adjusted strategy]                   │
│           Strategy: "Re-read table with explicit row counting"          │
│                                                                          │
│  EXTRACTOR AGENT (Retry)                                                 │
│                                                                          │
│  Thought: Previous extraction missed something. Let me read table       │
│           more carefully with explicit strategy.                        │
│                                                                          │
│  Action: extract_table(1, 0, table_strategy="explicit")                 │
│  Observation: Found additional row: ["Shipping", "1", "$200.00", "$200"]│
│                                                                          │
│  Thought: Found missing shipping line item! 500 + 500 + 200 = 1200 ✓   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Technology Choices & Rationale

### 7.1 Document Processing: Page-by-Page vs Full Document

| Approach | Pros | Cons |
|----------|------|------|
| Full Document | Simpler, single LLM call | Context limits, field confusion |
| **Page-by-Page + Merge** | Handles any length, focused extraction | Merge complexity |

**Chosen: Page-by-Page + Merge**

**Why**:
- Documents can exceed LLM context windows (128K tokens = ~50 pages)
- Page isolation improves extraction accuracy (less noise)
- Parallel processing possible for speed

**Why Not Full Document**:
- Context window limits exclude long contracts (100+ pages)
- LLM performance degrades with longer contexts
- Mixed content (tables + text) confuses single-pass extraction

**Merge Strategy**:
```
Page extractions → Merge Engine → Final Result
                       │
                       ├─ Single fields: First non-null wins
                       ├─ Arrays: Concatenate + deduplicate
                       └─ Conflicts: Flag for review with both values
```

---

### 3.3 Schema Storage: Database vs Files

| Approach | Pros | Cons |
|----------|------|------|
| JSON Files | Version controlled, simple | No runtime changes |
| **Database (JSONB)** | Runtime CRUD, impact tracking | Migration needed |
| Hybrid | Best of both | Complexity |

**Chosen: Database Only**

**Why**:
- Requirement R6 demands extensible schemas via UI
- Need to track schema modifications and their impact on existing extractions
- JSONB in PostgreSQL gives flexibility of JSON with query power of SQL

**Why Not JSON Files**:
- Requires server restart for schema changes
- No audit trail for modifications
- Can't track which extractions use which schema version

**Why Not Hybrid**:
- Adds complexity with two storage mechanisms
- Sync issues between file and DB versions
- Single source of truth is cleaner

---

### 3.4 OCR Strategy: Auto-Detect vs User-Specified

| Approach | UX | Accuracy |
|----------|-----|----------|
| User specifies | Extra step | User can be wrong |
| **Auto-detect** | Seamless | Reliable detection |

**Chosen: Auto-Detect**

**Why**:
- Requirement R1 demands intuitive UI with minimal friction
- PyMuPDF can reliably detect text vs image PDFs
- User shouldn't need to know if their PDF is scanned

**Detection Logic**:
```
Input File
    │
    ├─ JPG/PNG → Vision Provider (always)
    │
    └─ PDF → Extract via PyMuPDF4LLM
              │
              ├─ Text found → Use extracted markdown (fast, free)
              │   └─ Tables detected → Use table_strategy for structured extraction
              │
              └─ No text (scanned) → Vision Provider (OCR)
```

---

### 3.5 PDF Processing: PyMuPDF vs PyMuPDF4LLM

| Aspect | PyMuPDF | PyMuPDF4LLM |
|--------|---------|-------------|
| Table Extraction | Basic text | Advanced `table_strategy` parameter |
| Output Format | Raw text/HTML | LLM-optimized Markdown |
| Table Strategies | None | `lines_strict`, `lines`, `text`, `explicit` |
| Structured Data | Manual parsing | Returns table metadata (bbox, rows, columns) |

**Chosen: PyMuPDF4LLM**

**Why**:
- `table_strategy` parameter is essential for financial documents with tables
- LLM-optimized markdown output reduces preprocessing
- Built on PyMuPDF (same underlying engine, zero migration risk)
- Table detection strategies handle various formats:
  - `lines_strict` - Tables with clear visible borders (invoices)
  - `lines` - Tables with partial borders
  - `text` - Text-aligned tables without borders
  - `explicit` - User-defined table regions

**Why Not Basic PyMuPDF**:
- No built-in table detection
- Manual parsing required for structured data
- Raw text output needs additional LLM formatting

**Usage**:
```python
import pymupdf4llm

# Extract with table detection
md_text = pymupdf4llm.to_markdown(
    "financial_report.pdf",
    table_strategy="lines_strict",
)

# Get structured table data
chunks = pymupdf4llm.to_markdown("report.pdf", page_chunks=True)
for chunk in chunks:
    for table in chunk.get('tables', []):
        print(f"Table: {table['rows']} rows × {table['columns']} cols")
```

---

### 3.6 Web Framework: Flask vs FastAPI

| Aspect | Flask (Current) | FastAPI |
|--------|-----------------|---------|
| Async Support | Via extensions | Native `async/await` |
| File Upload | `request.files` | `UploadFile` with streaming |
| Type Safety | Manual | Pydantic automatic |
| API Docs | Manual/Swagger ext | Auto-generated OpenAPI |
| Integration | Already in codebase | New dependency |

**Chosen: Flask (Keep Existing)**

**Why**:
- **Zero Impact (R2)**: Adding FastAPI means two frameworks, violates simplicity
- **Sufficient for Use Case**: Document uploads typically <50MB, not requiring async streaming
- **Existing Infrastructure**: Auth, sessions, routes all work with Flask
- **Bottleneck is LLM**: Async benefits matter for I/O-bound concurrent requests; our bottleneck is LLM calls (already handled via existing patterns)

**Why Not FastAPI**:
- Adds deployment complexity (two ASGI/WSGI servers)
- Learning curve for team already familiar with Flask
- Marginal gains don't justify architectural change
- If async needed later, can add via Celery workers

**Alternative Considered**:
- FastAPI microservice for extraction only → Rejected due to added deployment complexity and service mesh overhead

---

### 3.7 Architecture Pattern: Standalone Module

| Approach | Coupling | Maintenance |
|----------|----------|-------------|
| Integrated with RAG | High | Risk to existing |
| **Standalone Module** | Zero | Independent |

**Chosen: Standalone Module**

**Why**:
- Requirement R2: Zero impact on existing flows
- Document extraction has different workflow than RAG (upload → extract → export vs chat)
- Independent testing and deployment
- Can be disabled without affecting core functionality

**Isolation Boundaries**:
```
EXTRACTION MODULE               EXISTING SYSTEM
─────────────────────          ─────────────────────
/api/extraction/*              /api/query, /api/chat (unchanged)
extraction_schemas table       notebooks, data_embeddings (unchanged)
extractions table              conversations (unchanged)
ExtractionService              LocalRAGPipeline (unchanged)
```

---

## 6. Requirements Traceability Matrix

| Req ID | Requirement | Design Element | How Addressed |
|--------|-------------|----------------|---------------|
| **R1** | Intuitive UI | 3-step workflow, auto-schema | Upload → Review → Manage; agent detects schema if not specified |
| **R2** | Full API access | REST endpoints (Flask) | `/api/extraction/*` with file upload, JSON responses, reasoning traces |
| **R3** | PDF/JPG/scanned support | PyMuPDF4LLM + Vision + Agent routing | Analyzer agent detects format; auto-routes to OCR if needed |
| **R4** | High accuracy (~98%+) | Agentic ReAct + Validator Agent | Multi-agent reasoning; validation agent catches errors; retry with adjusted strategy |
| **R5** | Extensible schemas | Database JSONB + Schema Manager | Runtime CRUD via API/UI, impact tracking |
| **R6** | Autonomous schema detection | Analyzer Agent | Agent classifies document and suggests schema without user input |
| **R7** | Transparent reasoning | Reasoning traces | Full chain-of-thought stored and returned for debugging/audit |
| **R8** | Standalone deployment | New project | Independent application, can be deployed anywhere |

---

## 7. Module Structure

### 7.1 Component Responsibilities (Agentic Module Structure)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENTIC MODULE STRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  dbnotebook/core/extraction/                                            │
│  │                                                                       │
│  ├── service.py              ExtractionService                          │
│  │                           - API entry point                          │
│  │                           - Initializes agents and tools             │
│  │                           - Manages extraction lifecycle             │
│  │                                                                       │
│  ├── agents/                                                            │
│  │   ├── __init__.py                                                    │
│  │   ├── base.py             BaseAgent                                  │
│  │   │                       - Common agent interface                   │
│  │   │                       - ReAct loop implementation               │
│  │   │                       - Reasoning trace management              │
│  │   │                                                                   │
│  │   ├── orchestrator.py     OrchestratorAgent                          │
│  │   │                       - Workflow coordination                    │
│  │   │                       - Agent dispatch and handoffs             │
│  │   │                       - Retry and escalation logic              │
│  │   │                                                                   │
│  │   ├── analyzer.py         AnalyzerAgent                              │
│  │   │                       - Document classification                 │
│  │   │                       - Schema detection/suggestion             │
│  │   │                       - Extraction plan creation                │
│  │   │                                                                   │
│  │   ├── extractor.py        ExtractorAgent                             │
│  │   │                       - Field extraction via tools              │
│  │   │                       - Table processing                        │
│  │   │                       - Per-field confidence scoring            │
│  │   │                                                                   │
│  │   └── validator.py        ValidatorAgent                             │
│  │                           - Math validation                          │
│  │                           - Format verification                      │
│  │                           - Cross-field consistency                  │
│  │                                                                       │
│  ├── tools/                                                             │
│  │   ├── __init__.py         Tool registry                              │
│  │   ├── document_tools.py   read_page, read_section, get_metadata     │
│  │   ├── table_tools.py      detect_tables, extract_table              │
│  │   ├── ocr_tools.py        ocr_region (Vision provider wrapper)      │
│  │   ├── parsing_tools.py    parse_date, parse_currency, extract_field │
│  │   ├── validation_tools.py validate_math, validate_format, cross_ref │
│  │   ├── schema_tools.py     list_schemas, lookup_schema               │
│  │   └── storage_tools.py    store_result, update_field                │
│  │                                                                       │
│  ├── schema_manager.py       SchemaManager                              │
│  │                           - Schema CRUD operations                   │
│  │                           - Schema validation                        │
│  │                           - System schema initialization            │
│  │                                                                       │
│  ├── document_processor.py   DocumentProcessor                          │
│  │                           - PyMuPDF4LLM wrapper                      │
│  │                           - Table extraction strategies             │
│  │                           - Page-level text extraction              │
│  │                                                                       │
│  └── types.py                Type definitions                           │
│                              - ExtractionResult, Schema, Field          │
│                              - AgentResponse, ReasoningStep            │
│                              - ToolCall, ToolResult                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Agent Dependency Flow

```
                         ExtractionService
                               │
                               ▼
                      OrchestratorAgent
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    AnalyzerAgent       ExtractorAgent       ValidatorAgent
          │                    │                    │
          │                    │                    │
          ▼                    ▼                    ▼
    ┌─────────────────────────────────────────────────────┐
    │                    TOOL LAYER                        │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
    │  │ Document │ │  Table   │ │   OCR    │ │ Parse  │ │
    │  │  Tools   │ │  Tools   │ │  Tools   │ │ Tools  │ │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
    └───────┼────────────┼────────────┼───────────┼──────┘
            │            │            │           │
            ▼            ▼            ▼           ▼
    ┌─────────────────────────────────────────────────────┐
    │                SHARED INFRASTRUCTURE                 │
    │  ┌────────────┐ ┌────────────┐ ┌────────────────┐   │
    │  │ PyMuPDF4LLM│ │  Vision    │ │   LLM Provider │   │
    │  │            │ │  Manager   │ │  (Existing)    │   │
    │  └────────────┘ └────────────┘ └────────────────┘   │
    │  ┌────────────┐ ┌────────────┐                      │
    │  │ PostgreSQL │ │   Schema   │                      │
    │  │ (Results)  │ │  Manager   │                      │
    │  └────────────┘ └────────────┘                      │
    └─────────────────────────────────────────────────────┘
```

### 7.3 Key Design Decisions

**Agent Architecture**:
- Each agent is stateless - receives context, returns result
- Agents communicate via structured messages (not direct calls)
- Reasoning traces stored for debugging and audit
- Tools are shared across agents via registry

**ReAct Implementation**:
```python
class BaseAgent:
    def run(self, input: AgentInput) -> AgentOutput:
        """Execute ReAct loop until completion or max iterations."""
        reasoning_trace = []
        for i in range(self.max_iterations):
            # THINK: Reason about current state
            thought = self.think(input, reasoning_trace)
            reasoning_trace.append({"type": "thought", "content": thought})

            # ACT: Decide on action (tool call or final answer)
            action = self.act(thought)

            if action.is_final_answer:
                return AgentOutput(
                    result=action.answer,
                    reasoning_trace=reasoning_trace,
                    confidence=action.confidence
                )

            # OBSERVE: Execute tool and observe result
            observation = self.execute_tool(action.tool_call)
            reasoning_trace.append({"type": "observation", "content": observation})

        # Max iterations reached
        return AgentOutput(
            result=None,
            reasoning_trace=reasoning_trace,
            error="Max iterations reached"
        )
```

**Tool Registration**:
```python
# tools/__init__.py
TOOL_REGISTRY = {
    "read_page": document_tools.read_page,
    "extract_table": table_tools.extract_table,
    "ocr_region": ocr_tools.ocr_region,
    "parse_date": parsing_tools.parse_date,
    "validate_math": validation_tools.validate_math,
    # ... etc
}

def get_tools_for_agent(agent_type: str) -> list[Tool]:
    """Return tools available to specific agent type."""
    agent_tools = {
        "analyzer": ["get_document_metadata", "read_page", "detect_tables",
                     "list_schemas", "lookup_schema"],
        "extractor": ["read_page", "read_section", "extract_table", "ocr_region",
                      "parse_date", "parse_currency", "extract_field"],
        "validator": ["validate_math", "validate_format", "cross_reference",
                      "flag_for_review", "suggest_correction"]
    }
    return [TOOL_REGISTRY[t] for t in agent_tools.get(agent_type, [])]
```

---

## 8. Scalability Design

### 6.1 Horizontal Scalability

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SCALABILITY PATTERNS                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CURRENT (Single Instance)          FUTURE (Scaled)                     │
│  ─────────────────────────          ─────────────────                   │
│                                                                          │
│  Flask App                          Load Balancer                        │
│      │                                   │                               │
│      ▼                              ┌────┴────┐                          │
│  ExtractionService                  │    │    │                          │
│      │                              ▼    ▼    ▼                          │
│      ▼                          Flask  Flask  Flask                      │
│  PostgreSQL                         │    │    │                          │
│                                     └────┬────┘                          │
│                                          ▼                               │
│                                     PostgreSQL                           │
│                                                                          │
│  SCALING POINTS:                                                        │
│  ─────────────────                                                      │
│  1. Stateless services → Add more Flask instances                       │
│  2. Async processing → Queue extractions for background workers         │
│  3. LLM calls → Parallel page processing                                │
│  4. Database → Read replicas for list/query operations                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Performance Optimization Paths

| Bottleneck | Current | Future Optimization |
|------------|---------|---------------------|
| LLM calls | Sequential | Parallel page extraction |
| Large PDFs | Memory load | Streaming page processing |
| Many users | Single process | Celery worker queue |
| Schema lookups | DB query | Redis cache |

---

## 9. Extensibility Design

### 7.1 Adding New Document Types

**Zero Code Change Required**:
```
1. Create schema via API:
   POST /api/extraction/schemas
   {
     "name": "purchase_order",
     "display_name": "Purchase Order",
     "fields": [
       {"name": "po_number", "type": "string", "required": true},
       {"name": "vendor", "type": "string", "required": true},
       ...
     ]
   }

2. Use immediately:
   POST /api/extraction/extract
   -F "file=@po.pdf"
   -F "document_type=purchase_order"
```

### 7.2 Adding New Field Types

**Single Point of Change**:
```python
# types.py - Add new type
class FieldType(Enum):
    STRING = "string"
    CURRENCY = "currency"
    ...
    ADDRESS = "address"  # NEW

# extractor.py - Add validation
def validate_field(value, field_type):
    if field_type == FieldType.ADDRESS:
        return validate_address(value)
```

### 7.3 Adding New LLM Providers

**Leverages Existing Infrastructure**:
```python
# Uses existing LocalRAGModel which already supports:
# - OpenAI, Anthropic, Gemini, Groq, Ollama

# ExtractionService just calls:
llm = LocalRAGModel.set(model_name=config.extraction_model)
```

### 7.4 Adding New Vision Providers

**Leverages Existing VisionManager**:
```python
# Uses existing VisionManager which already supports:
# - Gemini Vision, OpenAI Vision

# PageProcessor just calls:
text = vision_manager.extract_text(image_bytes)
```

---

## 10. Data Model

```sql
-- Document type definitions (extensible via API)
CREATE TABLE extraction_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    schema JSONB NOT NULL,           -- {fields: [], validation_rules: []}
    is_system BOOLEAN DEFAULT FALSE, -- System schemas can't be deleted
    user_id UUID,                    -- NULL = system, UUID = user-created
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Extracted documents
CREATE TABLE extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    schema_id UUID NOT NULL REFERENCES extraction_schemas(id),

    -- Source document
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_hash VARCHAR(64),           -- MD5 for duplicate detection
    page_count INTEGER,

    -- Results
    extracted_data JSONB NOT NULL,
    confidence FLOAT,
    needs_review BOOLEAN DEFAULT FALSE,
    review_status VARCHAR(20) DEFAULT 'pending',

    -- Metadata
    extraction_model VARCHAR(100),
    extraction_time_ms INTEGER,
    src_iterations INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit trail for human edits
CREATE TABLE extraction_edits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    edited_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_extractions_user ON extractions(user_id);
CREATE INDEX idx_extractions_schema ON extractions(schema_id);
CREATE INDEX idx_extractions_status ON extractions(review_status);
CREATE INDEX idx_extractions_created ON extractions(created_at DESC);
```

---

## 11. API Contract

### Extraction Operations

```yaml
POST /api/extraction/extract:
  description: Upload document and extract fields using agentic pipeline
  request:
    content-type: multipart/form-data
    fields:
      file: binary (required)
      document_type: string (optional) - schema name, auto-detected if not provided
      include_reasoning: boolean (optional, default: false) - include full reasoning trace
  response:
    extraction_id: uuid
    confidence: float
    needs_review: boolean
    extracted_data: object
    # Agentic-specific fields:
    detected_type: string - agent's classification (if auto-detected)
    detection_confidence: float - confidence in classification
    reasoning_summary: string - brief explanation of extraction
    reasoning_trace: array (if include_reasoning=true) - full chain-of-thought
    agent_iterations: int - number of agent loops used
    tools_used: array - list of tools invoked during extraction

GET /api/extraction/list:
  description: List extractions with filters
  query_params:
    document_type: string (optional)
    status: pending|reviewed|approved (optional)
    page: integer (default 1)
    limit: integer (default 20)

GET /api/extraction/{id}:
  description: Get extraction details

PATCH /api/extraction/{id}:
  description: Update extracted fields (human edit)
  request:
    fields: object - key/value pairs to update

DELETE /api/extraction/{id}:
  description: Delete extraction

POST /api/extraction/{id}/reextract:
  description: Re-run extraction with current schema

GET /api/extraction/{id}/download:
  description: Export as JSON file

POST /api/extraction/extract/stream:
  description: Stream extraction progress with real-time agent reasoning (SSE)
  request:
    content-type: multipart/form-data
    fields:
      file: binary (required)
      document_type: string (optional)
  response: text/event-stream
    events:
      - event: agent_start
        data: {"agent": "analyzer", "message": "Analyzing document structure..."}
      - event: thought
        data: {"agent": "analyzer", "thought": "Document has 2 pages with tables"}
      - event: tool_call
        data: {"agent": "analyzer", "tool": "detect_tables", "args": {"page": 1}}
      - event: tool_result
        data: {"tool": "detect_tables", "result": {"tables": [...]}}
      - event: agent_complete
        data: {"agent": "analyzer", "result": {"document_type": "invoice", ...}}
      - event: extraction_complete
        data: {"extraction_id": "uuid", "confidence": 0.97, ...}
      - event: error
        data: {"message": "...", "recoverable": true}

GET /api/extraction/{id}/reasoning:
  description: Get full reasoning trace for an extraction
  response:
    extraction_id: uuid
    reasoning_trace: array
      - step: 1
        agent: "analyzer"
        type: "thought"
        content: "Document appears to be an invoice based on header"
        timestamp: "2024-01-15T10:30:00Z"
      - step: 2
        agent: "analyzer"
        type: "tool_call"
        tool: "read_page"
        args: {"page": 1}
        result: "INVOICE\n\nInvoice #: INV-2024-001..."
        timestamp: "2024-01-15T10:30:01Z"
      # ... full trace
```

### Schema Operations

```yaml
GET /api/extraction/schemas:
  description: List all schemas

GET /api/extraction/schemas/{name}:
  description: Get schema definition

POST /api/extraction/schemas:
  description: Create new schema
  request:
    name: string
    display_name: string
    fields: array

PUT /api/extraction/schemas/{name}:
  description: Update schema
  response:
    affected_extractions: integer - count of impacted records

DELETE /api/extraction/schemas/{name}:
  description: Delete schema (non-system only)
```

---

## 12. Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Project Type** | Standalone application | Independent deployment, no DBNotebook dependency (R8) |
| **Project Name** | DocuAgent (working title) | Descriptive, brandable |
| **Base Code** | Fork from DBNotebook | Reuse LLM/Vision providers, auth, settings |
| **Architecture** | Agentic (4 agents) | Autonomous reasoning, tool use, self-correction |
| **Agents** | Orchestrator → Analyzer → Extractor → Validator | Clear separation of concerns, each agent specialized |
| **Tool System** | 15+ tools in registry | Shared tools across agents, testable, extensible |
| **Reasoning** | ReAct pattern | Think → Act → Observe loop with visible traces |
| **Document handling** | Page-by-page + agent routing | Agent decides strategy per document |
| **PDF Processing** | PyMuPDF4LLM | Table extraction with `table_strategy`, LLM-optimized output |
| **Web Framework** | Flask | Lightweight, proven, sufficient for use case |
| **Frontend** | React + Vite | Modern stack, 3-step workflow UI |
| **OCR** | Agent-directed | Analyzer agent detects need, routes to Vision provider |
| **Schema detection** | Analyzer Agent (auto) | Agent classifies and suggests schema (R6) |
| **Schema storage** | Database JSONB | Runtime extensibility (R5) |
| **Default schemas** | 5 system schemas | Invoice, Resume, Contract, PO, SOW |
| **Confidence threshold** | Fixed 95% | Consistency, triggers human review below threshold |
| **File storage** | Local (configurable) | `DOCUAGENT_STORAGE_PATH` via .env |
| **Transparency** | Reasoning traces | Full chain-of-thought for debugging (R7) |
| **Error recovery** | Retry with adjusted strategy | Max 3 retries with agent reasoning |
| **Accuracy target** | ~98% | Higher than pipeline approach via multi-agent validation |

---

## 13. Configuration

### 11.1 Environment Variables

```bash
# DocuAgent Configuration (.env)

# ===========================================
# Database
# ===========================================
DATABASE_URL=postgresql://docuagent:password@localhost:5432/docuagent
# Or individual settings:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docuagent
POSTGRES_USER=docuagent
POSTGRES_PASSWORD=password

# ===========================================
# LLM Providers (choose one or more)
# ===========================================
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google/Gemini
GOOGLE_API_KEY=...

# Groq (fast inference)
GROQ_API_KEY=gsk_...

# Ollama (local)
OLLAMA_HOST=localhost
OLLAMA_PORT=11434

# ===========================================
# Vision Providers (for OCR)
# ===========================================
VISION_PROVIDER=gemini                         # gemini|openai

# ===========================================
# Extraction Settings
# ===========================================
DOCUAGENT_STORAGE_PATH=./uploads               # Default: local project folder
DOCUAGENT_MAX_FILE_SIZE_MB=50                  # Maximum upload size (MB)
DOCUAGENT_CONFIDENCE_THRESHOLD=0.95            # Fixed at 95%
DOCUAGENT_DEFAULT_MODEL=gpt-4.1                # Default LLM for agents
DOCUAGENT_MAX_AGENT_ITERATIONS=10              # Max ReAct loops per agent
DOCUAGENT_MAX_RETRIES=3                        # Max extraction retries

# ===========================================
# Authentication
# ===========================================
FLASK_SECRET_KEY=your-secret-key-here          # Required for sessions
JWT_SECRET_KEY=your-jwt-secret-here            # For API tokens

# ===========================================
# Server
# ===========================================
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=false
```

### 11.2 Confidence Threshold

**Fixed at 95%** - Not configurable per schema.

**Rationale**:
- Consistency across all document types
- Avoids confusion about "what confidence means" for different schemas
- 95% represents the point where human review cost exceeds extraction benefit
- If extraction can't reach 95%, it flags for human review

---

## 14. Default Schemas

All five schemas ship as system defaults (`is_system: true`). Users can create additional custom schemas.

### 12.1 Invoice Schema

```json
{
  "name": "invoice",
  "display_name": "Invoice",
  "fields": [
    {"name": "invoice_number", "type": "string", "required": true},
    {"name": "invoice_date", "type": "date", "required": true},
    {"name": "due_date", "type": "date", "required": false},
    {"name": "vendor_name", "type": "string", "required": true},
    {"name": "vendor_address", "type": "string", "required": false},
    {"name": "bill_to_name", "type": "string", "required": false},
    {"name": "bill_to_address", "type": "string", "required": false},
    {"name": "subtotal", "type": "currency", "required": false},
    {"name": "tax_amount", "type": "currency", "required": false},
    {"name": "total_amount", "type": "currency", "required": true},
    {"name": "currency", "type": "string", "required": false, "default": "USD"},
    {"name": "line_items", "type": "array", "required": false, "item_schema": {
      "description": "string",
      "quantity": "number",
      "unit_price": "currency",
      "amount": "currency"
    }}
  ]
}
```

### 12.2 Resume Schema

```json
{
  "name": "resume",
  "display_name": "Resume / CV",
  "fields": [
    {"name": "full_name", "type": "string", "required": true},
    {"name": "email", "type": "email", "required": false},
    {"name": "phone", "type": "string", "required": false},
    {"name": "location", "type": "string", "required": false},
    {"name": "linkedin_url", "type": "url", "required": false},
    {"name": "summary", "type": "text", "required": false},
    {"name": "skills", "type": "array", "required": false, "item_type": "string"},
    {"name": "experience", "type": "array", "required": false, "item_schema": {
      "company": "string",
      "title": "string",
      "start_date": "date",
      "end_date": "date",
      "description": "text"
    }},
    {"name": "education", "type": "array", "required": false, "item_schema": {
      "institution": "string",
      "degree": "string",
      "field": "string",
      "graduation_date": "date"
    }},
    {"name": "certifications", "type": "array", "required": false, "item_type": "string"}
  ]
}
```

### 12.3 Contract Schema

```json
{
  "name": "contract",
  "display_name": "Contract",
  "fields": [
    {"name": "contract_title", "type": "string", "required": true},
    {"name": "contract_number", "type": "string", "required": false},
    {"name": "effective_date", "type": "date", "required": true},
    {"name": "expiration_date", "type": "date", "required": false},
    {"name": "party_a_name", "type": "string", "required": true},
    {"name": "party_a_address", "type": "string", "required": false},
    {"name": "party_b_name", "type": "string", "required": true},
    {"name": "party_b_address", "type": "string", "required": false},
    {"name": "contract_value", "type": "currency", "required": false},
    {"name": "payment_terms", "type": "string", "required": false},
    {"name": "governing_law", "type": "string", "required": false},
    {"name": "key_terms", "type": "array", "required": false, "item_type": "text"}
  ]
}
```

### 12.4 Purchase Order Schema

```json
{
  "name": "purchase_order",
  "display_name": "Purchase Order",
  "fields": [
    {"name": "po_number", "type": "string", "required": true},
    {"name": "po_date", "type": "date", "required": true},
    {"name": "vendor_name", "type": "string", "required": true},
    {"name": "vendor_address", "type": "string", "required": false},
    {"name": "ship_to_name", "type": "string", "required": false},
    {"name": "ship_to_address", "type": "string", "required": false},
    {"name": "delivery_date", "type": "date", "required": false},
    {"name": "payment_terms", "type": "string", "required": false},
    {"name": "subtotal", "type": "currency", "required": false},
    {"name": "tax_amount", "type": "currency", "required": false},
    {"name": "shipping_cost", "type": "currency", "required": false},
    {"name": "total_amount", "type": "currency", "required": true},
    {"name": "line_items", "type": "array", "required": false, "item_schema": {
      "item_number": "string",
      "description": "string",
      "quantity": "number",
      "unit_price": "currency",
      "amount": "currency"
    }}
  ]
}
```

### 12.5 Statement of Work (SOW) Schema

```json
{
  "name": "sow",
  "display_name": "Statement of Work",
  "fields": [
    {"name": "sow_title", "type": "string", "required": true},
    {"name": "sow_number", "type": "string", "required": false},
    {"name": "client_name", "type": "string", "required": true},
    {"name": "vendor_name", "type": "string", "required": true},
    {"name": "start_date", "type": "date", "required": false},
    {"name": "end_date", "type": "date", "required": false},
    {"name": "project_description", "type": "text", "required": false},
    {"name": "scope_of_work", "type": "text", "required": false},
    {"name": "deliverables", "type": "array", "required": false, "item_schema": {
      "name": "string",
      "description": "text",
      "due_date": "date"
    }},
    {"name": "milestones", "type": "array", "required": false, "item_schema": {
      "name": "string",
      "date": "date",
      "payment_amount": "currency"
    }},
    {"name": "total_value", "type": "currency", "required": false},
    {"name": "payment_terms", "type": "string", "required": false}
  ]
}
```

---

## 15. UI Flow

### 13.1 Three-Step Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTRACTION UI FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 1: UPLOAD                                                         │
│  ─────────────────                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Select Document Type: [▼ Invoice                            ]   │   │
│  │                            Resume                                │   │
│  │                            Contract                              │   │
│  │                            Purchase Order                        │   │
│  │                            Statement of Work                     │   │
│  │                            + Custom schemas...                   │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐    │   │
│  │  │                                                          │    │   │
│  │  │     📄 Drag & drop PDF, JPG, or scanned document        │    │   │
│  │  │                  or click to browse                      │    │   │
│  │  │                                                          │    │   │
│  │  └─────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │                              [Extract →]                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  STEP 2: REVIEW                                                         │
│  ─────────────────                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Extraction Results          Confidence: 97% ✅                  │   │
│  │  ──────────────────────────────────────────────────────────────  │   │
│  │                                                                  │   │
│  │  Invoice Number:    [INV-2024-001        ] ✓                    │   │
│  │  Invoice Date:      [2024-01-15          ] ✓                    │   │
│  │  Vendor Name:       [Acme Corporation    ] ✓                    │   │
│  │  Total Amount:      [$1,234.56           ] ✓                    │   │
│  │                                                                  │   │
│  │  Line Items:                                                     │   │
│  │  ┌──────────────┬──────┬───────────┬───────────┐                │   │
│  │  │ Description  │ Qty  │ Unit Price│ Amount    │                │   │
│  │  ├──────────────┼──────┼───────────┼───────────┤                │   │
│  │  │ Widget A     │ 10   │ $50.00    │ $500.00   │                │   │
│  │  │ Service B    │ 5    │ $100.00   │ $500.00   │                │   │
│  │  └──────────────┴──────┴───────────┴───────────┘                │   │
│  │                                                                  │   │
│  │  [← Back]                    [Save & Approve →]                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  STEP 3: MANAGE                                                         │
│  ─────────────────                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  My Extractions                              [+ New Extraction]  │   │
│  │  ──────────────────────────────────────────────────────────────  │   │
│  │                                                                  │   │
│  │  Filter: [All Types ▼] [All Status ▼]         🔍 Search...      │   │
│  │                                                                  │   │
│  │  ┌─────────┬──────────┬──────────┬────────┬─────────┬────────┐  │   │
│  │  │ File    │ Type     │ Date     │ Conf.  │ Status  │ Actions│  │   │
│  │  ├─────────┼──────────┼──────────┼────────┼─────────┼────────┤  │   │
│  │  │ inv.pdf │ Invoice  │ Jan 15   │ 97%    │ ✅ Done │ ⬇ 🗑   │  │   │
│  │  │ cv.pdf  │ Resume   │ Jan 14   │ 94%    │ ⚠ Review│ ✏ ⬇ 🗑 │  │   │
│  │  │ po.pdf  │ PO       │ Jan 13   │ 98%    │ ✅ Done │ ⬇ 🗑   │  │   │
│  │  └─────────┴──────────┴──────────┴────────┴─────────┴────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 13.2 Schema Selection UX

- Dropdown shows all available schemas (5 system + user-created)
- System schemas marked with 📋 icon
- User schemas marked with 👤 icon
- Most recently used schemas appear first
- "Manage Schemas" link at bottom for admin users
