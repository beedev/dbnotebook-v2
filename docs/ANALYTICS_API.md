# Analytics Dashboard API Documentation

**Version**: 1.0.0
**Base URL**: `/api/analytics`
**Authentication**: Session-based (uses existing dbnotebook user context)

---

## Overview

The Analytics Dashboard API provides endpoints for uploading Excel files, generating automated data profiling reports, and managing analytics sessions within dbnotebook. All endpoints require authenticated user sessions and operate within the user's workspace context.

**Key Features**:
- Automated data profiling using ydata-profiling
- LLM-powered analysis and insights
- Interactive dashboard configuration generation
- Session-based analytics state management
- PDF export capabilities

---

## Table of Contents

1. [Upload Analytics File](#1-upload-analytics-file)
2. [Retrieve Profile Report](#2-retrieve-profile-report)
3. [List Analytics Sessions](#3-list-analytics-sessions)
4. [Delete Analytics Session](#4-delete-analytics-session)
5. [Export Dashboard to PDF](#5-export-dashboard-to-pdf)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Type Definitions](#type-definitions)

---

## 1. Upload Analytics File

**Endpoint**: `POST /api/analytics/upload`

**Purpose**: Upload an Excel file for automated profiling and analysis. Generates a ydata-profiling report, runs LLM-based analysis, and returns dashboard configuration including KPIs, chart specifications, and filter options.

### Request

**Content-Type**: `multipart/form-data`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Excel file (.xlsx, .xls). Max size: 100MB |
| `notebook_id` | String | No | Optional notebook ID to associate session with |
| `analysis_depth` | String | No | Analysis depth: `quick`, `standard`, `comprehensive`. Default: `standard` |

### Response

**Status**: `200 OK`

**Content-Type**: `application/json`

```typescript
interface UploadResponse {
  session_id: string;
  created_at: string; // ISO 8601 timestamp
  data_summary: DataSummary;
  dashboard_config: DashboardConfig;
  profile_url: string; // URL to access HTML profile report
}

interface DataSummary {
  filename: string;
  rows: number;
  columns: number;
  file_size: number; // bytes
  column_types: Record<string, string>; // column_name -> data_type
  missing_values: Record<string, number>; // column_name -> count
  memory_usage: number; // bytes
}

interface DashboardConfig {
  kpis: KPI[];
  charts: ChartConfig[];
  filters: FilterConfig[];
  insights: Insight[];
}

interface KPI {
  id: string;
  label: string;
  value: number | string;
  format: 'number' | 'percentage' | 'currency' | 'text';
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    value: number;
    label: string;
  };
}

interface ChartConfig {
  id: string;
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'histogram';
  title: string;
  data_source: {
    x_column: string;
    y_column?: string;
    group_by?: string;
    aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max';
  };
  display_options: {
    show_legend: boolean;
    color_scheme?: string;
    orientation?: 'horizontal' | 'vertical';
  };
}

interface FilterConfig {
  id: string;
  column: string;
  type: 'select' | 'range' | 'date_range' | 'search';
  label: string;
  options?: string[]; // For select type
  range?: { min: number; max: number }; // For range type
  default_value?: any;
}

interface Insight {
  id: string;
  category: 'quality' | 'correlation' | 'distribution' | 'anomaly' | 'recommendation';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  affected_columns?: string[];
  action_items?: string[];
}
```

### Example Request

```bash
curl -X POST http://localhost:5000/api/analytics/upload \
  -H "Cookie: session=your_session_cookie" \
  -F "file=@sales_data_2024.xlsx" \
  -F "notebook_id=nb_12345" \
  -F "analysis_depth=standard"
```

### Example Response

```json
{
  "session_id": "sess_a7f3c9d1e2b4",
  "created_at": "2025-12-29T14:32:15.123Z",
  "data_summary": {
    "filename": "sales_data_2024.xlsx",
    "rows": 15420,
    "columns": 18,
    "file_size": 2458624,
    "column_types": {
      "order_id": "int64",
      "customer_id": "int64",
      "order_date": "datetime64",
      "total_amount": "float64",
      "region": "object",
      "product_category": "object"
    },
    "missing_values": {
      "customer_email": 234,
      "shipping_address": 12
    },
    "memory_usage": 2211840
  },
  "dashboard_config": {
    "kpis": [
      {
        "id": "kpi_total_revenue",
        "label": "Total Revenue",
        "value": 4523890.50,
        "format": "currency",
        "trend": {
          "direction": "up",
          "value": 12.5,
          "label": "+12.5% vs last quarter"
        }
      },
      {
        "id": "kpi_avg_order",
        "label": "Average Order Value",
        "value": 293.45,
        "format": "currency"
      },
      {
        "id": "kpi_total_orders",
        "label": "Total Orders",
        "value": 15420,
        "format": "number"
      }
    ],
    "charts": [
      {
        "id": "chart_revenue_by_region",
        "type": "bar",
        "title": "Revenue by Region",
        "data_source": {
          "x_column": "region",
          "y_column": "total_amount",
          "aggregation": "sum"
        },
        "display_options": {
          "show_legend": true,
          "color_scheme": "blues",
          "orientation": "vertical"
        }
      },
      {
        "id": "chart_orders_trend",
        "type": "line",
        "title": "Order Volume Over Time",
        "data_source": {
          "x_column": "order_date",
          "y_column": "order_id",
          "aggregation": "count"
        },
        "display_options": {
          "show_legend": false
        }
      },
      {
        "id": "chart_category_dist",
        "type": "pie",
        "title": "Sales Distribution by Category",
        "data_source": {
          "x_column": "product_category",
          "y_column": "total_amount",
          "aggregation": "sum"
        },
        "display_options": {
          "show_legend": true,
          "color_scheme": "category10"
        }
      }
    ],
    "filters": [
      {
        "id": "filter_date_range",
        "column": "order_date",
        "type": "date_range",
        "label": "Order Date Range",
        "default_value": {
          "start": "2024-01-01",
          "end": "2024-12-31"
        }
      },
      {
        "id": "filter_region",
        "column": "region",
        "type": "select",
        "label": "Region",
        "options": ["North", "South", "East", "West", "Central"],
        "default_value": null
      },
      {
        "id": "filter_amount_range",
        "column": "total_amount",
        "type": "range",
        "label": "Order Amount",
        "range": {
          "min": 0,
          "max": 5000
        }
      }
    ],
    "insights": [
      {
        "id": "insight_missing_data",
        "category": "quality",
        "severity": "warning",
        "title": "Missing Customer Emails",
        "description": "234 orders (1.5%) are missing customer email addresses, which may impact marketing campaigns.",
        "affected_columns": ["customer_email"],
        "action_items": [
          "Review data collection process",
          "Consider email validation at order entry"
        ]
      },
      {
        "id": "insight_correlation",
        "category": "correlation",
        "severity": "info",
        "title": "Strong Correlation: Product Category and Order Value",
        "description": "Electronics category shows 2.3x higher average order value compared to other categories.",
        "affected_columns": ["product_category", "total_amount"],
        "action_items": [
          "Focus marketing efforts on electronics",
          "Cross-sell electronics with other categories"
        ]
      },
      {
        "id": "insight_anomaly",
        "category": "anomaly",
        "severity": "critical",
        "title": "Unusual Spike in Returns - East Region",
        "description": "Return rate in East region increased to 18% in Q4, significantly above the 6% baseline.",
        "affected_columns": ["region", "order_status"],
        "action_items": [
          "Investigate East region fulfillment process",
          "Review product quality for East region orders"
        ]
      }
    ]
  },
  "profile_url": "/api/analytics/profile/sess_a7f3c9d1e2b4"
}
```

### Error Responses

**400 Bad Request**: Invalid file format or parameters
```json
{
  "error": "invalid_file_format",
  "message": "File must be in Excel format (.xlsx or .xls)",
  "details": {
    "provided_format": ".csv",
    "supported_formats": [".xlsx", ".xls"]
  }
}
```

**413 Payload Too Large**: File exceeds size limit
```json
{
  "error": "file_too_large",
  "message": "File size exceeds maximum allowed limit",
  "details": {
    "file_size": 125829120,
    "max_size": 104857600
  }
}
```

**500 Internal Server Error**: Processing failure
```json
{
  "error": "processing_failed",
  "message": "Failed to process analytics file",
  "details": {
    "stage": "profiling",
    "reason": "Insufficient memory for large dataset"
  }
}
```

---

## 2. Retrieve Profile Report

**Endpoint**: `GET /api/analytics/profile/{session_id}`

**Purpose**: Retrieve the generated ydata-profiling HTML report for a specific analytics session.

### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | String | Yes | Analytics session identifier |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `download` | Boolean | No | If `true`, returns as downloadable file. Default: `false` |

### Response

**Status**: `200 OK`

**Content-Type**: `text/html` (or `application/octet-stream` if download=true)

Returns the complete HTML profiling report generated by ydata-profiling, containing:
- Dataset overview and statistics
- Variable distributions and correlations
- Missing values analysis
- Duplicate rows detection
- Sample data preview

### Example Request

```bash
curl -X GET http://localhost:5000/api/analytics/profile/sess_a7f3c9d1e2b4 \
  -H "Cookie: session=your_session_cookie"
```

### Example Request (Download)

```bash
curl -X GET "http://localhost:5000/api/analytics/profile/sess_a7f3c9d1e2b4?download=true" \
  -H "Cookie: session=your_session_cookie" \
  -o profile_report.html
```

### Error Responses

**404 Not Found**: Session does not exist or profile not generated
```json
{
  "error": "session_not_found",
  "message": "Analytics session not found",
  "details": {
    "session_id": "sess_a7f3c9d1e2b4"
  }
}
```

**403 Forbidden**: User does not own this session
```json
{
  "error": "unauthorized_access",
  "message": "You do not have permission to access this analytics session"
}
```

---

## 3. List Analytics Sessions

**Endpoint**: `GET /api/analytics/sessions`

**Purpose**: Retrieve a paginated list of analytics sessions for the authenticated user, with optional filtering by notebook.

### Request

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | Integer | No | Maximum number of sessions to return. Default: 20, Max: 100 |
| `offset` | Integer | No | Number of sessions to skip. Default: 0 |
| `notebook_id` | String | No | Filter sessions by notebook ID |
| `sort_by` | String | No | Sort field: `created_at`, `filename`. Default: `created_at` |
| `order` | String | No | Sort order: `asc`, `desc`. Default: `desc` |

### Response

**Status**: `200 OK`

**Content-Type**: `application/json`

```typescript
interface SessionsListResponse {
  sessions: SessionSummary[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface SessionSummary {
  session_id: string;
  filename: string;
  created_at: string; // ISO 8601
  notebook_id?: string;
  data_summary: {
    rows: number;
    columns: number;
    file_size: number;
  };
  status: 'processing' | 'completed' | 'failed';
  profile_url?: string;
  last_accessed?: string; // ISO 8601
}
```

### Example Request

```bash
curl -X GET "http://localhost:5000/api/analytics/sessions?limit=10&notebook_id=nb_12345" \
  -H "Cookie: session=your_session_cookie"
```

### Example Response

```json
{
  "sessions": [
    {
      "session_id": "sess_a7f3c9d1e2b4",
      "filename": "sales_data_2024.xlsx",
      "created_at": "2025-12-29T14:32:15.123Z",
      "notebook_id": "nb_12345",
      "data_summary": {
        "rows": 15420,
        "columns": 18,
        "file_size": 2458624
      },
      "status": "completed",
      "profile_url": "/api/analytics/profile/sess_a7f3c9d1e2b4",
      "last_accessed": "2025-12-29T15:45:30.456Z"
    },
    {
      "session_id": "sess_b2c4d6e8f1a3",
      "filename": "customer_analytics_q4.xlsx",
      "created_at": "2025-12-28T09:15:42.789Z",
      "notebook_id": "nb_12345",
      "data_summary": {
        "rows": 8923,
        "columns": 12,
        "file_size": 1245680
      },
      "status": "completed",
      "profile_url": "/api/analytics/profile/sess_b2c4d6e8f1a3",
      "last_accessed": "2025-12-28T10:22:15.234Z"
    },
    {
      "session_id": "sess_c3d5e7f9a2b4",
      "filename": "inventory_audit.xlsx",
      "created_at": "2025-12-27T16:48:33.567Z",
      "data_summary": {
        "rows": 32145,
        "columns": 25,
        "file_size": 5834912
      },
      "status": "processing"
    }
  ],
  "pagination": {
    "total": 3,
    "limit": 10,
    "offset": 0,
    "has_more": false
  }
}
```

### Error Responses

**400 Bad Request**: Invalid query parameters
```json
{
  "error": "invalid_parameters",
  "message": "Invalid pagination parameters",
  "details": {
    "limit": "Must be between 1 and 100"
  }
}
```

---

## 4. Delete Analytics Session

**Endpoint**: `DELETE /api/analytics/sessions/{session_id}`

**Purpose**: Delete an analytics session and all associated data including uploaded files, profile reports, and dashboard configurations.

### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | String | Yes | Analytics session identifier to delete |

### Response

**Status**: `200 OK`

**Content-Type**: `application/json`

```typescript
interface DeleteSessionResponse {
  success: boolean;
  session_id: string;
  deleted_at: string; // ISO 8601
  resources_freed: {
    files_deleted: number;
    storage_freed: number; // bytes
  };
}
```

### Example Request

```bash
curl -X DELETE http://localhost:5000/api/analytics/sessions/sess_a7f3c9d1e2b4 \
  -H "Cookie: session=your_session_cookie"
```

### Example Response

```json
{
  "success": true,
  "session_id": "sess_a7f3c9d1e2b4",
  "deleted_at": "2025-12-29T16:20:45.789Z",
  "resources_freed": {
    "files_deleted": 2,
    "storage_freed": 2458624
  }
}
```

### Error Responses

**404 Not Found**: Session does not exist
```json
{
  "error": "session_not_found",
  "message": "Analytics session not found",
  "details": {
    "session_id": "sess_a7f3c9d1e2b4"
  }
}
```

**403 Forbidden**: User does not own this session
```json
{
  "error": "unauthorized_access",
  "message": "You do not have permission to delete this analytics session"
}
```

---

## 5. Export Dashboard to PDF

**Endpoint**: `POST /api/analytics/export`

**Purpose**: Generate a PDF export of the current dashboard state, including visible charts, applied filters, and insights. Useful for reporting and sharing analysis results.

### Request

**Content-Type**: `application/json`

```typescript
interface ExportRequest {
  session_id: string;
  dashboard_state: DashboardState;
  export_options?: ExportOptions;
}

interface DashboardState {
  visible_charts: string[]; // Chart IDs to include
  active_filters: Record<string, any>; // Filter ID -> current value
  selected_insights?: string[]; // Insight IDs to include
  custom_notes?: string; // User-added commentary
}

interface ExportOptions {
  format?: 'pdf' | 'png'; // Default: 'pdf'
  include_profile_summary?: boolean; // Default: true
  include_raw_data_sample?: boolean; // Default: false
  page_orientation?: 'portrait' | 'landscape'; // Default: 'portrait'
  branding?: {
    logo_url?: string;
    company_name?: string;
    footer_text?: string;
  };
}
```

### Response

**Status**: `200 OK`

**Content-Type**: `application/json`

```typescript
interface ExportResponse {
  success: boolean;
  export_id: string;
  download_url: string;
  file_size: number; // bytes
  expires_at: string; // ISO 8601 - URL valid for 24 hours
  created_at: string; // ISO 8601
}
```

### Example Request

```bash
curl -X POST http://localhost:5000/api/analytics/export \
  -H "Cookie: session=your_session_cookie" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_a7f3c9d1e2b4",
    "dashboard_state": {
      "visible_charts": [
        "chart_revenue_by_region",
        "chart_orders_trend",
        "chart_category_dist"
      ],
      "active_filters": {
        "filter_date_range": {
          "start": "2024-01-01",
          "end": "2024-12-31"
        },
        "filter_region": "North"
      },
      "selected_insights": [
        "insight_correlation",
        "insight_anomaly"
      ],
      "custom_notes": "Q4 2024 performance analysis for North region showing strong growth in electronics category."
    },
    "export_options": {
      "format": "pdf",
      "include_profile_summary": true,
      "page_orientation": "landscape",
      "branding": {
        "company_name": "Acme Analytics Corp",
        "footer_text": "Confidential - Internal Use Only"
      }
    }
  }'
```

### Example Response

```json
{
  "success": true,
  "export_id": "exp_f8a3d2c5e9b1",
  "download_url": "/api/analytics/exports/exp_f8a3d2c5e9b1/download",
  "file_size": 1245780,
  "expires_at": "2025-12-30T16:45:20.123Z",
  "created_at": "2025-12-29T16:45:20.123Z"
}
```

### Error Responses

**400 Bad Request**: Invalid dashboard state
```json
{
  "error": "invalid_dashboard_state",
  "message": "Invalid chart IDs specified in visible_charts",
  "details": {
    "invalid_ids": ["chart_nonexistent"],
    "valid_ids": ["chart_revenue_by_region", "chart_orders_trend", "chart_category_dist"]
  }
}
```

**404 Not Found**: Session does not exist
```json
{
  "error": "session_not_found",
  "message": "Analytics session not found",
  "details": {
    "session_id": "sess_a7f3c9d1e2b4"
  }
}
```

**500 Internal Server Error**: Export generation failed
```json
{
  "error": "export_failed",
  "message": "Failed to generate PDF export",
  "details": {
    "reason": "Chart rendering timeout"
  }
}
```

---

## Error Handling

### Standard Error Response Format

All error responses follow a consistent structure:

```typescript
interface ErrorResponse {
  error: string; // Machine-readable error code
  message: string; // Human-readable error message
  details?: Record<string, any>; // Additional context
  timestamp?: string; // ISO 8601
  request_id?: string; // For support debugging
}
```

### Common HTTP Status Codes

| Status Code | Meaning | Usage |
|-------------|---------|-------|
| `200 OK` | Success | Request completed successfully |
| `400 Bad Request` | Client Error | Invalid parameters, malformed request |
| `401 Unauthorized` | Authentication Required | Missing or invalid session |
| `403 Forbidden` | Authorization Denied | Valid session but insufficient permissions |
| `404 Not Found` | Resource Missing | Session, notebook, or resource not found |
| `413 Payload Too Large` | File Too Large | Upload exceeds size limit |
| `422 Unprocessable Entity` | Validation Error | Request valid but cannot be processed |
| `429 Too Many Requests` | Rate Limited | Too many requests from user |
| `500 Internal Server Error` | Server Error | Unexpected server-side failure |
| `503 Service Unavailable` | Service Down | Temporary service disruption |

### Error Code Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `invalid_file_format` | 400 | Unsupported file format |
| `file_too_large` | 413 | File exceeds maximum size |
| `session_not_found` | 404 | Analytics session does not exist |
| `unauthorized_access` | 403 | User lacks permission |
| `invalid_parameters` | 400 | Query/request parameters invalid |
| `processing_failed` | 500 | File processing error |
| `export_failed` | 500 | PDF export generation error |
| `rate_limit_exceeded` | 429 | Too many requests |
| `invalid_dashboard_state` | 400 | Dashboard state validation failed |

---

## Rate Limiting

### Limits by Endpoint

| Endpoint | Rate Limit | Window | Scope |
|----------|------------|--------|-------|
| `POST /upload` | 10 requests | 1 hour | Per user |
| `GET /profile/{id}` | 100 requests | 1 hour | Per user |
| `GET /sessions` | 60 requests | 1 minute | Per user |
| `DELETE /sessions/{id}` | 20 requests | 1 hour | Per user |
| `POST /export` | 20 requests | 1 hour | Per user |

### Rate Limit Headers

All responses include rate limit information in headers:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1735488000
```

### Rate Limit Exceeded Response

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "details": {
    "limit": 10,
    "window": "1 hour",
    "retry_after": 3145
  },
  "timestamp": "2025-12-29T16:45:20.123Z"
}
```

**Header**: `Retry-After: 3145` (seconds until limit resets)

---

## Type Definitions

### Complete TypeScript Definitions

```typescript
// ============================================================================
// Request Types
// ============================================================================

interface UploadRequest {
  file: File; // multipart/form-data
  notebook_id?: string;
  analysis_depth?: 'quick' | 'standard' | 'comprehensive';
}

interface ExportRequest {
  session_id: string;
  dashboard_state: DashboardState;
  export_options?: ExportOptions;
}

interface DashboardState {
  visible_charts: string[];
  active_filters: Record<string, any>;
  selected_insights?: string[];
  custom_notes?: string;
}

interface ExportOptions {
  format?: 'pdf' | 'png';
  include_profile_summary?: boolean;
  include_raw_data_sample?: boolean;
  page_orientation?: 'portrait' | 'landscape';
  branding?: {
    logo_url?: string;
    company_name?: string;
    footer_text?: string;
  };
}

// ============================================================================
// Response Types
// ============================================================================

interface UploadResponse {
  session_id: string;
  created_at: string;
  data_summary: DataSummary;
  dashboard_config: DashboardConfig;
  profile_url: string;
}

interface DataSummary {
  filename: string;
  rows: number;
  columns: number;
  file_size: number;
  column_types: Record<string, string>;
  missing_values: Record<string, number>;
  memory_usage: number;
}

interface DashboardConfig {
  kpis: KPI[];
  charts: ChartConfig[];
  filters: FilterConfig[];
  insights: Insight[];
}

interface KPI {
  id: string;
  label: string;
  value: number | string;
  format: 'number' | 'percentage' | 'currency' | 'text';
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    value: number;
    label: string;
  };
}

interface ChartConfig {
  id: string;
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'histogram';
  title: string;
  data_source: {
    x_column: string;
    y_column?: string;
    group_by?: string;
    aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max';
  };
  display_options: {
    show_legend: boolean;
    color_scheme?: string;
    orientation?: 'horizontal' | 'vertical';
  };
}

interface FilterConfig {
  id: string;
  column: string;
  type: 'select' | 'range' | 'date_range' | 'search';
  label: string;
  options?: string[];
  range?: { min: number; max: number };
  default_value?: any;
}

interface Insight {
  id: string;
  category: 'quality' | 'correlation' | 'distribution' | 'anomaly' | 'recommendation';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  affected_columns?: string[];
  action_items?: string[];
}

interface SessionsListResponse {
  sessions: SessionSummary[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface SessionSummary {
  session_id: string;
  filename: string;
  created_at: string;
  notebook_id?: string;
  data_summary: {
    rows: number;
    columns: number;
    file_size: number;
  };
  status: 'processing' | 'completed' | 'failed';
  profile_url?: string;
  last_accessed?: string;
}

interface DeleteSessionResponse {
  success: boolean;
  session_id: string;
  deleted_at: string;
  resources_freed: {
    files_deleted: number;
    storage_freed: number;
  };
}

interface ExportResponse {
  success: boolean;
  export_id: string;
  download_url: string;
  file_size: number;
  expires_at: string;
  created_at: string;
}

interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp?: string;
  request_id?: string;
}
```

---

## Authentication

All endpoints require authentication using dbnotebook's existing session-based authentication system. Requests must include a valid session cookie.

### Authentication Flow

1. User authenticates via dbnotebook login
2. Session cookie is set by the server
3. All Analytics API requests include the session cookie
4. Server validates session and user permissions
5. Resources are scoped to the authenticated user

### Session Cookie

```
Cookie: session=<session_token>
```

Sessions expire after **24 hours** of inactivity or when explicitly logged out.

### Unauthorized Response

```json
{
  "error": "unauthorized",
  "message": "Authentication required. Please log in.",
  "timestamp": "2025-12-29T16:45:20.123Z"
}
```

---

## Best Practices

### Upload Optimization

1. **File Size**: Keep files under 50MB for optimal performance
2. **Pre-processing**: Remove unnecessary columns before upload
3. **Batch Operations**: Upload multiple files sequentially, not in parallel
4. **Analysis Depth**: Use `quick` for exploratory analysis, `comprehensive` for final reports

### Session Management

1. **Cleanup**: Delete old sessions to free storage
2. **Organization**: Use `notebook_id` to organize sessions logically
3. **Naming**: Use descriptive filenames for easier identification
4. **Access Patterns**: Cache frequently accessed profiles

### Export Optimization

1. **Chart Selection**: Only include necessary charts to reduce file size
2. **Filter State**: Document filter selections in custom_notes
3. **Caching**: Reuse exports when dashboard state hasn't changed
4. **Expiration**: Download exports within 24 hours of generation

### Error Recovery

1. **Retry Logic**: Implement exponential backoff for transient errors
2. **Validation**: Validate file format and size client-side before upload
3. **Logging**: Log `request_id` from error responses for support
4. **Fallback**: Gracefully handle service unavailability

---

## Changelog

### Version 1.0.0 (2025-12-29)

**Initial Release**:
- Upload analytics files with automated profiling
- Generate ydata-profiling HTML reports
- LLM-powered dashboard configuration
- Session management and listing
- PDF export capabilities
- Comprehensive error handling and rate limiting

---

## Support

**Documentation Issues**: Create issue in dbnotebook repository
**API Questions**: Contact development team
**Feature Requests**: Submit via product feedback channel

**Related Documentation**:
- [dbnotebook Core API](./API.md)
- [Analytics Dashboard User Guide](./ANALYTICS_GUIDE.md)
- [Data Profiling Best Practices](./PROFILING_GUIDE.md)
