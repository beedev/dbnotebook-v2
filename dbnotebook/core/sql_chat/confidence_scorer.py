"""
Confidence Scoring for Chat with Data.

Computes multi-signal confidence scores for generated SQL queries.
Combines table relevance, few-shot similarity, retry count, and column overlap.
"""

import logging
from typing import Dict, List, Optional, Set

from dbnotebook.core.sql_chat.types import (
    ConfidenceLevel,
    ConfidenceScore,
    QueryResult,
)

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Compute query confidence from multiple signals.

    Combines:
    - Table relevance from schema retriever
    - Few-shot similarity from Gretel examples
    - Retry count from semantic inspector
    - Column-intent overlap

    Used to:
    - Show confidence badge (High/Medium/Low) on results
    - Gate "Generate Insights" behind Medium+ confidence
    - Suggest rephrasing for low confidence queries
    """

    # Signal weights for confidence calculation
    WEIGHTS = {
        "table_relevance": 0.30,
        "few_shot_similarity": 0.30,
        "retry_penalty": 0.20,
        "column_overlap": 0.20,
    }

    # Thresholds for confidence levels
    HIGH_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.5

    def __init__(
        self,
        high_threshold: float = 0.8,
        medium_threshold: float = 0.5
    ):
        """Initialize confidence scorer.

        Args:
            high_threshold: Score threshold for HIGH confidence
            medium_threshold: Score threshold for MEDIUM confidence
        """
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def compute(
        self,
        table_relevance: float = 0.5,
        few_shot_similarity: float = 0.5,
        retry_count: int = 0,
        column_intent_overlap: float = 0.5,
        custom_factors: Optional[Dict[str, float]] = None
    ) -> ConfidenceScore:
        """Compute confidence score from multiple signals.

        Args:
            table_relevance: Similarity score from schema retriever (0-1)
            few_shot_similarity: Best match score from Gretel examples (0-1)
            retry_count: Number of retries from semantic inspector (0-3)
            column_intent_overlap: Overlap between result columns and query terms (0-1)
            custom_factors: Optional additional factors to include

        Returns:
            ConfidenceScore with level and detailed factors
        """
        # Normalize retry count to a penalty (0 retries = 1.0, 3 retries = 0.0)
        retry_penalty = 1 - (retry_count / 3)

        # Calculate weighted score
        score = (
            table_relevance * self.WEIGHTS["table_relevance"] +
            few_shot_similarity * self.WEIGHTS["few_shot_similarity"] +
            retry_penalty * self.WEIGHTS["retry_penalty"] +
            column_intent_overlap * self.WEIGHTS["column_overlap"]
        )

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        # Determine level
        if score >= self.high_threshold:
            level = ConfidenceLevel.HIGH
        elif score >= self.medium_threshold:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        # Build factors dict
        factors = {
            "table_relevance": table_relevance,
            "few_shot_similarity": few_shot_similarity,
            "retry_penalty": retry_count,  # Store actual count, not normalized
            "column_overlap": column_intent_overlap,
        }

        # Add any custom factors
        if custom_factors:
            factors.update(custom_factors)

        logger.debug(
            f"Confidence score: {score:.2f} ({level.value}) "
            f"[table={table_relevance:.2f}, few_shot={few_shot_similarity:.2f}, "
            f"retries={retry_count}, overlap={column_intent_overlap:.2f}]"
        )

        return ConfidenceScore(
            score=score,
            level=level,
            factors=factors
        )

    def compute_column_overlap(
        self,
        query_terms: Set[str],
        result_columns: List[str]
    ) -> float:
        """Compute overlap between query terms and result column names.

        Args:
            query_terms: Set of terms from user query (lowercase)
            result_columns: List of column names in result

        Returns:
            Overlap score (0-1)
        """
        if not query_terms or not result_columns:
            return 0.5  # Default to medium if no info

        # Normalize column names
        col_terms: Set[str] = set()
        for col in result_columns:
            # Split camelCase and snake_case
            parts = col.replace('_', ' ').lower().split()
            col_terms.update(parts)

        # Calculate Jaccard-like overlap
        overlap = len(query_terms & col_terms)
        union = len(query_terms | col_terms)

        if union == 0:
            return 0.5

        # Normalize - even small overlap is significant
        raw_overlap = overlap / union
        # Boost small overlaps (1 match out of 10 terms = 0.1 -> 0.4)
        boosted = min(1.0, raw_overlap * 4)

        return boosted

    def extract_query_terms(self, query: str) -> Set[str]:
        """Extract meaningful terms from user query.

        Args:
            query: Natural language query

        Returns:
            Set of lowercase terms
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'of', 'to', 'for',
            'in', 'on', 'at', 'by', 'from', 'with', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'and', 'or', 'but', 'if', 'so', 'as', 'until', 'while',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these',
            'those', 'am', 'being', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'than', 'too', 'very', 'just', 'also',
            'how', 'many', 'much', 'all', 'any', 'both', 'here',
            'there', 'when', 'where', 'why', 'show', 'me', 'get',
            'find', 'give', 'tell', 'list', 'display',
        }

        # Tokenize and filter
        terms = set()
        for word in query.lower().split():
            # Remove punctuation
            word = ''.join(c for c in word if c.isalnum())
            if word and word not in stop_words and len(word) > 2:
                terms.add(word)

        return terms

    def get_confidence_message(self, score: ConfidenceScore) -> str:
        """Get user-friendly message for confidence level.

        Args:
            score: Confidence score

        Returns:
            Human-readable message
        """
        if score.level == ConfidenceLevel.HIGH:
            return "High confidence - Results are likely accurate"
        elif score.level == ConfidenceLevel.MEDIUM:
            return "Medium confidence - Results may need verification"
        else:
            return "Low confidence - Consider rephrasing your question"

    def should_show_insights(self, score: ConfidenceScore) -> bool:
        """Check if insights generation should be offered.

        Args:
            score: Confidence score

        Returns:
            True if confidence is medium or higher
        """
        return score.level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def get_improvement_suggestions(
        self,
        score: ConfidenceScore
    ) -> List[str]:
        """Get suggestions to improve query confidence.

        Args:
            score: Confidence score

        Returns:
            List of improvement suggestions
        """
        suggestions = []
        factors = score.factors

        # Low table relevance
        if factors.get("table_relevance", 1.0) < 0.5:
            suggestions.append(
                "Try using table or column names from the schema directly"
            )

        # Low few-shot similarity
        if factors.get("few_shot_similarity", 1.0) < 0.5:
            suggestions.append(
                "Try rephrasing your question more specifically"
            )

        # High retry count
        retry_count = factors.get("retry_penalty", 0)
        if retry_count >= 2:
            suggestions.append(
                "The query required multiple corrections - consider simplifying"
            )

        # Low column overlap
        if factors.get("column_overlap", 1.0) < 0.3:
            suggestions.append(
                "The returned columns may not match your intent - verify results"
            )

        # Generic suggestion for low confidence
        if score.level == ConfidenceLevel.LOW and not suggestions:
            suggestions.append(
                "Try breaking your question into simpler parts"
            )

        return suggestions
