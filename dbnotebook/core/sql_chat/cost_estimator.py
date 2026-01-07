"""
Query Cost Estimation for Chat with Data.

Uses EXPLAIN to estimate query cost before execution.
Prevents expensive queries from running unexpectedly.
"""

import json
import logging
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from dbnotebook.core.sql_chat.types import CostEstimate

logger = logging.getLogger(__name__)


class QueryCostEstimator:
    """Estimate query cost before execution using EXPLAIN.

    Provides:
    - Cost estimation from query plan
    - Row count estimation
    - Sequential scan detection
    - Cartesian join detection
    - Safety thresholds for blocking expensive queries
    """

    # Default thresholds
    MAX_ESTIMATED_ROWS = 100000
    MAX_COST = 50000  # PostgreSQL cost units

    def __init__(
        self,
        max_estimated_rows: int = 100000,
        max_cost: float = 50000
    ):
        """Initialize cost estimator.

        Args:
            max_estimated_rows: Maximum acceptable estimated rows
            max_cost: Maximum acceptable cost units
        """
        self.max_estimated_rows = max_estimated_rows
        self.max_cost = max_cost

    def estimate(
        self,
        engine: Engine,
        sql: str
    ) -> Optional[CostEstimate]:
        """Run EXPLAIN and parse cost metrics.

        Args:
            engine: SQLAlchemy engine
            sql: SQL query to analyze

        Returns:
            CostEstimate or None if estimation fails
        """
        dialect = engine.dialect.name

        try:
            if dialect == 'postgresql':
                return self._estimate_postgresql(engine, sql)
            elif dialect == 'mysql':
                return self._estimate_mysql(engine, sql)
            elif dialect == 'sqlite':
                return self._estimate_sqlite(engine, sql)
            else:
                logger.warning(f"Cost estimation not supported for {dialect}")
                return None
        except Exception as e:
            logger.warning(f"Cost estimation failed: {e}")
            return None

    def _estimate_postgresql(
        self,
        engine: Engine,
        sql: str
    ) -> Optional[CostEstimate]:
        """Estimate cost for PostgreSQL using EXPLAIN (FORMAT JSON).

        Args:
            engine: SQLAlchemy engine
            sql: SQL query

        Returns:
            CostEstimate
        """
        explain_sql = f"EXPLAIN (FORMAT JSON) {sql}"

        with engine.connect() as conn:
            result = conn.execute(text(explain_sql))
            row = result.fetchone()
            if not row:
                return None

            # Parse JSON plan
            plan_data = row[0]
            if isinstance(plan_data, str):
                plan_data = json.loads(plan_data)

            plan = plan_data[0]["Plan"]

            return CostEstimate(
                total_cost=plan.get("Total Cost", 0),
                estimated_rows=int(plan.get("Plan Rows", 0)),
                has_seq_scan=self._check_seq_scan_pg(plan),
                has_cartesian=self._check_cartesian_pg(plan),
                plan_json=plan,
            )

    def _estimate_mysql(
        self,
        engine: Engine,
        sql: str
    ) -> Optional[CostEstimate]:
        """Estimate cost for MySQL using EXPLAIN.

        Args:
            engine: SQLAlchemy engine
            sql: SQL query

        Returns:
            CostEstimate
        """
        explain_sql = f"EXPLAIN {sql}"

        with engine.connect() as conn:
            result = conn.execute(text(explain_sql))
            rows = result.fetchall()
            if not rows:
                return None

            # Sum up estimated rows from all table accesses
            total_rows = 0
            has_seq_scan = False
            has_cartesian = False

            for row in rows:
                # EXPLAIN columns: id, select_type, table, type, possible_keys, key, key_len, ref, rows, Extra
                row_dict = row._asdict() if hasattr(row, '_asdict') else dict(row)

                rows_estimate = row_dict.get('rows', 0) or 0
                total_rows += int(rows_estimate)

                # Check for full table scan (type = ALL)
                access_type = row_dict.get('type', '')
                if access_type == 'ALL':
                    has_seq_scan = True

                # Check for cartesian (no ref and multiple tables)
                if row_dict.get('ref') is None and len(rows) > 1:
                    has_cartesian = True

            # MySQL doesn't provide cost units like PostgreSQL
            # Estimate cost based on rows
            estimated_cost = total_rows * 0.01

            return CostEstimate(
                total_cost=estimated_cost,
                estimated_rows=total_rows,
                has_seq_scan=has_seq_scan,
                has_cartesian=has_cartesian,
            )

    def _estimate_sqlite(
        self,
        engine: Engine,
        sql: str
    ) -> Optional[CostEstimate]:
        """Estimate cost for SQLite using EXPLAIN QUERY PLAN.

        Args:
            engine: SQLAlchemy engine
            sql: SQL query

        Returns:
            CostEstimate (limited info for SQLite)
        """
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"

        with engine.connect() as conn:
            result = conn.execute(text(explain_sql))
            rows = result.fetchall()

            has_seq_scan = False
            for row in rows:
                detail = str(row[-1]) if row else ""
                if "SCAN" in detail.upper() and "INDEX" not in detail.upper():
                    has_seq_scan = True

            # SQLite doesn't provide row estimates in EXPLAIN QUERY PLAN
            return CostEstimate(
                total_cost=0,  # SQLite doesn't provide cost
                estimated_rows=0,  # Not available
                has_seq_scan=has_seq_scan,
                has_cartesian=False,  # Hard to detect in SQLite
            )

    def _check_seq_scan_pg(self, plan: dict) -> bool:
        """Check for sequential scans in PostgreSQL plan.

        Args:
            plan: Query plan dict

        Returns:
            True if sequential scan detected
        """
        node_type = plan.get("Node Type", "")
        if node_type == "Seq Scan":
            # Only flag if table has many rows
            rows = plan.get("Plan Rows", 0)
            if rows > 10000:
                return True

        # Check child nodes recursively
        for child in plan.get("Plans", []):
            if self._check_seq_scan_pg(child):
                return True

        return False

    def _check_cartesian_pg(self, plan: dict) -> bool:
        """Check for cartesian joins in PostgreSQL plan.

        Args:
            plan: Query plan dict

        Returns:
            True if cartesian join detected
        """
        node_type = plan.get("Node Type", "")

        # Nested Loop without proper join condition
        if node_type == "Nested Loop":
            # Check if join condition is missing
            join_filter = plan.get("Join Filter")
            if not join_filter:
                # Check row estimates - cartesian products have very high counts
                rows = plan.get("Plan Rows", 0)
                if rows > 1000000:
                    return True

        # Check child nodes
        for child in plan.get("Plans", []):
            if self._check_cartesian_pg(child):
                return True

        return False

    def is_safe(
        self,
        estimate: CostEstimate
    ) -> Tuple[bool, str]:
        """Check if query is safe to execute based on cost estimate.

        Args:
            estimate: Cost estimate from EXPLAIN

        Returns:
            Tuple of (is_safe, warning_message)
        """
        warnings = []

        # Check row count
        if estimate.estimated_rows > self.max_estimated_rows:
            warnings.append(
                f"Query would return ~{estimate.estimated_rows:,} rows. "
                "Add more specific filters or LIMIT."
            )

        # Check cost
        if estimate.total_cost > self.max_cost:
            warnings.append(
                f"Query cost ({estimate.total_cost:,.0f}) exceeds threshold. "
                "Consider adding indexes or filters."
            )

        # Check for cartesian join
        if estimate.has_cartesian:
            warnings.append(
                "Query contains potential cartesian join. "
                "Add proper JOIN conditions."
            )

        # Sequential scan is a warning, not blocking
        if estimate.has_seq_scan:
            logger.info("Query uses sequential scan on large table")

        if warnings:
            return False, " | ".join(warnings)

        return True, ""

    def get_optimization_suggestions(
        self,
        estimate: CostEstimate
    ) -> list[str]:
        """Get suggestions to optimize query based on cost estimate.

        Args:
            estimate: Cost estimate

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        if estimate.has_seq_scan:
            suggestions.append(
                "Consider adding an index on frequently filtered columns"
            )

        if estimate.has_cartesian:
            suggestions.append(
                "Add explicit JOIN conditions to prevent cartesian product"
            )

        if estimate.estimated_rows > 10000:
            suggestions.append(
                "Add LIMIT clause or more specific WHERE conditions"
            )

        if estimate.total_cost > 10000:
            suggestions.append(
                "Query is expensive - consider filtering data more aggressively"
            )

        return suggestions
