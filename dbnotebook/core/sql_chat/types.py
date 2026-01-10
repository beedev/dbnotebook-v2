"""
Type definitions for Chat with Data (Text-to-SQL) feature.

Defines core dataclasses for database connections, queries, results,
masking policies, and session management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


# Type aliases
DatabaseType = Literal["postgresql", "mysql", "sqlite"]
QueryState = Literal[
    "pending",
    "generating_dictionary",  # Dictionary batch generation in progress
    "ready",                  # Dictionary ready, queries enabled
    "generating",
    "validating",
    "executing",
    "complete",
    "error"
]


class QueryIntent(str, Enum):
    """Classification of query intent for SQL shape optimization."""
    LOOKUP = "lookup"           # show, get, find, details
    AGGREGATION = "aggregation" # total, sum, count, average
    COMPARISON = "comparison"   # vs, versus, compare, difference
    TREND = "trend"             # over time, growth, trend, change
    TOP_K = "top_k"             # top, best, highest, lowest


class ConfidenceLevel(str, Enum):
    """Confidence level for generated SQL queries."""
    HIGH = "high"       # >= 0.8
    MEDIUM = "medium"   # >= 0.5
    LOW = "low"         # < 0.5


@dataclass
class MaskingPolicy:
    """Column-level data masking configuration per connection.

    Defines how sensitive data should be handled in query results.
    """
    mask_columns: List[str] = field(default_factory=list)    # Show as "****" (e.g., email, phone)
    redact_columns: List[str] = field(default_factory=list)  # Remove entirely (e.g., ssn, password)
    hash_columns: List[str] = field(default_factory=list)    # Show hash (e.g., user_id for analytics)


@dataclass
class DatabaseConnection:
    """Configuration for an external database connection.

    Attributes:
        id: Unique identifier for the connection
        name: User-friendly display name
        type: Database type (postgresql, mysql, sqlite)
        host: Database host address
        port: Database port
        database: Database name
        schema: PostgreSQL schema(s) - comma-separated for multiple
        username: Database username
        password_encrypted: Encrypted password (Fernet encryption)
        masking_policy: Optional data masking configuration
        created_at: Timestamp when connection was created
        last_used_at: Timestamp of last successful query
    """
    id: str
    name: str
    type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password_encrypted: Optional[str] = None
    schema: Optional[str] = None  # PostgreSQL schema(s) e.g., 'public' or 'sales,hr'
    masking_policy: Optional[MaskingPolicy] = None
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    user_id: Optional[str] = None


@dataclass
class ColumnInfo:
    """Metadata for a database column."""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None  # "other_table.column" format
    comment: Optional[str] = None


@dataclass
class TableInfo:
    """Metadata for a database table."""
    name: str
    columns: List[ColumnInfo]
    row_count: Optional[int] = None
    sample_values: Dict[str, List[Any]] = field(default_factory=dict)  # column -> [sample values]
    comment: Optional[str] = None


@dataclass
class ForeignKey:
    """Foreign key relationship between tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class SchemaInfo:
    """Complete database schema information."""
    tables: List[TableInfo]
    relationships: List[ForeignKey] = field(default_factory=list)
    cached_at: Optional[datetime] = None
    database_name: str = ""


@dataclass
class IntentClassification:
    """Result of query intent classification."""
    intent: QueryIntent
    confidence: float
    prompt_hints: str = ""


@dataclass
class ConfidenceScore:
    """Confidence score for generated SQL with detailed factors."""
    score: float           # 0.0 - 1.0
    level: ConfidenceLevel
    factors: Dict[str, float] = field(default_factory=dict)
    # factors: table_relevance, few_shot_similarity, retry_penalty, column_overlap


@dataclass
class CostEstimate:
    """Query cost estimation from EXPLAIN."""
    total_cost: float
    estimated_rows: int
    has_seq_scan: bool = False
    has_cartesian: bool = False
    plan_json: Optional[Dict[str, Any]] = None


@dataclass
class QueryResult:
    """Result of SQL query execution."""
    success: bool
    sql_generated: str
    data: List[Dict[str, Any]]
    columns: List[ColumnInfo]
    row_count: int
    execution_time_ms: float
    error_message: Optional[str] = None
    confidence: Optional[ConfidenceScore] = None
    cost_estimate: Optional[CostEstimate] = None
    intent: Optional[IntentClassification] = None
    retry_count: int = 0
    explanation: Optional[str] = None  # Natural language explanation of results
    validation_warnings: Optional[List[Dict[str, str]]] = None  # Result validation warnings


@dataclass
class FewShotExample:
    """Few-shot example from Gretel dataset."""
    id: int
    sql_prompt: str
    sql_query: str
    sql_context: Optional[str] = None
    complexity: Optional[str] = None  # basic SQL, joins, aggregation, subqueries, window functions
    domain: Optional[str] = None      # finance, healthcare, tech, etc.
    similarity: float = 0.0


@dataclass
class SQLChatSession:
    """Active SQL chat session state."""
    session_id: str
    user_id: str
    connection_id: str
    schema: Optional[SchemaInfo] = None
    query_history: List[QueryResult] = field(default_factory=list)
    status: QueryState = "pending"
    created_at: Optional[datetime] = None
    last_query_at: Optional[datetime] = None


@dataclass
class QueryTelemetry:
    """Telemetry data for query analytics."""
    session_id: str
    user_query: str
    generated_sql: str
    intent: str
    confidence_score: float
    retry_count: int
    execution_time_ms: int
    row_count: int
    cost_estimate: float
    success: bool
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class ModificationResult:
    """Result of SQL modification/refinement."""
    original_sql: str
    modified_sql: str
    modification_description: str
    success: bool
