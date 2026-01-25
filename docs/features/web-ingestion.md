# Web Ingestion

Add web pages directly to your notebooks by searching or providing URLs.

---

## Overview

Web Ingestion lets you:

- **Search the web** for relevant content
- **Preview pages** before adding
- **Import content** directly into notebooks
- **Query imported content** alongside your documents

---

## Web Search

### 1. Open Web Search

1. Select a notebook
2. Click **"Add Web Source"** or the web search icon
3. Enter your search query

### 2. Review Results

Search results show:

- Page title
- URL
- Description snippet
- Relevance score

### 3. Preview Content

Click **"Preview"** to see:

- Full page content
- Word count
- Content preview (first 500 chars)

### 4. Add to Notebook

Select pages and click **"Add Selected"**:

- Content is scraped and cleaned
- Text is chunked and embedded
- Becomes queryable in your notebook

---

## Direct URL Import

Import specific URLs without searching:

1. Click **"Add URL"**
2. Paste the URL
3. Click **"Import"**

The system:

1. Fetches the page
2. Extracts main content (removes navigation, ads)
3. Converts to clean text
4. Chunks and embeds

---

## Providers

### Firecrawl (Search)

Used for web searching:

```bash
FIRECRAWL_API_KEY=your_key_here
```

Features:

- Web search with relevance scoring
- Clean content extraction
- Rate-limited API

### Jina Reader (Scraping)

Used for page content extraction:

```bash
JINA_API_KEY=your_key_here  # Optional - higher rate limits
```

Features:

- Clean HTML-to-text conversion
- Handles JavaScript-rendered pages
- Removes boilerplate content

---

## API Usage

### Search Web

```bash
curl -X POST http://localhost:7860/api/web/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "query": "machine learning best practices",
    "num_results": 5
  }'
```

### Preview URL

```bash
curl -X POST http://localhost:7860/api/web/scrape-preview \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "url": "https://example.com/article"
  }'
```

### Add to Notebook

```bash
curl -X POST http://localhost:7860/api/notebooks/{notebook_id}/web-sources \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "urls": [
      "https://example.com/article1",
      "https://example.com/article2"
    ],
    "source_name": "ML Research"
  }'
```

### Check Provider Status

```bash
curl http://localhost:7860/api/web/providers \
  -H "X-API-Key: YOUR_KEY"
```

---

## Best Practices

### Content Quality

- **Prefer authoritative sources** - Official docs, reputable sites
- **Check preview** - Ensure content is relevant
- **Avoid paywalled content** - May not extract properly

### Notebook Organization

- **Group related sources** - Import related pages together
- **Use source names** - Label imports for easy identification
- **Don't over-import** - Quality over quantity

### Limitations

- Some sites block scraping
- JavaScript-heavy sites may have issues
- Paywalled content won't import
- Maximum 10 URLs per request

---

## Troubleshooting

### "Search failed"

- Check Firecrawl API key is set
- Verify API quota not exceeded
- Try a simpler search query

### "Scrape failed"

- Site may block scraping
- Try with Jina API key for better success
- Some sites require authentication

### "Content is empty/garbled"

- JavaScript-rendered content may not extract
- Try a different source
- Check if site has a text-only version

### Duplicate detection

The system prevents adding duplicate content:

- URLs are normalized
- Content hashes are compared
- You'll see a warning if content already exists

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.
