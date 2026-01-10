"""
Result Validator for SQL Chat.

Performs sanity checks on query results to detect issues like:
- Empty results for non-filter queries
- Cartesian products from missing JOINs
- All NULL aggregations
- Suspicious row counts

Returns actionable warnings/errors to help users understand
potential issues with generated SQL.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from dbnotebook.core.sql_chat.types import SchemaInfo

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Severity level for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in query results."""
    severity: IssueSeverity
    code: str  # Machine-readable code (e.g., "EMPTY_RESULTS")
    message: str  # Human-readable message
    suggestion: str  # Actionable suggestion


class ResultValidator:
    """Validate query results for sanity checks.

    Detects common issues:
    - Empty results when not expected
    - Cartesian product explosions
    - All NULL values in aggregations
    - Suspiciously high/low row counts
    - Type mismatches
    """

    # Thresholds for validation
    HIGH_ROW_COUNT_THRESHOLD = 10000
    CARTESIAN_MULTIPLIER_THRESHOLD = 100

    def __init__(self):
        """Initialize result validator."""
        pass

    def validate(
        self,
        query: str,
        sql: str,
        results: List[Dict[str, Any]],
        schema: Optional[SchemaInfo] = None
    ) -> List[ValidationIssue]:
        """Validate query results and return any issues found.

        Args:
            query: Original natural language query
            sql: Generated SQL query
            results: Query result rows
            schema: Optional schema for additional validation

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        sql_lower = sql.lower()
        row_count = len(results)

        # Check 1: Empty results
        empty_issues = self._check_empty_results(query, sql_lower, row_count)
        issues.extend(empty_issues)

        # Check 2: Cartesian product detection
        cartesian_issues = self._check_cartesian_product(sql_lower, row_count, schema)
        issues.extend(cartesian_issues)

        # Check 3: NULL aggregations
        if results:
            null_issues = self._check_null_aggregations(sql_lower, results)
            issues.extend(null_issues)

        # Check 4: High row count warning
        high_count_issues = self._check_high_row_count(row_count, sql_lower)
        issues.extend(high_count_issues)

        # Check 5: Column type mismatches
        if results and schema:
            type_issues = self._check_type_consistency(results, sql_lower, schema)
            issues.extend(type_issues)

        # Check 6: Duplicate detection in aggregations
        if results:
            dup_issues = self._check_duplicate_aggregations(sql_lower, results)
            issues.extend(dup_issues)

        # Log issues
        if issues:
            logger.info(f"Validation found {len(issues)} issues for query")
            for issue in issues:
                logger.debug(f"  [{issue.severity.value}] {issue.code}: {issue.message}")

        return issues

    def _check_empty_results(
        self,
        query: str,
        sql_lower: str,
        row_count: int
    ) -> List[ValidationIssue]:
        """Check for unexpected empty results.

        Args:
            query: Natural language query
            sql_lower: Lowercase SQL query
            row_count: Number of result rows

        Returns:
            List of issues found
        """
        if row_count > 0:
            return []

        issues = []

        # Check if query has WHERE clause
        has_where = 'where' in sql_lower

        if not has_where:
            # Empty results without WHERE is suspicious
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                code="EMPTY_NO_FILTER",
                message="Query returned 0 rows but has no WHERE clause",
                suggestion="Check if table names are correct. The table might be empty."
            ))
        else:
            # Check for overly restrictive filters
            # Count number of AND conditions
            and_count = sql_lower.count(' and ')
            if and_count >= 3:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    code="EMPTY_STRICT_FILTER",
                    message=f"Query returned 0 rows with {and_count + 1} filter conditions",
                    suggestion="Try removing some filter conditions to broaden the search."
                ))
            else:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    code="EMPTY_RESULTS",
                    message="Query returned 0 rows - filter may be too restrictive",
                    suggestion="Try broadening the search criteria or check filter values."
                ))

        return issues

    def _check_cartesian_product(
        self,
        sql_lower: str,
        row_count: int,
        schema: Optional[SchemaInfo]
    ) -> List[ValidationIssue]:
        """Detect potential cartesian products from missing JOIN conditions.

        Args:
            sql_lower: Lowercase SQL query
            row_count: Number of result rows
            schema: Database schema

        Returns:
            List of issues found
        """
        issues = []

        # Count JOINs and ON clauses
        join_count = sql_lower.count(' join ')
        on_count = sql_lower.count(' on ')

        # If we have JOINs but fewer ON clauses, might be cartesian
        if join_count > 0 and on_count < join_count:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                code="MISSING_JOIN_CONDITION",
                message=f"Found {join_count} JOIN(s) but only {on_count} ON clause(s)",
                suggestion="Review JOIN conditions - missing ON clause causes cartesian product."
            ))

        # Check for comma-separated tables in FROM (implicit cross join)
        from_match = re.search(r'from\s+(\w+)\s*,\s*(\w+)', sql_lower)
        if from_match:
            table1, table2 = from_match.groups()
            # Check if there's a WHERE clause joining them
            join_pattern = rf'{table1}\..*=.*{table2}\.|{table2}\..*=.*{table1}\.'
            if not re.search(join_pattern, sql_lower):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="IMPLICIT_CROSS_JOIN",
                    message=f"Tables {table1} and {table2} appear to be cross-joined",
                    suggestion="Use explicit JOIN with ON clause instead of comma-separated tables."
                ))

        # High row count with JOINs might indicate cartesian
        if row_count > self.HIGH_ROW_COUNT_THRESHOLD and join_count > 0:
            if schema:
                # Estimate expected row count based on schema
                expected_max = self._estimate_max_join_rows(sql_lower, schema)
                if expected_max and row_count > expected_max * self.CARTESIAN_MULTIPLIER_THRESHOLD:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        code="POSSIBLE_CARTESIAN",
                        message=f"Row count ({row_count:,}) seems unusually high for this query",
                        suggestion="Check if all JOINs have proper conditions."
                    ))

        return issues

    def _check_null_aggregations(
        self,
        sql_lower: str,
        results: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Check for all-NULL columns in aggregation results.

        Args:
            sql_lower: Lowercase SQL query
            results: Query results

        Returns:
            List of issues found
        """
        issues = []

        # Check if query has aggregations
        agg_functions = ['sum(', 'avg(', 'count(', 'max(', 'min(']
        has_aggregation = any(agg in sql_lower for agg in agg_functions)

        if not has_aggregation:
            return []

        # Check for all-NULL columns
        for col_name in results[0].keys():
            if all(row.get(col_name) is None for row in results):
                # Check if this column looks like an aggregation result
                col_lower = col_name.lower()
                if any(agg.replace('(', '') in col_lower for agg in agg_functions):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        code="NULL_AGGREGATION",
                        message=f"Column '{col_name}' is all NULL - aggregation may be on wrong column",
                        suggestion="Check if the column name is spelled correctly."
                    ))

        return issues

    def _check_high_row_count(
        self,
        row_count: int,
        sql_lower: str
    ) -> List[ValidationIssue]:
        """Check for suspiciously high row counts.

        Args:
            row_count: Number of result rows
            sql_lower: Lowercase SQL query

        Returns:
            List of issues found
        """
        issues = []

        if row_count <= self.HIGH_ROW_COUNT_THRESHOLD:
            return []

        # Check if query has LIMIT
        has_limit = 'limit' in sql_lower

        if not has_limit:
            issues.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                code="HIGH_ROW_COUNT",
                message=f"Query returned {row_count:,} rows - consider adding LIMIT",
                suggestion="Add LIMIT clause for better performance and usability."
            ))

        return issues

    def _check_type_consistency(
        self,
        results: List[Dict[str, Any]],
        sql_lower: str,
        schema: SchemaInfo
    ) -> List[ValidationIssue]:
        """Check for type consistency in results.

        Args:
            results: Query results
            sql_lower: Lowercase SQL query
            schema: Database schema

        Returns:
            List of issues found
        """
        issues = []

        # This is a simplified check - mainly looking for obvious type mismatches
        # like strings where numbers are expected

        for col_name in results[0].keys():
            values = [row.get(col_name) for row in results[:100]]  # Sample first 100
            non_null_values = [v for v in values if v is not None]

            if not non_null_values:
                continue

            # Check for mixed types
            types = set(type(v).__name__ for v in non_null_values)
            if len(types) > 1:
                # Allow int/float mixing
                numeric_types = {'int', 'float', 'Decimal'}
                if not types.issubset(numeric_types):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        code="MIXED_TYPES",
                        message=f"Column '{col_name}' has mixed types: {types}",
                        suggestion="This may indicate data quality issues or type casting."
                    ))

        return issues

    def _check_duplicate_aggregations(
        self,
        sql_lower: str,
        results: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Check for potential duplicate counting in aggregations.

        Args:
            sql_lower: Lowercase SQL query
            results: Query results

        Returns:
            List of issues found
        """
        issues = []

        # Check for COUNT without DISTINCT when JOINs are present
        if 'count(' in sql_lower and 'join' in sql_lower:
            if 'count(distinct' not in sql_lower and 'count(*)' not in sql_lower:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    code="COUNT_WITHOUT_DISTINCT",
                    message="COUNT with JOIN may include duplicates",
                    suggestion="Consider using COUNT(DISTINCT column) to avoid counting duplicates."
                ))

        # Check for SUM that might include duplicates
        if 'sum(' in sql_lower and 'join' in sql_lower:
            # This is hard to detect automatically, just warn
            if 'group by' not in sql_lower:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    code="SUM_WITH_JOIN",
                    message="SUM with JOIN and no GROUP BY may sum duplicates",
                    suggestion="Verify that JOINs don't create duplicate rows before summing."
                ))

        return issues

    def _estimate_max_join_rows(
        self,
        sql_lower: str,
        schema: SchemaInfo
    ) -> Optional[int]:
        """Estimate maximum expected rows from JOIN based on table sizes.

        Args:
            sql_lower: Lowercase SQL query
            schema: Database schema

        Returns:
            Estimated maximum row count or None if unable to estimate
        """
        # Extract table names from query
        table_pattern = r'(?:from|join)\s+(\w+)'
        tables = re.findall(table_pattern, sql_lower)

        if not tables:
            return None

        # Find row counts for each table
        row_counts = []
        table_map = {t.name.lower(): t for t in schema.tables}

        for table_name in tables:
            table = table_map.get(table_name.lower())
            if table and table.row_count:
                row_counts.append(table.row_count)

        if not row_counts:
            return None

        # For inner join, max is min of all tables (roughly)
        # For outer joins, it's more complex - use largest table as estimate
        return max(row_counts)

    def format_issues_for_display(
        self,
        issues: List[ValidationIssue]
    ) -> str:
        """Format issues for user display.

        Args:
            issues: List of validation issues

        Returns:
            Formatted string for display
        """
        if not issues:
            return ""

        lines = ["**Query Validation Results:**", ""]

        for issue in issues:
            icon = {
                IssueSeverity.INFO: "ℹ️",
                IssueSeverity.WARNING: "⚠️",
                IssueSeverity.ERROR: "❌"
            }.get(issue.severity, "•")

            lines.append(f"{icon} **{issue.message}**")
            lines.append(f"   💡 {issue.suggestion}")
            lines.append("")

        return "\n".join(lines)

    def has_errors(self, issues: List[ValidationIssue]) -> bool:
        """Check if any issues are errors.

        Args:
            issues: List of validation issues

        Returns:
            True if any issue has ERROR severity
        """
        return any(i.severity == IssueSeverity.ERROR for i in issues)

    def has_warnings(self, issues: List[ValidationIssue]) -> bool:
        """Check if any issues are warnings or errors.

        Args:
            issues: List of validation issues

        Returns:
            True if any issue has WARNING or ERROR severity
        """
        return any(
            i.severity in (IssueSeverity.WARNING, IssueSeverity.ERROR)
            for i in issues
        )
