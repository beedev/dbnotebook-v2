# Content Studio

Generate visual content like infographics and mind maps from your notebook documents.

---

## Overview

Content Studio uses AI to create visual representations of your document content:

- **Infographics** - Visual summaries with icons and layouts
- **Mind Maps** - Hierarchical concept maps
- **Brand Extraction** - Extract colors and style from reference images

---

## Generating Infographics

### 1. Navigate to Studio

1. Select a notebook with uploaded documents
2. Click **"Studio"** tab
3. Select **"Infographic"** as content type

### 2. Configure Options

| Option | Description |
|--------|-------------|
| **Topic** | Focus area for the infographic |
| **Style** | Visual style (modern, corporate, playful) |
| **Color Scheme** | Primary colors to use |
| **Reference Image** | Optional brand image for style extraction |

### 3. Generate

Click **"Generate"** and wait for processing:

1. AI analyzes relevant document content
2. Extracts key points and statistics
3. Generates visual layout with Gemini Imagen
4. Returns downloadable image

### 4. Download

Generated infographics appear in the gallery. Click to download PNG/JPG.

---

## Brand Extraction

Upload a reference image (logo, existing marketing material) to extract:

- **Colors** - Dominant brand colors in hex format
- **Style** - Design style description
- **Fonts** - Typography style suggestions

This ensures generated content matches your brand identity.

### How to Use

1. Click **"Upload Reference Image"**
2. Select a brand image (logo, brochure, etc.)
3. AI analyzes and extracts brand elements
4. Brand info is applied to generation

---

## Mind Maps

Generate hierarchical concept maps from your documents:

### Options

| Option | Description |
|--------|-------------|
| **Central Topic** | Main concept for the map center |
| **Depth** | Number of levels (2-4 recommended) |
| **Focus Area** | Specific section to emphasize |

### Output

Mind maps show:

- Central concept
- Primary branches (main topics)
- Secondary branches (subtopics)
- Key terms and relationships

---

## Gallery

All generated content is saved to your gallery:

- View generation history
- Re-download previous creations
- Delete unwanted items
- Filter by type and date

---

## Configuration

### Image Generation Provider

```bash
# .env
IMAGE_GENERATION_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
# Alternative: imagen-4.0-generate-001

# Output settings
IMAGE_OUTPUT_DIR=outputs/images
MAX_IMAGE_SIZE_MB=10
SUPPORTED_IMAGE_FORMATS=jpg,jpeg,png,webp
```

### Vision Provider (for brand extraction)

```bash
VISION_PROVIDER=gemini
GEMINI_VISION_MODEL=gemini-2.0-flash-exp
# Alternative: OpenAI GPT-4V
OPENAI_VISION_MODEL=gpt-4o
```

---

## API Usage

### Generate Infographic

```bash
curl -X POST http://localhost:7860/api/studio/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "notebook_id": "uuid",
    "content_type": "infographic",
    "topic": "Key Findings",
    "style": "modern",
    "colors": ["#2563eb", "#10b981"]
  }'
```

### List Gallery Items

```bash
curl http://localhost:7860/api/studio/gallery?notebook_id=uuid \
  -H "X-API-Key: YOUR_KEY"
```

### Download Generated Content

```bash
curl http://localhost:7860/api/studio/download/{content_id} \
  -H "X-API-Key: YOUR_KEY" \
  -o infographic.png
```

---

## Best Practices

### For Better Infographics

1. **Upload relevant documents** - Quality of output depends on input
2. **Be specific with topics** - "Q3 Sales Performance" vs "Sales"
3. **Use brand extraction** - Consistent visual identity
4. **Iterate** - Generate multiple versions, pick the best

### Content Selection

The system uses RAG retrieval to select the most relevant content:

- Queries your notebook for topic-related chunks
- Extracts statistics, key points, quotes
- Structures into visual-friendly format

### Image Limitations

- Maximum resolution depends on provider
- Text rendering may need refinement
- Complex diagrams may simplify concepts

---

## Troubleshooting

### "Generation failed"

- Check image provider API key is set
- Verify `IMAGE_GENERATION_PROVIDER` is valid
- Check API quota limits

### Poor quality output

- Add more relevant documents to notebook
- Be more specific with topic
- Try different style options
- Use brand extraction for consistency

### "Brand extraction failed"

- Ensure vision provider is configured
- Image must be clear and contain brand elements
- Supported formats: PNG, JPG, WebP

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.
