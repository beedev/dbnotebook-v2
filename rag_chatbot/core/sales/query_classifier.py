"""Query classification for sales enablement system."""
import logging
import re
from typing import Dict, Optional
from llama_index.core.llms.llm import LLM

logger = logging.getLogger(__name__)


class QueryClassifier:
    """
    Classifies user queries into different sales modes:
    - problem_solving: Customer has a problem, need to recommend offering bundle
    - pitch_specific: Generate pitch for specific customer/industry
    - pitch_generic: Generate generic pitch for selected offerings
    - offering_summary: Summarize a specific offering
    """

    # Keywords for different query types
    PROBLEM_KEYWORDS = [
        "problem", "issue", "challenge", "difficult", "need", "help",
        "struggling", "can't", "cannot", "how can", "solution for"
    ]

    PITCH_KEYWORDS = [
        "pitch", "present", "sell", "convince", "proposal", "demonstrate"
    ]

    SUMMARY_KEYWORDS = [
        "summarize", "explain", "describe", "what is", "tell me about",
        "overview", "summary", "details about"
    ]

    CUSTOMER_INDICATORS = [
        "customer", "client", "company", "organization", "business"
    ]

    def __init__(self, llm: Optional[LLM] = None):
        """
        Initialize query classifier.

        Args:
            llm: Optional LLM for advanced classification (currently uses rule-based)
        """
        self._llm = llm
        logger.debug("QueryClassifier initialized")

    def classify(self, query: str, selected_offerings: Optional[list] = None) -> Dict:
        """
        Classify a user query to determine the appropriate response mode.

        Args:
            query: User's query text
            selected_offerings: List of offerings selected by user (if any)

        Returns:
            Dictionary with classification results:
            {
                "mode": str,  # problem_solving, pitch_specific, pitch_generic, offering_summary
                "customer_name": str | None,
                "industry": str | None,
                "problem_description": str | None,
                "offering_mentioned": str | None,
                "confidence": float
            }
        """
        query_lower = query.lower()

        # Extract potential customer/company names and industry
        customer_name = self._extract_customer_name(query)
        industry = self._extract_industry(query)

        # Check for offering summary queries (highest priority)
        offering_mentioned = self._extract_offering_name(query)
        if offering_mentioned and any(kw in query_lower for kw in self.SUMMARY_KEYWORDS):
            return {
                "mode": "offering_summary",
                "customer_name": None,
                "industry": None,
                "problem_description": None,
                "offering_mentioned": offering_mentioned,
                "confidence": 0.9
            }

        # Check for problem-solving queries
        has_problem = any(kw in query_lower for kw in self.PROBLEM_KEYWORDS)
        if has_problem and not selected_offerings:
            return {
                "mode": "problem_solving",
                "customer_name": customer_name,
                "industry": industry,
                "problem_description": query,
                "offering_mentioned": None,
                "confidence": 0.85
            }

        # Check for pitch queries
        has_pitch_intent = any(kw in query_lower for kw in self.PITCH_KEYWORDS)
        has_customer_context = any(kw in query_lower for kw in self.CUSTOMER_INDICATORS)

        if has_pitch_intent or (selected_offerings and (customer_name or industry)):
            if customer_name or industry:
                return {
                    "mode": "pitch_specific",
                    "customer_name": customer_name,
                    "industry": industry,
                    "problem_description": query if has_problem else None,
                    "offering_mentioned": None,
                    "confidence": 0.8
                }
            else:
                return {
                    "mode": "pitch_generic",
                    "customer_name": None,
                    "industry": None,
                    "problem_description": None,
                    "offering_mentioned": None,
                    "confidence": 0.75
                }

        # Default: if offerings selected, treat as pitch; otherwise problem-solving
        if selected_offerings:
            return {
                "mode": "pitch_generic",
                "customer_name": customer_name,
                "industry": industry,
                "problem_description": None,
                "offering_mentioned": None,
                "confidence": 0.6
            }
        else:
            return {
                "mode": "problem_solving",
                "customer_name": customer_name,
                "industry": industry,
                "problem_description": query,
                "offering_mentioned": None,
                "confidence": 0.6
            }

    def _extract_customer_name(self, query: str) -> Optional[str]:
        """Extract customer/company name from query."""
        # Look for patterns like "ACME Corp", "XYZ Company", etc.
        patterns = [
            r'(?:for|to|with|at)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+(?:Corp|Inc|LLC|Ltd|Company|Corporation))?)',
            r'(?:customer|client|company)\s+(?:named|called)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)'
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)

        return None

    def _extract_industry(self, query: str) -> Optional[str]:
        """Extract industry from query."""
        industries = [
            "healthcare", "finance", "financial", "banking", "retail", "e-commerce",
            "ecommerce", "manufacturing", "technology", "tech", "education",
            "telecommunications", "telecom", "automotive", "insurance", "energy",
            "hospitality", "real estate", "media", "entertainment", "logistics",
            "transportation", "pharmaceutical", "biotech", "agriculture"
        ]

        query_lower = query.lower()
        for industry in industries:
            if industry in query_lower:
                return industry.capitalize()

        return None

    def _extract_offering_name(self, query: str) -> Optional[str]:
        """Extract offering name mentioned in query."""
        # Common offering names (can be enhanced with metadata manager integration)
        offering_patterns = [
            r'\b(Nexus|Portal|Framework|Platform|Solution|Suite)\b',
            r'\b([A-Z][a-zA-Z]+\s+(?:Framework|Platform|Solution|Suite))\b'
        ]

        for pattern in offering_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
