"""
Natural Language Response Generator for SQL Chat.

Generates human-readable explanations of SQL query results.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from llama_index.core.llms.llm import LLM

if TYPE_CHECKING:
    from dbnotebook.core.observability.query_logger import QueryLogger

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate natural language explanations from SQL query results.

    Converts raw query results into conversational responses that
    directly answer the user's original question.
    """

    MAX_ROWS_FOR_CONTEXT = 20  # Limit rows sent to LLM
    MAX_CELL_LENGTH = 100      # Truncate long cell values

    def __init__(self, llm: LLM):
        """Initialize response generator.

        Args:
            llm: LlamaIndex LLM instance
        """
        self._llm = llm

    def generate(
        self,
        user_query: str,
        sql: str,
        data: List[Dict[str, Any]],
        columns: List[str],
        row_count: int,
        error_message: Optional[str] = None,
        query_logger: Optional["QueryLogger"] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Generate natural language explanation of query results.

        Args:
            user_query: Original user question
            sql: Generated SQL query
            data: Query result data (list of dicts)
            columns: Column names
            row_count: Total row count
            error_message: Error message if query failed
            query_logger: Optional query logger for metrics tracking
            user_id: Optional user ID for metrics
            session_id: Optional session ID for metrics

        Returns:
            Natural language explanation
        """
        if error_message:
            return self._generate_error_response(user_query, error_message)

        if not data or row_count == 0:
            return self._generate_empty_response(user_query, sql)

        # Prepare data summary for LLM
        data_summary = self._prepare_data_summary(data, columns, row_count)

        prompt = f"""You are a helpful data analyst assistant. A user asked a question about their database, and I executed a SQL query to answer it.

User's Question: {user_query}

SQL Query Executed:
{sql}

Query Results ({row_count} row{'s' if row_count != 1 else ''} returned):
{data_summary}

Based on these results, provide a clear, conversational answer to the user's question. Be concise but complete:
- Directly answer their question first
- Include the key numbers/facts from the results
- If there are multiple results, summarize the main findings
- Use natural language, not technical jargon
- Do NOT mention the SQL query or technical details
- Do NOT say "based on the query results" - just answer naturally

Answer:"""

        try:
            start_time = time.time()
            response = self._llm.complete(prompt)
            response_time_ms = int((time.time() - start_time) * 1000)
            explanation = response.text.strip()

            # Log query metrics
            if query_logger:
                try:
                    from dbnotebook.core.observability.token_counter import get_token_counter
                    token_counter = get_token_counter()
                    prompt_tokens = token_counter.count_tokens(prompt)
                    completion_tokens = token_counter.count_tokens(explanation)
                    model_name = self._llm.model if hasattr(self._llm, 'model') else 'unknown'

                    query_logger.log_query(
                        notebook_id=session_id or "sql-chat",
                        user_id=user_id or "sql-chat-system",
                        query_text=f"[SQL Chat Response Generation]",
                        model_name=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        response_time_ms=response_time_ms
                    )
                except Exception as log_err:
                    logger.warning(f"Failed to log SQL response generation metrics: {log_err}")

            # Clean up any preamble
            explanation = self._clean_response(explanation)

            return explanation

        except Exception as e:
            logger.warning(f"Failed to generate NL response: {e}")
            # Fallback to simple response
            return self._generate_fallback_response(data, columns, row_count)

    def _prepare_data_summary(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        row_count: int
    ) -> str:
        """Prepare data summary for LLM context.

        Args:
            data: Query result data
            columns: Column names
            row_count: Total rows

        Returns:
            Formatted data summary string
        """
        # Limit rows for context
        sample_data = data[:self.MAX_ROWS_FOR_CONTEXT]

        if len(columns) == 1 and row_count == 1:
            # Single value result - return directly
            key = columns[0]
            value = sample_data[0].get(key, "N/A")
            return f"{key}: {value}"

        # Format as markdown table for readability
        lines = []

        # Header
        header = " | ".join(str(col) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for row in sample_data:
            values = []
            for col in columns:
                val = row.get(col, "")
                # Truncate long values
                val_str = str(val) if val is not None else "NULL"
                if len(val_str) > self.MAX_CELL_LENGTH:
                    val_str = val_str[:self.MAX_CELL_LENGTH] + "..."
                values.append(val_str)
            lines.append(" | ".join(values))

        if row_count > self.MAX_ROWS_FOR_CONTEXT:
            lines.append(f"... and {row_count - self.MAX_ROWS_FOR_CONTEXT} more rows")

        return "\n".join(lines)

    def _generate_error_response(self, user_query: str, error: str) -> str:
        """Generate response for failed queries.

        Args:
            user_query: Original question
            error: Error message

        Returns:
            User-friendly error explanation
        """
        return f"I couldn't answer your question due to an error: {error}. Please try rephrasing your question."

    def _generate_empty_response(self, user_query: str, sql: str) -> str:
        """Generate response for queries with no results.

        Args:
            user_query: Original question
            sql: Generated SQL

        Returns:
            User-friendly empty result message
        """
        return "No results were found matching your query. The data might not exist, or you may want to try a broader search."

    def _generate_fallback_response(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        row_count: int
    ) -> str:
        """Generate simple fallback response when LLM fails.

        Args:
            data: Query result data
            columns: Column names
            row_count: Total rows

        Returns:
            Simple summary
        """
        if row_count == 1 and len(columns) == 1:
            # Single value
            key = columns[0]
            value = data[0].get(key, "N/A")
            return f"The result is {value}."

        if row_count == 1:
            # Single row, multiple columns
            parts = [f"{col}: {data[0].get(col, 'N/A')}" for col in columns[:5]]
            return "Found: " + ", ".join(parts)

        return f"Found {row_count} results."

    def _clean_response(self, response: str) -> str:
        """Clean up LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Cleaned response
        """
        # Remove common preambles
        prefixes_to_remove = [
            "Based on the query results,",
            "Based on the results,",
            "According to the data,",
            "The query shows that",
            "The results show that",
            "Here's what I found:",
            "Answer:",
        ]

        cleaned = response
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()

        return cleaned
