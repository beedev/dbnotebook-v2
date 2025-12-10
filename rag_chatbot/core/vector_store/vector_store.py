import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.vector_stores.chroma import ChromaVectorStore
from dotenv import load_dotenv
import chromadb

from ...setting import get_settings, RAGSettings

load_dotenv()

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """Persistent vector store using ChromaDB."""

    def __init__(
        self,
        host: str = "host.docker.internal",
        setting: RAGSettings | None = None,
        persist: bool = True
    ) -> None:
        self._setting = setting or get_settings()
        self._host = host
        self._persist = persist

        # Initialize ChromaDB
        if persist:
            persist_dir = Path(self._setting.storage.persist_dir_chroma)
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(persist_dir)
            )
        else:
            self._chroma_client = chromadb.EphemeralClient()

        self._collection_name = self._setting.storage.collection_name
        self._index_cache: Optional[VectorStoreIndex] = None
        self._cached_node_count: int = 0
        logger.debug("LocalVectorStore initialized with ChromaDB")

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection."""
        return self._chroma_client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def get_index(
        self,
        nodes: List[BaseNode],
        force_rebuild: bool = False
    ) -> Optional[VectorStoreIndex]:
        """
        Get or create vector index with caching.

        Args:
            nodes: List of nodes to index
            force_rebuild: Force rebuild even if cached

        Returns:
            VectorStoreIndex or None if no nodes
        """
        if not nodes:
            return None

        # Return cached index if node count matches and not forcing rebuild
        if (
            not force_rebuild and
            self._index_cache is not None and
            len(nodes) == self._cached_node_count
        ):
            logger.debug("Using cached vector index")
            return self._index_cache

        # Create new index
        try:
            if self._persist:
                # Use ChromaDB for persistence
                collection = self._get_or_create_collection()
                vector_store = ChromaVectorStore(chroma_collection=collection)
                storage_context = StorageContext.from_defaults(
                    vector_store=vector_store
                )
                index = VectorStoreIndex(
                    nodes=nodes,
                    storage_context=storage_context
                )
            else:
                # In-memory index
                index = VectorStoreIndex(nodes=nodes)

            # Cache the index
            self._index_cache = index
            self._cached_node_count = len(nodes)

            logger.debug(f"Created vector index with {len(nodes)} nodes")
            return index

        except Exception as e:
            logger.error(f"Error creating vector index: {e}")
            # Fallback to in-memory index
            index = VectorStoreIndex(nodes=nodes)
            self._index_cache = index
            self._cached_node_count = len(nodes)
            return index

    def get_index_with_filter(
        self,
        nodes: List[BaseNode],
        offering_ids: Optional[List[str]] = None,
        practice_names: Optional[List[str]] = None,
        force_rebuild: bool = False
    ) -> Optional[VectorStoreIndex]:
        """
        Get or create filtered vector index based on offerings or practices.

        Args:
            nodes: List of all available nodes
            offering_ids: List of offering IDs to filter by (OR operation)
            practice_names: List of practice names to filter by (OR operation)
            force_rebuild: Force rebuild even if cached

        Returns:
            VectorStoreIndex with filtered nodes, or None if no matching nodes
        """
        if not nodes:
            return None

        # Filter nodes based on metadata
        filtered_nodes = nodes

        if offering_ids or practice_names:
            filtered_nodes = []

            for node in nodes:
                metadata = node.metadata or {}

                # Check offering filter (by name or id)
                if offering_ids:
                    node_offering_id = metadata.get("offering_id")
                    node_offering_name = metadata.get("offering_name")
                    if (node_offering_id and node_offering_id in offering_ids) or \
                       (node_offering_name and node_offering_name in offering_ids):
                        filtered_nodes.append(node)
                        continue

                # Check practice filter
                if practice_names:
                    node_practice = metadata.get("it_practice")
                    if node_practice and node_practice in practice_names:
                        filtered_nodes.append(node)
                        continue

            if not filtered_nodes:
                logger.warning(
                    f"No nodes found matching filters: "
                    f"offerings={offering_ids}, practices={practice_names}"
                )
                return None

            logger.info(
                f"Filtered {len(filtered_nodes)} nodes from {len(nodes)} total "
                f"(offerings={offering_ids}, practices={practice_names})"
            )

        # Create index with filtered nodes
        return self.get_index(filtered_nodes, force_rebuild=force_rebuild)

    def get_nodes_by_metadata(
        self,
        nodes: List[BaseNode],
        metadata_filters: Dict[str, Any]
    ) -> List[BaseNode]:
        """
        Filter nodes by arbitrary metadata key-value pairs.

        Args:
            nodes: List of nodes to filter
            metadata_filters: Dictionary of metadata key-value pairs to match

        Returns:
            List of nodes matching all specified metadata filters
        """
        if not metadata_filters:
            return nodes

        filtered_nodes = []

        for node in nodes:
            metadata = node.metadata or {}

            # Check if all filter conditions are met (AND operation)
            matches_all = True
            for key, value in metadata_filters.items():
                if metadata.get(key) != value:
                    matches_all = False
                    break

            if matches_all:
                filtered_nodes.append(node)

        logger.debug(
            f"Filtered {len(filtered_nodes)} nodes from {len(nodes)} "
            f"using metadata filters: {metadata_filters}"
        )

        return filtered_nodes

    def clear_collection(self) -> None:
        """Clear the current collection."""
        try:
            self._chroma_client.delete_collection(self._collection_name)
            self._index_cache = None
            self._cached_node_count = 0
            logger.info(f"Cleared collection: {self._collection_name}")
        except Exception as e:
            logger.warning(f"Error clearing collection: {e}")

    def reset(self) -> None:
        """Reset the vector store (clear cache and collection)."""
        self.clear_collection()
        self._index_cache = None
        self._cached_node_count = 0

    def get_collection_stats(self) -> dict:
        """Get statistics about the current collection."""
        try:
            collection = self._get_or_create_collection()
            return {
                "name": self._collection_name,
                "count": collection.count(),
                "cached": self._index_cache is not None,
                "cached_node_count": self._cached_node_count
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
