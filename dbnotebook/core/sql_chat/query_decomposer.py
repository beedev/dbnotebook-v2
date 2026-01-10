"""
Query Decomposer for SQL Chat.

Decomposes complex natural language queries into simpler sub-questions
that can each be answered with SQL. The results are then combined
using CTEs (Common Table Expressions).

This approach improves accuracy for complex queries like:
- Comparisons (X vs Y)
- Time-based analysis (before/after, trends)
- Multi-step aggregations
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from llama_index.core.llms.llm import LLM

from dbnotebook.core.sql_chat.types import SchemaInfo

logger = logging.getLogger(__name__)


@dataclass
class SubQuery:
    """Represents a decomposed sub-question."""
    id: int
    question: str
    depends_on: List[int] = field(default_factory=list)
    sql: Optional[str] = None
    cte_name: Optional[str] = None
    original_question: Optional[str] = None


class QueryDecomposer:
    """Decompose complex queries into simpler sub-questions.

    Detects complexity triggers and breaks queries into CTEs that
    can be executed and combined for better accuracy.

    Complexity triggers:
    - Comparisons: "vs", "versus", "compare", "difference between"
    - Time analysis: "over time", "trend", "before and after"
    - Multi-grouping: "by X and Y", "grouped by multiple"
    - Segmentation: "new vs returning", "top vs bottom"
    """

    # Complexity trigger patterns
    COMPLEXITY_TRIGGERS = [
        # Comparisons
        r'\bvs\.?\b',
        r'\bversus\b',
        r'\bcompare\b',
        r'\bdifference between\b',
        r'\bcompared to\b',

        # Time analysis
        r'\bover time\b',
        r'\btrend\b',
        r'\bbefore and after\b',
        r'\bgrowth\b',
        r'\bchange over\b',
        r'\bmonth over month\b',
        r'\byear over year\b',

        # Multi-grouping
        r'\bby .+ and .+\b',
        r'\bgrouped by multiple\b',
        r'\bbreakdown by\b',

        # Segmentation
        r'\bnew vs\.? returning\b',
        r'\btop .+ vs\.? bottom\b',
        r'\bhigh vs\.? low\b',
        r'\bfirst .+ vs\.? repeat\b',
    ]

    def __init__(self, llm: LLM):
        """Initialize query decomposer.

        Args:
            llm: Language model for decomposition
        """
        self._llm = llm
        self._compiled_triggers = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.COMPLEXITY_TRIGGERS
        ]

    def is_complex(self, query: str) -> bool:
        """Detect if query needs decomposition.

        Args:
            query: Natural language query

        Returns:
            True if query is complex and should be decomposed
        """
        for pattern in self._compiled_triggers:
            if pattern.search(query):
                logger.debug(f"Complexity trigger found: {pattern.pattern}")
                return True
        return False

    def decompose(
        self,
        query: str,
        schema: SchemaInfo,
        max_sub_queries: int = 5
    ) -> List[SubQuery]:
        """Break complex query into sub-questions.

        Args:
            query: Natural language query
            schema: Database schema for context
            max_sub_queries: Maximum number of sub-queries to generate

        Returns:
            List of SubQuery objects with dependencies
        """
        # Build prompt for decomposition
        table_list = ", ".join(t.name for t in schema.tables[:20])

        prompt = f"""Break this complex question into simpler sub-questions that can each be answered with a single SQL query.

**Question**: {query}

**Available tables**: {table_list}

**Instructions**:
1. Identify the logical steps needed to answer the question
2. Create sub-questions that each produce a clear result
3. Order sub-questions so dependencies come first
4. Use clear, specific questions that map to SQL operations

**Output format** (JSON array):
[
  {{"id": 1, "question": "First sub-question", "depends_on": []}},
  {{"id": 2, "question": "Second sub-question that uses result of #1", "depends_on": [1]}},
  ...
]

Only output the JSON array, no other text."""

        try:
            response = self._llm.complete(prompt)
            sub_queries = self._parse_decomposition(response.text, query)

            # Limit number of sub-queries
            if len(sub_queries) > max_sub_queries:
                logger.warning(f"Truncating {len(sub_queries)} sub-queries to {max_sub_queries}")
                sub_queries = sub_queries[:max_sub_queries]

            logger.info(f"Decomposed query into {len(sub_queries)} sub-questions")
            return sub_queries

        except Exception as e:
            logger.error(f"Query decomposition failed: {e}")
            # Return single sub-query with original question
            return [SubQuery(
                id=1,
                question=query,
                depends_on=[],
                original_question=query
            )]

    def _parse_decomposition(
        self,
        response_text: str,
        original_query: str
    ) -> List[SubQuery]:
        """Parse LLM decomposition response.

        Args:
            response_text: LLM response text
            original_query: Original user query

        Returns:
            List of SubQuery objects
        """
        # Extract JSON array from response
        text = response_text.strip()

        # Try to find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', text)
        if not json_match:
            logger.warning("No JSON array found in decomposition response")
            return [SubQuery(id=1, question=original_query, depends_on=[], original_question=original_query)]

        try:
            parsed = json.loads(json_match.group())

            sub_queries = []
            for item in parsed:
                sq = SubQuery(
                    id=item.get('id', len(sub_queries) + 1),
                    question=item.get('question', ''),
                    depends_on=item.get('depends_on', []),
                    original_question=original_query
                )
                # Generate CTE name
                sq.cte_name = f"sq_{sq.id}"
                sub_queries.append(sq)

            return sub_queries

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse decomposition JSON: {e}")
            return [SubQuery(id=1, question=original_query, depends_on=[], original_question=original_query)]

    def combine_into_cte(
        self,
        sub_queries: List[SubQuery],
        final_columns: Optional[List[str]] = None
    ) -> str:
        """Combine sub-query SQLs into final CTE-based query.

        Args:
            sub_queries: Sub-queries with SQL populated
            final_columns: Optional specific columns for final SELECT

        Returns:
            Combined SQL with CTEs
        """
        if not sub_queries:
            return ""

        # Filter out sub-queries without SQL
        with_sql = [sq for sq in sub_queries if sq.sql]
        if not with_sql:
            return ""

        if len(with_sql) == 1:
            # Single query, no need for CTE
            return with_sql[0].sql

        # Build CTE structure
        cte_parts = []
        for sq in with_sql[:-1]:  # All but last become CTEs
            cte_name = sq.cte_name or f"sq_{sq.id}"
            # Clean SQL (remove trailing semicolon)
            sql = sq.sql.strip().rstrip(';')
            cte_parts.append(f"{cte_name} AS (\n    {sql}\n)")

        # Build final query
        cte_section = "WITH " + ",\n".join(cte_parts)

        # Last sub-query is the main query
        final_sq = with_sql[-1]
        final_sql = final_sq.sql.strip().rstrip(';')

        return f"{cte_section}\n{final_sql}"

    def generate_combination_query(
        self,
        sub_queries: List[SubQuery],
        original_query: str
    ) -> str:
        """Generate SQL to combine sub-query results.

        Uses LLM to create the final combining SELECT.

        Args:
            sub_queries: Sub-queries with SQL populated
            original_query: Original user question

        Returns:
            Final combining SQL query
        """
        if not sub_queries:
            return ""

        # Build CTE descriptions
        cte_descriptions = []
        for sq in sub_queries:
            if sq.sql:
                cte_descriptions.append(f"- {sq.cte_name}: {sq.question}")

        prompt = f"""Given these CTEs (Common Table Expressions), write a final SELECT query that answers the original question.

**Original question**: {original_query}

**Available CTEs**:
{chr(10).join(cte_descriptions)}

**Instructions**:
1. Combine the CTEs to answer the original question
2. Use appropriate JOINs, UNIONs, or subqueries as needed
3. Output ONLY the SELECT query (the CTEs are already defined)

**Output**: Just the SELECT statement, no explanations."""

        try:
            response = self._llm.complete(prompt)
            final_sql = response.text.strip()

            # Clean up
            if final_sql.lower().startswith('select'):
                return final_sql
            else:
                # Try to extract SELECT from response
                select_match = re.search(r'SELECT[\s\S]+', final_sql, re.IGNORECASE)
                if select_match:
                    return select_match.group()

            logger.warning("Could not extract final SELECT from combination response")
            return ""

        except Exception as e:
            logger.error(f"Failed to generate combination query: {e}")
            return ""

    def get_execution_order(self, sub_queries: List[SubQuery]) -> List[int]:
        """Get execution order respecting dependencies.

        Args:
            sub_queries: List of sub-queries

        Returns:
            List of sub-query IDs in execution order
        """
        # Topological sort
        executed = set()
        order = []

        sq_map = {sq.id: sq for sq in sub_queries}

        def can_execute(sq: SubQuery) -> bool:
            return all(dep in executed for dep in sq.depends_on)

        while len(order) < len(sub_queries):
            made_progress = False
            for sq in sub_queries:
                if sq.id not in executed and can_execute(sq):
                    order.append(sq.id)
                    executed.add(sq.id)
                    made_progress = True

            if not made_progress:
                # Circular dependency - add remaining in order
                logger.warning("Circular dependency detected in sub-queries")
                for sq in sub_queries:
                    if sq.id not in executed:
                        order.append(sq.id)
                        executed.add(sq.id)
                break

        return order

    def format_for_display(self, sub_queries: List[SubQuery]) -> str:
        """Format sub-queries for user display.

        Args:
            sub_queries: List of sub-queries

        Returns:
            Formatted string for display
        """
        lines = ["**Query Decomposition:**", ""]

        for sq in sub_queries:
            deps = f" (depends on: {sq.depends_on})" if sq.depends_on else ""
            lines.append(f"{sq.id}. {sq.question}{deps}")

        return "\n".join(lines)
