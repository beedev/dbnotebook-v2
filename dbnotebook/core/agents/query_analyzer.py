"""Query analyzer agent - analyzes user queries to understand intent and suggest improvements."""

from .base import BaseAgent


class QueryAnalyzer(BaseAgent):
    """
    Analyzes user queries to understand intent and suggest improvements.

    Capabilities:
    - Intent classification (factual, comparison, exploration, action, clarification)
    - Query complexity assessment
    - Query refinement suggestions
    """

    INTENT_CATEGORIES = [
        "factual",      # Looking for specific facts
        "comparison",   # Comparing options
        "exploration",  # Open-ended exploration
        "action",       # Wants to do something
        "clarification" # Needs explanation
    ]

    def analyze(self, query: str) -> dict:
        """
        Analyze query intent and complexity.

        Args:
            query: User query text

        Returns:
            Dictionary with:
                - query: Original query text
                - intent: Classified intent category
                - complexity: Complexity score 0.0-1.0
                - suggested_refinements: List of refinement suggestions
                - confidence: Confidence in classification (0.0-1.0)
        """
        return {
            "query": query,
            "intent": self._classify_intent(query),
            "complexity": self._assess_complexity(query),
            "suggested_refinements": self._suggest_refinements(query),
            "confidence": self._calculate_confidence(query)
        }

    def suggest(self, context: dict) -> list[dict]:
        """
        Suggest query improvements based on context.

        Args:
            context: Context dictionary containing:
                - query: Current query text
                - history: Optional conversation history
                - notebook_context: Optional notebook information

        Returns:
            List of suggestion dictionaries with:
                - type: Suggestion type
                - text: Suggested query text
                - reason: Why this suggestion is made
        """
        query = context.get("query", "")
        history = context.get("history", [])

        suggestions = []

        # Suggest more specific queries for vague questions
        if self._is_vague(query):
            suggestions.append({
                "type": "specificity",
                "text": f"{query} - please provide specific details about...",
                "reason": "Query is too vague, needs more context"
            })

        # Suggest follow-up questions based on intent
        intent = self._classify_intent(query)
        if intent == "factual" and history:
            suggestions.append({
                "type": "follow_up",
                "text": f"Can you provide more details about {query}?",
                "reason": "Factual query could benefit from more details"
            })

        return suggestions

    def _classify_intent(self, query: str) -> str:
        """
        Classify query intent using simple heuristics.

        Can be enhanced with LLM-based classification in the future.

        Args:
            query: Query text

        Returns:
            Intent category string
        """
        query_lower = query.lower()

        # Comparison intent
        if any(w in query_lower for w in ["compare", "vs", "versus", "difference", "better"]):
            return "comparison"

        # Factual intent
        if any(w in query_lower for w in ["what is", "who is", "when", "where", "define"]):
            return "factual"

        # Action intent
        if any(w in query_lower for w in ["how to", "can i", "should i", "help me"]):
            return "action"

        # Clarification intent
        if any(w in query_lower for w in ["explain", "clarify", "elaborate", "tell me more"]):
            return "clarification"

        # Default to exploration
        return "exploration"

    def _assess_complexity(self, query: str) -> float:
        """
        Assess query complexity based on length and structure.

        Simple heuristic: longer queries with more clauses are more complex.

        Args:
            query: Query text

        Returns:
            Complexity score 0.0-1.0
        """
        words = query.split()
        word_count = len(words)

        # Base complexity on word count (normalized to 0-1)
        # 20+ words = max complexity
        base_complexity = min(word_count / 20, 1.0)

        # Add complexity for question words (indicates multiple questions)
        question_words = ["what", "when", "where", "why", "how", "who"]
        question_count = sum(1 for w in query.lower().split() if w in question_words)
        question_complexity = min(question_count * 0.15, 0.3)

        return min(base_complexity + question_complexity, 1.0)

    def _suggest_refinements(self, query: str) -> list[str]:
        """
        Suggest refinements for the query.

        Placeholder implementation - can be enhanced with LLM.

        Args:
            query: Query text

        Returns:
            List of refinement suggestions
        """
        refinements = []

        # Suggest adding context for short queries
        if len(query.split()) < 5:
            refinements.append(
                "Consider adding more context to get better results"
            )

        # Suggest breaking down complex queries
        if self._assess_complexity(query) > 0.7:
            refinements.append(
                "Consider breaking this into multiple simpler questions"
            )

        return refinements

    def _calculate_confidence(self, query: str) -> float:
        """
        Calculate confidence in intent classification.

        Higher confidence for queries with clear intent signals.

        Args:
            query: Query text

        Returns:
            Confidence score 0.0-1.0
        """
        # Base confidence
        confidence = 0.5

        # Increase confidence for queries with clear intent markers
        query_lower = query.lower()
        intent_markers = [
            "what", "when", "where", "why", "how", "who",
            "compare", "explain", "help", "show"
        ]

        marker_count = sum(1 for marker in intent_markers if marker in query_lower)
        confidence += min(marker_count * 0.15, 0.4)

        return min(confidence, 1.0)

    def _is_vague(self, query: str) -> bool:
        """
        Check if query is too vague.

        Args:
            query: Query text

        Returns:
            True if query is vague
        """
        vague_indicators = [
            "this", "that", "it", "stuff", "things", "something"
        ]

        query_lower = query.lower()
        word_count = len(query.split())

        # Vague if very short and contains vague indicators
        if word_count < 5:
            return any(indicator in query_lower for indicator in vague_indicators)

        return False
