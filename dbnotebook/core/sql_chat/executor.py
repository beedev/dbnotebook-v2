"""
Safe Query Executor for Chat with Data.

Executes SQL queries with safety guarantees:
- Read-only enforcement (auto-rollback)
- Row limits
- Timeout handling
- Error recovery
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from dbnotebook.core.sql_chat.types import (
    ColumnInfo,
    QueryResult,
)
from dbnotebook.core.sql_chat.validators import QueryValidator

logger = logging.getLogger(__name__)


class SafeQueryExecutor:
    """Execute queries with safety guarantees.

    Provides:
    - Read-only enforcement via auto-rollback
    - Row limits to prevent memory issues
    - Query timeout handling
    - Error capture and recovery
    """

    MAX_ROWS = 10000
    QUERY_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        max_rows: int = 10000,
        query_timeout_seconds: int = 30
    ):
        """Initialize safe query executor.

        Args:
            max_rows: Maximum rows to return
            query_timeout_seconds: Query timeout in seconds
        """
        self.max_rows = max_rows
        self.query_timeout_seconds = query_timeout_seconds
        self._validator = QueryValidator()

    def execute_readonly(
        self,
        engine: Engine,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute query in read-only mode with safety checks.

        Uses transaction that auto-rollbacks to ensure read-only.

        Args:
            engine: SQLAlchemy engine
            sql: SQL query to execute
            params: Optional query parameters

        Returns:
            QueryResult with data or error
        """
        start_time = time.time()

        # Pre-validate SQL
        is_valid, error = self._validator.validate_generated_sql(sql)
        if not is_valid:
            return QueryResult(
                success=False,
                sql_generated=sql,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message=error,
            )

        # Add LIMIT if not present
        sql_with_limit = self._ensure_limit(sql)

        try:
            with engine.connect() as conn:
                # Set statement timeout (PostgreSQL specific)
                if engine.dialect.name == 'postgresql':
                    timeout_ms = self.query_timeout_seconds * 1000
                    conn.execute(text(f"SET statement_timeout = {timeout_ms}"))

                # Execute query
                result = conn.execute(text(sql_with_limit), params or {})

                # Fetch all rows (up to limit)
                rows = result.fetchall()

                # Get column info
                columns = self._extract_column_info(result)

                # Convert to dicts
                data = [dict(row._mapping) for row in rows]

                # IMPORTANT: Do NOT commit - rollback to ensure read-only
                conn.rollback()

            execution_time_ms = (time.time() - start_time) * 1000

            return QueryResult(
                success=True,
                sql_generated=sql,
                data=data,
                columns=columns,
                row_count=len(data),
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_message = str(e)

            # Check for common error types
            if "statement_timeout" in error_message.lower():
                error_message = f"Query timed out after {self.query_timeout_seconds} seconds"
            elif "permission denied" in error_message.lower():
                error_message = "Permission denied - check database user permissions"

            logger.error(f"Query execution failed: {error_message}")

            return QueryResult(
                success=False,
                sql_generated=sql,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
            )

    def _ensure_limit(self, sql: str) -> str:
        """Add LIMIT clause if not present.

        Args:
            sql: SQL query

        Returns:
            SQL with LIMIT added if needed
        """
        sql_upper = sql.upper().strip()

        # Check if LIMIT already present
        if 'LIMIT' in sql_upper:
            return sql

        # Add LIMIT to prevent unbounded results
        sql_trimmed = sql.rstrip().rstrip(';')
        return f"{sql_trimmed} LIMIT {self.max_rows}"

    def _extract_column_info(self, result) -> List[ColumnInfo]:
        """Extract column metadata from result.

        Args:
            result: SQLAlchemy result object

        Returns:
            List of ColumnInfo
        """
        columns = []
        for col in result.keys():
            # Get type if available
            type_name = "unknown"
            try:
                cursor_desc = result.cursor.description
                for desc in cursor_desc:
                    if desc[0] == col:
                        type_name = str(desc[1].__name__) if hasattr(desc[1], '__name__') else str(desc[1])
                        break
            except Exception:
                pass

            columns.append(ColumnInfo(
                name=col,
                type=type_name,
            ))

        return columns

    def execute_raw(
        self,
        engine: Engine,
        sql: str
    ) -> Any:
        """Execute raw SQL (for EXPLAIN, etc.).

        Only for internal use with validated SQL.

        Args:
            engine: SQLAlchemy engine
            sql: SQL to execute

        Returns:
            Raw result data
        """
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(row._mapping) for row in result.fetchall()]

    def test_query_syntax(
        self,
        engine: Engine,
        sql: str
    ) -> Tuple[bool, str]:
        """Test query syntax without executing.

        Uses EXPLAIN to validate syntax.

        Args:
            engine: SQLAlchemy engine
            sql: SQL to test

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            dialect = engine.dialect.name

            if dialect == 'postgresql':
                explain_sql = f"EXPLAIN {sql}"
            elif dialect == 'mysql':
                explain_sql = f"EXPLAIN {sql}"
            else:
                # SQLite - just try preparing
                explain_sql = f"EXPLAIN QUERY PLAN {sql}"

            with engine.connect() as conn:
                conn.execute(text(explain_sql))
                conn.rollback()

            return True, ""

        except Exception as e:
            return False, str(e)

    def get_result_summary(self, result: QueryResult) -> Dict[str, Any]:
        """Get summary statistics for query result.

        Args:
            result: Query result

        Returns:
            Summary dict
        """
        if not result.success:
            return {
                "success": False,
                "error": result.error_message,
            }

        return {
            "success": True,
            "row_count": result.row_count,
            "column_count": len(result.columns),
            "columns": [c.name for c in result.columns],
            "execution_time_ms": round(result.execution_time_ms, 2),
            "truncated": result.row_count >= self.max_rows,
        }
