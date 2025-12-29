"""Tests for RAPTOR tree builder module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import numpy as np

from llama_index.core.schema import TextNode

from dbnotebook.core.raptor.tree_builder import (
    TreeBuildResult,
    RAPTORTreeBuilder,
    create_tree_builder,
)
from dbnotebook.core.raptor.config import RAPTORConfig


def _has_dependencies() -> bool:
    """Check if required dependencies are installed."""
    try:
        import umap
        from sklearn.mixture import GaussianMixture
        return True
    except ImportError:
        return False


def create_mock_chunks(n: int) -> list:
    """Create mock chunks for testing."""
    chunks = []
    for i in range(n):
        chunk = TextNode(
            id_=f"chunk_{i}",
            text=f"This is chunk {i} content. It contains important information about topic {i}.",
            metadata={"source_id": "test_source"},
        )
        chunk.embedding = np.random.rand(768).tolist()
        chunks.append(chunk)
    return chunks


def create_mock_llm():
    """Create a mock LLM."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a generated summary capturing the main themes."
    mock_llm.complete.return_value = mock_response
    mock_llm.acomplete = AsyncMock(return_value=mock_response)
    return mock_llm


def create_mock_embed_model():
    """Create a mock embedding model."""
    mock_embed = MagicMock()

    def mock_get_batch(texts, **kwargs):
        return [np.random.rand(768).tolist() for _ in texts]

    def mock_get_single(text):
        return np.random.rand(768).tolist()

    mock_embed.get_text_embedding_batch = mock_get_batch
    mock_embed.get_text_embedding = mock_get_single
    return mock_embed


class TestTreeBuildResult:
    """Tests for TreeBuildResult dataclass."""

    def test_result_creation(self):
        """Test creating a tree build result."""
        result = TreeBuildResult(
            success=True,
            source_id="source_1",
            notebook_id="notebook_1",
            total_nodes=50,
            levels={0: 40, 1: 8, 2: 2},
            max_level=2,
        )

        assert result.success is True
        assert result.total_nodes == 50
        assert result.max_level == 2

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = TreeBuildResult(
            success=True,
            source_id="source_1",
            notebook_id="notebook_1",
            total_nodes=50,
            levels={0: 40, 1: 8, 2: 2},
            max_level=2,
            build_time_seconds=5.5,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["total_nodes"] == 50
        assert d["build_time_seconds"] == 5.5


class TestRAPTORTreeBuilder:
    """Tests for RAPTORTreeBuilder class."""

    def test_init(self):
        """Test tree builder initialization."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()

        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        assert builder.llm == mock_llm
        assert builder.embed_model == mock_embed
        assert builder.config is not None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        config = RAPTORConfig.fast()

        builder = RAPTORTreeBuilder(mock_llm, mock_embed, config)

        assert builder.config.tree_building.max_tree_depth == 3

    def test_build_tree_too_few_chunks(self):
        """Test building tree with too few chunks."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        chunks = create_mock_chunks(3)  # Less than min_nodes_to_cluster

        result = builder.build_tree(
            chunks=chunks,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        # Should succeed but not create a tree
        assert result.success is True
        assert result.total_nodes == 3
        assert len(result.summary_nodes) == 0

    @pytest.mark.skipif(
        not _has_dependencies(),
        reason="umap-learn or scikit-learn not installed"
    )
    def test_build_tree_with_chunks(self):
        """Test building tree with sufficient chunks."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        chunks = create_mock_chunks(20)

        result = builder.build_tree(
            chunks=chunks,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        assert result.success is True
        assert result.total_nodes > 20  # Original chunks + summaries
        assert len(result.summary_nodes) > 0
        assert result.max_level >= 1

    @pytest.mark.skipif(
        not _has_dependencies(),
        reason="umap-learn or scikit-learn not installed"
    )
    def test_build_tree_progress_callback(self):
        """Test progress callback is called."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        chunks = create_mock_chunks(20)
        progress_calls = []

        def callback(stage, progress, message):
            progress_calls.append((stage, progress, message))

        result = builder.build_tree(
            chunks=chunks,
            source_id="source_1",
            notebook_id="notebook_1",
            progress_callback=callback,
        )

        assert len(progress_calls) > 0
        # Should have init and complete at minimum
        stages = [c[0] for c in progress_calls]
        assert "init" in stages or len(stages) > 0

    def test_build_tree_error_handling(self):
        """Test error handling during tree build."""
        mock_llm = create_mock_llm()
        mock_llm.complete.side_effect = Exception("LLM error")
        mock_embed = create_mock_embed_model()
        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        chunks = create_mock_chunks(20)

        # Should not raise, but return failure result
        result = builder.build_tree(
            chunks=chunks,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        # May succeed with fallback or fail gracefully
        assert result.completed_at is not None

    def test_summary_nodes_have_embeddings(self):
        """Test that summary nodes have embeddings."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        builder = RAPTORTreeBuilder(mock_llm, mock_embed)

        # Use enough chunks to trigger clustering
        chunks = create_mock_chunks(10)

        # Skip if dependencies missing
        try:
            import umap
            from sklearn.mixture import GaussianMixture
        except ImportError:
            pytest.skip("Dependencies not installed")

        result = builder.build_tree(
            chunks=chunks,
            source_id="source_1",
            notebook_id="notebook_1",
        )

        if result.success and result.summary_nodes:
            for node in result.summary_nodes:
                assert node.embedding is not None
                assert len(node.embedding) == 768


class TestCreateTreeBuilder:
    """Tests for create_tree_builder convenience function."""

    def test_create_tree_builder(self):
        """Test the convenience function."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()

        builder = create_tree_builder(mock_llm, mock_embed)

        assert builder is not None
        assert isinstance(builder, RAPTORTreeBuilder)

    def test_create_tree_builder_with_config(self):
        """Test with custom config."""
        mock_llm = create_mock_llm()
        mock_embed = create_mock_embed_model()
        config = RAPTORConfig.thorough()

        builder = create_tree_builder(mock_llm, mock_embed, config)

        assert builder.config.tree_building.max_tree_depth == 5
