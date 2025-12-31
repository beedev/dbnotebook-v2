/**
 * TypeScript types for Analytics Dashboard
 */

// Data Types
export type DataType = 'numeric' | 'categorical' | 'datetime' | 'boolean' | 'text';
export type AggregationType = 'sum' | 'avg' | 'count' | 'min' | 'max' | 'median';
export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area';
export type FilterType = 'categorical' | 'range' | 'date';

// Analysis State
export type AnalysisState = 'idle' | 'uploading' | 'parsing' | 'profiling' | 'analyzing' | 'complete' | 'error';

// Column Statistics
export interface ColumnStatistics {
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  skewness: number;
  kurtosis: number;
  quartiles: [number, number, number]; // Q1, Q2, Q3
  iqr: number;
}

// Categorical Statistics
export interface CategoricalStats {
  uniqueCount: number;
  topValues: Array<{
    value: string;
    count: number;
    percent: number;
  }>;
  entropy: number;
}

// Column Metadata
export interface ColumnMetadata {
  name: string;
  inferredType: DataType;
  uniqueCount: number;
  nullCount: number;
  nullPercent: number;
  sampleValues: any[];
  statistics?: ColumnStatistics;
  categorical?: CategoricalStats;
}

// Parsed Data
export interface ParsedData {
  data: Record<string, any>[];
  columns: ColumnMetadata[];
  rowCount: number;
  columnCount: number;
  sampleData: Record<string, any>[];
  fileName: string;
  fileSize: number;
  parsingErrors: Array<{
    row?: number;
    column?: string;
    message: string;
    severity: 'warning' | 'error';
  }>;
}

// Correlation Info
export interface CorrelationInfo {
  var1: string;
  var2: string;
  correlation: number;
}

// Quality Alert
export interface QualityAlert {
  column: string | null;
  severity: 'critical' | 'warning' | 'info';
  alertType: string;
  message: string;
  recommendation?: string;
}

// Profiling Result
export interface ProfilingResult {
  overview: {
    rowCount: number;
    columnCount: number;
    missingCellsPercent: number;
    duplicateRowsPercent: number;
    memorySize: string;
  };
  columns: ColumnMetadata[];
  correlations: CorrelationInfo[];
  qualityAlerts: QualityAlert[];
  qualityScore: number; // 0-10
  htmlReportUrl?: string;
}

// KPI Configuration
export interface KPIConfig {
  id: string;
  title: string;
  metric: string; // Column name
  aggregation: AggregationType;
  format: 'number' | 'currency' | 'percentage';
  icon?: string; // Lucide icon name
  color?: 'blue' | 'green' | 'red' | 'purple' | 'orange';
  prefix?: string;
  suffix?: string;
  decimalPlaces?: number;
}

// Chart Configuration
export interface ChartConfig {
  id: string;
  title: string;
  type: ChartType;
  xAxis: string; // Column name
  yAxis: string; // Column name
  aggregation?: AggregationType;
  color?: string;
  allowCrossFilter?: boolean;
  sortBy?: 'value' | 'label';
  sortOrder?: 'asc' | 'desc';
  limit?: number; // Legacy - prefer topN
  topN?: number;  // Limit to top N items (for high-cardinality columns)
}

// Filter Configuration
export interface FilterConfig {
  id: string;
  column: string;
  type: FilterType;
  label: string;
  defaultValue?: any;
  options?: string[]; // For categorical
  minValue?: number; // For range
  maxValue?: number; // For range
}

// Dashboard Metadata
export interface DashboardMetadata {
  title: string;
  description: string;
  recommendationReason?: string;
  generatedAt?: string;
  dataSource?: string;
}

// Dashboard Configuration
export interface DashboardConfig {
  kpis: KPIConfig[];
  charts: ChartConfig[];
  filters: FilterConfig[];
  metadata: DashboardMetadata;
}

// Analysis Session
export interface AnalysisSession {
  sessionId: string;
  userId?: string;
  notebookId?: string;
  fileName: string;
  filePath?: string;
  fileSize: number;
  status: AnalysisState;
  createdAt: string;
  updatedAt?: string;
  parsedData?: ParsedData;
  profilingResult?: ProfilingResult;
  dashboardConfig?: DashboardConfig;
  errorMessage?: string;
  progress: number; // 0-100
}

// Filter State (current filter values)
export interface FilterState {
  [filterId: string]: {
    type: FilterType;
    value: any; // string[] for categorical, [min, max] for range, [start, end] for date
  };
}

// Cross-filter Event
export interface CrossFilterEvent {
  sourceChartId: string;
  filterColumn: string;
  filterValue: any;
  filterType: 'include' | 'exclude';
}

// API Response Types
export interface UploadResponse {
  success: boolean;
  sessionId?: string;
  status?: string;
  metadata?: {
    fileName: string;
    fileSize: number;
    uploadedAt: string;
  };
  error?: string;
}

export interface ParseResponse {
  success: boolean;
  sessionId?: string;
  status?: string;
  parsedData?: ParsedData;
  error?: string;
}

export interface ProfileResponse {
  success: boolean;
  sessionId?: string;
  status?: string;
  profilingResult?: ProfilingResult;
  error?: string;
}

export interface SessionResponse {
  success: boolean;
  session?: AnalysisSession;
  error?: string;
}

export interface SessionDataResponse {
  success: boolean;
  sessionId?: string;
  status?: string;
  fileName?: string;
  parsedData?: ParsedData;
  profilingResult?: ProfilingResult;
  dashboardConfig?: DashboardConfig;
  error?: string;
}

// ========================================
// NLP Modification Types
// ========================================

// Modification state for undo/redo
export interface ModificationState {
  canUndo: boolean;
  canRedo: boolean;
  lastChanges: string[];
  initialRequirements?: string;
}

// Response from modification endpoints
export interface ModifyResponse {
  success: boolean;
  dashboardConfig?: DashboardConfig;
  changes?: string[];
  canUndo?: boolean;
  canRedo?: boolean;
  error?: string;
}

// Extended AnalyzeResponse with modification state
export interface AnalyzeResponse {
  success: boolean;
  sessionId?: string;
  status?: string;
  dashboardConfig?: DashboardConfig;
  modificationState?: ModificationState;
  error?: string;
}

// Requirements response
export interface RequirementsResponse {
  success: boolean;
  message?: string;
  requirements?: string;
  error?: string;
}
