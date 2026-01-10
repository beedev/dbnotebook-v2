"""
SQL Query Validation and Safety Checks.

Provides pre and post-generation SQL validation to ensure:
- No destructive operations (DROP, DELETE, INSERT, UPDATE)
- No SQL injection patterns
- Table references match schema
- Read-only enforcement
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from dbnotebook.core.sql_chat.types import SchemaInfo

logger = logging.getLogger(__name__)


class QueryValidator:
    """Pre and post-generation SQL validation.

    Ensures all generated SQL is safe for execution by checking:
    - Forbidden operations (DROP, DELETE, INSERT, etc.)
    - SQL injection patterns
    - Table reference validation
    - Query structure safety
    """

    # Forbidden SQL operations - these should never be in generated SQL
    FORBIDDEN_OPERATIONS: Set[str] = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE',
        'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL',
        'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'LOCK', 'UNLOCK'
    }

    # SQL injection patterns to detect
    INJECTION_PATTERNS: List[str] = [
        r"';.*--",                     # Classic SQL injection
        r'UNION\s+SELECT',             # UNION-based injection
        r'OR\s+1\s*=\s*1',             # Always-true condition
        r'OR\s+\'1\'\s*=\s*\'1\'',     # String-based always-true
        r'--\s*$',                     # Comment-based injection (end of query)
        r'/\*.*\*/',                   # Block comments
        r';\s*(DROP|DELETE|INSERT)',   # Stacked queries with destructive ops
        r'SLEEP\s*\(',                 # Time-based injection
        r'BENCHMARK\s*\(',             # MySQL time-based injection
        r'WAITFOR\s+DELAY',            # SQL Server time-based
        r'pg_sleep\s*\(',              # PostgreSQL time-based
        r'LOAD_FILE\s*\(',             # File access
        r'INTO\s+(OUT|DUMP)FILE',      # File write
        r'xp_cmdshell',                # SQL Server command execution
    ]

    def __init__(self):
        """Initialize validator with compiled regex patterns."""
        self._injection_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        ]

    def validate_user_input(self, query: str) -> Tuple[bool, str]:
        """Validate user's natural language query for suspicious patterns.

        Args:
            query: User's natural language query

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"

        # Check for SQL-like content in natural language query
        # This catches users trying to inject SQL directly
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'DROP', 'DELETE', 'INSERT']
        upper_query = query.upper()

        # If query looks like it's trying to be SQL directly
        if any(upper_query.startswith(kw) for kw in ['SELECT', 'DROP', 'DELETE', 'INSERT']):
            return False, "Please describe what you want in natural language, not SQL"

        # Check for injection patterns in user input
        for pattern in self._injection_patterns:
            if pattern.search(query):
                logger.warning(f"Potential injection pattern detected in user input: {pattern.pattern}")
                return False, "Query contains suspicious patterns"

        return True, ""

    def validate_generated_sql(
        self,
        sql: str,
        schema: Optional[SchemaInfo] = None
    ) -> Tuple[bool, str]:
        """Validate LLM-generated SQL for safety.

        Args:
            sql: Generated SQL query
            schema: Optional schema for table reference validation

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Generated SQL is empty"

        # Normalize for checking
        sql_upper = sql.upper()
        sql_normalized = ' '.join(sql_upper.split())

        # Check 1: Forbidden operations
        for op in self.FORBIDDEN_OPERATIONS:
            # Use word boundary matching to avoid false positives
            pattern = rf'\b{op}\b'
            if re.search(pattern, sql_normalized):
                logger.warning(f"Forbidden operation detected: {op}")
                return False, f"Query contains forbidden operation: {op}"

        # Check 2: SQL injection patterns
        for pattern in self._injection_patterns:
            if pattern.search(sql):
                logger.warning(f"Injection pattern detected: {pattern.pattern}")
                return False, "Query contains potentially unsafe pattern"

        # Check 3: Must start with SELECT or WITH (for CTEs)
        if not (sql_normalized.startswith('SELECT') or sql_normalized.startswith('WITH')):
            return False, "Only SELECT queries are allowed"

        # Check 4: Table reference validation (if schema provided)
        if schema:
            is_valid, error = self.check_table_references(sql, schema)
            if not is_valid:
                return False, error

        # Check 5: Column reference validation (if schema provided)
        if schema:
            is_valid, error = self.check_column_references(sql, schema)
            if not is_valid:
                return False, error

        # Check 6: No multiple statements (prevent stacked queries)
        # Allow semicolon at end but not in middle
        sql_stripped = sql.strip().rstrip(';')
        if ';' in sql_stripped:
            return False, "Multiple SQL statements not allowed"

        return True, ""

    def check_table_references(
        self,
        sql: str,
        schema: SchemaInfo
    ) -> Tuple[bool, str]:
        """Verify all table references exist in schema.

        Args:
            sql: SQL query to check
            schema: Database schema

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get allowed table names (case-insensitive)
        allowed_tables = {t.name.lower() for t in schema.tables}

        # Extract table references from SQL
        # This is a simplified extraction - covers common patterns
        table_patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]

        referenced_tables: Set[str] = set()
        for pattern in table_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            referenced_tables.update(m.lower() for m in matches)

        # Remove common SQL keywords that might match
        sql_keywords = {'select', 'from', 'where', 'and', 'or', 'not', 'null',
                       'true', 'false', 'case', 'when', 'then', 'else', 'end'}
        referenced_tables -= sql_keywords

        # Check all referenced tables exist
        invalid_tables = referenced_tables - allowed_tables
        if invalid_tables:
            return False, f"Unknown table(s): {', '.join(invalid_tables)}"

        return True, ""

    def check_column_references(
        self,
        sql: str,
        schema: SchemaInfo
    ) -> Tuple[bool, str]:
        """Verify all column references exist in schema.

        Args:
            sql: SQL query to check
            schema: Database schema

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Build mapping of table -> columns
        table_columns: Dict[str, Set[str]] = {}
        all_columns: Set[str] = set()
        for table in schema.tables:
            table_columns[table.name.lower()] = {c.name.lower() for c in table.columns}
            all_columns.update(c.name.lower() for c in table.columns)

        # Extract column references - patterns like table.column or just column
        # Pattern 1: table.column references
        qualified_patterns = [
            r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)',  # table.column
        ]

        # Check qualified column references (table.column)
        for pattern in qualified_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for table_ref, col_ref in matches:
                table_lower = table_ref.lower()
                col_lower = col_ref.lower()

                # Skip SQL keywords that might look like table.column
                sql_keywords = {'count', 'sum', 'avg', 'min', 'max', 'coalesce', 'cast', 'extract'}
                if table_lower in sql_keywords:
                    continue

                # If table is known, check column exists in that table
                if table_lower in table_columns:
                    if col_lower not in table_columns[table_lower]:
                        # Get available columns for helpful error message
                        available = sorted(table_columns[table_lower])[:10]
                        return False, f"Column '{col_ref}' does not exist in table '{table_ref}'. Available columns: {', '.join(available)}"

        return True, ""

    def sanitize_output(
        self,
        results: List[dict],
        sensitive_columns: Optional[Set[str]] = None
    ) -> List[dict]:
        """Sanitize query results by removing sensitive data.

        This is a fallback - prefer using MaskingPolicy via DataMasker.

        Args:
            results: Query result rows
            sensitive_columns: Column names to redact

        Returns:
            Sanitized results
        """
        if not sensitive_columns:
            return results

        sensitive_lower = {c.lower() for c in sensitive_columns}

        sanitized = []
        for row in results:
            sanitized_row = {}
            for col, value in row.items():
                if col.lower() in sensitive_lower:
                    sanitized_row[col] = "****"
                else:
                    sanitized_row[col] = value
            sanitized.append(sanitized_row)

        return sanitized

    def validate_connection_test_sql(self, db_type: str) -> str:
        """Get safe SQL for connection testing.

        Args:
            db_type: Database type (postgresql, mysql, sqlite)

        Returns:
            Safe SQL query for testing connection
        """
        if db_type == "sqlite":
            return "SELECT 1"
        elif db_type == "mysql":
            return "SELECT 1"
        else:  # postgresql
            return "SELECT 1"

    def get_read_only_test_sql(self, db_type: str) -> str:
        """Get SQL to test that connection is read-only.

        This SQL should FAIL if user has write access.

        Args:
            db_type: Database type

        Returns:
            SQL that tests write capability (should fail for read-only users)
        """
        if db_type == "sqlite":
            return "CREATE TABLE __test_readonly_check (id INTEGER)"
        else:
            return "CREATE TABLE __test_readonly_check (id INT)"
