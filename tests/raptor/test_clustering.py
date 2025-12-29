"""Tests for RAPTOR clustering module."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from llama_index.core.schema import TextNode

from dbnotebook.core.raptor.clustering import (
    Cluster,
    RAPTORClustering,
    cluster_nodes,
)
from dbnotebook.core.raptor.config import ClusteringConfig


def _has_umap_sklearn() -> bool:
    """Check if umap and sklearn are installed."""
    try:
        import umap
        from sklearn.mixture import GaussianMixture
        return True
    except ImportError:
        return False


def create_mock_nodes(n: int, with_embeddings: bool = True) -> list:
    """Create mock TextNodes for testing."""
    nodes = []
    for i in range(n):
        node = TextNode(
            id_=f"node_{i}",
            text=f"This is test content for node {i}. It contains some sample text.",
        )
        if with_embeddings:
            # Create random embedding
            node.embedding = np.random.rand(768).tolist()
        nodes.append(node)
    return nodes


class TestCluster:
    """Tests for Cluster dataclass."""

    def test_cluster_creation(self):
        """Test creating a cluster."""
        nodes = create_mock_nodes(3)
        cluster = Cluster(
            cluster_id="test_cluster",
            node_ids=[n.node_id for n in nodes],
            nodes=nodes,
        )

        assert cluster.cluster_id == "test_cluster"
        assert cluster.size == 3
        assert len(cluster.node_ids) == 3

    def test_get_texts(self):
        """Test getting texts from cluster."""
        nodes = create_mock_nodes(3)
        cluster = Cluster(
            cluster_id="test_cluster",
            node_ids=[n.node_id for n in nodes],
            nodes=nodes,
        )

        texts = cluster.get_texts()
        assert len(texts) == 3
        assert all("test content" in t for t in texts)


class TestRAPTORClustering:
    """Tests for RAPTORClustering class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        clustering = RAPTORClustering()
        assert clustering.config is not None
        assert clustering.config.min_cluster_size == 3

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = ClusteringConfig(min_cluster_size=5)
        clustering = RAPTORClustering(config)
        assert clustering.config.min_cluster_size == 5

    def test_cluster_nodes_too_few(self):
        """Test clustering with too few nodes returns single cluster."""
        nodes = create_mock_nodes(2)  # Less than min_cluster_size
        clustering = RAPTORClustering()

        clusters = clustering.cluster_nodes(nodes)

        assert len(clusters) == 1
        assert clusters[0].size == 2

    def test_cluster_nodes_no_embeddings(self):
        """Test clustering without embeddings returns single cluster."""
        nodes = create_mock_nodes(10, with_embeddings=False)
        clustering = RAPTORClustering()

        clusters = clustering.cluster_nodes(nodes)

        assert len(clusters) == 1

    def test_create_single_cluster(self):
        """Test creating a single cluster from nodes."""
        nodes = create_mock_nodes(5)
        clustering = RAPTORClustering()

        cluster = clustering._create_single_cluster(nodes)

        assert cluster.size == 5
        assert len(cluster.probability_scores) == 5
        assert all(p == 1.0 for p in cluster.probability_scores)

    def test_extract_embeddings(self):
        """Test extracting embeddings from nodes."""
        nodes = create_mock_nodes(5, with_embeddings=True)
        clustering = RAPTORClustering()

        embeddings = clustering._extract_embeddings(nodes)

        assert embeddings is not None
        assert embeddings.shape == (5, 768)

    def test_extract_embeddings_missing(self):
        """Test extracting embeddings when some are missing."""
        nodes = create_mock_nodes(5, with_embeddings=True)
        nodes[2].embedding = None  # Remove one embedding
        clustering = RAPTORClustering()

        embeddings = clustering._extract_embeddings(nodes)

        assert embeddings is None

    def test_estimate_n_clusters(self):
        """Test cluster count estimation."""
        clustering = RAPTORClustering()

        # Small dataset
        n = clustering._estimate_n_clusters(10)
        assert n >= 2

        # Medium dataset
        n = clustering._estimate_n_clusters(50)
        assert 2 <= n <= 10

        # Large dataset
        n = clustering._estimate_n_clusters(200)
        assert n <= clustering.config.max_clusters

    @pytest.mark.skipif(
        not _has_umap_sklearn(),
        reason="umap-learn or scikit-learn not installed"
    )
    def test_cluster_nodes_with_embeddings(self):
        """Test full clustering with embeddings (requires umap and sklearn)."""
        # Create nodes with more distinct embeddings
        nodes = create_mock_nodes(20, with_embeddings=True)
        clustering = RAPTORClustering()

        clusters = clustering.cluster_nodes(nodes)

        # Should create multiple clusters
        assert len(clusters) >= 1
        # All nodes should be in at least one cluster
        all_node_ids = set()
        for cluster in clusters:
            all_node_ids.update(cluster.node_ids)
        assert len(all_node_ids) == 20


class TestClusterNodesFunction:
    """Tests for cluster_nodes convenience function."""

    def test_convenience_function(self):
        """Test the convenience function works."""
        nodes = create_mock_nodes(5)

        clusters = cluster_nodes(nodes)

        assert len(clusters) >= 1
