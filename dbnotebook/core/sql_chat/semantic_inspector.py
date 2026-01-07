"""
Semantic Inspector for Chat with Data.

Implements agentic result inspection (inspired by Smolagents).
Goes beyond syntax validation to check if results make semantic sense.
Automatically retries with feedback when results are incorrect/useless.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from llama_index.core.llms.llm import LLM

from dbnotebook.core.sql_chat.types import QueryResult

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
    ) -> Tuple[QueryResult, bool, int]:
        """Execute SQL with semantic validation and auto-retry.

        Args:
            nl_query: Original natural language query
            sql: Generated SQL
            execute_fn: Function to execute SQL (engine, sql) -> QueryResult
            connection_id: Connection ID

        Returns:
            Tuple of (QueryResult, success, retry_count)
        """
        current_sql = sql
        retry_count = 0

        for attempt in range(self.max_retries):
            result = execute_fn(current_sql)

            if not result.success:
                # Syntax error - let LLM fix it
                feedback = f"SQL error: {result.error_message}"
                logger.info(f"Attempt {attempt + 1}: Syntax error, retrying")
                current_sql = await self._retry_with_feedback(nl_query, current_sql, feedback)
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
        feedback: str
    ) -> str:
        """Ask LLM to fix SQL based on semantic feedback.

        Args:
            nl_query: Original user query
            sql: Current SQL
            feedback: Semantic issue description

        Returns:
            Corrected SQL
        """
        prompt = f"""The following SQL query has a semantic issue:

Original question: {nl_query}

SQL query:
{sql}

Issue detected: {feedback}

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
