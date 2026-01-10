"""
Query Learner for SQL Chat.

Learns from successful queries to improve future accuracy.
Saves successful queries as few-shot examples and extracts
JOIN patterns for schema enhancement.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from dbnotebook.core.db import DatabaseManager
from dbnotebook.core.sql_chat.types import QueryResult, SchemaInfo, SQLChatSession

logger = logging.getLogger(__name__)


@dataclass
class JoinPattern:
    """Represents a learned JOIN pattern."""
    table1: str
    column1: str
    table2: str
    column2: str
    join_type: str  # INNER, LEFT, RIGHT
    usage_count: int = 1
    last_used: Optional[datetime] = None


@dataclass
class LearnedQuery:
    """Represents a learned successful query."""
    question: str
    sql: str
    connection_id: str
    tables_used: List[str]
    complexity: str  # basic, joins, aggregation, subqueries, window
    domain: Optional[str] = None
    created_at: Optional[datetime] = None


class QueryLearner:
    """Learn from successful queries to improve SQL generation.

    Features:
    - Records successful queries as few-shot examples
    - Extracts and saves JOIN patterns
    - Detects query complexity and domain
    - Appends examples to Dictionary notebooks
    """

    # Complexity levels
    COMPLEXITY_BASIC = "basic"
    COMPLEXITY_JOINS = "joins"
    COMPLEXITY_AGGREGATION = "aggregation"
    COMPLEXITY_SUBQUERIES = "subqueries"
    COMPLEXITY_WINDOW = "window"

    def __init__(
        self,
        db_manager: DatabaseManager,
        notebook_manager=None
    ):
        """Initialize query learner.

        Args:
            db_manager: Database manager for storing learned patterns
            notebook_manager: Optional notebook manager for appending to dictionaries
        """
        self._db_manager = db_manager
        self._notebook_manager = notebook_manager

        # In-memory cache of learned patterns
        self._join_patterns: Dict[str, List[JoinPattern]] = {}  # connection_id -> patterns
        self._learned_queries: List[LearnedQuery] = []

    def record_success(
        self,
        session: SQLChatSession,
        query: str,
        sql: str,
        result: QueryResult
    ) -> None:
        """Record a successful query for learning.

        Args:
            session: SQL chat session
            query: Natural language query
            sql: Generated SQL that succeeded
            result: Query result
        """
        if not result.success or result.row_count == 0:
            return

        # Extract information
        tables = self._extract_tables(sql)
        complexity = self._assess_complexity(sql)
        domain = self._detect_domain(session.schema) if session.schema else None
        joins = self._extract_joins(sql)

        # Create learned query record
        learned = LearnedQuery(
            question=query,
            sql=sql,
            connection_id=session.connection_id,
            tables_used=tables,
            complexity=complexity,
            domain=domain,
            created_at=datetime.utcnow()
        )

        self._learned_queries.append(learned)

        # Update JOIN patterns
        if joins:
            self._update_join_patterns(session.connection_id, joins)

        # Persist to database
        self._save_learned_query(learned)

        # Append to Dictionary notebook if available
        if self._notebook_manager and hasattr(session, 'notebook_id') and session.notebook_id:
            self._append_to_dictionary(session.notebook_id, query, sql, result)

        logger.info(f"Recorded successful query: complexity={complexity}, tables={len(tables)}")

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL.

        Args:
            sql: SQL query

        Returns:
            List of table names
        """
        sql_lower = sql.lower()
        tables = set()

        # FROM clause
        from_match = re.findall(r'from\s+(\w+)', sql_lower)
        tables.update(from_match)

        # JOIN clauses
        join_match = re.findall(r'join\s+(\w+)', sql_lower)
        tables.update(join_match)

        return list(tables)

    def _assess_complexity(self, sql: str) -> str:
        """Assess complexity level of SQL query.

        Args:
            sql: SQL query

        Returns:
            Complexity level string
        """
        sql_lower = sql.lower()

        # Check for window functions
        if re.search(r'over\s*\(', sql_lower):
            return self.COMPLEXITY_WINDOW

        # Check for subqueries
        if sql_lower.count('select') > 1:
            return self.COMPLEXITY_SUBQUERIES

        # Check for aggregations
        agg_functions = ['count(', 'sum(', 'avg(', 'min(', 'max(', 'group by']
        if any(agg in sql_lower for agg in agg_functions):
            return self.COMPLEXITY_AGGREGATION

        # Check for joins
        if 'join' in sql_lower:
            return self.COMPLEXITY_JOINS

        return self.COMPLEXITY_BASIC

    def _detect_domain(self, schema: SchemaInfo) -> Optional[str]:
        """Detect domain from schema table names.

        Args:
            schema: Database schema

        Returns:
            Domain string or None
        """
        table_names = ' '.join(t.name.lower() for t in schema.tables)

        # Domain detection based on table names
        domain_keywords = {
            'ecommerce': ['order', 'product', 'cart', 'customer', 'payment', 'shipping'],
            'finance': ['transaction', 'account', 'balance', 'ledger', 'payment', 'invoice'],
            'healthcare': ['patient', 'doctor', 'appointment', 'diagnosis', 'prescription'],
            'hr': ['employee', 'department', 'salary', 'leave', 'attendance', 'payroll'],
            'education': ['student', 'course', 'grade', 'enrollment', 'teacher'],
            'social': ['user', 'post', 'comment', 'like', 'follow', 'message'],
        }

        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in table_names)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)

        return None

    def _extract_joins(self, sql: str) -> List[JoinPattern]:
        """Extract JOIN patterns from SQL.

        Args:
            sql: SQL query

        Returns:
            List of JoinPattern objects
        """
        patterns = []

        # Pattern: JOIN table ON table1.col1 = table2.col2
        join_pattern = re.compile(
            r'((?:inner|left|right|full)\s+)?join\s+(\w+)(?:\s+(?:as\s+)?(\w+))?\s+on\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)',
            re.IGNORECASE
        )

        for match in join_pattern.finditer(sql):
            join_type = (match.group(1) or 'inner').strip().upper()
            # table2 is the joined table
            table2 = match.group(2)
            # Parse ON condition
            left_table = match.group(4)
            left_col = match.group(5)
            right_table = match.group(6)
            right_col = match.group(7)

            patterns.append(JoinPattern(
                table1=left_table,
                column1=left_col,
                table2=right_table,
                column2=right_col,
                join_type=join_type,
                last_used=datetime.utcnow()
            ))

        return patterns

    def _update_join_patterns(
        self,
        connection_id: str,
        new_patterns: List[JoinPattern]
    ) -> None:
        """Update stored JOIN patterns with new observations.

        Args:
            connection_id: Connection ID
            new_patterns: New JOIN patterns found
        """
        if connection_id not in self._join_patterns:
            self._join_patterns[connection_id] = []

        existing = self._join_patterns[connection_id]

        for new_pattern in new_patterns:
            # Check if pattern already exists
            found = False
            for existing_pattern in existing:
                if (
                    existing_pattern.table1 == new_pattern.table1 and
                    existing_pattern.column1 == new_pattern.column1 and
                    existing_pattern.table2 == new_pattern.table2 and
                    existing_pattern.column2 == new_pattern.column2
                ):
                    existing_pattern.usage_count += 1
                    existing_pattern.last_used = datetime.utcnow()
                    found = True
                    break

            if not found:
                existing.append(new_pattern)

    def _save_learned_query(self, learned: LearnedQuery) -> None:
        """Save learned query to database.

        Args:
            learned: Learned query to save
        """
        # TODO: Implement database persistence
        # For now, queries are kept in memory
        pass

    def _append_to_dictionary(
        self,
        notebook_id: str,
        query: str,
        sql: str,
        result: QueryResult
    ) -> None:
        """Append successful query as example to Dictionary notebook.

        Args:
            notebook_id: Dictionary notebook ID
            query: Natural language query
            sql: Generated SQL
            result: Query result
        """
        if not self._notebook_manager:
            return

        # Format as Markdown example
        example_md = f"""
## Query Example

**Question**: {query}

**SQL**:
```sql
{sql}
```

**Result**: {result.row_count} rows returned

---
"""

        # TODO: Implement append to notebook source
        # This requires updating the Dictionary document and re-indexing
        logger.debug(f"Would append query example to notebook {notebook_id}")

    def get_join_patterns(
        self,
        connection_id: str
    ) -> List[JoinPattern]:
        """Get learned JOIN patterns for a connection.

        Args:
            connection_id: Connection ID

        Returns:
            List of JOIN patterns sorted by usage
        """
        patterns = self._join_patterns.get(connection_id, [])
        return sorted(patterns, key=lambda p: p.usage_count, reverse=True)

    def get_similar_queries(
        self,
        query: str,
        connection_id: Optional[str] = None,
        limit: int = 5
    ) -> List[LearnedQuery]:
        """Get similar previously successful queries.

        Args:
            query: Current query
            connection_id: Optional filter by connection
            limit: Maximum results

        Returns:
            List of similar learned queries
        """
        # Simple keyword matching for now
        # TODO: Use embedding similarity
        query_words = set(query.lower().split())

        scored = []
        for learned in self._learned_queries:
            if connection_id and learned.connection_id != connection_id:
                continue

            learned_words = set(learned.question.lower().split())
            overlap = len(query_words & learned_words)
            if overlap > 0:
                scored.append((learned, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored[:limit]]

    def format_join_hints(
        self,
        connection_id: str,
        tables: List[str]
    ) -> str:
        """Format JOIN hints for given tables based on learned patterns.

        Args:
            connection_id: Connection ID
            tables: Tables being used in query

        Returns:
            Formatted JOIN hints string
        """
        patterns = self.get_join_patterns(connection_id)
        if not patterns:
            return ""

        tables_lower = {t.lower() for t in tables}
        relevant_patterns = []

        for pattern in patterns:
            if pattern.table1.lower() in tables_lower or pattern.table2.lower() in tables_lower:
                relevant_patterns.append(pattern)

        if not relevant_patterns:
            return ""

        hints = ["Learned JOIN patterns:"]
        for p in relevant_patterns[:5]:
            hints.append(f"  - {p.table1}.{p.column1} = {p.table2}.{p.column2} ({p.join_type}, used {p.usage_count}x)")

        return "\n".join(hints)

    def clear_cache(self, connection_id: Optional[str] = None) -> None:
        """Clear learned patterns cache.

        Args:
            connection_id: Specific connection to clear, or None for all
        """
        if connection_id:
            self._join_patterns.pop(connection_id, None)
            self._learned_queries = [
                q for q in self._learned_queries
                if q.connection_id != connection_id
            ]
        else:
            self._join_patterns.clear()
            self._learned_queries.clear()
