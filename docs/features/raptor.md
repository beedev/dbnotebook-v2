# RAPTOR Hierarchical Retrieval

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) builds hierarchical summaries of your documents for better retrieval of both high-level concepts and specific details.

---

## What is RAPTOR?

Traditional RAG retrieves flat chunks of text. RAPTOR adds a hierarchical layer:

```
Level 3:  [Document Summary]
              │
Level 2:  [Section A]  [Section B]  [Section C]
              │             │             │
Level 1:  [Summary]    [Summary]    [Summary]
              │             │             │
Level 0:  [chunks]     [chunks]     [chunks]  (original text)
```

This tree structure enables:

- **Summary queries** → Retrieve from higher levels
- **Detail queries** → Retrieve from lower levels
- **Mixed queries** → Combine both for comprehensive answers

---

## How It Works

### 1. Clustering

Document chunks are clustered by semantic similarity using:

- **UMAP** for dimensionality reduction
- **Gaussian Mixture Models** for soft clustering
- Chunks can belong to multiple clusters (soft assignment)

### 2. Summarization

Each cluster is summarized by the LLM:

```
Cluster of 5-10 related chunks
        ↓
LLM generates comprehensive summary
        ↓
Summary becomes a new node at Level 1
```

### 3. Recursive Building

The process repeats recursively:

```
Level 0 chunks → Cluster → Summarize → Level 1 nodes
Level 1 nodes  → Cluster → Summarize → Level 2 nodes
Level 2 nodes  → Cluster → Summarize → Level 3 nodes
...until root summary
```

### 4. Multi-Level Retrieval

Queries retrieve from appropriate levels:

| Query Type | Levels Used | Example |
|------------|-------------|---------|
| Summary | 2, 3 | "Summarize the document" |
| Detail | 0, 1 | "What exact number..." |
| Mixed | 0, 1, 2 | "Explain the main finding and give examples" |

---

## Enabling RAPTOR

### Automatic Building

RAPTOR trees are built automatically when you upload documents (if enabled):

```bash
# .env
RAPTOR_ENABLED=true
RAPTOR_AUTO_BUILD=true
```

### Manual Building

Trigger RAPTOR build for a notebook:

```bash
python scripts/rebuild_raptor.py --notebook-id YOUR_NOTEBOOK_ID
```

Or via API:

```bash
curl -X POST http://localhost:7860/api/notebooks/{id}/raptor/build \
  -H "X-API-Key: YOUR_KEY"
```

### Check RAPTOR Status

Each document source has a `raptor_status`:

- `pending` - Not yet built
- `building` - Currently processing
- `complete` - Tree ready
- `failed` - Build failed (check logs)

---

## Configuration

### Tree Building Parameters

```yaml
# config/dbnotebook.yaml (raptor section)
raptor:
  tree_building:
    max_tree_depth: 4          # Maximum levels in tree
    min_nodes_to_cluster: 5    # Minimum nodes to create new level
    batch_size: 50             # Nodes processed per batch
    max_concurrent_summaries: 3

  clustering:
    min_cluster_size: 3
    max_cluster_size: 10
    max_clusters: 50
    gmm_probability_threshold: 0.3

  summarization:
    max_input_tokens: 6000
    summary_max_tokens: 500
    max_chunks_per_summary: 10
```

### Retrieval Parameters

```yaml
level_retrieval:
  summary_query_levels: [0, 1, 2, 3]  # Levels for summary queries
  detail_query_levels: [0, 1]          # Levels for detail queries
  top_k_per_level: 6
  min_similarity_threshold: 0.3
  summary_level_boost: 1.5             # Boost for summary nodes
```

### Presets

Quick configuration presets:

```yaml
presets:
  fast:
    tree_building:
      max_tree_depth: 2
    clustering:
      max_cluster_size: 15
    summarization:
      summary_max_tokens: 300

  thorough:
    tree_building:
      max_tree_depth: 5
    clustering:
      min_cluster_size: 2
      max_cluster_size: 6
    summarization:
      summary_max_tokens: 800
```

---

## Query Routing

The system automatically routes queries to appropriate RAPTOR levels:

### Summary Keywords

These trigger higher-level retrieval:

```
summarize, summary, overview, main points, key takeaways,
themes, gist, brief, tldr, highlights
```

### Detail Keywords

These trigger lower-level retrieval:

```
specific, detail, exactly, quote, where, when, how many,
what is the, explain, section
```

### API Control

Override automatic routing:

```json
{
  "notebook_id": "uuid",
  "query": "...",
  "skip_raptor": false,      // Include RAPTOR summaries
  "raptor_levels": [1, 2]    // Specific levels to query
}
```

---

## Benefits

### Better Summary Answers

Without RAPTOR:
> "The document discusses various topics including..." (vague, based on random chunks)

With RAPTOR:
> "The document's three main themes are: 1) Market Analysis showing 15% growth, 2) Technology roadmap with Q3 milestones, 3) Financial projections targeting $10M revenue" (comprehensive, from tree summaries)

### Preserved Details

RAPTOR summaries are designed to preserve:

- **Numerical values** - Exact figures, percentages, dates
- **Named entities** - People, companies, products
- **Key relationships** - Cause-effect, comparisons

### Fallback Behavior

If RAPTOR isn't available for a notebook:

- System falls back to standard retrieval
- No user impact - just slightly different retrieval
- Enable `RAPTOR_FALLBACK_TO_FLAT=true` for graceful degradation

---

## Performance Considerations

### Build Time

| Document Size | Build Time | Recommendation |
|---------------|------------|----------------|
| < 50 pages | 1-2 min | Enable auto-build |
| 50-200 pages | 5-10 min | Background worker |
| > 200 pages | 15-30 min | Off-peak building |

### Storage

RAPTOR adds ~20-30% storage overhead for summary nodes.

### Query Latency

RAPTOR adds minimal latency (~50-100ms) for multi-level retrieval, often offset by better precision (fewer irrelevant chunks).

---

## Troubleshooting

### "RAPTOR tree not found"

- Check `raptor_status` for the notebook sources
- Verify RAPTOR is enabled in config
- Manually trigger rebuild

### "Summary queries return chunks instead of summaries"

- RAPTOR may not be built yet
- Check `skip_raptor` isn't set to `true`
- Verify tree depth > 1

### Build failures

Common causes:

- LLM rate limits during summarization
- Out of memory for large documents
- Embedding dimension mismatch

Check logs:
```bash
grep "RAPTOR" logs/dbnotebook.log
```

### Slow builds

- Reduce `max_concurrent_summaries`
- Use `fast` preset
- Process large documents overnight

---

## Advanced: Custom Summarization Prompts

Customize how clusters are summarized:

```yaml
# config/dbnotebook.yaml (raptor section)
raptor:
  summarization:
    cluster_summary_prompt: |
      You are an expert summarizer. Below are related text chunks.

      CRITICAL: Preserve ALL numerical values exactly as written.

      CHUNKS TO SUMMARIZE:
      {chunks}

      COMPREHENSIVE SUMMARY:

    root_summary_prompt: |
      You are an expert summarizer. Below are section summaries.

      Create a document-level summary that captures the key themes.

      SECTION SUMMARIES:
      {summaries}

      DOCUMENT SUMMARY:
```

This allows domain-specific summarization strategies.
