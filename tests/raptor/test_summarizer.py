"""Tests for RAPTOR summarizer module."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from llama_index.core.schema import TextNode

from dbnotebook.core.raptor.summarizer import (
    SummaryNode,
    RAPTORSummarizer,
    create_summarizer,
)
from dbnotebook.core.raptor.clustering import Cluster
from dbnotebook.core.raptor.config import SummarizationConfig


def create_mock_cluster(n_nodes: int = 5) -> Cluster:
    """Create a mock cluster for testing."""
    nodes = []
    for i in range(n_nodes):
        node = TextNode(
            id_=f"node_{i}",
            text=f"This is test content for node {i}. It contains important information about topic {i}.",
        )
        nodes.append(node)

    return Cluster(
        cluster_id="test_cluster",
        node_ids=[n.node_id for n in nodes],
        nodes=nodes,
    )


def create_mock_llm():
    """Create a mock LLM for testing."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a summary of the cluster content. It captures the main themes."

    mock_llm.complete.return_value = mock_response
    mock_llm.acomplete = AsyncMock(return_value=mock_response)

    return mock_llm


class TestSummaryNode:
    """Tests for SummaryNode dataclass."""

    def test_summary_node_creation(self):
        """Test creating a summary node."""
        node = SummaryNode(
            node_id="summary_1",
            text="This is a summary.",
            child_node_ids=["node_1", "node_2"],
            tree_level=1,
            cluster_id="cluster_1",
            token_count=10,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        assert node.node_id == "summary_1"
        assert node.tree_level == 1
        assert len(node.child_node_ids) == 2

    def test_to_text_node(self):
        """Test converting to TextNode."""
        summary = SummaryNode(
            node_id="summary_1",
            text="This is a summary.",
            child_node_ids=["node_1", "node_2"],
            tree_level=1,
            cluster_id="cluster_1",
            token_count=10,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        text_node = summary.to_text_node()

        assert text_node.id_ == "summary_1"
        assert text_node.text == "This is a summary."
        assert text_node.metadata["node_type"] == "raptor_summary"
        assert text_node.metadata["tree_level"] == 1
        assert text_node.metadata["source_id"] == "source_1"


class TestRAPTORSummarizer:
    """Tests for RAPTORSummarizer class."""

    def test_init(self):
        """Test summarizer initialization."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)

        assert summarizer.llm == mock_llm
        assert summarizer.config is not None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        mock_llm = create_mock_llm()
        config = SummarizationConfig(summary_max_tokens=300)
        summarizer = RAPTORSummarizer(mock_llm, config)

        assert summarizer.config.summary_max_tokens == 300

    def test_summarize_cluster_sync(self):
        """Test synchronous cluster summarization."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)
        cluster = create_mock_cluster(5)

        summary = summarizer.summarize_cluster_sync(
            cluster=cluster,
            tree_level=1,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        assert summary is not None
        assert summary.tree_level == 1
        assert summary.source_id == "source_1"
        assert len(summary.child_node_ids) == 5
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_cluster_async(self):
        """Test asynchronous cluster summarization."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)
        cluster = create_mock_cluster(5)

        summary = await summarizer.summarize_cluster(
            cluster=cluster,
            tree_level=1,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        assert summary is not None
        assert summary.tree_level == 1
        mock_llm.acomplete.assert_called_once()

    def test_summarize_summaries_sync(self):
        """Test synchronous summary of summaries."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)

        summary_nodes = [
            SummaryNode(
                node_id=f"sum_{i}",
                text=f"Summary {i} content.",
                child_node_ids=[f"node_{i}"],
                tree_level=1,
                cluster_id=f"cluster_{i}",
                token_count=10,
                source_id="source_1",
                notebook_id="notebook_1",
            )
            for i in range(3)
        ]

        root_summary = summarizer.summarize_summaries_sync(
            summary_nodes=summary_nodes,
            tree_level=2,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        assert root_summary is not None
        assert root_summary.tree_level == 2
        assert len(root_summary.child_node_ids) == 3

    def test_prepare_chunks_text(self):
        """Test chunk text preparation."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)
        cluster = create_mock_cluster(3)

        chunks_text = summarizer._prepare_chunks_text(cluster)

        assert "[Chunk 1]" in chunks_text
        assert "[Chunk 2]" in chunks_text
        assert "[Chunk 3]" in chunks_text

    def test_prepare_chunks_text_truncation(self):
        """Test chunk text truncation for large clusters."""
        mock_llm = create_mock_llm()
        config = SummarizationConfig(max_chunks_per_summary=2)
        summarizer = RAPTORSummarizer(mock_llm, config)
        cluster = create_mock_cluster(5)

        chunks_text = summarizer._prepare_chunks_text(cluster)

        # Should only include 2 chunks
        assert "[Chunk 1]" in chunks_text
        assert "[Chunk 2]" in chunks_text
        assert "[Chunk 3]" not in chunks_text

    def test_fallback_summary(self):
        """Test fallback summary when LLM fails."""
        mock_llm = create_mock_llm()
        summarizer = RAPTORSummarizer(mock_llm)
        cluster = create_mock_cluster(3)

        fallback = summarizer._fallback_summary(cluster)

        assert len(fallback) > 0
        # Should contain first sentences from chunks

    def test_llm_failure_uses_fallback(self):
        """Test that LLM failure triggers fallback."""
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = Exception("LLM error")
        summarizer = RAPTORSummarizer(mock_llm)
        cluster = create_mock_cluster(3)

        summary = summarizer.summarize_cluster_sync(
            cluster=cluster,
            tree_level=1,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        # Should still return a summary (fallback)
        assert summary is not None
        assert len(summary.text) > 0


class TestCreateSummarizer:
    """Tests for create_summarizer convenience function."""

    def test_create_summarizer(self):
        """Test the convenience function."""
        mock_llm = create_mock_llm()

        summarizer = create_summarizer(mock_llm)

        assert summarizer is not None
        assert isinstance(summarizer, RAPTORSummarizer)

    def test_create_summarizer_with_config(self):
        """Test with custom config."""
        mock_llm = create_mock_llm()
        config = SummarizationConfig(summary_max_tokens=400)

        summarizer = create_summarizer(mock_llm, config)

        assert summarizer.config.summary_max_tokens == 400
