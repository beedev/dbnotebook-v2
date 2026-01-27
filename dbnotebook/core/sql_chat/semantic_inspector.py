"""
Semantic Inspector for Chat with Data.

Implements agentic result inspection (inspired by Smolagents).
Goes beyond syntax validation to check if results make semantic sense.
Automatically retries with feedback when results are incorrect/useless.

Key enhancement: Schema-aware error correction.
When SQL errors mention wrong column names, includes actual schema in retry prompt.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from llama_index.core.llms.llm import LLM

from dbnotebook.core.sql_chat.types import QueryResult, SchemaInfo

logger = logging.getLogger(__name__)


class SemanticInspector:
    """Inspect SQL results for semantic correctness, not just syntax.

    Key insight from Smolagents: Standard Text-to-SQL only catches syntax errors.
    Agentic systems inspect results semantically and retry when outputs are
    incorrect or useless.

    Checks performed:
    - Empty results (wrong table, overly restrictive filter)
    - Too many rows (missing filter, likely unintended)
    - Columns don't match intent (wrong SELECT clause)
    - Suspicious NULLs in aggregations (non-existent column)
    - Type mismatches (expected number, got string)
    """

    MAX_RETRIES = 3

    # Aggregation keywords for detecting aggregation queries
    AGG_KEYWORDS = ['sum', 'avg', 'average', 'count', 'total', 'max', 'min', 'mean']

    def __init__(
        self,
        llm: LLM,
        max_retries: int = 3,
        max_acceptable_rows: int = 5000
    ):
        """Initialize semantic inspector.

        Args:
            llm: Language model for SQL correction
            max_retries: Maximum retry attempts
            max_acceptable_rows: Row count above which to suggest filtering
        """
        self._llm = llm
        self.max_retries = max_retries
        self.max_acceptable_rows = max_acceptable_rows

    async def execute_with_inspection(
        self,
        nl_query: str,
        sql: str,
        execute_fn,
        connection_id: str,
        schema: Optional[SchemaInfo] = None,
    ) -> Tuple[QueryResult, bool, int]:
        """Execute SQL with semantic validation and auto-retry.

        Args:
            nl_query: Original natural language query
            sql: Generated SQL
            execute_fn: Function to execute SQL (engine, sql) -> QueryResult
            connection_id: Connection ID
            schema: Optional schema info for column-aware error correction

        Returns:
            Tuple of (QueryResult, success, retry_count)
        """
        current_sql = sql
        retry_count = 0

        for attempt in range(self.max_retries):
            result = execute_fn(current_sql)

            if not result.success:
                # Syntax error - let LLM fix it with schema context if available
                feedback = self._build_error_feedback(result.error_message, schema)
                logger.info(f"Attempt {attempt + 1}: SQL error, retrying with schema context")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback, schema)
                retry_count += 1
                continue

            # Check 1: Empty results
            if result.row_count == 0:
                feedback = (
                    "Query returned 0 rows. Possible issues: "
                    "wrong table name, overly restrictive WHERE clause, "
                    "incorrect JOIN condition, or data doesn't exist."
                )
                logger.info(f"Attempt {attempt + 1}: Empty results, retrying")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback)
                retry_count += 1
                continue

            # Check 2: Too many results (likely missing filter)
            if result.row_count > self.max_acceptable_rows:
                feedback = (
                    f"Query returned {result.row_count} rows, which is too many. "
                    "Add more specific WHERE conditions or a LIMIT clause."
                )
                logger.info(f"Attempt {attempt + 1}: Too many rows, retrying")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback)
                retry_count += 1
                continue

            # Check 3: Columns don't match intent
            if not self._columns_match_intent(nl_query, result):
                feedback = (
                    f"Columns {[c.name for c in result.columns]} don't seem to answer "
                    f"the question '{nl_query}'. Review the SELECT clause."
                )
                logger.info(f"Attempt {attempt + 1}: Column mismatch, retrying")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback)
                retry_count += 1
                continue

            # Check 4: Aggregation sanity (e.g., AVG returning NULL)
            if self._has_suspicious_nulls(nl_query, result):
                feedback = (
                    "Aggregation returned NULL values. "
                    "Check if the column exists and contains data. "
                    "Verify column name spelling."
                )
                logger.info(f"Attempt {attempt + 1}: Suspicious NULLs, retrying")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback)
                retry_count += 1
                continue

            # All checks passed
            logger.info(f"Semantic inspection passed after {retry_count} retries")
            # Update the result with the final SQL
            result.sql_generated = current_sql
            result.retry_count = retry_count
            return result, True, retry_count

        # Max retries exhausted
        logger.warning(f"Semantic inspection failed after {self.max_retries} attempts")
        result.retry_count = retry_count
        return result, False, retry_count

    async def _retry_with_feedback(
        self,
        nl_query: str,
        sql: str,
        feedback: str,
        schema: Optional[SchemaInfo] = None
    ) -> str:
        """Ask LLM to fix SQL based on semantic feedback with schema context.

        Args:
            nl_query: Original user query
            sql: Current SQL
            feedback: Semantic issue description (may include schema context)
            schema: Optional schema info for column reference

        Returns:
            Corrected SQL
        """
        # Include schema context if available for better correction
        schema_context = ""
        if schema:
            schema_context = self._format_schema_context(schema)

        prompt = f"""The following SQL query has an issue that needs correction.

Original question: {nl_query}

SQL query:
{sql}

Issue detected: {feedback}
{schema_context}
IMPORTANT: Use ONLY the exact column and table names from the schema above.
- Generate ANSI-compliant SQL (works across all databases)
- NO QUALIFY clause - use subquery with ROW_NUMBER() instead: SELECT * FROM (SELECT ..., ROW_NUMBER() OVER (...) as rn FROM ...) sub WHERE rn = 1
- Use COALESCE() for null handling (not IFNULL, NVL, or ISNULL)
- Use CASE WHEN for conditionals (not IF())
- Use STRING_AGG() for string concatenation (PostgreSQL standard)

Generate a corrected SQL query that addresses this issue.
Return ONLY the SQL query, no explanation or markdown.
"""
        try:
            response = await self._llm.acomplete(prompt)
            corrected_sql = response.text.strip()

            # Clean up response (remove markdown if present)
            corrected_sql = self._clean_sql_response(corrected_sql)

            logger.debug(f"LLM corrected SQL: {corrected_sql[:100]}...")
            return corrected_sql

        except Exception as e:
            logger.error(f"LLM correction failed: {e}")
            return sql  # Return original if correction fails

    def _clean_sql_response(self, response: str) -> str:
        """Clean LLM response to extract pure SQL.

        Args:
            response: LLM response text

        Returns:
            Clean SQL string
        """
        # Remove markdown code blocks
        if "```sql" in response:
            match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                return match.group(1).strip()

        if "```" in response:
            match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                return match.group(1).strip()

        return response.strip()

    def _columns_match_intent(
        self,
        nl_query: str,
        result: QueryResult
    ) -> bool:
        """Check if returned columns are relevant to the question.

        Args:
            nl_query: User's question
            result: Query result

        Returns:
            True if columns seem relevant
        """
        if not result.columns:
            return False

        # Extract terms from query
        query_terms = self._extract_terms(nl_query)

        # Extract terms from column names
        col_terms: Set[str] = set()
        for col in result.columns:
            col_name = col.name.lower().replace('_', ' ')
            col_terms.update(col_name.split())

        # Check for overlap
        overlap = query_terms & col_terms

        # Small result sets (5 or fewer columns) are usually OK
        if len(result.columns) <= 5:
            return True

        # At least some overlap expected for larger result sets
        return len(overlap) > 0

    def _has_suspicious_nulls(
        self,
        nl_query: str,
        result: QueryResult
    ) -> bool:
        """Detect if aggregations returned unexpected NULLs.

        Args:
            nl_query: User's question
            result: Query result

        Returns:
            True if suspicious NULLs detected
        """
        # Check if this is an aggregation query
        is_aggregation = any(kw in nl_query.lower() for kw in self.AGG_KEYWORDS)

        if not is_aggregation:
            return False

        if result.row_count != 1:
            return False

        # Single row with NULL values is suspicious for aggregation
        if result.data:
            row = result.data[0]
            null_count = sum(1 for v in row.values() if v is None)
            total_cols = len(row)

            # If more than half the columns are NULL, suspicious
            if total_cols > 0 and null_count / total_cols > 0.5:
                return True

        return False

    def _extract_terms(self, text: str) -> Set[str]:
        """Extract meaningful terms from text.

        Args:
            text: Text to extract terms from

        Returns:
            Set of lowercase terms
        """
        # Common stop words to ignore
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'of', 'to', 'for',
            'in', 'on', 'at', 'by', 'from', 'with', 'about', 'into',
            'and', 'or', 'but', 'if', 'so', 'as', 'what', 'which', 'who',
            'how', 'many', 'much', 'all', 'any', 'show', 'me', 'get',
            'find', 'give', 'tell', 'list', 'display', 'total', 'sum',
            'count', 'average', 'avg', 'max', 'min',
        }

        terms = set()
        for word in text.lower().split():
            word = ''.join(c for c in word if c.isalnum())
            if word and word not in stop_words and len(word) > 2:
                terms.add(word)

        return terms

    def _build_error_feedback(
        self,
        error_message: Optional[str],
        schema: Optional[SchemaInfo]
    ) -> str:
        """Build detailed error feedback with schema context for column/table errors.

        Args:
            error_message: Original error message from database
            schema: Schema info for context

        Returns:
            Enhanced error feedback string
        """
        if not error_message:
            return "Unknown SQL error occurred."

        feedback = f"SQL error: {error_message}"

        # Detect column-related errors
        column_error_patterns = [
            r'column ["\']?(\w+\.)?(\w+)["\']? does not exist',
            r'unknown column ["\']?(\w+\.)?(\w+)["\']?',
            r'no such column[: ]+["\']?(\w+\.)?(\w+)["\']?',
            r'column ["\']?(\w+)["\']? not found',
        ]

        # Detect table-related errors
        table_error_patterns = [
            r'relation ["\']?(\w+)["\']? does not exist',
            r'table ["\']?(\w+)["\']? doesn\'?t exist',
            r'unknown table ["\']?(\w+)["\']?',
            r'no such table[: ]+["\']?(\w+)["\']?',
        ]

        # Detect function errors (like GROUP_CONCAT vs STRING_AGG)
        function_error_patterns = [
            r'function (\w+)\([^)]*\) does not exist',
            r'unknown function[: ]+["\']?(\w+)["\']?',
        ]

        error_lower = error_message.lower()

        # Check for column errors and extract the bad column name
        for pattern in column_error_patterns:
            match = re.search(pattern, error_lower)
            if match:
                bad_column = match.group(2) if match.lastindex >= 2 else match.group(1)
                feedback += f"\n\nThe column '{bad_column}' does not exist in the database."
                if schema:
                    feedback += self._suggest_similar_columns(bad_column, schema)
                break

        # Check for table errors
        for pattern in table_error_patterns:
            match = re.search(pattern, error_lower)
            if match:
                bad_table = match.group(1)
                feedback += f"\n\nThe table '{bad_table}' does not exist in the database."
                if schema:
                    feedback += f"\n\nAvailable tables: {', '.join(t.name for t in schema.tables)}"
                break

        # Check for function errors (MySQL vs PostgreSQL syntax)
        for pattern in function_error_patterns:
            match = re.search(pattern, error_lower)
            if match:
                bad_func = match.group(1)
                feedback += f"\n\nThe function '{bad_func}' is not available in this database."
                # Provide common alternatives
                func_alternatives = {
                    'group_concat': 'STRING_AGG(column, delimiter) for PostgreSQL',
                    'concat_ws': 'CONCAT_WS(separator, val1, val2, ...) or use || operator',
                    'ifnull': 'COALESCE(value, default) for PostgreSQL',
                    'if': 'CASE WHEN condition THEN value1 ELSE value2 END',
                }
                if bad_func.lower() in func_alternatives:
                    feedback += f"\nUse: {func_alternatives[bad_func.lower()]}"
                break

        return feedback

    def _suggest_similar_columns(
        self,
        bad_column: str,
        schema: SchemaInfo
    ) -> str:
        """Suggest columns that might be what the user intended.

        Args:
            bad_column: The column name that caused the error
            schema: Database schema

        Returns:
            Suggestion string with similar columns
        """
        bad_column_lower = bad_column.lower().replace('_', '')
        suggestions = []

        for table in schema.tables:
            for col in table.columns:
                col_name_normalized = col.name.lower().replace('_', '')
                # Check for partial matches or similar names
                if (bad_column_lower in col_name_normalized or
                    col_name_normalized in bad_column_lower or
                    self._levenshtein_similar(bad_column_lower, col_name_normalized)):
                    suggestions.append(f"{table.name}.{col.name}")

        if suggestions:
            return f"\n\nDid you mean one of these columns?\n- " + "\n- ".join(suggestions[:5])
        return ""

    def _levenshtein_similar(self, s1: str, s2: str, threshold: int = 3) -> bool:
        """Check if two strings are similar using Levenshtein distance.

        Args:
            s1: First string
            s2: Second string
            threshold: Maximum edit distance to be considered similar

        Returns:
            True if strings are similar
        """
        if abs(len(s1) - len(s2)) > threshold:
            return False

        # Simple Levenshtein distance calculation
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if not s2:
            return len(s1) <= threshold

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1] <= threshold

    def _format_schema_context(self, schema: SchemaInfo) -> str:
        """Format schema information for inclusion in LLM prompt.

        Args:
            schema: Database schema

        Returns:
            Formatted schema string
        """
        lines = ["\n\nDatabase Schema (use EXACT column names):"]

        for table in schema.tables[:15]:  # Limit to first 15 tables
            col_list = ", ".join(c.name for c in table.columns)
            lines.append(f"\n{table.name}: {col_list}")

        return "\n".join(lines)

    def get_inspection_report(
        self,
        nl_query: str,
        result: QueryResult
    ) -> Dict[str, Any]:
        """Generate detailed inspection report for a result.

        Args:
            nl_query: User's question
            result: Query result

        Returns:
            Inspection report dict
        """
        report = {
            "success": result.success,
            "row_count": result.row_count,
            "checks": {}
        }

        if not result.success:
            report["checks"]["syntax"] = {
                "passed": False,
                "message": result.error_message
            }
            return report

        # Empty check
        report["checks"]["non_empty"] = {
            "passed": result.row_count > 0,
            "message": "Query returned results" if result.row_count > 0 else "No results"
        }

        # Row count check
        report["checks"]["row_count"] = {
            "passed": result.row_count <= self.max_acceptable_rows,
            "message": f"{result.row_count} rows" + (
                " (within limit)" if result.row_count <= self.max_acceptable_rows
                else " (exceeds limit)"
            )
        }

        # Column relevance check
        columns_match = self._columns_match_intent(nl_query, result)
        report["checks"]["column_relevance"] = {
            "passed": columns_match,
            "message": "Columns match intent" if columns_match else "Column mismatch detected"
        }

        # NULL check
        has_nulls = self._has_suspicious_nulls(nl_query, result)
        report["checks"]["null_check"] = {
            "passed": not has_nulls,
            "message": "No suspicious NULLs" if not has_nulls else "Suspicious NULL values"
        }

        # Overall
        all_passed = all(c["passed"] for c in report["checks"].values())
        report["all_passed"] = all_passed

        return report
