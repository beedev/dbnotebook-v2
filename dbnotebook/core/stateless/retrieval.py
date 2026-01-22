"""Fast retrieval functions extracted from /api/query pattern.

These functions create per-request retrievers without global state,
making them safe for multi-user concurrent access.
"""

import logging
from typing import List, Optional, Tuple, Any

from llama_index.core import Settings
from llama_index.core.schema import QueryBundle, TextNode, NodeWithScore

logger = logging.getLogger(__name__)


def _unwrap_llm(llm):
    """Extract raw LlamaIndex LLM from wrapper classes like GroqWithBackoff.

    LlamaIndex's resolve_llm() requires instances of the LLM base class.
    Wrapper classes (e.g., GroqWithBackoff for rate limiting) must be
    unwrapped before passing to components like QueryFusionRetriever.

    Args:
        llm: LLM instance or wrapper

    Returns:
        Raw LlamaIndex LLM instance
    """
    if hasattr(llm, 'get_raw_llm'):
        raw_llm = llm.get_raw_llm()
        logger.debug(f"Unwrapped LLM: {type(llm).__name__} → {type(raw_llm).__name__}")
        return raw_llm
    return llm


def create_retriever(
    nodes: List[TextNode],
    notebook_id: str,
    vector_store: Any,
    llm: Optional[Any] = None,
    source_ids: Optional[List[str]] = None,
    language: str = "eng",
    retriever_factory: Optional[Any] = None,
) -> Any:
    """Create a per-request RAPTOR-aware retriever.

    This is thread-safe because it creates a new retriever instance
    for each request rather than reusing a global one.

    Args:
        nodes: Cached nodes for the notebook
        notebook_id: UUID of the notebook to query
        vector_store: PGVectorStore instance
        llm: LLM instance (defaults to Settings.llm)
        source_ids: Optional list of source IDs to filter
        language: Language code for prompts (default: "eng")
        retriever_factory: LocalRetriever instance with get_combined_raptor_retriever method

    Returns:
        RAPTOR-aware retriever instance
    """
    if llm is None:
        llm = Settings.llm

    # Unwrap LLM wrappers (e.g., GroqWithBackoff) for LlamaIndex compatibility
    llm = _unwrap_llm(llm)

    if retriever_factory is None:
        raise ValueError("retriever_factory is required to create per-request retrievers")

    return retriever_factory.get_combined_raptor_retriever(
        llm=llm,
        language=language,
        nodes=nodes,
        vector_store=vector_store,
        notebook_id=notebook_id,
        source_ids=source_ids,
    )


def fast_retrieve(
    nodes: List[TextNode],
    query: str,
    notebook_id: str,
    vector_store: Any,
    retriever_factory: Any,
    llm: Optional[Any] = None,
    source_ids: Optional[List[str]] = None,
    top_k: int = 6,
    language: str = "eng",
) -> List[NodeWithScore]:
    """Fast retrieval using the API pattern - no global state.

    This is the core retrieval function extracted from /api/query.
    It creates a per-request retriever and returns relevant chunks.

    Args:
        nodes: Cached nodes for the notebook
        query: User's query string
        notebook_id: UUID of the notebook to query
        vector_store: PGVectorStore instance
        retriever_factory: LocalRetriever instance
        llm: LLM instance (defaults to Settings.llm)
        source_ids: Optional list of source IDs to filter
        top_k: Maximum number of results to return
        language: Language code for prompts

    Returns:
        List of NodeWithScore containing relevant chunks

    Example:
        nodes = pipeline._get_cached_nodes(notebook_id)
        results = fast_retrieve(
            nodes=nodes,
            query="What are the key findings?",
            notebook_id=notebook_id,
            vector_store=pipeline._vector_store,
            retriever_factory=pipeline._engine._retriever,
        )
    """
    if not nodes:
        logger.debug(f"No nodes found for notebook {notebook_id}")
        return []

    try:
        # Create per-request retriever (thread-safe)
        retriever = create_retriever(
            nodes=nodes,
            notebook_id=notebook_id,
            vector_store=vector_store,
            llm=llm,
            source_ids=source_ids,
            language=language,
            retriever_factory=retriever_factory,
        )

        # Retrieve relevant chunks
        query_bundle = QueryBundle(query_str=query)
        retrieval_results = retriever.retrieve(query_bundle)

        # Limit to top_k
        return retrieval_results[:top_k]

    except Exception as e:
        logger.warning(f"Retrieval failed [{type(e).__name__}]: {e}", exc_info=True)
        return []


def get_raptor_summaries(
    query: str,
    notebook_id: str,
    vector_store: Any,
    embed_model: Optional[Any] = None,
    top_k: int = 5,
    min_score: float = 0.3,
) -> List[Tuple[TextNode, float]]:
    """Get RAPTOR hierarchical summaries for query context.

    RAPTOR summaries provide high-level document understanding
    that complements chunk-level retrieval.

    Args:
        query: User's query string
        notebook_id: UUID of the notebook
        vector_store: PGVectorStore instance with get_top_raptor_summaries method
        embed_model: Embedding model (defaults to Settings.embed_model)
        top_k: Maximum number of summaries to return
        min_score: Minimum relevance score threshold

    Returns:
        List of (TextNode, score) tuples for relevant summaries

    Example:
        summaries = get_raptor_summaries(
            query="What are the key findings?",
            notebook_id=notebook_id,
            vector_store=pipeline._vector_store,
        )
    """
    if not hasattr(vector_store, 'get_top_raptor_summaries'):
        logger.debug("Vector store does not support RAPTOR summaries")
        return []

    try:
        if embed_model is None:
            embed_model = Settings.embed_model

        # Get query embedding for similarity search
        query_embedding = embed_model.get_query_embedding(query)

        # Bounded lookup: max top_k summaries, tree_level >= 1
        raptor_results = vector_store.get_top_raptor_summaries(
            notebook_id=notebook_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # Filter by relevance threshold
        filtered_summaries = [
            (node, score) for node, score in raptor_results
            if score >= min_score
        ]

        if filtered_summaries:
            logger.debug(f"Retrieved {len(filtered_summaries)} RAPTOR summaries for query")

        return filtered_summaries

    except Exception as e:
        logger.debug(f"RAPTOR summaries unavailable: {e}")
        return []
