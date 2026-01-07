"""
SQL Chat Memory for Multi-turn Conversations.

Maintains conversation context for query refinement and follow-up questions.
Enables chat-based modifications like "filter by last month".
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dbnotebook.core.sql_chat.types import QueryResult

logger = logging.getLogger(__name__)


@dataclass
class SQLExchange:
    """A single query/response exchange."""
    user_query: str
    sql: str
    result_summary: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)


class SQLChatMemory:
    """Multi-turn conversation memory for SQL chat.

    Maintains history of user queries, generated SQL, and result summaries
    to enable:
    - Query refinement ("filter by last month")
    - Follow-up questions ("show me just the top 5")
    - Context-aware SQL generation
    """

    # Keywords that indicate a follow-up/refinement
    FOLLOW_UP_INDICATORS = [
        "filter", "but", "only", "just", "also", "add",
        "remove", "change", "modify", "exclude", "include",
        "sort", "order", "limit", "group", "show me",
        "what about", "how about", "instead", "without",
        "last", "previous", "same", "that", "those",
        "more", "less", "fewer", "greater", "above", "below",
    ]

    def __init__(self, max_history: int = 10):
        """Initialize SQL chat memory.

        Args:
            max_history: Maximum exchanges to retain
        """
        self._history: List[SQLExchange] = []
        self._max_history = max_history

    def add_exchange(
        self,
        user_query: str,
        sql: str,
        result: Optional[QueryResult] = None
    ) -> None:
        """Add a query/response exchange to history.

        Args:
            user_query: User's natural language query
            sql: Generated SQL
            result: Query result (optional)
        """
        result_summary = ""
        row_count = 0
        columns = []

        if result:
            row_count = result.row_count
            columns = [c.name for c in result.columns]
            if result.success:
                result_summary = f"Returned {row_count} rows with columns: {', '.join(columns)}"
            else:
                result_summary = f"Error: {result.error_message}"

        exchange = SQLExchange(
            user_query=user_query,
            sql=sql,
            result_summary=result_summary,
            row_count=row_count,
            columns=columns,
        )

        self._history.append(exchange)

        # Trim to max history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug(f"Added exchange to memory, history size: {len(self._history)}")

    def get_context_string(self, limit: int = 5) -> str:
        """Get conversation context as string for LLM prompt.

        Args:
            limit: Maximum exchanges to include

        Returns:
            Formatted context string
        """
        if not self._history:
            return ""

        recent = self._history[-limit:]
        lines = ["Previous conversation:"]

        for i, exchange in enumerate(recent, 1):
            lines.append(f"\n[{i}] User: {exchange.user_query}")
            lines.append(f"    SQL: {exchange.sql}")
            lines.append(f"    Result: {exchange.result_summary}")

        return "\n".join(lines)

    def get_last_sql(self) -> Optional[str]:
        """Get the most recent generated SQL.

        Returns:
            Last SQL query or None
        """
        if self._history:
            return self._history[-1].sql
        return None

    def get_last_query(self) -> Optional[str]:
        """Get the most recent user query.

        Returns:
            Last user query or None
        """
        if self._history:
            return self._history[-1].user_query
        return None

    def get_last_columns(self) -> List[str]:
        """Get columns from the most recent result.

        Returns:
            List of column names
        """
        if self._history:
            return self._history[-1].columns
        return []

    def is_follow_up(self, query: str) -> bool:
        """Detect if query is a follow-up/refinement.

        Args:
            query: User's query

        Returns:
            True if this appears to be a follow-up
        """
        if not self._history:
            return False

        query_lower = query.lower()

        # Check for follow-up indicators
        for indicator in self.FOLLOW_UP_INDICATORS:
            if indicator in query_lower:
                return True

        # Check for short queries (likely refinements)
        word_count = len(query.split())
        if word_count <= 5 and self._history:
            return True

        # Check for pronoun references
        pronouns = ["it", "them", "this", "that", "those", "these"]
        if any(p in query_lower.split() for p in pronouns):
            return True

        return False

    def get_refinement_context(self, new_query: str) -> Tuple[str, str]:
        """Get context for refining the previous query.

        Args:
            new_query: New user query

        Returns:
            Tuple of (previous_sql, refinement_instruction)
        """
        if not self._history:
            return "", new_query

        last = self._history[-1]

        refinement_context = f"""
Previous query: {last.user_query}
Previous SQL: {last.sql}
Previous result: {last.result_summary}

User's refinement request: {new_query}

Generate a modified SQL query that applies the user's refinement to the previous query.
"""
        return last.sql, refinement_context

    def clear(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        logger.debug("SQL chat memory cleared")

    def get_history(self) -> List[SQLExchange]:
        """Get full conversation history.

        Returns:
            List of exchanges
        """
        return list(self._history)

    def get_history_summary(self) -> Dict:
        """Get summary of conversation history.

        Returns:
            Summary dict
        """
        return {
            "exchange_count": len(self._history),
            "queries": [e.user_query for e in self._history],
            "total_rows_returned": sum(e.row_count for e in self._history),
        }
