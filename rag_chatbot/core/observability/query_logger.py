"""Query logging service for token usage tracking and cost calculation."""

import logging
from datetime import datetime
from typing import Dict, Optional, List
from uuid import uuid4

logger = logging.getLogger(__name__)


# Model pricing database (per 1M tokens)
MODEL_PRICING = {
    # OpenAI (per 1M tokens)
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.00},

    # Anthropic (per 1M tokens)
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},

    # Google Gemini (per 1M tokens)
    "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Free tier
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},

    # Ollama (local - no cost)
    "llama3.1": {"input": 0.00, "output": 0.00},
    "llama3.1:latest": {"input": 0.00, "output": 0.00},
    "llama3.1:70b": {"input": 0.00, "output": 0.00},
    "deepseek-r1:32b": {"input": 0.00, "output": 0.00},
    "deepseek-r1": {"input": 0.00, "output": 0.00},
}


class QueryLogger:
    """
    Query logging service for tracking token usage and calculating costs.

    Provides in-memory logging with optional database persistence.
    Tracks token usage, response times, and estimated costs per query.
    """

    def __init__(self, db_manager=None):
        """
        Initialize query logger.

        Args:
            db_manager: Optional database manager for persistent storage
        """
        self.db = db_manager
        self._in_memory_logs: List[Dict] = []
        logger.info("QueryLogger initialized")

    def log_query(
        self,
        notebook_id: str,
        user_id: str,
        query_text: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_time_ms: int
    ) -> str:
        """
        Log a query with token usage and timing information.

        Args:
            notebook_id: Notebook identifier
            user_id: User identifier
            query_text: The query text
            model_name: LLM model used
            prompt_tokens: Input token count
            completion_tokens: Output token count
            response_time_ms: Response time in milliseconds

        Returns:
            Log ID (UUID)
        """
        log_id = str(uuid4())
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.estimate_cost(model_name, prompt_tokens, completion_tokens)

        log_entry = {
            "log_id": log_id,
            "notebook_id": notebook_id,
            "user_id": user_id,
            "query_text": query_text,
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "response_time_ms": response_time_ms,
            "estimated_cost": estimated_cost,
            "timestamp": datetime.utcnow()
        }

        # Store in memory
        self._in_memory_logs.append(log_entry)

        # Store in database if available
        if self.db:
            try:
                with self.db.get_session() as session:
                    from ..db.models import QueryLog

                    query_log = QueryLog(
                        log_id=log_id,
                        notebook_id=notebook_id,
                        user_id=user_id,
                        query_text=query_text,
                        model_name=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        response_time_ms=response_time_ms,
                        timestamp=log_entry["timestamp"]
                    )
                    session.add(query_log)
                logger.debug(f"Query logged to database: {log_id}")
            except Exception as e:
                logger.error(f"Failed to log query to database: {e}")

        logger.info(
            f"Query logged | Model: {model_name} | "
            f"Tokens: {total_tokens} ({prompt_tokens} in, {completion_tokens} out) | "
            f"Time: {response_time_ms}ms | Cost: ${estimated_cost:.4f}"
        )

        return log_id

    def estimate_cost(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Calculate estimated cost based on token usage and model pricing.

        Args:
            model_name: LLM model name
            prompt_tokens: Input token count
            completion_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        # Normalize model name
        model_key = model_name.lower().strip()

        # Check if model exists in pricing database
        if model_key not in MODEL_PRICING:
            # Try to find partial match
            for key in MODEL_PRICING.keys():
                if key in model_key or model_key in key:
                    model_key = key
                    break
            else:
                # Unknown model, assume free (local) or return 0
                logger.warning(f"Unknown model '{model_name}', assuming free/local")
                return 0.0

        pricing = MODEL_PRICING[model_key]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return total_cost

    def get_usage_stats(
        self,
        notebook_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get usage statistics with optional filtering.

        Args:
            notebook_id: Filter by notebook ID
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Dictionary with usage statistics:
            - total_queries: Total number of queries
            - total_tokens: Total tokens used
            - total_cost: Total estimated cost
            - avg_response_time: Average response time in ms
            - queries_by_model: Breakdown by model
        """
        # Filter logs based on criteria
        filtered_logs = self._in_memory_logs

        if notebook_id:
            filtered_logs = [log for log in filtered_logs if log["notebook_id"] == notebook_id]

        if user_id:
            filtered_logs = [log for log in filtered_logs if log["user_id"] == user_id]

        if start_date:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] >= start_date]

        if end_date:
            filtered_logs = [log for log in filtered_logs if log["timestamp"] <= end_date]

        # Calculate statistics
        if not filtered_logs:
            return {
                "total_queries": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0.0,
                "queries_by_model": {}
            }

        total_queries = len(filtered_logs)
        total_tokens = sum(log["total_tokens"] for log in filtered_logs)
        total_cost = sum(log["estimated_cost"] for log in filtered_logs)
        avg_response_time = sum(log["response_time_ms"] for log in filtered_logs) / total_queries

        # Breakdown by model
        queries_by_model = {}
        for log in filtered_logs:
            model = log["model_name"]
            if model not in queries_by_model:
                queries_by_model[model] = {
                    "count": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            queries_by_model[model]["count"] += 1
            queries_by_model[model]["tokens"] += log["total_tokens"]
            queries_by_model[model]["cost"] += log["estimated_cost"]

        return {
            "total_queries": total_queries,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "avg_response_time": avg_response_time,
            "queries_by_model": queries_by_model
        }

    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """
        Get most recent query logs.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of log entries sorted by timestamp (newest first)
        """
        sorted_logs = sorted(
            self._in_memory_logs,
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return sorted_logs[:limit]

    def clear_logs(self) -> None:
        """Clear all in-memory logs."""
        self._in_memory_logs.clear()
        logger.info("Query logs cleared")

    def get_model_pricing(self, model_name: str) -> Optional[Dict[str, float]]:
        """
        Get pricing information for a specific model.

        Args:
            model_name: Model name

        Returns:
            Dictionary with 'input' and 'output' pricing per 1M tokens,
            or None if model not found
        """
        model_key = model_name.lower().strip()
        return MODEL_PRICING.get(model_key)

    def list_supported_models(self) -> List[str]:
        """
        Get list of all models with pricing information.

        Returns:
            List of model names
        """
        return list(MODEL_PRICING.keys())
