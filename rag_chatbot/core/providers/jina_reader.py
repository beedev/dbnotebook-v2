"""Jina Reader Web Scraping provider implementation."""

import logging
import os
import requests
from typing import Dict, Any, Optional

from ..interfaces.web_content import WebScraperProvider, ScrapedContent
from ...setting import get_settings, RAGSettings

logger = logging.getLogger(__name__)


class JinaReaderProvider(WebScraperProvider):
    """
    Jina Reader Web Scraping provider.

    Provides web content extraction using Jina Reader's r.jina.ai endpoint.
    Jina Reader converts web pages to LLM-friendly markdown format.

    API Documentation: https://jina.ai/reader/
    """

    BASE_URL = "https://r.jina.ai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        setting: Optional[RAGSettings] = None,
    ):
        """
        Initialize Jina Reader provider.

        Args:
            api_key: Jina API key for higher rate limits (optional)
            timeout: Request timeout in seconds
            setting: RAG settings instance
        """
        self._setting = setting or get_settings()
        self._api_key = api_key or os.getenv("JINA_API_KEY")
        self._timeout = timeout
        self._session = requests.Session()

        # Set headers
        headers = {
            "Accept": "application/json",
            "X-Return-Format": "markdown",
        }

        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            logger.debug("Initialized Jina Reader with API key")
        else:
            logger.debug("Initialized Jina Reader without API key (rate-limited)")

        self._session.headers.update(headers)

    def scrape(
        self,
        url: str,
        **kwargs
    ) -> ScrapedContent:
        """
        Scrape content from a URL using Jina Reader.

        Args:
            url: URL to scrape
            **kwargs: Additional options (timeout, etc.)

        Returns:
            ScrapedContent object with extracted text
        """
        timeout = kwargs.get("timeout", self._timeout)

        try:
            # Jina Reader API: https://r.jina.ai/{url}
            reader_url = f"{self.BASE_URL}/{url}"

            response = self._session.get(reader_url, timeout=timeout)
            response.raise_for_status()

            # Parse response
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"content": response.text}

            content = data.get("content", data.get("text", response.text))
            title = data.get("title", url)

            # Count words
            word_count = len(content.split())

            result = ScrapedContent(
                url=url,
                title=title,
                content=content,
                word_count=word_count,
                metadata={
                    "description": data.get("description"),
                    "image": data.get("image"),
                    "links": data.get("links", []),
                    "raw_data": data
                }
            )

            logger.info(f"Jina Reader scraped {word_count} words from: {url}")
            return result

        except requests.Timeout:
            logger.error(f"Jina Reader timeout for: {url}")
            raise RuntimeError(f"Timeout scraping URL: {url}")
        except requests.RequestException as e:
            logger.error(f"Jina Reader request failed: {e}")
            raise RuntimeError(f"Failed to scrape URL: {e}") from e
        except Exception as e:
            logger.error(f"Jina Reader scraping failed: {e}")
            raise RuntimeError(f"Failed to scrape: {e}") from e

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.

        Returns:
            Dictionary with provider capabilities and settings
        """
        return {
            "name": "jina_reader",
            "display_name": "Jina Reader",
            "available": True,  # Always available (rate-limited without API key)
            "has_api_key": bool(self._api_key),
            "timeout": self._timeout,
            "capabilities": [
                "web_scraping",
                "markdown_conversion",
                "content_extraction",
                "metadata_extraction",
            ],
            "documentation": "https://jina.ai/reader/",
            "rate_limits": {
                "with_api_key": "200 RPM",
                "without_api_key": "20 RPM"
            }
        }

    @property
    def name(self) -> str:
        """Get the provider name identifier."""
        return "jina_reader"

    def validate(self) -> bool:
        """
        Validate provider configuration and connectivity.

        Returns:
            True if provider is properly configured
        """
        try:
            # Try to scrape a simple test URL
            test_url = "https://example.com"
            result = self.scrape(test_url)
            return bool(result.content)
        except Exception as e:
            logger.warning(f"Jina Reader validation failed: {e}")
            return False

    def preview(self, url: str, max_chars: int = 500) -> ScrapedContent:
        """
        Get a preview of scraped content.

        Args:
            url: URL to preview
            max_chars: Maximum characters in preview

        Returns:
            ScrapedContent with truncated content
        """
        result = self.scrape(url)
        if len(result.content) > max_chars:
            result.content = result.content[:max_chars] + "..."
            result.metadata["truncated"] = True
        return result
