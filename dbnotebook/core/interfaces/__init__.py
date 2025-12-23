"""Abstract interfaces for swappable RAG components."""

from .retrieval import RetrievalStrategy
from .llm import LLMProvider
from .embedding import EmbeddingProvider
from .processor import ContentProcessor
from .image_generation import ImageGenerationProvider
from .web_content import WebSearchProvider, WebScraperProvider, WebSearchResult, ScrapedContent
from .vision import VisionProvider, VisionAnalysisResult

__all__ = [
    "RetrievalStrategy",
    "LLMProvider",
    "EmbeddingProvider",
    "ContentProcessor",
    "ImageGenerationProvider",
    "WebSearchProvider",
    "WebScraperProvider",
    "WebSearchResult",
    "ScrapedContent",
    "VisionProvider",
    "VisionAnalysisResult",
]
