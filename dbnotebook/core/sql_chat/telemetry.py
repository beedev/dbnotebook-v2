"""
Query Telemetry for Chat with Data.

Logs query telemetry for observability and accuracy improvement.
Tracks success rates, retry counts, confidence scores, and timing.
"""

import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dbnotebook.core.sql_chat.types import (
    QueryResult,
    QueryTelemetry,
)

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """Log query telemetry for observability and improvement.

    Stores telemetry data for:
    - Success/failure tracking
    - Accuracy metrics computation
    - Query pattern analysis
    - Performance monitoring
    """

    def __init__(self, db_manager=None):
        """Initialize telemetry logger.

        Args:
            db_manager: Optional database manager for persistence
        """
        self._db_manager = db_manager
        self._memory_store: List[QueryTelemetry] = []  # In-memory fallback
        self._max_memory_entries = 1000

    def log(self, telemetry: QueryTelemetry) -> None:
        """Persist telemetry entry.

        Args:
            telemetry: Telemetry data to log
        """
        # Set timestamp if not set
        if telemetry.timestamp is None:
            telemetry.timestamp = datetime.utcnow()

        # Try to persist to database
        if self._db_manager:
            try:
                self._persist_to_db(telemetry)
                logger.debug(f"Logged telemetry for session {telemetry.session_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to persist telemetry to DB: {e}")

        # Fallback to in-memory storage
        self._memory_store.append(telemetry)
        if len(self._memory_store) > self._max_memory_entries:
            self._memory_store = self._memory_store[-self._max_memory_entries:]

        logger.debug(f"Logged telemetry to memory for session {telemetry.session_id}")

    def _persist_to_db(self, telemetry: QueryTelemetry) -> None:
        """Persist telemetry to database.

        Args:
            telemetry: Telemetry data
        """
        # This will be implemented when database models are added
        # For now, just log
        pass

    def log_from_result(
        self,
        session_id: str,
        user_query: str,
        result: QueryResult,
        intent: str = "unknown"
    ) -> QueryTelemetry:
        """Create and log telemetry from a QueryResult.

        Args:
            session_id: Session ID
            user_query: Original user query
            result: Query result
            intent: Detected intent

        Returns:
            Created telemetry entry
        """
        telemetry = QueryTelemetry(
            session_id=session_id,
            user_query=user_query,
            generated_sql=result.sql_generated,
            intent=intent,
            confidence_score=result.confidence.score if result.confidence else 0.0,
            retry_count=result.retry_count,
            execution_time_ms=int(result.execution_time_ms),
            row_count=result.row_count,
            cost_estimate=result.cost_estimate.total_cost if result.cost_estimate else 0.0,
            success=result.success,
            error_message=result.error_message,
            timestamp=datetime.utcnow(),
        )

        self.log(telemetry)
        return telemetry

    def get_accuracy_metrics(
        self,
        days: int = 30,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute accuracy metrics from telemetry.

        Args:
            days: Days of history to analyze
            session_id: Optional filter by session

        Returns:
            Accuracy metrics dict
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Filter entries
        entries = [
            t for t in self._memory_store
            if t.timestamp and t.timestamp >= cutoff
            and (session_id is None or t.session_id == session_id)
        ]

        if not entries:
            return {
                "total_queries": 0,
                "success_rate": 0.0,
                "avg_retries": 0.0,
                "avg_confidence": 0.0,
                "empty_result_rate": 0.0,
                "avg_execution_time_ms": 0.0,
            }

        total = len(entries)
        successful = sum(1 for t in entries if t.success)
        empty_results = sum(1 for t in entries if t.success and t.row_count == 0)
        total_retries = sum(t.retry_count for t in entries)
        total_confidence = sum(t.confidence_score for t in entries)
        total_time = sum(t.execution_time_ms for t in entries)

        return {
            "total_queries": total,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_retries": total_retries / total if total > 0 else 0.0,
            "avg_confidence": total_confidence / total if total > 0 else 0.0,
            "empty_result_rate": empty_results / total if total > 0 else 0.0,
            "avg_execution_time_ms": total_time / total if total > 0 else 0.0,
        }

    def get_error_patterns(
        self,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Analyze common error patterns.

        Args:
            days: Days of history to analyze
            limit: Max patterns to return

        Returns:
            List of error pattern dicts
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get failed entries
        failed = [
            t for t in self._memory_store
            if t.timestamp and t.timestamp >= cutoff
            and not t.success and t.error_message
        ]

        # Group by error message prefix (first 50 chars)
        error_groups: Dict[str, int] = {}
        for t in failed:
            prefix = t.error_message[:50] if t.error_message else "Unknown"
            error_groups[prefix] = error_groups.get(prefix, 0) + 1

        # Sort by frequency
        sorted_errors = sorted(error_groups.items(), key=lambda x: x[1], reverse=True)

        return [
            {"error_prefix": err, "count": count}
            for err, count in sorted_errors[:limit]
        ]

    def get_intent_distribution(
        self,
        days: int = 30
    ) -> Dict[str, int]:
        """Get distribution of query intents.

        Args:
            days: Days of history to analyze

        Returns:
            Dict mapping intent to count
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        entries = [
            t for t in self._memory_store
            if t.timestamp and t.timestamp >= cutoff
        ]

        distribution: Dict[str, int] = {}
        for t in entries:
            distribution[t.intent] = distribution.get(t.intent, 0) + 1

        return distribution

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get telemetry summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Session summary dict
        """
        entries = [t for t in self._memory_store if t.session_id == session_id]

        if not entries:
            return {"session_id": session_id, "query_count": 0}

        return {
            "session_id": session_id,
            "query_count": len(entries),
            "success_count": sum(1 for t in entries if t.success),
            "total_rows_returned": sum(t.row_count for t in entries),
            "total_retries": sum(t.retry_count for t in entries),
            "avg_confidence": sum(t.confidence_score for t in entries) / len(entries),
            "total_time_ms": sum(t.execution_time_ms for t in entries),
        }

    def export_telemetry(
        self,
        days: int = 30,
        format: str = "dict"
    ) -> Any:
        """Export telemetry data.

        Args:
            days: Days of history to export
            format: Output format ("dict" or "csv")

        Returns:
            Exported data
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        entries = [
            t for t in self._memory_store
            if t.timestamp and t.timestamp >= cutoff
        ]

        if format == "dict":
            return [asdict(t) for t in entries]

        elif format == "csv":
            if not entries:
                return ""

            headers = list(asdict(entries[0]).keys())
            lines = [",".join(headers)]

            for t in entries:
                d = asdict(t)
                row = [str(d.get(h, "")) for h in headers]
                lines.append(",".join(row))

            return "\n".join(lines)

        return entries

    def clear(self) -> None:
        """Clear in-memory telemetry store."""
        self._memory_store.clear()
        logger.info("Telemetry store cleared")
