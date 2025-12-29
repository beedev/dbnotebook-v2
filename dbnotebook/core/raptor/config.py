"""RAPTOR Configuration Constants.

Configuration for Recursive Abstractive Processing for Tree-Organized Retrieval.
These values control clustering behavior, summarization, and tree construction.

Reference: https://arxiv.org/abs/2401.18059
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ClusteringConfig:
    """Configuration for GMM clustering with UMAP dimensionality reduction."""

    # UMAP dimensionality reduction
    umap_n_components: int = 10  # Target dimensions after reduction
    umap_n_neighbors: int = 15  # Local neighborhood size for UMAP
    umap_min_dist: float = 0.1  # Minimum distance between points in embedding
    umap_metric: str = "cosine"  # Distance metric for UMAP

    # GMM clustering
    gmm_probability_threshold: float = 0.3  # Min probability for soft cluster membership
    min_cluster_size: int = 3  # Minimum nodes per cluster
    max_cluster_size: int = 10  # Maximum nodes per cluster (split if larger)
    max_clusters: int = 50  # Maximum clusters per level (safety limit)

    # Clustering behavior
    random_state: int = 42  # For reproducibility
    n_init: int = 10  # GMM initialization attempts


@dataclass
class SummarizationConfig:
    """Configuration for LLM-based cluster summarization."""

    # Token limits
    max_input_tokens: int = 6000  # Max tokens for chunks being summarized
    summary_max_tokens: int = 500  # Max tokens for generated summary

    # Content limits
    max_chunks_per_summary: int = 10  # Max chunks to include in one summary

    # LLM prompts
    cluster_summary_prompt: str = """You are an expert summarizer. Below are related text chunks from a document that have been grouped together by semantic similarity.

Create a comprehensive summary that:
1. Captures the main themes and key points across all chunks
2. Preserves important details, facts, and figures
3. Maintains logical flow and coherence
4. Is self-contained and understandable without the original chunks

CHUNKS TO SUMMARIZE:
{chunks}

COMPREHENSIVE SUMMARY:"""

    root_summary_prompt: str = """You are an expert summarizer. Below are summaries from different sections of a document.

Create a high-level executive summary that:
1. Provides an overview of the entire document's content
2. Highlights the most important themes and conclusions
3. Notes any key relationships between different sections
4. Is suitable for answering "summarize this document" queries

SECTION SUMMARIES:
{summaries}

DOCUMENT SUMMARY:"""


@dataclass
class TreeBuildingConfig:
    """Configuration for RAPTOR tree construction."""

    # Tree structure
    max_tree_depth: int = 4  # Maximum levels in the tree (0=chunks, 1-3=summaries)
    min_nodes_to_cluster: int = 5  # Minimum nodes needed to create a new level

    # Processing
    batch_size: int = 50  # Nodes to process in one batch
    embedding_batch_size: int = 8  # Embeddings to generate at once

    # Concurrency
    max_concurrent_summaries: int = 3  # Parallel LLM calls for summarization

    # Retry behavior
    max_retries: int = 3  # Retry failed operations
    retry_delay_seconds: float = 1.0  # Delay between retries


@dataclass
class RetrievalConfig:
    """Configuration for RAPTOR-aware retrieval."""

    # Level selection for different query types
    # Always include L0 chunks since they contain the actual content
    summary_query_levels: List[int] = field(default_factory=lambda: [0, 1, 2, 3])  # All levels - summaries boost ranking
    detail_query_levels: List[int] = field(default_factory=lambda: [0, 1])  # L0 chunks + L1 cluster summaries

    # Intent detection keywords
    summary_keywords: List[str] = field(default_factory=lambda: [
        "summarize", "summary", "overview", "main points",
        "key takeaways", "themes", "gist", "brief",
        "what is this about", "tldr", "highlights",
        "main ideas", "general idea", "big picture"
    ])

    detail_keywords: List[str] = field(default_factory=lambda: [
        "specific", "detail", "exactly", "quote",
        "what does it say about", "where", "when",
        "how many", "what is the", "explain",
        "section", "page", "paragraph"
    ])

    # Retrieval parameters
    top_k_per_level: int = 6  # Results to retrieve per tree level
    rerank_top_k: int = 6  # Final results after reranking
    min_similarity_threshold: float = 0.3  # Minimum similarity for inclusion

    # Score boosting for level-aware retrieval
    summary_level_boost: float = 1.5  # Boost for higher-level nodes in summary queries
    detail_level_boost: float = 1.3  # Boost for level-0 nodes in detail queries

    # Hybrid retrieval (BM25 + Vector fusion)
    use_hybrid_retrieval: bool = True  # Enable BM25 keyword search + vector fusion
    bm25_weight: float = 0.5  # Weight for BM25 keyword matching (0.0-1.0) - higher for structured content
    vector_weight: float = 0.5  # Weight for vector semantic search (0.0-1.0)

    # Query expansion for hybrid retrieval
    num_query_variations: int = 3  # Generate additional query variations for better coverage


@dataclass
class RAPTORConfig:
    """Master configuration for RAPTOR system."""

    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    summarization: SummarizationConfig = field(default_factory=SummarizationConfig)
    tree_building: TreeBuildingConfig = field(default_factory=TreeBuildingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)

    # Feature flags
    enabled: bool = True  # Enable RAPTOR processing
    auto_build_on_upload: bool = True  # Auto-build tree after document upload
    fallback_to_flat_retrieval: bool = True  # Use flat retrieval if tree not built

    @classmethod
    def default(cls) -> "RAPTORConfig":
        """Create default configuration."""
        return cls()

    @classmethod
    def fast(cls) -> "RAPTORConfig":
        """Create configuration optimized for speed (fewer clusters, smaller summaries)."""
        return cls(
            clustering=ClusteringConfig(
                max_cluster_size=15,
                umap_n_components=5,
            ),
            summarization=SummarizationConfig(
                summary_max_tokens=300,
                max_chunks_per_summary=15,
            ),
            tree_building=TreeBuildingConfig(
                max_tree_depth=3,
                min_nodes_to_cluster=8,
            ),
        )

    @classmethod
    def thorough(cls) -> "RAPTORConfig":
        """Create configuration for maximum quality (more clusters, detailed summaries)."""
        return cls(
            clustering=ClusteringConfig(
                min_cluster_size=2,
                max_cluster_size=6,
                gmm_probability_threshold=0.2,
            ),
            summarization=SummarizationConfig(
                summary_max_tokens=800,
                max_chunks_per_summary=6,
            ),
            tree_building=TreeBuildingConfig(
                max_tree_depth=5,
                min_nodes_to_cluster=3,
            ),
        )


# Default configuration instance
DEFAULT_CONFIG = RAPTORConfig.default()
