/**
 * TypeScript types for SQL Chat (Chat with Data) feature
 */

// Database Types
export type DatabaseType = 'postgresql' | 'mysql' | 'sqlite';
export type QueryState = 'idle' | 'connecting' | 'generating' | 'validating' | 'executing' | 'complete' | 'error';
export type QueryIntent = 'lookup' | 'aggregation' | 'comparison' | 'trend' | 'top_k' | 'unknown';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

// Masking Policy
export interface MaskingPolicy {
  maskColumns: string[];    // Show as "****" (e.g., email, phone)
  redactColumns: string[];  // Remove entirely (e.g., ssn, password)
  hashColumns: string[];    // Show hash (e.g., user_id for analytics)
}

// Database Connection
export interface DatabaseConnection {
  id: string;
  userId: string;
  name: string;
  dbType: DatabaseType;
  host?: string;
  port?: number;
  databaseName?: string;
  schema?: string;           // PostgreSQL schema (e.g., 'public', 'sales')
  username?: string;
  maskingPolicy?: MaskingPolicy;
  createdAt: string;
  lastUsedAt?: string;
}

// Connection Form Data (for creating connections)
export interface ConnectionFormData {
  name: string;
  dbType: DatabaseType;
  host?: string;
  port?: number;
  databaseName?: string;
  schema?: string;           // PostgreSQL schema (e.g., 'public', 'sales')
  username?: string;
  password?: string;
  connectionString?: string;
  useConnectionString?: boolean;
  maskingPolicy?: MaskingPolicy;
}

// Column Info
export interface ColumnInfo {
  name: string;
  dataType: string;
  nullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  defaultValue?: string;
  comment?: string;
}

// Foreign Key
export interface ForeignKey {
  constraintName: string;
  columnName: string;
  referencedTable: string;
  referencedColumn: string;
}

// Table Info
export interface TableInfo {
  name: string;
  columns: ColumnInfo[];
  rowCount?: number;
  sampleValues: Record<string, any[]>;
  comment?: string;
}

// Schema Info
export interface SchemaInfo {
  tables: TableInfo[];
  relationships: ForeignKey[];
  cachedAt: string;
}

// Intent Classification
export interface IntentClassification {
  intent: QueryIntent;
  confidence: number;
  hints: string;
}

// Confidence Score
export interface ConfidenceScore {
  score: number;  // 0.0 - 1.0
  level: ConfidenceLevel;
  factors: {
    tableRelevance: number;
    fewShotSimilarity: number;
    retryPenalty: number;
    columnOverlap: number;
  };
}

// Cost Estimate
export interface CostEstimate {
  totalCost: number;
  estimatedRows: number;
  hasSequentialScan: boolean;
  hasCartesianJoin: boolean;
  isSafe: boolean;
  warning?: string;
}

// Validation Warning
export type ValidationSeverity = 'info' | 'warning' | 'error';

export interface ValidationWarning {
  severity: ValidationSeverity;
  code: string;
  message: string;
  suggestion: string;
}

// Query Result
export interface QueryResult {
  success: boolean;
  sqlGenerated: string;
  data: Record<string, any>[];
  columns: ColumnInfo[];
  rowCount: number;
  executionTimeMs: number;
  explanation?: string;
  intent?: IntentClassification;
  confidence?: ConfidenceScore;
  costEstimate?: CostEstimate;
  validationWarnings?: ValidationWarning[];
  errorMessage?: string;
  retryCount?: number;
}

// Few-Shot Example
export interface FewShotExample {
  sqlPrompt: string;
  sqlQuery: string;
  sqlContext?: string;
  complexity?: string;
  domain?: string;
  similarity?: number;
}

// SQL Chat Session
export interface SQLChatSession {
  id: string;
  userId: string;
  connectionId: string;
  connection?: DatabaseConnection;
  schema?: SchemaInfo;
  createdAt: string;
  lastQueryAt?: string;
}

// Query History Entry
export interface QueryHistoryEntry {
  id: number;
  sessionId: string;
  userQuery: string;
  generatedSql: string;
  executionTimeMs?: number;
  rowCount?: number;
  success: boolean;
  errorMessage?: string;
  createdAt: string;
}

// Query Telemetry
export interface QueryTelemetry {
  id: number;
  sessionId: string;
  userQuery?: string;
  generatedSql?: string;
  intent?: string;
  confidenceScore?: number;
  retryCount?: number;
  executionTimeMs?: number;
  rowCount?: number;
  costEstimate?: number;
  success: boolean;
  errorMessage?: string;
  createdAt: string;
}

// Accuracy Metrics
export interface AccuracyMetrics {
  successRate: number;
  avgRetries: number;
  avgConfidence: number;
  emptyResultRate: number;
  totalQueries: number;
  periodDays: number;
}

// Chat Message
export interface SQLChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sql?: string;
  result?: QueryResult;
  timestamp: string;
}

// API Response Types
export interface ConnectionResponse {
  success: boolean;
  connectionId?: string;
  connection?: DatabaseConnection;
  error?: string;
}

export interface ConnectionListResponse {
  success: boolean;
  connections?: DatabaseConnection[];
  error?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface SchemaResponse {
  success: boolean;
  schema?: SchemaInfo;
  error?: string;
}

export interface SessionResponse {
  success: boolean;
  sessionId?: string;
  session?: SQLChatSession;
  error?: string;
}

export interface QueryResponse {
  success: boolean;
  result?: QueryResult;
  error?: string;
}

export interface HistoryResponse {
  success: boolean;
  history?: QueryHistoryEntry[];
  error?: string;
}

export interface MetricsResponse {
  success: boolean;
  metrics?: AccuracyMetrics;
  error?: string;
}

// Streaming Types
export interface StreamingQueryState {
  state: QueryState;
  message?: string;
  sql?: string;
  intent?: IntentClassification;
  confidence?: ConfidenceScore;
  result?: QueryResult;
  error?: string;
}

// SQL Chat Context State
export interface SQLChatContextState {
  // Connections
  connections: DatabaseConnection[];
  activeConnection: DatabaseConnection | null;
  isLoadingConnections: boolean;

  // Session
  activeSession: SQLChatSession | null;
  isCreatingSession: boolean;

  // Schema
  schema: SchemaInfo | null;
  isLoadingSchema: boolean;

  // Query
  isQuerying: boolean;
  queryState: QueryState;
  currentQuery: string;
  queryResult: QueryResult | null;

  // Chat
  messages: SQLChatMessage[];

  // History
  queryHistory: QueryHistoryEntry[];
  isLoadingHistory: boolean;

  // Error
  error: string | null;
}

// SQL Chat Context Actions
export interface SQLChatContextActions {
  // Connection management
  loadConnections: () => Promise<void>;
  createConnection: (data: ConnectionFormData) => Promise<string | null>;
  testConnection: (data: ConnectionFormData) => Promise<boolean>;
  deleteConnection: (connectionId: string) => Promise<boolean>;
  selectConnection: (connectionId: string) => Promise<void>;

  // Session management
  createSession: (connectionId: string) => Promise<string | null>;
  loadSession: (sessionId: string) => Promise<void>;

  // Schema
  loadSchema: (connectionId: string) => Promise<void>;
  refreshSchema: (connectionId: string) => Promise<void>;

  // Query execution
  sendQuery: (query: string) => Promise<QueryResult | null>;
  refineQuery: (refinement: string) => Promise<QueryResult | null>;
  cancelQuery: () => void;

  // History
  loadHistory: (sessionId: string) => Promise<void>;

  // Chat
  clearMessages: () => void;

  // Error handling
  clearError: () => void;
}

// Full Context Value
export interface SQLChatContextValue extends SQLChatContextState, SQLChatContextActions {}
