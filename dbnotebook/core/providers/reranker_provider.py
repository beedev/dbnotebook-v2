"""Singleton Reranker Provider for shared model across components.

This module provides a shared reranker instance to avoid loading the heavy
cross-encoder model (~3GB) multiple times across different components.

Usage:
    from dbnotebook.core.providers.reranker_provider import get_shared_reranker

    reranker = get_shared_reranker(
        model="mixedbread-ai/mxbai-rerank-large-v1",
        top_n=10
    )
"""

import logging
from typing import Optional

from llama_index.core.postprocessor import SentenceTransformerRerank

logger = logging.getLogger(__name__)

# Module-level singleton
_shared_reranker: Optional[SentenceTransformerRerank] = None
_reranker_config: dict = {}


def get_shared_reranker(
    model: str = "mixedbread-ai/mxbai-rerank-large-v1",
    top_n: int = 10
) -> SentenceTransformerRerank:
    """Get or create shared reranker instance.

    Uses singleton pattern to avoid loading ~3GB model multiple times.
    The top_n can be overridden per-call using postprocess_nodes().

    Args:
        model: Reranker model name (default: mixedbread-ai/mxbai-rerank-large-v1)
        top_n: Default top_n for reranking (can be overridden per-call)

    Returns:
        Shared SentenceTransformerRerank instance
    """
    global _shared_reranker, _reranker_config

    # Check if we need to create or recreate the reranker
    if _shared_reranker is None or _reranker_config.get("model") != model:
        logger.info(f"Initializing shared reranker: {model}")
        _shared_reranker = SentenceTransformerRerank(
            model=model,
            top_n=top_n
        )
        _reranker_config = {"model": model, "top_n": top_n}
        logger.info("Shared reranker initialized successfully")

    return _shared_reranker


def clear_shared_reranker() -> None:
    """Clear the shared reranker instance.

    Useful for testing or when you need to release memory.
    """
    global _shared_reranker, _reranker_config
    _shared_reranker = None
    _reranker_config = {}
    logger.debug("Shared reranker cleared")
