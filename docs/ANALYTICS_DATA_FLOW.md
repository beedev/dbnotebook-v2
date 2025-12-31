# Analytics Dashboard Data Flow Documentation

## Overview

This document details the end-to-end data pipeline for the Analytics Dashboard feature in dbnotebook. The pipeline transforms Excel files into interactive, AI-recommended dashboard visualizations with cross-filtering capabilities.

---

## 1. End-to-End Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYTICS DATA PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │
│ Excel Upload │───▶│ Parse Stage  │───▶│  Profiling   │───▶│ LLM Analysis │
│  (.xlsx)     │    │  (pandas)    │    │(ydata-prof.) │    │   (OpenAI)   │
│              │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │                    │                    │
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐    ┌─────────────┐
                    │  Normalized │     │  Statistical│    │  Dashboard  │
                    │     Data    │     │   Insights  │    │    Config   │
                    │   (JSON)    │     │   (JSON)    │    │   (JSON)    │
                    └─────────────┘     └─────────────┘    └─────────────┘
                           │                    │                    │
                           └────────────────────┴────────────────────┘
                                                │
                                                ▼
                           ┌──────────────────────────────────────┐
                           │     Dashboard Rendering Engine       │
                           │  • KPI Cards                         │
                           │  • Interactive Charts (Recharts)     │
                           │  • Dynamic Filters                   │
                           │  • Cross-Filter Coordination         │
                           └──────────────────────────────────────┘
                                                │
                                                ▼
                           ┌──────────────────────────────────────┐
                           │      User Interaction Loop           │
                           │  Filter Selection → State Update     │
                           │  → Re-render → Visual Feedback       │
                           └──────────────────────────────────────┘
```

**Performance Characteristics**:
- Excel parsing: ~100-500ms for typical files (<10MB)
- Profiling: ~1-3s depending on data complexity
- LLM analysis: ~2-5s (network dependent)
- Dashboard render: ~200-500ms initial, <100ms updates

---

## 2. Excel Parsing Stage

### Technology Stack
- **pandas**: Data manipulation and analysis
- **openpyxl**: Excel file reading
- **numpy**: Numeric operations

### Process Flow

```typescript
interface ParsedExcelData {
  data: Record<string, any>[];      // Normalized row data
  columns: ColumnMetadata[];         // Column definitions
  rowCount: number;                  // Total rows
  sampleData: Record<string, any>[]; // First 100 rows for LLM
  errors: ParsingError[];            // Any issues encountered
}

interface ColumnMetadata {
  name: string;                      // Column name
  inferredType: DataType;            // auto|numeric|categorical|datetime|boolean
  uniqueCount: number;               // Distinct values
  nullCount: number;                 // Missing values
  sampleValues: any[];               // Representative values
}

type DataType = 'auto' | 'numeric' | 'categorical' | 'datetime' | 'boolean';

interface ParsingError {
  row?: number;
  column?: string;
  message: string;
  severity: 'warning' | 'error';
}
```

### Data Normalization Steps

1. **Type Inference**
   ```python
   # Pandas dtype mapping to dashboard types
   dtype_mapping = {
       'int64': 'numeric',
       'float64': 'numeric',
       'object': 'categorical',  # Further refined below
       'datetime64[ns]': 'datetime',
       'bool': 'boolean'
   }

   # Categorical refinement rules:
   # - <50 unique values → categorical
   # - String type + >50 unique → text (not filterable)
   # - Numeric with <20 unique → potentially categorical
   ```

2. **Missing Value Handling**
   - Detect: `null`, `NaN`, empty strings, `-`, `N/A`
   - Strategy: Preserve as `null` in JSON
   - Report: Missing % per column in metadata

3. **Date Parsing**
   ```python
   # Auto-detect common date formats
   formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%Y', 'ISO 8601']
   pd.to_datetime(column, infer_datetime_format=True, errors='coerce')
   ```

4. **Sample Extraction**
   ```python
   # Extract representative sample for LLM
   sample_size = min(100, len(df))
   sample = df.head(sample_size).to_dict('records')
   ```

### Error Recovery

- **Malformed Cells**: Convert to string, log warning
- **Mixed Types**: Coerce to most common type, log conversions
- **Encoding Issues**: Try UTF-8 → Latin1 → CP1252 fallback
- **Empty Sheets**: Return error with available sheet names

---

## 3. ydata-profiling Stage

### Profile Generation

```python
from ydata_profiling import ProfileReport

# Generate comprehensive profile
profile = ProfileReport(
    df,
    title="Analytics Dataset Profile",
    explorative=True,
    minimal=False,
    config_file={
        'correlations': {'auto': {'calculate': True}},
        'missing_diagrams': {'heatmap': True},
        'interactions': {'continuous': True},
        'samples': {'head': 10, 'tail': 10}
    }
)
```

### Insight Extraction for LLM

The profiling stage generates statistical insights that inform LLM recommendations:

```typescript
interface ProfilingInsights {
  overview: {
    variableCount: number;
    observationCount: number;
    missingCellsPercent: number;
    duplicateRowsPercent: number;
    totalMemorySize: string;
  };

  variables: VariableProfile[];
  correlations: CorrelationMatrix;
  dataQuality: QualityAlert[];
}

interface VariableProfile {
  name: string;
  type: 'numeric' | 'categorical' | 'datetime' | 'boolean' | 'text';

  // Numeric statistics
  stats?: {
    mean: number;
    median: number;
    std: number;
    min: number;
    max: number;
    skewness: number;
    kurtosis: number;
    quartiles: [number, number, number]; // Q1, Q2, Q3
    iqr: number;
  };

  // Categorical analysis
  categorical?: {
    uniqueCount: number;
    topValues: Array<{ value: string; count: number; percent: number }>;
    entropy: number; // Measure of diversity
  };

  // Missing value analysis
  missing: {
    count: number;
    percent: number;
  };

  // Data quality indicators
  quality: {
    duplicates: number;
    zeros: number;
    infinites: number;
    negatives?: number; // For numeric
  };
}

interface CorrelationMatrix {
  method: 'pearson' | 'spearman' | 'kendall';
  matrix: Record<string, Record<string, number>>;
  highCorrelations: Array<{
    var1: string;
    var2: string;
    correlation: number;
  }>;
}

interface QualityAlert {
  column: string;
  severity: 'high' | 'medium' | 'low';
  type: 'missing_values' | 'duplicates' | 'skewness' | 'outliers' | 'low_variance';
  message: string;
  recommendation?: string;
}
```

### HTML Report Generation

```python
# Generate interactive HTML report
profile.to_file("profile_report.html")

# Extract JSON summary for LLM
profile_summary = {
    'overview': profile.description_set['table'],
    'variables': profile.description_set['variables'],
    'correlations': profile.description_set['correlations'],
    'alerts': profile.description_set['alerts']
}
```

### Key Insights Extracted

1. **Data Types**: Refined type classification
2. **Missing Values**: Patterns and percentages
3. **Correlations**: Strong relationships (|r| > 0.7)
4. **Numeric Statistics**: Distribution characteristics
5. **Categorical Analysis**: Cardinality and top values
6. **Data Quality**: Alerts for anomalies
7. **Duplicates**: Exact and fuzzy duplicates

---

## 4. LLM Analysis Stage

### Prompt Template

```typescript
const DASHBOARD_PROMPT_TEMPLATE = `
You are an expert data analyst helping create an interactive analytics dashboard.

## Dataset Overview
- Total Rows: {rowCount}
- Total Columns: {columnCount}
- Data Quality Score: {qualityScore}/10

## Column Metadata
{columnMetadataTable}

## Statistical Insights
{profilingInsights}

## Correlations
High correlations detected:
{correlationList}

## Data Quality Alerts
{qualityAlerts}

## Sample Data (First 10 Rows)
{sampleDataJson}

## Task
Based on this analysis, create a comprehensive dashboard configuration with:

1. **KPIs** (3-6 key metrics): Identify the most important numeric metrics to highlight
   - Consider: business relevance, data quality, variance
   - Prefer: aggregations (sum, avg, count), percentages, ratios

2. **Charts** (4-8 visualizations): Recommend chart types and configurations
   - Bar Chart: Categorical comparisons, rankings
   - Line Chart: Time series, trends
   - Pie Chart: Proportional breakdowns (<8 categories)
   - Scatter Plot: Correlations between two numeric variables
   - Area Chart: Cumulative trends over time

3. **Filters** (2-5 dimensions): Suggest interactive filters
   - Categorical with <50 unique values
   - Date ranges for datetime columns
   - Numeric ranges for continuous variables

4. **Cross-Filter Strategy**: Define how filters should cascade

## Response Format
Return a valid JSON object matching this schema:

{
  "kpis": [
    {
      "id": "unique_kpi_id",
      "title": "Display Name",
      "metric": "column_name",
      "aggregation": "sum|avg|count|min|max|median",
      "format": "number|currency|percentage",
      "icon": "TrendingUp|DollarSign|Users|...",
      "color": "blue|green|red|purple|orange"
    }
  ],
  "charts": [
    {
      "id": "unique_chart_id",
      "title": "Chart Title",
      "type": "bar|line|pie|scatter|area",
      "xAxis": "column_name",
      "yAxis": "column_name", // or metric expression
      "aggregation": "sum|avg|count|min|max",
      "color": "color_name",
      "allowCrossFilter": true|false
    }
  ],
  "filters": [
    {
      "id": "unique_filter_id",
      "column": "column_name",
      "type": "categorical|range|date",
      "label": "Display Label",
      "defaultValue": null|value
    }
  ],
  "metadata": {
    "title": "Dashboard Title",
    "description": "Brief description",
    "recommendationReason": "Why these visualizations?"
  }
}

## Guidelines
- Prioritize columns with high data quality (low missing %)
- Use correlations to suggest scatter plots
- Recommend time-based charts if datetime columns exist
- Limit pie charts to <8 categories
- Ensure at least one filter per major categorical dimension
- Make KPIs actionable and business-relevant
`;
```

### LLM Provider Integration

```typescript
interface LLMAnalysisRequest {
  provider: 'openai' | 'anthropic' | 'gemini' | 'ollama';
  model: string;
  temperature: number; // 0.3 for structured output
  maxTokens: number;   // 2000-3000
  promptData: {
    rowCount: number;
    columnCount: number;
    qualityScore: number;
    columnMetadataTable: string;
    profilingInsights: string;
    correlationList: string;
    qualityAlerts: string;
    sampleDataJson: string;
  };
}

// Uses existing dbnotebook LLM infrastructure
async function analyzeDashboard(request: LLMAnalysisRequest): Promise<DashboardConfig> {
  const prompt = formatPrompt(DASHBOARD_PROMPT_TEMPLATE, request.promptData);

  const response = await llmProvider.complete({
    model: request.model,
    messages: [{ role: 'user', content: prompt }],
    temperature: request.temperature,
    maxTokens: request.maxTokens,
    responseFormat: { type: 'json_object' } // For OpenAI structured output
  });

  const config = JSON.parse(response.content);
  return validateDashboardConfig(config);
}
```

### Expected JSON Response Structure

```typescript
interface DashboardConfig {
  kpis: KPIDefinition[];
  charts: ChartDefinition[];
  filters: FilterDefinition[];
  metadata: DashboardMetadata;
}

interface KPIDefinition {
  id: string;
  title: string;
  metric: string;                    // Column name
  aggregation: AggregationType;
  format: 'number' | 'currency' | 'percentage';
  icon: LucideIconName;
  color: 'blue' | 'green' | 'red' | 'purple' | 'orange';
  prefix?: string;                   // e.g., "$" for currency
  suffix?: string;                   // e.g., "%" for percentage
  decimalPlaces?: number;
}

type AggregationType = 'sum' | 'avg' | 'count' | 'min' | 'max' | 'median';

interface ChartDefinition {
  id: string;
  title: string;
  type: ChartType;
  xAxis: string;                     // Column name
  yAxis: string;                     // Column name or expression
  aggregation: AggregationType;
  color: string;                     // Color name or hex
  allowCrossFilter: boolean;
  sortBy?: 'value' | 'label';
  sortOrder?: 'asc' | 'desc';
  limit?: number;                    // Top N items
}

type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area';

interface FilterDefinition {
  id: string;
  column: string;
  type: 'categorical' | 'range' | 'date';
  label: string;
  defaultValue?: any;
  options?: string[];                // For categorical
  min?: number;                      // For range
  max?: number;
}

interface DashboardMetadata {
  title: string;
  description: string;
  recommendationReason: string;
  generatedAt: string;               // ISO timestamp
  dataSource: string;                // Original filename
}
```

### KPI Identification Logic

The LLM follows these heuristics (embedded in prompt):

1. **Business Relevance**
   - Revenue, sales, profit metrics
   - Customer counts, conversion rates
   - Efficiency metrics (e.g., avg processing time)

2. **Data Quality Filter**
   - Exclude columns with >20% missing values
   - Prefer numeric columns with low variance
   - Avoid derived columns if raw metrics exist

3. **Statistical Significance**
   - High variance indicates interesting metric
   - Correlations suggest derived KPIs (e.g., ratio)
   - Outliers may indicate important events

4. **Aggregation Strategy**
   - Sum: Transactional metrics (revenue, quantity)
   - Avg: Performance metrics (rating, duration)
   - Count: Entity counts (customers, orders)
   - Min/Max: Extremes (best/worst performance)

### Chart Type Selection Logic

```typescript
interface ChartSelectionCriteria {
  barChart: {
    conditions: [
      'categorical x-axis',
      'numeric y-axis',
      'comparing categories',
      'ranking/distribution'
    ];
    optimal: '<20 categories, clear differences';
  };

  lineChart: {
    conditions: [
      'datetime/sequential x-axis',
      'numeric y-axis',
      'trend analysis',
      'time series'
    ];
    optimal: '>5 data points, temporal pattern';
  };

  pieChart: {
    conditions: [
      'categorical breakdown',
      'proportional analysis',
      'part-to-whole relationship'
    ];
    optimal: '3-7 categories, clear proportions';
    avoid: '>8 categories, similar values';
  };

  scatterPlot: {
    conditions: [
      'two numeric variables',
      'correlation analysis',
      'outlier detection'
    ];
    optimal: 'correlation |r| > 0.5, >20 points';
  };

  areaChart: {
    conditions: [
      'cumulative metrics over time',
      'stacked comparisons',
      'volume/magnitude emphasis'
    ];
    optimal: 'continuous time series, positive values';
  };
}
```

### Filter Recommendation Logic

1. **Categorical Filters**
   - Unique values: 2-50
   - Data quality: <10% missing
   - Business relevance: High (e.g., region, category, status)

2. **Date Filters**
   - Any datetime column with >30 unique dates
   - Default: Last 90 days or full range
   - Format: Date range picker

3. **Numeric Range Filters**
   - Continuous variables with wide range
   - Avoid if highly skewed (use categorical binning)
   - Default: Full range (min-max)

---

## 5. Dashboard Configuration Schema

### Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Dashboard Configuration Schema",
  "type": "object",
  "required": ["kpis", "charts", "filters", "metadata"],
  "properties": {
    "kpis": {
      "type": "array",
      "minItems": 3,
      "maxItems": 6,
      "items": {
        "type": "object",
        "required": ["id", "title", "metric", "aggregation", "format"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^kpi_[a-z0-9_]+$",
            "description": "Unique identifier (e.g., kpi_total_revenue)"
          },
          "title": {
            "type": "string",
            "minLength": 3,
            "maxLength": 50,
            "description": "Display name for the KPI card"
          },
          "metric": {
            "type": "string",
            "description": "Column name to aggregate"
          },
          "aggregation": {
            "type": "string",
            "enum": ["sum", "avg", "count", "min", "max", "median"]
          },
          "format": {
            "type": "string",
            "enum": ["number", "currency", "percentage"]
          },
          "icon": {
            "type": "string",
            "description": "Lucide icon name (e.g., TrendingUp, DollarSign)"
          },
          "color": {
            "type": "string",
            "enum": ["blue", "green", "red", "purple", "orange"]
          },
          "prefix": {
            "type": "string",
            "description": "Optional prefix (e.g., '$', '€')"
          },
          "suffix": {
            "type": "string",
            "description": "Optional suffix (e.g., '%', 'ms')"
          },
          "decimalPlaces": {
            "type": "integer",
            "minimum": 0,
            "maximum": 4,
            "default": 0
          }
        }
      }
    },
    "charts": {
      "type": "array",
      "minItems": 4,
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["id", "title", "type", "xAxis", "yAxis"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^chart_[a-z0-9_]+$"
          },
          "title": {
            "type": "string",
            "minLength": 5,
            "maxLength": 100
          },
          "type": {
            "type": "string",
            "enum": ["bar", "line", "pie", "scatter", "area"]
          },
          "xAxis": {
            "type": "string",
            "description": "Column name for x-axis"
          },
          "yAxis": {
            "type": "string",
            "description": "Column name or expression for y-axis"
          },
          "aggregation": {
            "type": "string",
            "enum": ["sum", "avg", "count", "min", "max", "median"]
          },
          "color": {
            "type": "string",
            "description": "Color name or hex code"
          },
          "allowCrossFilter": {
            "type": "boolean",
            "default": true,
            "description": "Enable cross-filtering on click"
          },
          "sortBy": {
            "type": "string",
            "enum": ["value", "label"],
            "description": "Sort axis by value or label"
          },
          "sortOrder": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "desc"
          },
          "limit": {
            "type": "integer",
            "minimum": 5,
            "maximum": 50,
            "description": "Limit to top N items"
          }
        }
      }
    },
    "filters": {
      "type": "array",
      "minItems": 2,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["id", "column", "type", "label"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^filter_[a-z0-9_]+$"
          },
          "column": {
            "type": "string",
            "description": "Column name to filter"
          },
          "type": {
            "type": "string",
            "enum": ["categorical", "range", "date"]
          },
          "label": {
            "type": "string",
            "description": "User-facing label"
          },
          "defaultValue": {
            "description": "Initial filter value (null = all)"
          },
          "options": {
            "type": "array",
            "items": { "type": "string" },
            "description": "For categorical filters"
          },
          "min": {
            "type": "number",
            "description": "For range filters"
          },
          "max": {
            "type": "number",
            "description": "For range filters"
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "required": ["title", "description"],
      "properties": {
        "title": {
          "type": "string",
          "minLength": 5,
          "maxLength": 100
        },
        "description": {
          "type": "string",
          "maxLength": 500
        },
        "recommendationReason": {
          "type": "string",
          "description": "Why the LLM suggested this configuration"
        },
        "generatedAt": {
          "type": "string",
          "format": "date-time"
        },
        "dataSource": {
          "type": "string",
          "description": "Original Excel filename"
        }
      }
    }
  }
}
```

### TypeScript Interfaces

```typescript
// Complete type definitions for dashboard configuration

interface DashboardConfig {
  kpis: KPIDefinition[];
  charts: ChartDefinition[];
  filters: FilterDefinition[];
  metadata: DashboardMetadata;
}

interface KPIDefinition {
  id: string;                        // Pattern: kpi_[a-z0-9_]+
  title: string;                     // 3-50 chars
  metric: string;                    // Column name
  aggregation: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'median';
  format: 'number' | 'currency' | 'percentage';
  icon?: string;                     // Lucide icon name
  color?: 'blue' | 'green' | 'red' | 'purple' | 'orange';
  prefix?: string;                   // e.g., "$"
  suffix?: string;                   // e.g., "%"
  decimalPlaces?: number;            // 0-4
}

interface ChartDefinition {
  id: string;                        // Pattern: chart_[a-z0-9_]+
  title: string;                     // 5-100 chars
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'area';
  xAxis: string;                     // Column name
  yAxis: string;                     // Column name or expression
  aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'median';
  color?: string;                    // Color name or hex
  allowCrossFilter?: boolean;        // Default: true
  sortBy?: 'value' | 'label';
  sortOrder?: 'asc' | 'desc';        // Default: desc
  limit?: number;                    // 5-50, top N items
}

interface FilterDefinition {
  id: string;                        // Pattern: filter_[a-z0-9_]+
  column: string;                    // Column name
  type: 'categorical' | 'range' | 'date';
  label: string;                     // User-facing label
  defaultValue?: any;                // null = all
  options?: string[];                // For categorical
  min?: number;                      // For range
  max?: number;                      // For range
}

interface DashboardMetadata {
  title: string;                     // 5-100 chars
  description: string;               // Max 500 chars
  recommendationReason?: string;     // LLM explanation
  generatedAt?: string;              // ISO timestamp
  dataSource?: string;               // Excel filename
}
```

---

## 6. Cross-Filter Event Flow

### Event Sequence Diagram

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   User      │         │  Component  │         │   Context   │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │ Click Chart Element   │                       │
       ├──────────────────────▶│                       │
       │                       │                       │
       │                       │ Update chartSelections│
       │                       ├──────────────────────▶│
       │                       │                       │
       │                       │   Derive Filters      │
       │                       │◀──────────────────────┤
       │                       │                       │
       │                       │   Apply to rawData    │
       │                       │──────────────────────▶│
       │                       │                       │
       │                       │   Return filteredData │
       │                       │◀──────────────────────┤
       │                       │                       │
       │                       │   Re-render Charts    │
       │                       │◀──────────────────────┤
       │                       │                       │
       │   Visual Feedback     │                       │
       │◀──────────────────────┤                       │
       │   (Highlight + Fade)  │                       │
       │                       │                       │
```

### Implementation Details

```typescript
// 1. Chart Click Handler
const handleChartClick = (chartId: string, dataPoint: any) => {
  const chart = config.charts.find(c => c.id === chartId);
  if (!chart?.allowCrossFilter) return;

  // Create filter condition from clicked element
  const filterCondition: ChartSelection = {
    chartId,
    column: chart.xAxis,
    value: dataPoint[chart.xAxis],
    label: `${chart.title}: ${dataPoint[chart.xAxis]}`
  };

  // Update selections in context
  updateChartSelections(prev => {
    const existing = prev.find(s => s.chartId === chartId);
    if (existing && existing.value === filterCondition.value) {
      // Toggle off if clicking same element
      return prev.filter(s => s.chartId !== chartId);
    }
    // Replace existing selection for this chart
    return [...prev.filter(s => s.chartId !== chartId), filterCondition];
  });
};

// 2. Filter Derivation (in Context)
interface ChartSelection {
  chartId: string;
  column: string;
  value: any;
  label: string;
}

const deriveFiltersFromSelections = (
  selections: ChartSelection[]
): Record<string, any> => {
  return selections.reduce((acc, selection) => {
    acc[selection.column] = selection.value;
    return acc;
  }, {} as Record<string, any>);
};

// 3. Data Filtering Logic
const applyFilters = (
  data: Record<string, any>[],
  activeFilters: Record<string, any>,
  chartSelections: ChartSelection[]
): Record<string, any>[] => {
  let filtered = data;

  // Apply explicit filters
  Object.entries(activeFilters).forEach(([column, value]) => {
    if (value === null || value === undefined) return;

    if (Array.isArray(value)) {
      // Multi-select categorical
      filtered = filtered.filter(row => value.includes(row[column]));
    } else if (typeof value === 'object' && 'min' in value) {
      // Range filter
      const { min, max } = value;
      filtered = filtered.filter(row =>
        row[column] >= min && row[column] <= max
      );
    } else {
      // Single value
      filtered = filtered.filter(row => row[column] === value);
    }
  });

  // Apply chart cross-filters
  const chartFilters = deriveFiltersFromSelections(chartSelections);
  Object.entries(chartFilters).forEach(([column, value]) => {
    filtered = filtered.filter(row => row[column] === value);
  });

  return filtered;
};

// 4. Re-render Trigger
useEffect(() => {
  const filtered = applyFilters(rawData, activeFilters, chartSelections);
  setFilteredData(filtered);

  // Trigger re-render of all chart components
  // (Handled automatically via React state)
}, [rawData, activeFilters, chartSelections]);

// 5. Visual Feedback
const ChartWrapper = ({ chart, isFiltered }: ChartWrapperProps) => {
  const hasActiveSelection = chartSelections.some(s => s.chartId === chart.id);

  return (
    <div className={cn(
      "chart-container transition-all duration-300",
      hasActiveSelection && "ring-2 ring-blue-500",
      isFiltered && !hasActiveSelection && "opacity-60"
    )}>
      {/* Chart content */}
      {hasActiveSelection && (
        <div className="absolute top-2 right-2 badge badge-blue">
          Filtered
        </div>
      )}
    </div>
  );
};
```

### Cross-Filter Behavior Matrix

| User Action | Chart A | Chart B | Chart C | Filter Panel |
|-------------|---------|---------|---------|--------------|
| Click Chart A element | Highlight | Fade + Update | Fade + Update | Add badge |
| Click Chart B element | Fade + Update | Highlight | Fade + Update | Add badge |
| Click same element again | Remove highlight | Restore | Restore | Remove badge |
| Clear all filters | Restore | Restore | Restore | Reset |

### Performance Optimizations

```typescript
// Memoize filtered data computation
const filteredData = useMemo(() => {
  return applyFilters(rawData, activeFilters, chartSelections);
}, [rawData, activeFilters, chartSelections]);

// Memoize chart data aggregation
const chartData = useMemo(() => {
  return aggregateChartData(filteredData, chart);
}, [filteredData, chart]);

// Debounce filter updates for range sliders
const debouncedFilterUpdate = useDebouncedCallback(
  (column: string, value: any) => {
    updateActiveFilters(prev => ({ ...prev, [column]: value }));
  },
  300 // 300ms debounce
);
```

---

## 7. State Management Architecture

### AnalyticsContext Structure

```typescript
interface AnalyticsContextValue {
  // Data State
  rawData: Record<string, any>[];          // Original parsed data
  filteredData: Record<string, any>[];     // After filters applied
  columns: ColumnMetadata[];               // Column definitions

  // Configuration State
  config: DashboardConfig | null;          // LLM-generated config
  isConfigLoading: boolean;
  configError: string | null;

  // Filter State
  activeFilters: Record<string, any>;      // User-applied filters
  chartSelections: ChartSelection[];       // Cross-filter selections

  // UI State
  isLoading: boolean;
  error: string | null;
  uploadProgress: number;                  // 0-100

  // Actions
  uploadFile: (file: File) => Promise<void>;
  updateActiveFilters: (filters: Record<string, any>) => void;
  updateChartSelections: (selections: ChartSelection[]) => void;
  clearAllFilters: () => void;
  regenerateConfig: () => Promise<void>;
  exportDashboard: (format: 'json' | 'pdf') => void;
}

// Context Provider Implementation
const AnalyticsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [rawData, setRawData] = useState<Record<string, any>[]>([]);
  const [config, setConfig] = useState<DashboardConfig | null>(null);
  const [activeFilters, setActiveFilters] = useState<Record<string, any>>({});
  const [chartSelections, setChartSelections] = useState<ChartSelection[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Derived state - memoized for performance
  const filteredData = useMemo(() =>
    applyFilters(rawData, activeFilters, chartSelections),
    [rawData, activeFilters, chartSelections]
  );

  const uploadFile = async (file: File) => {
    setIsLoading(true);
    try {
      // 1. Parse Excel
      const parsed = await parseExcel(file);
      setRawData(parsed.data);

      // 2. Generate profile
      const profile = await generateProfile(parsed.data);

      // 3. LLM analysis
      const dashboardConfig = await analyzeDashboard({
        data: parsed,
        profile: profile,
        provider: 'openai',
        model: 'gpt-4'
      });

      setConfig(dashboardConfig);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const clearAllFilters = () => {
    setActiveFilters({});
    setChartSelections([]);
  };

  return (
    <AnalyticsContext.Provider value={{
      rawData,
      filteredData,
      config,
      activeFilters,
      chartSelections,
      isLoading,
      uploadFile,
      updateActiveFilters: setActiveFilters,
      updateChartSelections: setChartSelections,
      clearAllFilters,
    }}>
      {children}
    </AnalyticsContext.Provider>
  );
};
```

### Data Flow Between Components

```
┌────────────────────────────────────────────────────────────────┐
│                      AnalyticsContext                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State:                                                   │  │
│  │  • rawData (immutable source of truth)                   │  │
│  │  • filteredData (computed from rawData + filters)        │  │
│  │  • config (LLM-generated dashboard definition)           │  │
│  │  • activeFilters (user selections)                       │  │
│  │  • chartSelections (cross-filter state)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────────────────────┐
                              │                                 │
                              ▼                                 ▼
                    ┌─────────────────┐             ┌─────────────────┐
                    │  FilterPanel    │             │   KPIGrid       │
                    ├─────────────────┤             ├─────────────────┤
                    │ Reads:          │             │ Reads:          │
                    │ • config.filters│             │ • config.kpis   │
                    │ • activeFilters │             │ • filteredData  │
                    │                 │             │                 │
                    │ Updates:        │             │ Computes:       │
                    │ • activeFilters │             │ • Aggregations  │
                    └─────────────────┘             └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  ChartGrid      │
                    ├─────────────────┤
                    │ Reads:          │
                    │ • config.charts │
                    │ • filteredData  │
                    │ • chartSelections│
                    │                 │
                    │ Updates:        │
                    │ • chartSelections│
                    │   (on click)    │
                    └─────────────────┘
```

### Component Communication Pattern

```typescript
// 1. FilterPanel → Context
const FilterPanel = () => {
  const { config, activeFilters, updateActiveFilters } = useAnalytics();

  const handleFilterChange = (filterId: string, value: any) => {
    const filter = config?.filters.find(f => f.id === filterId);
    if (!filter) return;

    updateActiveFilters({
      ...activeFilters,
      [filter.column]: value
    });
  };

  return (
    <>
      {config?.filters.map(filter => (
        <FilterControl
          key={filter.id}
          filter={filter}
          value={activeFilters[filter.column]}
          onChange={(value) => handleFilterChange(filter.id, value)}
        />
      ))}
    </>
  );
};

// 2. ChartGrid → Context
const ChartGrid = () => {
  const { config, filteredData, chartSelections, updateChartSelections } = useAnalytics();

  const handleChartClick = (chartId: string, dataPoint: any) => {
    const chart = config?.charts.find(c => c.id === chartId);
    if (!chart?.allowCrossFilter) return;

    const newSelection: ChartSelection = {
      chartId,
      column: chart.xAxis,
      value: dataPoint[chart.xAxis],
      label: `${chart.title}: ${dataPoint[chart.xAxis]}`
    };

    updateChartSelections(prev => {
      const existing = prev.find(s => s.chartId === chartId);
      if (existing?.value === newSelection.value) {
        return prev.filter(s => s.chartId !== chartId);
      }
      return [...prev.filter(s => s.chartId !== chartId), newSelection];
    });
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {config?.charts.map(chart => (
        <ChartRenderer
          key={chart.id}
          chart={chart}
          data={filteredData}
          isFiltered={chartSelections.some(s => s.chartId === chart.id)}
          onClick={(dataPoint) => handleChartClick(chart.id, dataPoint)}
        />
      ))}
    </div>
  );
};

// 3. KPIGrid → Context (read-only)
const KPIGrid = () => {
  const { config, filteredData } = useAnalytics();

  const calculateKPI = (kpi: KPIDefinition) => {
    const values = filteredData.map(row => row[kpi.metric]).filter(v => v != null);

    switch (kpi.aggregation) {
      case 'sum': return values.reduce((a, b) => a + b, 0);
      case 'avg': return values.reduce((a, b) => a + b, 0) / values.length;
      case 'count': return values.length;
      case 'min': return Math.min(...values);
      case 'max': return Math.max(...values);
      default: return 0;
    }
  };

  return (
    <>
      {config?.kpis.map(kpi => (
        <KPICard key={kpi.id} kpi={kpi} value={calculateKPI(kpi)} />
      ))}
    </>
  );
};
```

### Performance Optimizations

#### 1. Memoization Strategy

```typescript
// Aggressive memoization for expensive computations
const filteredData = useMemo(() =>
  applyFilters(rawData, activeFilters, chartSelections),
  [rawData, activeFilters, chartSelections]
);

const aggregatedChartData = useMemo(() =>
  config?.charts.map(chart => ({
    chartId: chart.id,
    data: aggregateData(filteredData, chart)
  })),
  [filteredData, config?.charts]
);

const kpiValues = useMemo(() =>
  config?.kpis.map(kpi => ({
    kpiId: kpi.id,
    value: calculateKPI(filteredData, kpi)
  })),
  [filteredData, config?.kpis]
);
```

#### 2. Web Workers for Large Datasets

```typescript
// worker.ts - Offload heavy computations
interface WorkerMessage {
  type: 'filter' | 'aggregate' | 'profile';
  payload: any;
}

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'filter':
      const filtered = applyFilters(payload.data, payload.filters);
      self.postMessage({ type: 'filter', result: filtered });
      break;

    case 'aggregate':
      const aggregated = aggregateData(payload.data, payload.chart);
      self.postMessage({ type: 'aggregate', result: aggregated });
      break;

    case 'profile':
      const profile = generateProfile(payload.data);
      self.postMessage({ type: 'profile', result: profile });
      break;
  }
};

// Context usage
const worker = useMemo(() => new Worker(new URL('./worker.ts', import.meta.url)), []);

const uploadFile = async (file: File) => {
  // Offload profiling to worker
  worker.postMessage({
    type: 'profile',
    payload: { data: parsedData }
  });

  worker.onmessage = (event) => {
    if (event.data.type === 'profile') {
      setProfile(event.data.result);
    }
  };
};
```

#### 3. Virtual Scrolling for Large Tables

```typescript
// For data preview tables with >1000 rows
import { useVirtualizer } from '@tanstack/react-virtual';

const DataTable = ({ data }: { data: Record<string, any>[] }) => {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35, // Row height
    overscan: 10 // Render extra rows
  });

  return (
    <div ref={parentRef} style={{ height: '500px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`
            }}
          >
            <TableRow data={data[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

#### 4. Chart Rendering Optimization

```typescript
// Lazy load chart library
const ChartRenderer = lazy(() => import('./ChartRenderer'));

// Debounce resize events
const useResponsiveChart = () => {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const handleResize = debounce(() => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    }, 200);

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return dimensions;
};

// Limit chart data points
const limitDataPoints = (data: any[], maxPoints: number = 1000) => {
  if (data.length <= maxPoints) return data;

  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, index) => index % step === 0);
};
```

---

## Performance Benchmarks

### Expected Performance Metrics

| Stage | Small (<1MB) | Medium (1-10MB) | Large (10-50MB) |
|-------|--------------|-----------------|-----------------|
| Excel Parsing | 50-100ms | 200-500ms | 1-3s |
| Profiling | 100-300ms | 1-2s | 3-10s |
| LLM Analysis | 2-3s | 3-5s | 5-8s |
| Initial Render | 100-200ms | 200-400ms | 500-1000ms |
| Filter Update | <50ms | <100ms | <200ms |
| Cross-Filter | <50ms | <100ms | <200ms |

### Optimization Thresholds

- **Web Worker Activation**: >5000 rows
- **Virtual Scrolling**: >1000 table rows
- **Chart Data Limiting**: >1000 data points per chart
- **Debouncing**: Range filters, resize events (200-300ms)
- **Lazy Loading**: Non-critical components, chart library

---

## Error Handling & Edge Cases

### Data Quality Issues

```typescript
interface DataQualityReport {
  issues: Array<{
    severity: 'critical' | 'warning' | 'info';
    column?: string;
    message: string;
    recommendation: string;
  }>;
  overallScore: number; // 0-10
}

// Example checks
const validateDataQuality = (data: any[]): DataQualityReport => {
  const issues = [];

  // Check 1: Empty dataset
  if (data.length === 0) {
    issues.push({
      severity: 'critical',
      message: 'Dataset is empty',
      recommendation: 'Upload a file with data'
    });
  }

  // Check 2: Missing values >50%
  columns.forEach(col => {
    const missingPercent = calculateMissingPercent(data, col.name);
    if (missingPercent > 50) {
      issues.push({
        severity: 'warning',
        column: col.name,
        message: `${missingPercent}% missing values`,
        recommendation: 'Consider excluding or imputing this column'
      });
    }
  });

  // Check 3: Low cardinality
  // Check 4: Outliers
  // ...

  return { issues, overallScore: calculateScore(issues) };
};
```

### LLM Response Validation

```typescript
const validateDashboardConfig = (config: any): DashboardConfig => {
  // Schema validation
  const result = DashboardConfigSchema.safeParse(config);
  if (!result.success) {
    throw new Error(`Invalid config: ${result.error.message}`);
  }

  // Business logic validation
  if (config.kpis.length < 3) {
    throw new Error('At least 3 KPIs required');
  }

  // Cross-reference validation
  const columnNames = new Set(columns.map(c => c.name));
  config.charts.forEach(chart => {
    if (!columnNames.has(chart.xAxis)) {
      throw new Error(`Invalid xAxis: ${chart.xAxis}`);
    }
  });

  return config;
};
```

---

## File Paths

- **Main Documentation**: `/Users/bharath/Desktop/dbnotebook/docs/ANALYTICS_DATA_FLOW.md`
- **Context Provider**: `/Users/bharath/Desktop/dbnotebook/dbnotebook/core/analytics/AnalyticsContext.tsx`
- **Worker Script**: `/Users/bharath/Desktop/dbnotebook/dbnotebook/core/analytics/worker.ts`
- **Type Definitions**: `/Users/bharath/Desktop/dbnotebook/dbnotebook/core/analytics/types.ts`

---

## Next Steps

1. **Implementation**: Build components following this data flow
2. **Testing**: Validate each stage with sample datasets
3. **Optimization**: Profile performance and apply optimizations
4. **Documentation**: Keep this document updated with learnings
