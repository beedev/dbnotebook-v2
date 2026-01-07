"""
Chat with Data (Text-to-SQL) module.

Enables natural language queries against external databases (PostgreSQL, MySQL, SQLite)
with best-in-class accuracy through LlamaIndex integration, few-shot learning, and
semantic inspection.

Features:
- Multi-database support (PostgreSQL, MySQL, SQLite)
- LlamaIndex Text-to-SQL with schema RAG for large databases
- Gretel dataset (100K examples) for few-shot learning
- Semantic inspection with automatic retry
- Intent classification and confidence scoring
- Query cost estimation and safety validation
- Per-connection data masking
- Multi-turn conversation memory
"""

from dbnotebook.core.sql_chat.types import (
    # Type aliases
    DatabaseType,
    QueryState,
    # Enums
    QueryIntent,
    ConfidenceLevel,
    # Core dataclasses
    MaskingPolicy,
    DatabaseConnection,
    ColumnInfo,
    TableInfo,
    ForeignKey,
    SchemaInfo,
    IntentClassification,
    ConfidenceScore,
    CostEstimate,
    QueryResult,
    FewShotExample,
    SQLChatSession,
    QueryTelemetry,
    ModificationResult,
)

# Service - import separately to avoid circular imports
from dbnotebook.core.sql_chat.service import SQLChatService

__all__ = [
    # Service
    "SQLChatService",
    # Type aliases
    "DatabaseType",
    "QueryState",
    # Enums
    "QueryIntent",
    "ConfidenceLevel",
    # Core dataclasses
    "MaskingPolicy",
    "DatabaseConnection",
    "ColumnInfo",
    "TableInfo",
    "ForeignKey",
    "SchemaInfo",
    "IntentClassification",
    "ConfidenceScore",
    "CostEstimate",
    "QueryResult",
    "FewShotExample",
    "SQLChatSession",
    "QueryTelemetry",
    "ModificationResult",
]
