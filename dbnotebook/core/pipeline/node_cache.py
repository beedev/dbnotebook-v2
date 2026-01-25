"""Thread-safe node caching with TTL for multi-user RAG pipelines.

Provides efficient caching of document nodes per notebook to avoid
repeated database queries. Cache entries expire after TTL.

Usage:
    cache = NodeCache(vector_store, ttl=300)
    nodes = cache.get(notebook_id)  # Thread-safe
    cache.invalidate(notebook_id)   # Invalidate specific notebook
    cache.clear()                   # Clear all
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Tuple

from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)


class NodeCache:
    """Thread-safe node cache with TTL for multi-user access.

    Caches document nodes per notebook to avoid repeated DB queries.
    Cache is invalidated when:
    - TTL expires (default: 5 minutes)
    - Explicitly invalidated (e.g., after document upload)

    Attributes:
        vector_store: PGVectorStore instance for loading nodes
        ttl: Time-to-live in seconds (default: 300)
    """

    def __init__(
        self,
        vector_store,
        ttl: int = 300,
    ):
        """Initialize the node cache.

        Args:
            vector_store: PGVectorStore instance with get_nodes_by_notebook_sql method
            ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self._vector_store = vector_store
        self._ttl = ttl
        self._cache: Dict[str, Tuple[List[TextNode], float, int]] = {}
        self._lock = threading.Lock()

    def get(self, notebook_id: str) -> List[TextNode]:
        """Get nodes for a notebook with caching.

        Thread-safe for multi-user concurrent access.

        Args:
            notebook_id: UUID of the notebook

        Returns:
            List of TextNode objects for the notebook
        """
        with self._lock:
            current_time = time.time()

            # Check cache
            if notebook_id in self._cache:
                nodes, timestamp, cached_count = self._cache[notebook_id]

                # Check TTL
                if current_time - timestamp < self._ttl:
                    logger.debug(f"Cache hit for notebook {notebook_id}: {len(nodes)} nodes")
                    return nodes
                else:
                    logger.debug(f"Cache expired for notebook {notebook_id}")

            # Cache miss - load from DB
            start_time = time.time()
            nodes = self._vector_store.get_nodes_by_notebook_sql(notebook_id)
            load_time_ms = int((time.time() - start_time) * 1000)

            # Store in cache
            self._cache[notebook_id] = (nodes, current_time, len(nodes))
            logger.info(
                f"Cached {len(nodes)} nodes for notebook {notebook_id} "
                f"(loaded in {load_time_ms}ms)"
            )

            return nodes

    def invalidate(self, notebook_id: Optional[str] = None) -> None:
        """Invalidate cache for a notebook or all notebooks.

        Call this after document upload/delete to ensure fresh nodes.
        Thread-safe for multi-user concurrent access.

        Args:
            notebook_id: Specific notebook to invalidate, or None for all
        """
        with self._lock:
            if notebook_id:
                if notebook_id in self._cache:
                    del self._cache[notebook_id]
                    logger.debug(f"Invalidated node cache for notebook {notebook_id}")
            else:
                self._cache.clear()
                logger.debug("Invalidated all node caches")

    def clear(self) -> None:
        """Clear all cached nodes."""
        self.invalidate()

    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dict with cache stats (notebook_count, total_nodes, oldest_entry)
        """
        with self._lock:
            if not self._cache:
                return {
                    "notebook_count": 0,
                    "total_nodes": 0,
                    "oldest_entry_age_sec": 0,
                }

            current_time = time.time()
            oldest_age = 0
            total_nodes = 0

            for notebook_id, (nodes, timestamp, count) in self._cache.items():
                age = current_time - timestamp
                if age > oldest_age:
                    oldest_age = age
                total_nodes += len(nodes)

            return {
                "notebook_count": len(self._cache),
                "total_nodes": total_nodes,
                "oldest_entry_age_sec": int(oldest_age),
                "ttl_sec": self._ttl,
            }

    @property
    def ttl(self) -> int:
        """Get the cache TTL in seconds."""
        return self._ttl

    @ttl.setter
    def ttl(self, value: int) -> None:
        """Set the cache TTL in seconds."""
        self._ttl = value
