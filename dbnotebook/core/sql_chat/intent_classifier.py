"""
Query Intent Classification for Chat with Data.

Classifies natural language query intent to optimize SQL generation.
Uses keyword matching and pattern analysis to determine query type.
"""

import logging
import re
from typing import Dict, List, Set

from dbnotebook.core.sql_chat.types import (
    IntentClassification,
    QueryIntent,
)

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classify NL query intent for SQL shape optimization.

    Determines query intent (lookup, aggregation, comparison, trend, top_k)
    to provide appropriate hints to the LLM for SQL generation.
    """

    # Intent keyword mappings
    INTENT_KEYWORDS: Dict[QueryIntent, List[str]] = {
        QueryIntent.LOOKUP: [
            "show", "get", "find", "list", "display", "details", "info",
            "what is", "who is", "where is", "tell me about", "give me"
        ],
        QueryIntent.AGGREGATION: [
            "total", "sum", "count", "average", "avg", "how many",
            "how much", "minimum", "maximum", "min", "max", "mean",
            "aggregate", "summarize", "statistics"
        ],
        QueryIntent.COMPARISON: [
            "vs", "versus", "compare", "difference", "between",
            "compared to", "relative to", "against", "contrast"
        ],
        QueryIntent.TREND: [
            "over time", "growth", "trend", "change", "history",
            "monthly", "yearly", "weekly", "daily", "quarterly",
            "evolution", "progression", "timeline", "by month", "by year"
        ],
        QueryIntent.TOP_K: [
            "top", "best", "highest", "lowest", "most", "least",
            "bottom", "leading", "worst", "first", "last",
            "biggest", "smallest", "largest", "ranking"
        ],
    }

    # SQL generation hints for each intent
    INTENT_HINTS: Dict[QueryIntent, str] = {
        QueryIntent.LOOKUP: (
            "Return specific rows. Include identifying columns like name, id, or title. "
            "Use WHERE clause to filter to relevant records."
        ),
        QueryIntent.AGGREGATION: (
            "Use GROUP BY with aggregate functions (SUM, COUNT, AVG, MIN, MAX). "
            "Include the grouping dimension in SELECT. Consider HAVING for filtering groups."
        ),
        QueryIntent.COMPARISON: (
            "Return comparable metrics side-by-side. Use CASE expressions, UNION, "
            "or self-joins to show data from different categories together."
        ),
        QueryIntent.TREND: (
            "Include date/time column in results. ORDER BY date. "
            "Consider DATE_TRUNC or similar for date bucketing. Use window functions if needed."
        ),
        QueryIntent.TOP_K: (
            "Use ORDER BY with the ranking metric (DESC for highest, ASC for lowest). "
            "Add LIMIT clause. Include the metric being ranked."
        ),
    }

    def __init__(self):
        """Initialize intent classifier with compiled patterns."""
        # Pre-compile patterns for faster matching
        self._keyword_patterns: Dict[QueryIntent, List[re.Pattern]] = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            self._keyword_patterns[intent] = [
                re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
                for kw in keywords
            ]

    def classify(self, query: str) -> IntentClassification:
        """Classify query intent based on keywords and patterns.

        Args:
            query: Natural language query

        Returns:
            IntentClassification with intent type and confidence
        """
        if not query or not query.strip():
            return IntentClassification(
                intent=QueryIntent.LOOKUP,
                confidence=0.3,
                prompt_hints=""
            )

        query_lower = query.lower()

        # Score each intent based on keyword matches
        scores: Dict[QueryIntent, float] = {}
        for intent, patterns in self._keyword_patterns.items():
            match_count = sum(1 for p in patterns if p.search(query_lower))
            # Normalize by number of keywords to avoid bias toward intents with more keywords
            scores[intent] = match_count / len(patterns) if patterns else 0

        # Find best matching intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Adjust confidence based on score
        # Max score of 1.0 would mean all keywords matched (unlikely)
        # A score of 0.2-0.4 is typical for a good match
        if best_score >= 0.3:
            confidence = 0.9
        elif best_score >= 0.2:
            confidence = 0.7
        elif best_score >= 0.1:
            confidence = 0.5
        else:
            confidence = 0.3
            best_intent = QueryIntent.LOOKUP  # Default to lookup

        # Get prompt hints
        prompt_hints = self.INTENT_HINTS.get(best_intent, "")

        logger.debug(f"Intent classified: {best_intent.value} (confidence: {confidence})")

        return IntentClassification(
            intent=best_intent,
            confidence=confidence,
            prompt_hints=prompt_hints
        )

    def get_intent_prompt_hints(self, intent: QueryIntent) -> str:
        """Get SQL generation hints for an intent.

        Args:
            intent: Query intent

        Returns:
            Hint string for LLM prompt
        """
        return self.INTENT_HINTS.get(intent, "")

    def detect_temporal_granularity(self, query: str) -> str:
        """Detect time granularity mentioned in query.

        Args:
            query: Natural language query

        Returns:
            Granularity string (day, week, month, quarter, year) or empty
        """
        query_lower = query.lower()

        granularities = {
            "day": ["daily", "by day", "each day", "per day", "days"],
            "week": ["weekly", "by week", "each week", "per week", "weeks"],
            "month": ["monthly", "by month", "each month", "per month", "months"],
            "quarter": ["quarterly", "by quarter", "each quarter", "per quarter", "quarters"],
            "year": ["yearly", "annually", "by year", "each year", "per year", "years"],
        }

        for granularity, keywords in granularities.items():
            if any(kw in query_lower for kw in keywords):
                return granularity

        return ""

    def detect_limit_value(self, query: str) -> int:
        """Detect numeric limit mentioned in query (e.g., "top 10").

        Args:
            query: Natural language query

        Returns:
            Limit value or 0 if not detected
        """
        # Patterns like "top 10", "bottom 5", "first 20"
        patterns = [
            r'\btop\s+(\d+)\b',
            r'\bbottom\s+(\d+)\b',
            r'\bfirst\s+(\d+)\b',
            r'\blast\s+(\d+)\b',
            r'\b(\d+)\s+(?:best|worst|highest|lowest)\b',
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return 0

    def enhance_prompt_with_intent(
        self,
        query: str,
        intent: IntentClassification
    ) -> str:
        """Enhance query with intent-specific instructions.

        Args:
            query: Original user query
            intent: Classified intent

        Returns:
            Enhanced prompt for LLM
        """
        parts = [f"User Query: {query}"]

        if intent.prompt_hints:
            parts.append(f"\nSQL Generation Hints: {intent.prompt_hints}")

        # Add temporal granularity if detected
        if intent.intent == QueryIntent.TREND:
            granularity = self.detect_temporal_granularity(query)
            if granularity:
                parts.append(f"\nTemporal Granularity: {granularity}")

        # Add limit if detected
        if intent.intent == QueryIntent.TOP_K:
            limit = self.detect_limit_value(query)
            if limit > 0:
                parts.append(f"\nLimit: {limit}")

        return "\n".join(parts)
