"""Tests for RAPTOR configuration module."""

import pytest
from dbnotebook.core.raptor.config import (
    ClusteringConfig,
    SummarizationConfig,
    TreeBuildingConfig,
    RetrievalConfig,
    RAPTORConfig,
    DEFAULT_CONFIG,
)


class TestClusteringConfig:
    """Tests for ClusteringConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ClusteringConfig()

        assert config.umap_n_components == 10
        assert config.umap_n_neighbors == 15
        assert config.gmm_probability_threshold == 0.3
        assert config.min_cluster_size == 3
        assert config.max_cluster_size == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClusteringConfig(
            min_cluster_size=5,
            max_cluster_size=15,
        )

        assert config.min_cluster_size == 5
        assert config.max_cluster_size == 15


class TestSummarizationConfig:
    """Tests for SummarizationConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SummarizationConfig()

        assert config.max_input_tokens == 6000
        assert config.summary_max_tokens == 500
        assert config.max_chunks_per_summary == 10

    def test_prompts_contain_placeholders(self):
        """Test that prompts contain required placeholders."""
        config = SummarizationConfig()

        assert "{chunks}" in config.cluster_summary_prompt
        assert "{summaries}" in config.root_summary_prompt


class TestTreeBuildingConfig:
    """Tests for TreeBuildingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TreeBuildingConfig()

        assert config.max_tree_depth == 4
        assert config.min_nodes_to_cluster == 5
        assert config.batch_size == 50


class TestRetrievalConfig:
    """Tests for RetrievalConfig."""

    def test_default_values(self):
        """Test default configuration values (from config/raptor.yaml)."""
        config = RetrievalConfig()

        # Summary queries include all levels for better coverage
        assert config.summary_query_levels == [0, 1, 2, 3]
        assert 0 in config.detail_query_levels
        assert "summarize" in config.summary_keywords
        assert "specific" in config.detail_keywords


class TestRAPTORConfig:
    """Tests for master RAPTORConfig."""

    def test_default_factory(self):
        """Test default configuration creation."""
        config = RAPTORConfig.default()

        assert config.enabled is True
        assert config.auto_build_on_upload is True
        assert config.fallback_to_flat_retrieval is True
        assert isinstance(config.clustering, ClusteringConfig)
        assert isinstance(config.summarization, SummarizationConfig)

    def test_fast_preset(self):
        """Test fast configuration preset (from config/raptor.yaml presets.fast)."""
        config = RAPTORConfig.fast()

        # Fast preset should have larger cluster sizes
        assert config.clustering.max_cluster_size == 15
        # And smaller summaries
        assert config.summarization.summary_max_tokens == 300
        # And shallower tree (config/raptor.yaml sets max_tree_depth: 2)
        assert config.tree_building.max_tree_depth == 2

    def test_thorough_preset(self):
        """Test thorough configuration preset."""
        config = RAPTORConfig.thorough()

        # Thorough preset should have smaller cluster sizes
        assert config.clustering.min_cluster_size == 2
        assert config.clustering.max_cluster_size == 6
        # And larger summaries
        assert config.summarization.summary_max_tokens == 800
        # And deeper tree
        assert config.tree_building.max_tree_depth == 5

    def test_default_config_singleton(self):
        """Test DEFAULT_CONFIG is properly initialized."""
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, RAPTORConfig)
        assert DEFAULT_CONFIG.enabled is True
