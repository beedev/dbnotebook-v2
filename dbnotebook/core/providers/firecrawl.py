"""Firecrawl Web Search provider implementation."""

import logging
import os
from typing import List, Dict, Any, Optional

from ..interfaces.web_content import WebSearchProvider, WebSearchResult
from ...setting import get_settings, RAGSettings

logger = logging.getLogger(__name__)


class FirecrawlSearchProvider(WebSearchProvider):
    """
    Firecrawl Web Search provider.

    Provides web search capabilities using Firecrawl's /search endpoint.
    Firecrawl is designed specifically for LLM-ready content extraction.

    API Documentation: https://docs.firecrawl.dev/
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        setting: Optional[RAGSettings] = None,
    ):
        """
        Initialize Firecrawl Search provider.

        Args:
            api_key: Firecrawl API key (uses FIRECRAWL_API_KEY env var if not provided)
            setting: RAG settings instance
        """
        self._setting = setting or get_settings()
        self._api_key = api_key or os.getenv("FIRECRAWL_API_KEY")

        if not self._api_key:
            raise ValueError(
                "Firecrawl API key required. Set FIRECRAWL_API_KEY environment variable."
            )

        self._client = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the Firecrawl client."""
        try:
            from firecrawl import Firecrawl

            self._client = Firecrawl(api_key=self._api_key)
            logger.debug("Initialized Firecrawl Search provider")
        except ImportError:
            raise ImportError(
                "firecrawl-py not installed. "
                "Run: pip install firecrawl-py"
            )

    def search(
        self,
        query: str,
        num_results: int = 5,
        **kwargs
    ) -> List[WebSearchResult]:
        """
        Search the web for a given query using Firecrawl.

        Args:
            query: Search query string
            num_results: Number of results to return (1-20)
            **kwargs: Additional options (scrape_options, etc.)

        Returns:
            List of WebSearchResult objects
        """
        if self._client is None:
            raise RuntimeError("Firecrawl client not initialized")

        num_results = max(1, min(num_results, 20))

        try:
            # Firecrawl search API (v2)
            response = self._client.search(
                query=query,
                limit=num_results,
                **kwargs
            )

            results = []
            # Response is a SearchData object with 'web' attribute (v2 API)
            if hasattr(response, 'web') and response.web:
                data = response.web
            elif hasattr(response, 'data'):
                data = response.data
            elif isinstance(response, dict):
                data = response.get("web", response.get("data", []))
            else:
                data = response if isinstance(response, list) else []

            for idx, item in enumerate(data):
                # Handle both dict and object responses
                if hasattr(item, '__dict__'):
                    # Object response - convert to dict-like access
                    url = getattr(item, 'url', '') or ''
                    title = getattr(item, 'title', None) or url or 'Untitled'
                    description = getattr(item, 'description', '') or ''
                    if not description:
                        markdown = getattr(item, 'markdown', '') or ''
                        description = markdown[:300] if markdown else ''
                    score = getattr(item, 'score', None) or (1.0 - (idx * 0.1))
                    markdown = getattr(item, 'markdown', None)
                    links = getattr(item, 'links', []) or []
                else:
                    # Dict response
                    url = item.get("url", "")
                    title = item.get("title", item.get("url", "Untitled"))
                    description = item.get("description", item.get("markdown", "")[:300])
                    score = item.get("score", 1.0 - (idx * 0.1))
                    markdown = item.get("markdown")
                    links = item.get("links", [])

                result = WebSearchResult(
                    url=url,
                    title=title,
                    description=description,
                    score=score,
                    metadata={
                        "markdown": markdown,
                        "links": links,
                        "raw_data": item if isinstance(item, dict) else str(item)
                    }
                )
                results.append(result)

            logger.info(f"Firecrawl search returned {len(results)} results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Firecrawl search failed: {e}")
            raise RuntimeError(f"Failed to search: {e}") from e

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.

        Returns:
            Dictionary with provider capabilities and settings
        """
        return {
            "name": "firecrawl",
            "display_name": "Firecrawl Web Search",
            "available": self._client is not None,
            "max_results": 20,
            "capabilities": [
                "web_search",
                "markdown_extraction",
                "link_extraction",
            ],
            "documentation": "https://docs.firecrawl.dev/",
        }

    @property
    def name(self) -> str:
        """Get the provider name identifier."""
        return "firecrawl"

    def validate(self) -> bool:
        """
        Validate provider configuration and connectivity.

        Returns:
            True if provider is properly configured
        """
        try:
            if self._client is None:
                return False

            # Try a simple search to verify API key works
            # This is a lightweight check
            info = self.get_provider_info()
            return info.get("available", False)
        except Exception as e:
            logger.warning(f"Firecrawl validation failed: {e}")
            return False
