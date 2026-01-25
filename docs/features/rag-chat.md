# RAG Chat

The core feature of DBNotebook - have intelligent conversations with your documents using Retrieval-Augmented Generation.

---

## How It Works

When you ask a question, DBNotebook:

1. **Analyzes your query** - Determines query type (factual, comparison, summary)
2. **Retrieves relevant chunks** - Uses hybrid BM25 + vector search
3. **Reranks results** - Cross-encoder reranking for precision
4. **Generates response** - LLM synthesizes answer with sources

```mermaid
graph LR
    A[Your Question] --> B[Query Analysis]
    B --> C[Hybrid Retrieval]
    C --> D[Reranking]
    D --> E[LLM Response]
    E --> F[Answer + Sources]
```

---

## Retrieval Strategies

### Hybrid Search (Default)

Combines two complementary approaches:

| Method | Weight | Best For |
|--------|--------|----------|
| **BM25** | 50% | Exact keywords, technical terms, names |
| **Vector** | 50% | Semantic similarity, paraphrased queries |

This ensures both exact matches AND semantically similar content are found.

### Query Expansion

For ambiguous queries, the system generates 3 variations:

```
Original: "What are the benefits?"
Variations:
  - "What advantages does this provide?"
  - "List the positive outcomes"
  - "Describe the value proposition"
```

Results are fused using reciprocal rank fusion.

### Reranking

Retrieved chunks are reranked using `mixedbread-ai/mxbai-rerank-large-v1`:

- **Input**: Top 20 chunks from hybrid search
- **Output**: Top 6 most relevant chunks
- **Benefit**: Much higher precision than retrieval alone

---

## Query Types

The system adapts retrieval based on detected query intent:

### Summary Queries

*"Summarize the document" / "Give me an overview"*

- Uses RAPTOR hierarchical summaries
- Retrieves from higher tree levels
- Broader context, less detail

### Factual Queries

*"What is the revenue for Q3?" / "When was the company founded?"*

- Targets specific chunks
- High precision retrieval
- Exact answer extraction

### Comparison Queries

*"Compare product A vs product B"*

- Retrieves from multiple sections
- Balances coverage across topics
- Structured comparison output

### Exploration Queries

*"Tell me about the technology stack"*

- Broader retrieval
- Multiple relevant sections
- Comprehensive coverage

---

## Conversation Memory

Chat history is preserved per notebook:

- **Session continuity**: Pick up where you left off
- **Context awareness**: Follow-up questions understand previous context
- **Query expansion**: "What about the other one?" resolves to specific reference

### Follow-up Handling

```
User: What products does the company offer?
AI: The company offers three main products: A, B, and C...

User: Tell me more about the first one
AI: Product A is a... [correctly interprets "first one" as Product A]
```

The system uses a condense prompt to expand follow-up queries with conversation context before retrieval.

---

## Source Citations

Every response includes source citations:

```markdown
Based on the documents, the main findings are:

1. Revenue increased 15% year-over-year
2. Customer satisfaction improved to 92%

**Sources:**
- Annual Report 2024.pdf (page 12) - Score: 0.89
- Customer Survey Results.xlsx - Score: 0.76
```

Click on sources to see the full context.

---

## Best Practices

### Writing Effective Queries

| Do | Don't |
|----|-------|
| Be specific: "What was Q3 2024 revenue?" | Vague: "Tell me about money" |
| Ask one thing at a time | Combine multiple unrelated questions |
| Use document terminology | Assume AI knows your abbreviations |
| Reference specific documents if needed | Expect AI to read your mind |

### Improving Results

1. **Add more context**: "In the financial report, what..."
2. **Specify time period**: "...in the last quarter"
3. **Indicate document**: "According to the strategy deck..."
4. **Use follow-ups**: Build on previous answers

### Handling Poor Results

If you get unsatisfactory answers:

1. **Rephrase the question** - Try different wording
2. **Check document coverage** - Is the information in your docs?
3. **Be more specific** - Narrow down what you're asking
4. **Check source quality** - Are the right sources being retrieved?

---

## API Usage

### Basic Query

```bash
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "notebook_id": "uuid",
    "query": "What are the key findings?",
    "include_sources": true,
    "max_sources": 6
  }'
```

### With Conversation Memory

```bash
# Generate a session ID (UUID)
SESSION_ID=$(uuidgen)

# First query
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "notebook_id": "uuid",
    "query": "What products are offered?",
    "session_id": "'$SESSION_ID'"
  }'

# Follow-up query (same session)
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "notebook_id": "uuid",
    "query": "Tell me more about the first one",
    "session_id": "'$SESSION_ID'"
  }'
```

### Response Formats

Control output format with `response_format`:

- `default` - Adaptive based on query
- `brief` - Concise 2-3 paragraph summary
- `detailed` - Comprehensive with headers
- `analytical` - Tables, metrics, structured data

```json
{
  "notebook_id": "uuid",
  "query": "Analyze the financial data",
  "response_format": "analytical"
}
```

---

## Configuration

### Environment Variables

```bash
# Retrieval settings
RETRIEVAL_STRATEGY=hybrid    # hybrid, semantic, keyword
RERANKER_MODEL=large         # xsmall, base, large, disabled
DISABLE_RERANKER=false       # Set true to disable reranking

# Chat settings
CHAT_TOKEN_LIMIT=32000       # Max tokens for chat memory
CONTEXT_WINDOW=128000        # Model context window
```

### Per-Request Overrides

```json
{
  "notebook_id": "uuid",
  "query": "...",
  "reranker_enabled": true,
  "reranker_model": "base",
  "top_k": 10,
  "skip_raptor": false
}
```

---

## Troubleshooting

### "No relevant context found"

- Check that documents are uploaded and processed
- Verify the information exists in your documents
- Try rephrasing the question

### Slow responses

- Reduce `top_k` for faster retrieval
- Use `reranker_model=base` instead of `large`
- Check LLM provider latency

### Incorrect information

- Check source citations - is the right document being used?
- The information may not be in your documents
- Try a more specific query

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.
