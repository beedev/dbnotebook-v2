# Excel Analytics

Upload Excel or CSV files and get AI-generated interactive dashboards with KPIs, charts, and filters.

---

## Overview

Excel Analytics transforms your spreadsheets into intelligent dashboards:

1. **Upload** - Excel (XLSX, XLS) or CSV files
2. **Profile** - Automatic data profiling with ydata-profiling
3. **Analyze** - AI generates optimal dashboard configuration
4. **Interact** - Filter, cross-filter, and explore your data
5. **Modify** - Use natural language to customize the dashboard

---

## Getting Started

### 1. Upload Your File

1. Navigate to **Analytics** in the sidebar
2. Click **"Upload File"** or drag-and-drop
3. Supported: `.xlsx`, `.xls`, `.csv` (max 50MB)

### 2. Automatic Processing

The system automatically:

1. **Parses** - Reads data, detects column types
2. **Profiles** - Generates statistical analysis
3. **Analyzes** - AI creates dashboard config

### 3. View Dashboard

The generated dashboard includes:

- **KPIs** - Key metrics at a glance
- **Charts** - Visualizations of your data
- **Filters** - Interactive filtering
- **Data Table** - Filtered raw data view

---

## Dashboard Components

### KPI Cards

Automatically generated metrics:

| KPI Type | Example |
|----------|---------|
| Count | Total Records: 1,234 |
| Sum | Total Revenue: $1.2M |
| Average | Avg Order Value: $156 |
| Unique | Unique Customers: 892 |
| Percent | Completion Rate: 78% |

### Chart Types

| Type | Best For |
|------|----------|
| **Bar** | Categorical comparisons |
| **Line** | Time series trends |
| **Pie** | Part-of-whole distributions |
| **Scatter** | Correlations |
| **Area** | Cumulative trends |

### Filters

| Filter Type | Description |
|-------------|-------------|
| **Categorical** | Dropdown/checkbox for text columns |
| **Range** | Min-max slider for numbers |
| **Date** | Date range picker |

---

## Data Profiling

The profiling report includes:

### Overview Stats

- Row and column counts
- Missing data percentage
- Duplicate rows
- Memory usage

### Column Analysis

For each column:

- Data type (numeric, categorical, datetime)
- Missing values
- Unique values
- Distribution statistics
- Sample values

### Quality Alerts

Automatic detection of:

- High missing rates (>10%)
- Constant columns
- High cardinality
- Duplicate rows
- Correlation warnings

### Quality Score

Overall data quality score (0-10) based on:

- Completeness
- Uniqueness
- Consistency
- Validity

---

## Interactive Features

### Cross-Filtering

Click on chart elements to filter other charts:

1. Click a bar in "Sales by Region"
2. All other charts filter to that region
3. Click again to clear filter

### Filter Bar

Use the filter bar to:

- Select categorical values
- Set numeric ranges
- Pick date ranges
- Combine multiple filters

### Data Export

Export filtered data as CSV:

1. Apply desired filters
2. Click **"Export CSV"**
3. Download filtered dataset

---

## NLP Dashboard Modification

Modify your dashboard using natural language:

### Add Elements

```
"Add a pie chart showing distribution by category"
"Create a KPI for average order value"
"Add a filter for the status column"
```

### Remove Elements

```
"Remove the scatter chart"
"Delete the revenue KPI"
"Remove all filters"
```

### Modify Elements

```
"Change the bar chart to show top 10 instead of all"
"Update the KPI to show sum instead of average"
"Rename the chart title to 'Monthly Trends'"
```

### Undo/Redo

- Click **Undo** to revert last change
- Click **Redo** to restore undone change
- Full modification history maintained

---

## API Usage

### Upload and Analyze

```bash
# 1. Upload file
curl -X POST http://localhost:7860/api/analytics/upload \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@data.xlsx"

# Response: { "sessionId": "uuid", ... }

# 2. Parse data
curl -X POST http://localhost:7860/api/analytics/parse/{sessionId} \
  -H "X-API-Key: YOUR_KEY"

# 3. Profile data
curl -X POST http://localhost:7860/api/analytics/profile/{sessionId} \
  -H "X-API-Key: YOUR_KEY"

# 4. Generate dashboard
curl -X POST http://localhost:7860/api/analytics/analyze/{sessionId} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"requirements": "Focus on sales trends"}'
```

### Get Dashboard Data

```bash
curl http://localhost:7860/api/analytics/sessions/{sessionId}/data \
  -H "X-API-Key: YOUR_KEY"
```

### Modify Dashboard

```bash
curl -X POST http://localhost:7860/api/analytics/sessions/{sessionId}/modify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"instruction": "Add a line chart for monthly revenue"}'
```

### Undo/Redo

```bash
# Undo
curl -X POST http://localhost:7860/api/analytics/sessions/{sessionId}/undo \
  -H "X-API-Key: YOUR_KEY"

# Redo
curl -X POST http://localhost:7860/api/analytics/sessions/{sessionId}/redo \
  -H "X-API-Key: YOUR_KEY"
```

---

## Configuration

### File Limits

```bash
# Maximum upload size
MAX_ANALYTICS_FILE_SIZE_MB=50

# Row limits
MAX_ANALYTICS_ROWS=100000
```

### LLM Settings

Dashboard generation uses the configured LLM provider. For best results:

- GPT-4 or Claude recommended for complex analysis
- Groq Llama 4 works well for standard dashboards

---

## Best Practices

### Data Preparation

1. **Clean headers** - Use descriptive column names
2. **Consistent formats** - Dates as dates, numbers as numbers
3. **No merged cells** - Flatten complex Excel structures
4. **First row headers** - Column names in row 1

### Getting Good Dashboards

1. **Add requirements** - "Focus on sales by region and time"
2. **Be specific** - "Show top 10 products" vs "show products"
3. **Iterate with NLP** - Use modification to refine
4. **Check profiles** - Fix data quality issues first

### Performance

- Large files (>50K rows) may take longer to profile
- Charts with many categories auto-group to "Top 10 + Others"
- Use filters to focus on relevant subsets

---

## Troubleshooting

### "Upload failed"

- Check file size (max 50MB)
- Verify file format (XLSX, XLS, CSV)
- Ensure file isn't corrupted

### "Parsing error"

- Check for merged cells
- Verify first row has headers
- Look for special characters in column names

### "Poor dashboard quality"

- Add specific requirements during analysis
- Use NLP modification to customize
- Check data quality score and fix issues

### Charts show wrong data

- Verify column types were detected correctly
- Check for mixed data types in columns
- Use modification to specify correct aggregations

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.
