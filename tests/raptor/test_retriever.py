"""Tests for RAPTOR retriever module."""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from llama_index.core.schema import TextNode, NodeWithScore, QueryBundle

from dbnotebook.core.raptor.retriever import (
    RAPTORQueryType,
    RAPTORRetriever,
    create_raptor_retriever,
    has_raptor_tree,
    SUMMARY_KEYWORDS,
    DETAIL_KEYWORDS,
)
from dbnotebook.core.raptor.config import RAPTORConfig


def create_mock_nodes(n: int, tree_level: int = 0) -> list:
    """Create mock TextNodes for testing."""
    nodes = []
    for i in range(n):
        node = TextNode(
            id_=f"node_{tree_level}_{i}",
            text=f"This is test content for node {i} at level {tree_level}.",
            metadata={
                "tree_level": tree_level,
                "source_id": "source_1",
                "notebook_id": "notebook_1",
            },
        )
        node.embedding = np.random.rand(768).tolist()
        nodes.append(node)
    return nodes


class TestQueryTypeDetection:
    """Tests for query type detection."""

    def test_summary_query_detected(self):
        """Test that summary queries are detected."""
        mock_vector_store = MagicMock()
        mock_vector_store.get_nodes_by_tree_level.return_value = create_mock_nodes(5)

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        # Test summary queries
        query_type, confidence = retriever.detect_query_type("summarize this document")
        assert query_type == RAPTORQueryType.SUMMARY
        assert confidence > 0

        query_type, confidence = retriever.detect_query_type("give me an overview")
        assert query_type == RAPTORQueryType.SUMMARY

        query_type, confidence = retriever.detect_query_type("give me a high-level summary")
        assert query_type == RAPTORQueryType.SUMMARY

    def test_detail_query_detected(self):
        """Test that detail queries are detected."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        # Test detail queries
        query_type, confidence = retriever.detect_query_type("what specifically does it say about X")
        assert query_type == RAPTORQueryType.DETAIL

        query_type, confidence = retriever.detect_query_type("give me the exact details")
        assert query_type == RAPTORQueryType.DETAIL

    def test_mixed_query_detected(self):
        """Test that mixed queries are detected."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        # Query with both summary and detail signals
        query_type, confidence = retriever.detect_query_type("summarize specifically")
        assert query_type == RAPTORQueryType.MIXED

    def test_default_to_mixed(self):
        """Test that unknown queries default to mixed."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        query_type, confidence = retriever.detect_query_type("random query without keywords")
        assert query_type == RAPTORQueryType.MIXED
        assert confidence < 0.5


class TestLevelSelection:
    """Tests for tree level selection."""

    def test_summary_levels(self):
        """Test level selection for summary queries."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        levels = retriever.get_levels_for_query_type(RAPTORQueryType.SUMMARY)
        assert 2 in levels or 3 in levels  # Higher levels for summaries

    def test_detail_levels(self):
        """Test level selection for detail queries."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        levels = retriever.get_levels_for_query_type(RAPTORQueryType.DETAIL)
        assert 0 in levels  # Level 0 for details


class TestRAPTORRetriever:
    """Tests for RAPTORRetriever class."""

    def test_init(self):
        """Test retriever initialization."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        assert retriever.notebook_id == "notebook_1"
        assert retriever.config is not None

    def test_init_with_source_ids(self):
        """Test initialization with source IDs."""
        mock_vector_store = MagicMock()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
            source_ids=["source_1", "source_2"],
        )

        assert retriever.source_ids == ["source_1", "source_2"]

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        mock_vector_store = MagicMock()
        config = RAPTORConfig.fast()

        retriever = RAPTORRetriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
            config=config,
        )

        assert retriever.config.tree_building.max_tree_depth == 3


class TestCreateRaptorRetriever:
    """Tests for create_raptor_retriever convenience function."""

    def test_create_retriever(self):
        """Test the convenience function."""
        mock_vector_store = MagicMock()

        retriever = create_raptor_retriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
        )

        assert retriever is not None
        assert isinstance(retriever, RAPTORRetriever)

    def test_create_retriever_with_options(self):
        """Test with all options."""
        mock_vector_store = MagicMock()
        config = RAPTORConfig.thorough()

        retriever = create_raptor_retriever(
            vector_store=mock_vector_store,
            notebook_id="notebook_1",
            source_ids=["source_1"],
            config=config,
            similarity_top_k=5,
        )

        assert retriever.source_ids == ["source_1"]
        assert retriever.similarity_top_k == 5


class TestHasRaptorTree:
    """Tests for has_raptor_tree function."""

    def test_has_tree_true(self):
        """Test when RAPTOR tree exists."""
        mock_vector_store = MagicMock()
        mock_vector_store.get_tree_stats.return_value = {
            "max_level": 2,
            "total_nodes": 50,
        }

        result = has_raptor_tree(mock_vector_store, "source_1", "notebook_1")
        assert result is True

    def test_has_tree_false(self):
        """Test when RAPTOR tree does not exist."""
        mock_vector_store = MagicMock()
        mock_vector_store.get_tree_stats.return_value = {
            "max_level": 0,
            "total_nodes": 10,
        }

        result = has_raptor_tree(mock_vector_store, "source_1", "notebook_1")
        assert result is False

    def test_has_tree_error(self):
        """Test when error occurs."""
        mock_vector_store = MagicMock()
        mock_vector_store.get_tree_stats.side_effect = Exception("Error")

        result = has_raptor_tree(mock_vector_store, "source_1", "notebook_1")
        assert result is False
