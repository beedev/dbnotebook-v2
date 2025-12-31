# Analytics Dashboard Feature

## Feature Overview

### Goal
Transform raw Excel data into interactive, AI-powered analytics dashboards with minimal user effort. The workflow is:

1. **Upload** Excel file via drag-and-drop interface
2. **AI Analysis** automatically identifies key performance indicators (KPIs) and metrics
3. **Auto-Generate** interactive dashboards with appropriate visualizations
4. **Interact** with cross-filtering capabilities across charts
5. **Export** polished dashboards to PDF for sharing

### Core Capabilities

| Capability | Description | Technology |
|------------|-------------|------------|
| **Statistical Analysis** | Automated data profiling, quality assessment, and statistical insights | ydata-profiling |
| **KPI Detection** | AI-powered identification of meaningful metrics and relationships | LLM (existing providers) |
| **Interactive Visualization** | Multiple chart types with cross-filtering and drill-down | Chart.js, D3.js |
| **Quality Alerts** | Automated detection of data quality issues and anomalies | ydata-profiling |
| **Export** | Generate shareable PDF reports with all visualizations | html2canvas, jsPDF |

### Key Differentiators

- **Zero Configuration**: No manual KPI selection required
- **AI-Driven Insights**: Intelligent detection of relevant metrics and relationships
- **Advanced Visualizations**: Beyond basic charts with D3.js interactive graphics
- **Cross-Filtering**: Click any chart element to filter all other visualizations
- **Quality First**: Automated data quality assessment and alerts

---

## Integration with dbnotebook

### Architecture Position

The Analytics Dashboard integrates as a standalone feature within dbnotebook's RAG system, complementing the existing notebook-based workflow with structured data analysis capabilities.

```
dbnotebook (RAG System)
├── Notebooks (Unstructured Data)
│   ├── PDF/Document Upload
│   ├── Chat-based RAG
│   └── Knowledge Base
│
└── Analytics Dashboard (Structured Data) ← NEW
    ├── Excel Upload
    ├── KPI Detection
    └── Interactive Dashboards
```

### Backend Integration

**New Flask Blueprint**: `/api/analytics/*`

```python
# New file: backend/api/analytics.py
from flask import Blueprint

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

# Endpoints:
# POST   /api/analytics/upload          - Upload Excel file
# POST   /api/analytics/analyze          - Trigger KPI detection
# GET    /api/analytics/sessions         - List user's sessions
# GET    /api/analytics/sessions/<id>    - Get session details
# POST   /api/analytics/generate-charts  - Create visualizations
# DELETE /api/analytics/sessions/<id>    - Delete session
```

**New Database Model**: `AnalyticsSession`

```python
# backend/models/analytics.py
class AnalyticsSession(db.Model):
    __tablename__ = 'analytics_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notebook_id = db.Column(db.Integer, db.ForeignKey('notebooks.id'), nullable=True)

    filename = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Data storage
    raw_data_path = db.Column(db.Text)  # Path to uploaded Excel
    profiling_report_path = db.Column(db.Text)  # ydata report HTML

    # AI-generated content
    detected_kpis = db.Column(db.JSON)  # List of KPI definitions
    chart_configs = db.Column(db.JSON)  # Chart.js configurations
    filters = db.Column(db.JSON)  # Auto-generated filter definitions

    # Metadata
    data_quality_score = db.Column(db.Float)
    row_count = db.Column(db.Integer)
    column_count = db.Column(db.Integer)
    quality_alerts = db.Column(db.JSON)  # Data quality warnings

    # Relationships
    user = db.relationship('User', backref='analytics_sessions')
    notebook = db.relationship('Notebook', backref='analytics_sessions')
```

### Frontend Integration

**New React Components**: `frontend/src/components/Analytics/`

```
src/components/Analytics/
├── AnalyticsDashboard.jsx       # Main container component
├── FileUpload.jsx                # Drag-and-drop Excel upload
├── KPIPanel.jsx                  # Display detected KPIs
├── ChartRenderer.jsx             # Wrapper for all chart types
├── FilterPanel.jsx               # Auto-generated filters UI
├── CrossFilterManager.jsx        # Manage cross-filtering state
├── DataQualityAlerts.jsx         # Display ydata warnings
├── ProfileReportViewer.jsx       # Embedded ydata HTML report
├── ExportButton.jsx              # PDF export functionality
└── charts/
    ├── BasicCharts.jsx           # Chart.js (Bar, Line, Pie, etc.)
    └── AdvancedVisualizations.jsx # D3.js (TreeMap, Sankey, etc.)
```

**New Route**: `/analytics`

```jsx
// frontend/src/App.jsx
import AnalyticsDashboard from './components/Analytics/AnalyticsDashboard';

<Route path="/analytics" element={<AnalyticsDashboard />} />
```

### Reused Components & Infrastructure

| Component | Usage in Analytics | Source |
|-----------|-------------------|--------|
| **LLM Providers** | KPI detection, insight generation | `backend/services/llm_provider.py` |
| **ThemeContext** | Deep Space theme application | `frontend/src/contexts/ThemeContext.jsx` |
| **useToast** | User feedback and notifications | `frontend/src/hooks/useToast.js` |
| **Database Connection** | Session persistence | `backend/db.py` |
| **User Authentication** | Access control | `backend/auth.py` |
| **File Storage** | Excel and report storage | `backend/storage/` |

### Optional Notebook Linking

Analytics sessions can optionally link to notebooks for combined analysis:

```python
# Example: Link analytics session to notebook for context
session = AnalyticsSession(
    user_id=current_user.id,
    notebook_id=123,  # Optional: link to sales notebook
    filename="Q4_sales.xlsx"
)
```

---

## Tech Stack Additions

### Backend Dependencies

Add to `backend/requirements.txt`:

```txt
# Analytics Feature
ydata-profiling==4.6.0        # Automated data profiling and quality assessment
openpyxl==3.1.2                # Excel file parsing and manipulation
pandas==2.1.4                  # Data manipulation (already required by ydata)
```

**Installation**:
```bash
cd backend
pip install ydata-profiling openpyxl
```

### Frontend Dependencies

Add to `frontend/package.json`:

```json
{
  "dependencies": {
    "chart.js": "^4.4.1",
    "react-chartjs-2": "^5.2.0",
    "d3": "^7.8.5",
    "react-dropzone": "^14.2.3",
    "html2canvas": "^1.4.1",
    "jspdf": "^2.5.1"
  }
}
```

**Installation**:
```bash
cd frontend
npm install chart.js react-chartjs-2 d3 react-dropzone html2canvas jspdf
```

### Technology Rationale

| Technology | Purpose | Why This Choice |
|------------|---------|-----------------|
| **ydata-profiling** | Statistical analysis | Industry-standard, comprehensive profiling, minimal configuration |
| **openpyxl** | Excel parsing | Robust, well-maintained, handles complex Excel features |
| **Chart.js** | Basic charts | Lightweight, responsive, extensive chart types, good React integration |
| **D3.js** | Advanced visualizations | Maximum flexibility, powerful data-driven graphics, rich ecosystem |
| **react-dropzone** | File upload | Accessible, customizable, drag-and-drop support |
| **html2canvas + jsPDF** | PDF export | Client-side export, no server load, maintains visual fidelity |

---

## Feature Capabilities

### 1. Excel File Upload

**User Experience**:
- Drag-and-drop interface with visual feedback
- Click to browse file system
- Real-time upload progress indicator
- File validation (size limits, format checking)
- Preview of uploaded data (first 100 rows)

**Supported Formats**:
- `.xlsx` (Excel 2007+)
- `.xls` (Excel 97-2003)
- `.xlsm` (Excel with macros)

**Technical Flow**:
```
User drops file → Frontend validation → Upload to /api/analytics/upload
→ Backend saves to storage → Parse with openpyxl → Extract sheets
→ Store in AnalyticsSession → Return session_id
```

**Error Handling**:
- File too large (>50MB limit)
- Invalid format
- Corrupted file
- Empty sheets
- Unsupported Excel features (external links, complex formulas)

---

### 2. Automatic KPI Detection

**AI-Powered Analysis**:

The system uses existing LLM providers to intelligently identify KPIs by analyzing:

1. **Column Semantics**: Name patterns, data types, value distributions
2. **Business Context**: Common KPI patterns (revenue, growth, conversion)
3. **Statistical Significance**: High variance columns, time-series data
4. **Relationships**: Correlations, aggregation opportunities

**Example Prompt to LLM**:
```
Analyze this Excel data and identify 5-10 key performance indicators (KPIs).

Columns: [Date, Region, Product, Revenue, Units Sold, Customer Count, Churn Rate]
Sample Data: [first 20 rows]
Statistical Summary: [from ydata-profiling]

For each KPI, provide:
1. Name (e.g., "Monthly Revenue Trend")
2. Metric (e.g., SUM(Revenue) grouped by month)
3. Chart type (Bar, Line, Pie, Scatter, Area)
4. Insight (why this KPI matters)
5. Filters (relevant dimensions for filtering)
```

**LLM Response Structure**:
```json
{
  "kpis": [
    {
      "id": "kpi_1",
      "name": "Revenue by Region",
      "metric": {
        "measure": "Revenue",
        "aggregation": "SUM",
        "groupBy": ["Region"]
      },
      "chartType": "bar",
      "insight": "Identifies top-performing regions for resource allocation",
      "suggestedFilters": ["Date", "Product"]
    },
    {
      "id": "kpi_2",
      "name": "Monthly Sales Trend",
      "metric": {
        "measure": "Units Sold",
        "aggregation": "SUM",
        "groupBy": ["Month"]
      },
      "chartType": "line",
      "insight": "Tracks sales velocity and seasonal patterns",
      "suggestedFilters": ["Region", "Product"]
    }
  ]
}
```

**Fallback Strategy**:
If LLM is unavailable, use rule-based detection:
- Numeric columns → potential measures
- Date columns → time-series
- Low-cardinality text → dimensions
- High-cardinality → exclude from grouping

---

### 3. Chart Types

#### Basic Charts (Chart.js)

| Type | Use Case | Example |
|------|----------|---------|
| **Bar Chart** | Compare categories | Revenue by Product |
| **Line Chart** | Show trends over time | Monthly Active Users |
| **Pie Chart** | Show composition | Market Share by Region |
| **Scatter Plot** | Show correlations | Price vs. Demand |
| **Area Chart** | Cumulative trends | Total Sales Accumulation |

**Implementation Example**:
```jsx
import { Bar } from 'react-chartjs-2';

<Bar
  data={{
    labels: ['Q1', 'Q2', 'Q3', 'Q4'],
    datasets: [{
      label: 'Revenue',
      data: [120000, 150000, 180000, 210000],
      backgroundColor: '#6366f1'
    }]
  }}
  options={{
    responsive: true,
    onClick: handleCrossFilter  // Enable cross-filtering
  }}
/>
```

#### Advanced Visualizations (D3.js)

| Type | Use Case | Example |
|------|----------|---------|
| **TreeMap** | Hierarchical proportions | Budget Allocation by Department |
| **Sankey Diagram** | Flow analysis | Customer Journey Stages |
| **Heatmap** | Multi-dimensional patterns | Sales by Region × Product |
| **Sunburst** | Nested hierarchies | Organizational Structure |
| **Force-Directed Graph** | Network relationships | Product Dependencies |

**Implementation Example**:
```jsx
import * as d3 from 'd3';

const TreeMap = ({ data }) => {
  const svgRef = useRef();

  useEffect(() => {
    const root = d3.hierarchy(data)
      .sum(d => d.value)
      .sort((a, b) => b.value - a.value);

    d3.treemap()
      .size([width, height])
      .padding(2)(root);

    const svg = d3.select(svgRef.current);

    svg.selectAll('rect')
      .data(root.leaves())
      .join('rect')
      .attr('x', d => d.x0)
      .attr('y', d => d.y0)
      .attr('width', d => d.x1 - d.x0)
      .attr('height', d => d.y1 - d.y0)
      .attr('fill', d => colorScale(d.parent.data.name))
      .on('click', handleCrossFilter);  // Cross-filtering
  }, [data]);

  return <svg ref={svgRef} width={width} height={height} />;
};
```

---

### 4. Auto-Generated Filters

**Intelligent Filter Creation**:

The system automatically generates filters based on:
- Column data types (date ranges, categorical selects, numeric ranges)
- Cardinality (low → dropdown, high → search)
- LLM-suggested relevance

**Filter Types**:

```jsx
// Date Range Filter
<DateRangePicker
  startDate={filters.startDate}
  endDate={filters.endDate}
  onChange={handleDateChange}
/>

// Categorical Multi-Select
<MultiSelect
  options={['North', 'South', 'East', 'West']}
  selected={filters.regions}
  onChange={handleRegionChange}
/>

// Numeric Range Slider
<RangeSlider
  min={0}
  max={1000000}
  value={filters.revenueRange}
  onChange={handleRevenueChange}
/>

// Search/Autocomplete (high cardinality)
<Autocomplete
  options={products}  // 10,000+ products
  selected={filters.products}
  onChange={handleProductChange}
/>
```

**Filter Persistence**:
Filters are stored in session state and optionally in URL query parameters for shareability:

```
/analytics/session/123?region=North,South&startDate=2024-01-01&endDate=2024-03-31
```

---

### 5. Cross-Filtering

**Interaction Model**:

1. User clicks on any chart element (bar, line point, pie slice, etc.)
2. CrossFilterManager captures the click event
3. Identifies the dimension and value (e.g., Region = "North")
4. Applies filter to all other charts
5. Visual feedback shows active filter state
6. Click again to toggle off filter

**Technical Implementation**:

```jsx
// CrossFilterManager.jsx
const CrossFilterManager = ({ children, onFilterChange }) => {
  const [activeFilters, setActiveFilters] = useState({});

  const handleChartClick = (chartId, dimension, value) => {
    setActiveFilters(prev => {
      const key = `${chartId}_${dimension}`;
      const newFilters = { ...prev };

      if (newFilters[key] === value) {
        // Toggle off
        delete newFilters[key];
      } else {
        // Apply filter
        newFilters[key] = value;
      }

      onFilterChange(newFilters);
      return newFilters;
    });
  };

  return (
    <FilterContext.Provider value={{ activeFilters, handleChartClick }}>
      {children}
    </FilterContext.Provider>
  );
};
```

**Visual Feedback**:
- Active filters shown in chip/badge UI
- Filtered charts have visual indicator (border color change)
- Grayed-out elements in other charts (non-matching data)
- Clear all filters button

**Performance Optimization**:
- Debounce filter updates (300ms)
- Memoize filtered datasets
- Virtual scrolling for large datasets
- Web Workers for heavy filtering operations

---

### 6. Data Quality Alerts

**ydata-profiling Integration**:

Automatic detection of:

| Issue | Detection | Alert Level |
|-------|-----------|-------------|
| **Missing Values** | >5% null in any column | Warning |
| **Duplicates** | Duplicate rows detected | Info |
| **Outliers** | Values >3 std deviations | Warning |
| **Data Type Mismatch** | Mixed types in column | Error |
| **Low Cardinality** | <2 unique values in numeric | Warning |
| **High Correlation** | Pearson correlation >0.95 | Info |
| **Skewed Distribution** | Skewness >2 or <-2 | Info |

**Alert Display**:

```jsx
<DataQualityAlerts alerts={[
  {
    level: 'warning',
    column: 'Revenue',
    issue: 'Missing Values',
    description: '12% of rows have null Revenue values',
    recommendation: 'Consider imputation or filtering',
    affectedRows: 1234
  },
  {
    level: 'error',
    column: 'Date',
    issue: 'Data Type Mismatch',
    description: 'Column contains both dates and text',
    recommendation: 'Clean data before analysis',
    affectedRows: 45
  }
]} />
```

**User Actions**:
- View detailed analysis in profiling report
- Apply suggested fixes (imputation, filtering)
- Exclude problematic columns from analysis
- Export data quality report

---

### 7. Full ydata Profile Report

**Separate Tab Interface**:

```jsx
<Tabs>
  <TabPanel value="dashboard">
    <ChartGrid charts={charts} />
  </TabPanel>

  <TabPanel value="profile-report">
    <ProfileReportViewer
      htmlPath={session.profiling_report_path}
      onNavigate={handleReportNavigation}
    />
  </TabPanel>

  <TabPanel value="raw-data">
    <DataTable
      data={session.raw_data}
      pagination
      searchable
    />
  </TabPanel>
</Tabs>
```

**Profile Report Contents** (generated by ydata):
- Overview statistics
- Variable analysis (numeric, categorical, datetime)
- Correlations matrix
- Missing values analysis
- Sample data
- Duplicate rows
- Interactions (scatter plots matrix)

**Backend Generation**:

```python
from ydata_profiling import ProfileReport

def generate_profile_report(df, session_id):
    profile = ProfileReport(
        df,
        title=f"Analytics Session {session_id}",
        explorative=True,
        config_file="ydata_config.yaml"
    )

    report_path = f"storage/analytics/{session_id}/profile.html"
    profile.to_file(report_path)

    return {
        'report_path': report_path,
        'quality_score': profile.get_description()['table']['n_cells_missing'] / profile.get_description()['table']['n_cells'],
        'alerts': extract_alerts(profile)
    }
```

---

### 8. PDF Export

**Export Workflow**:

1. User clicks "Export Dashboard"
2. Render all charts to canvas using html2canvas
3. Generate multi-page PDF with jsPDF
4. Include: title page, KPI summary, all charts, data quality report
5. Download or save to session

**Implementation**:

```jsx
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const exportToPDF = async (dashboardRef, sessionData) => {
  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  // Title Page
  pdf.setFontSize(24);
  pdf.text(sessionData.filename, pageWidth / 2, 30, { align: 'center' });
  pdf.setFontSize(12);
  pdf.text(`Generated: ${new Date().toLocaleDateString()}`, pageWidth / 2, 40, { align: 'center' });

  // KPI Summary
  pdf.addPage();
  pdf.setFontSize(16);
  pdf.text('Key Performance Indicators', 20, 20);
  sessionData.kpis.forEach((kpi, i) => {
    pdf.setFontSize(12);
    pdf.text(`${i + 1}. ${kpi.name}`, 20, 30 + (i * 10));
    pdf.setFontSize(10);
    pdf.text(`   ${kpi.insight}`, 25, 35 + (i * 10));
  });

  // Charts (one per page)
  const chartElements = dashboardRef.current.querySelectorAll('.chart-container');
  for (const chart of chartElements) {
    const canvas = await html2canvas(chart, { scale: 2 });
    const imgData = canvas.toDataURL('image/png');

    pdf.addPage();
    const imgWidth = pageWidth - 20;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight);
  }

  // Save
  pdf.save(`${sessionData.filename}_dashboard.pdf`);
};
```

**Export Options**:
- Include/exclude data quality report
- Chart arrangement (grid vs. one-per-page)
- Color vs. grayscale
- Include raw data table (appendix)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (React)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐         ┌─────────────────────────────────────┐      │
│  │  AnalyticsDash   │────────▶│      CrossFilterManager              │      │
│  │   (Main Page)    │         │   (Global filter state)              │      │
│  └────────┬─────────┘         └──────────────┬──────────────────────┘      │
│           │                                   │                              │
│           ├───────────┬───────────┬──────────┼───────────┬─────────┐        │
│           ▼           ▼           ▼          ▼           ▼         ▼        │
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────┐   │
│  │ FileUpload │ │ KPIPanel │ │ Charts │ │ Filters│ │ Quality │ │Export│   │
│  │ (Dropzone) │ │          │ │Renderer│ │ Panel  │ │ Alerts  │ │ (PDF)│   │
│  └──────┬─────┘ └─────┬────┘ └───┬────┘ └───┬────┘ └────┬────┘ └──┬───┘   │
│         │             │          │           │           │          │        │
│         │    ┌────────┴──────────┴───────────┴───────────┴──────────┘       │
│         │    │                                                               │
│         ▼    ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │           Reused: ThemeContext, useToast, axios              │           │
│  └──────────────────────────────────────────────────────────────┘           │
│         │                                                                     │
└─────────┼─────────────────────────────────────────────────────────────────────┘
          │
          │ HTTP/JSON
          │
┌─────────┼─────────────────────────────────────────────────────────────────────┐
│         ▼                  BACKEND (Flask)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │              Blueprint: /api/analytics/*                          │       │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐   │       │
│  │  │  upload  │  │  analyze  │  │ generate │  │  sessions    │   │       │
│  │  │  (POST)  │  │  (POST)   │  │  charts  │  │  (GET/DEL)   │   │       │
│  │  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └──────┬───────┘   │       │
│  └───────┼──────────────┼─────────────┼───────────────┼───────────┘       │
│          │              │             │               │                     │
│          ▼              ▼             ▼               ▼                     │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                  Service Layer                            │              │
│  │  ┌──────────┐  ┌───────────────┐  ┌─────────────────┐   │              │
│  │  │ openpyxl │  │ LLM Provider  │  │ ydata-profiling │   │              │
│  │  │  Parser  │  │  (KPI detect) │  │  (Statistics)   │   │              │
│  │  └────┬─────┘  └───────┬───────┘  └────────┬────────┘   │              │
│  └───────┼────────────────┼───────────────────┼────────────┘              │
│          │                │                   │                             │
│          │    ┌───────────┴───────────────────┘                             │
│          │    │                                                              │
│          ▼    ▼                                                              │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │               Database Layer (SQLAlchemy)                 │              │
│  │  ┌──────────────────┐          ┌────────────────────┐    │              │
│  │  │AnalyticsSession  │◀────────▶│  User (existing)   │    │              │
│  │  │  - raw_data      │          │  Notebook (exist)  │    │              │
│  │  │  - kpis          │          └────────────────────┘    │              │
│  │  │  - chart_configs │                                     │              │
│  │  │  - filters       │                                     │              │
│  │  └──────────────────┘                                     │              │
│  └──────────────────────────────────────────────────────────┘              │
│          │                                                                   │
│          ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │         File Storage (Excel files, ydata reports)         │              │
│  │         storage/analytics/{session_id}/                   │              │
│  └──────────────────────────────────────────────────────────┘              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DEPENDENCIES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │   Chart.js   │   │     D3.js    │   │  html2canvas │                    │
│  │  (Rendering) │   │  (Advanced)  │   │  + jsPDF     │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow**:

```
1. Upload Flow:
   User drops Excel → FileUpload → POST /upload → openpyxl parse
   → Save to storage → Create AnalyticsSession → Return session_id

2. Analysis Flow:
   Frontend triggers → POST /analyze → ydata-profiling (stats)
   → LLM provider (KPI detection) → Save to session.detected_kpis
   → Return KPIs + quality alerts

3. Visualization Flow:
   Frontend receives KPIs → Generate Chart.js configs locally
   → Render charts → Enable cross-filtering via CrossFilterManager
   → User interactions update global filter state → Re-render all charts

4. Export Flow:
   User clicks export → html2canvas captures charts → jsPDF generates PDF
   → Download to user's device (client-side, no backend)
```

---

## Relationship to Existing Features

### Integration Points

| Feature | Analytics Integration | Benefit |
|---------|----------------------|---------|
| **Notebooks** | Optional linking via `notebook_id` | Combine unstructured insights with structured data analysis |
| **User Context** | Inherits user authentication and permissions | Consistent access control |
| **Deep Space Theme** | Uses ThemeContext for consistent styling | Unified visual experience |
| **LLM Providers** | Reuses existing LLM configuration | No duplicate setup, consistent AI behavior |
| **File Storage** | Uses existing storage infrastructure | Centralized file management |

### Workflow Scenarios

#### Scenario 1: Standalone Analytics
```
User → Upload sales.xlsx → AI detects KPIs → Interactive dashboard
→ Export PDF for stakeholder meeting
```

#### Scenario 2: Notebook-Linked Analysis
```
User working in "Q4 Sales Strategy" notebook
→ Upload sales.xlsx and link to notebook
→ Analytics dashboard shows data insights
→ Reference dashboard findings in notebook RAG queries
→ Example: "Based on the analytics dashboard, what drove the revenue spike in November?"
```

#### Scenario 3: Data Quality Workflow
```
User → Upload customer_data.xlsx
→ ydata alerts show 15% missing emails
→ User cleans data in Excel
→ Re-upload → Green quality score
→ Proceed with analysis
```

### Shared Components

**Frontend**:
- `ThemeContext` → Applies Deep Space theme colors to charts
- `useToast` → User feedback for uploads, errors, exports
- `AuthContext` → Access control and user identification
- `axios` → API communication with error handling

**Backend**:
- `LLMProvider` → KPI detection and insight generation
- `User` model → Session ownership and permissions
- `File storage` → Upload handling and retrieval
- `Database connection` → Session persistence

### Data Model Relationships

```sql
-- AnalyticsSession can optionally link to Notebook
SELECT
  a.filename,
  a.upload_timestamp,
  n.title AS linked_notebook,
  u.username
FROM analytics_sessions a
LEFT JOIN notebooks n ON a.notebook_id = n.id
JOIN users u ON a.user_id = u.id
WHERE u.id = :current_user_id;
```

**Benefits of Linking**:
1. **Contextual Analysis**: Analytics sessions appear in notebook sidebar
2. **Cross-Reference**: RAG queries can reference dashboard insights
3. **Unified History**: Complete analysis trail in one place
4. **Collaboration**: Share notebook with embedded analytics

---

## Future Enhancements

### Phase 2 Roadmap

1. **Real-Time Data Connections**
   - Connect to databases (PostgreSQL, MySQL, MongoDB)
   - Scheduled data refreshes
   - Live dashboard updates

2. **Collaborative Features**
   - Share dashboards with other users
   - Comments and annotations on charts
   - Version history for sessions

3. **Advanced AI Features**
   - Natural language queries ("Show me revenue by region")
   - Anomaly detection with alerts
   - Predictive analytics (forecasting)

4. **Enhanced Visualizations**
   - Geographic maps with choropleth
   - 3D visualizations
   - Animated time-series

5. **Export Improvements**
   - Interactive HTML export
   - PowerPoint generation
   - Scheduled email reports

---

## Performance Considerations

### Optimization Strategies

| Area | Strategy | Target |
|------|----------|--------|
| **Upload** | Chunked upload for large files | <5s for 10MB files |
| **Parsing** | Web Workers for Excel parsing | Non-blocking UI |
| **KPI Detection** | Caching LLM responses | <3s after first analysis |
| **Rendering** | Virtual scrolling for data tables | Smooth 60fps |
| **Cross-Filtering** | Memoized filtered datasets | <100ms filter application |
| **Export** | Progressive PDF generation | <10s for 20 charts |

### Scalability Limits

**Current Implementation**:
- Max file size: 50MB
- Max rows: 100,000 (optimized rendering)
- Max charts: 20 per dashboard
- Concurrent sessions: 100 per user

**Future Scaling**:
- Server-side rendering for large datasets
- Incremental data loading
- CDN for static assets
- Redis caching for frequent queries

---

## Security Considerations

### Data Protection

1. **File Upload Validation**
   - MIME type checking
   - Virus scanning (ClamAV integration)
   - Size limits enforcement

2. **Access Control**
   - User-scoped sessions (can't access others' data)
   - Optional notebook-level permissions
   - Admin audit logging

3. **Data Retention**
   - Automatic cleanup of old sessions (90 days)
   - User-initiated deletion
   - Secure file deletion (shred)

4. **Privacy**
   - No logging of sensitive data values
   - LLM queries anonymize data samples
   - Export watermarking (optional)

---

## Testing Strategy

### Test Coverage

| Component | Test Type | Coverage Target |
|-----------|-----------|-----------------|
| **Backend API** | Unit tests (pytest) | 90% |
| **Excel Parsing** | Integration tests | 85% |
| **LLM Integration** | Mocked tests | 80% |
| **React Components** | Jest + React Testing Library | 85% |
| **Chart Rendering** | Snapshot tests | 90% |
| **Cross-Filtering** | E2E tests (Playwright) | 75% |

### Key Test Scenarios

```python
# Backend test example
def test_kpi_detection(client, sample_excel):
    response = client.post('/api/analytics/analyze',
                          data={'session_id': 123})
    assert response.status_code == 200
    assert len(response.json['kpis']) >= 5
    assert all('chartType' in kpi for kpi in response.json['kpis'])
```

```jsx
// Frontend test example
test('cross-filtering updates all charts', async () => {
  render(<AnalyticsDashboard sessionId={123} />);

  const barChart = screen.getByTestId('chart-revenue-by-region');
  fireEvent.click(barChart, { target: { dataset: { value: 'North' } } });

  await waitFor(() => {
    const lineChart = screen.getByTestId('chart-monthly-trend');
    expect(lineChart).toHaveAttribute('data-filtered', 'true');
  });
});
```

---

## Developer Onboarding

### Quick Start

1. **Install Dependencies**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt

   # Frontend
   cd frontend
   npm install
   ```

2. **Database Migration**
   ```bash
   flask db upgrade
   # Creates analytics_sessions table
   ```

3. **Run Development Servers**
   ```bash
   # Backend (port 5000)
   cd backend
   flask run

   # Frontend (port 3000)
   cd frontend
   npm start
   ```

4. **Access Analytics**
   - Navigate to `http://localhost:3000/analytics`
   - Upload sample Excel file from `backend/tests/fixtures/sample_sales.xlsx`
   - Observe auto-generated dashboard

### Code Style

Follow existing dbnotebook conventions:
- **Python**: PEP 8, Black formatter
- **JavaScript**: ESLint + Prettier
- **React**: Functional components, hooks
- **CSS**: CSS Modules, Deep Space theme variables

### Debugging

**Backend**:
```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend**:
```jsx
// Enable React DevTools
// Chrome extension: React Developer Tools
// Inspect CrossFilterManager state
```

---

## Documentation References

### External Documentation

- **ydata-profiling**: https://docs.profiling.ydata.ai/
- **Chart.js**: https://www.chartjs.org/docs/
- **D3.js**: https://d3js.org/
- **react-dropzone**: https://react-dropzone.js.org/
- **jsPDF**: https://rawgit.com/MrRio/jsPDF/master/docs/

### Internal Documentation

- Main README: `/Users/bharath/Desktop/dbnotebook/README.md`
- API Documentation: `/Users/bharath/Desktop/dbnotebook/docs/API.md` (add analytics endpoints)
- Database Schema: `/Users/bharath/Desktop/dbnotebook/docs/SCHEMA.md` (add AnalyticsSession)

---

## Appendix: Sample KPI Detection Response

```json
{
  "session_id": 123,
  "filename": "Q4_sales.xlsx",
  "kpis": [
    {
      "id": "kpi_1",
      "name": "Total Revenue by Region",
      "metric": {
        "measure": "Revenue",
        "aggregation": "SUM",
        "groupBy": ["Region"]
      },
      "chartType": "bar",
      "chartConfig": {
        "type": "bar",
        "data": {
          "labels": ["North", "South", "East", "West"],
          "datasets": [{
            "label": "Revenue",
            "data": [450000, 380000, 520000, 410000],
            "backgroundColor": "#6366f1"
          }]
        },
        "options": {
          "responsive": true,
          "plugins": {
            "legend": { "display": true },
            "title": { "display": true, "text": "Total Revenue by Region" }
          }
        }
      },
      "insight": "North and East regions generate 55% of total revenue. Consider increasing resource allocation to these high-performing areas.",
      "suggestedFilters": ["Date Range", "Product Category"],
      "dataQualityNote": "No issues detected"
    },
    {
      "id": "kpi_2",
      "name": "Monthly Sales Trend",
      "metric": {
        "measure": "Units Sold",
        "aggregation": "SUM",
        "groupBy": ["Month"]
      },
      "chartType": "line",
      "chartConfig": {
        "type": "line",
        "data": {
          "labels": ["Oct", "Nov", "Dec"],
          "datasets": [{
            "label": "Units Sold",
            "data": [12000, 18000, 25000],
            "borderColor": "#8b5cf6",
            "tension": 0.4
          }]
        },
        "options": {
          "responsive": true,
          "plugins": {
            "title": { "display": true, "text": "Monthly Sales Trend" }
          }
        }
      },
      "insight": "Sales velocity increased 108% from October to December, driven by holiday season. Strong upward momentum suggests successful Q4 campaigns.",
      "suggestedFilters": ["Region", "Product Category"],
      "dataQualityNote": "No issues detected"
    },
    {
      "id": "kpi_3",
      "name": "Product Category Distribution",
      "metric": {
        "measure": "Revenue",
        "aggregation": "SUM",
        "groupBy": ["Product Category"]
      },
      "chartType": "pie",
      "chartConfig": {
        "type": "pie",
        "data": {
          "labels": ["Electronics", "Apparel", "Home Goods", "Sports"],
          "datasets": [{
            "data": [620000, 450000, 380000, 310000],
            "backgroundColor": ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b"]
          }]
        },
        "options": {
          "responsive": true,
          "plugins": {
            "title": { "display": true, "text": "Revenue by Category" }
          }
        }
      },
      "insight": "Electronics dominate with 35% market share. Diversification opportunity in underperforming Sports category.",
      "suggestedFilters": ["Region", "Date Range"],
      "dataQualityNote": "No issues detected"
    },
    {
      "id": "kpi_4",
      "name": "Price vs. Demand Correlation",
      "metric": {
        "measure": ["Average Price", "Units Sold"],
        "aggregation": "AVG_and_SUM",
        "groupBy": ["Product"]
      },
      "chartType": "scatter",
      "chartConfig": {
        "type": "scatter",
        "data": {
          "datasets": [{
            "label": "Products",
            "data": [
              { "x": 50, "y": 1200 },
              { "x": 100, "y": 800 },
              { "x": 150, "y": 500 }
            ],
            "backgroundColor": "#6366f1"
          }]
        },
        "options": {
          "responsive": true,
          "scales": {
            "x": { "title": { "display": true, "text": "Average Price ($)" } },
            "y": { "title": { "display": true, "text": "Units Sold" } }
          }
        }
      },
      "insight": "Negative correlation (-0.72) between price and demand. Price optimization opportunity for premium products.",
      "suggestedFilters": ["Category", "Region"],
      "dataQualityNote": "3 outliers detected (luxury items)"
    },
    {
      "id": "kpi_5",
      "name": "Customer Acquisition Funnel (Sankey)",
      "metric": {
        "measure": "Customer Count",
        "aggregation": "COUNT",
        "groupBy": ["Funnel Stage"]
      },
      "chartType": "sankey",
      "chartConfig": {
        "type": "sankey",
        "data": {
          "nodes": [
            { "name": "Visitors" },
            { "name": "Leads" },
            { "name": "Qualified" },
            { "name": "Customers" }
          ],
          "links": [
            { "source": 0, "target": 1, "value": 10000 },
            { "source": 1, "target": 2, "value": 3000 },
            { "source": 2, "target": 3, "value": 1200 }
          ]
        }
      },
      "insight": "12% overall conversion rate. Significant drop-off between Leads and Qualified (70% loss). Focus on lead nurturing.",
      "suggestedFilters": ["Date Range", "Marketing Channel"],
      "dataQualityNote": "No issues detected"
    }
  ],
  "dataQuality": {
    "score": 0.92,
    "alerts": [
      {
        "level": "warning",
        "column": "Customer Email",
        "issue": "Missing Values",
        "description": "8% of rows have null email addresses",
        "recommendation": "Consider email validation requirements",
        "affectedRows": 456
      },
      {
        "level": "info",
        "column": "Price and Revenue",
        "issue": "High Correlation",
        "description": "Correlation of 0.98 detected (expected for calculated field)",
        "recommendation": "No action needed",
        "affectedRows": 0
      }
    ]
  },
  "statistics": {
    "rowCount": 5678,
    "columnCount": 12,
    "numericColumns": 5,
    "categoricalColumns": 7,
    "dateColumns": 1,
    "missingCellsPercent": 2.3,
    "duplicateRows": 0
  }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-29
**Author**: Analytics Feature Team
**Status**: Implementation Ready
