"""
PGVectorStore - PostgreSQL + pgvector based vector store.

Replaces ChromaDB with PostgreSQL pgvector for unified database architecture.
Benefits:
- O(log n) metadata filtering via SQL indexes
- Native hybrid search (BM25 + vector)
- ACID transactions across metadata + vectors
- Incremental vector updates (no index rebuild)
"""

import os
import logging
from typing import List, Optional, Dict, Any

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import BaseNode, TextNode
from llama_index.vector_stores.postgres import PGVectorStore as LlamaPGVectorStore
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ...setting import get_settings, RAGSettings

load_dotenv()

logger = logging.getLogger(__name__)


class PGVectorStore:
    """
    PostgreSQL + pgvector based vector store.

    Drop-in replacement for LocalVectorStore (ChromaDB) with enhanced features:
    - SQL-native metadata filtering (O(log n) vs O(n) client-side)
    - Incremental add/delete without full index rebuild
    - Unified PostgreSQL backend for all data
    """

    def __init__(
        self,
        host: str = "localhost",
        setting: RAGSettings | None = None,
        persist: bool = True
    ) -> None:
        self._setting = setting or get_settings()
        self._host = host
        self._persist = persist

        # PostgreSQL connection settings from environment
        self._db_host = os.getenv("POSTGRES_HOST", "localhost")
        self._db_port = int(os.getenv("POSTGRES_PORT", "5433"))
        self._db_name = os.getenv("POSTGRES_DB", "rag_chatbot_dev")
        self._db_user = os.getenv("POSTGRES_USER", "postgres")
        self._db_password = os.getenv("POSTGRES_PASSWORD", "root")

        # pgvector settings
        self._table_name = os.getenv("PGVECTOR_TABLE_NAME", "embeddings")
        self._embed_dim = int(os.getenv("PGVECTOR_EMBED_DIM", "768"))

        # Build connection URL
        self._connection_string = (
            f"postgresql://{self._db_user}:{self._db_password}@"
            f"{self._db_host}:{self._db_port}/{self._db_name}"
        )

        # Initialize SQLAlchemy engine for direct queries
        self._engine = create_engine(self._connection_string)
        self._Session = sessionmaker(bind=self._engine)

        # Initialize LlamaIndex PGVectorStore
        self._vector_store = self._create_vector_store()

        # LlamaIndex prefixes table names with "data_"
        self._actual_table_name = f"data_{self._table_name}"

        # Index cache
        self._index_cache: Optional[VectorStoreIndex] = None
        self._cached_node_count: int = 0

        logger.info(
            f"PGVectorStore initialized: {self._db_host}:{self._db_port}/{self._db_name}, "
            f"table={self._actual_table_name}, embed_dim={self._embed_dim}"
        )

        # Ensure indexes exist for fast metadata filtering
        self._ensure_metadata_indexes()

    def _ensure_metadata_indexes(self) -> None:
        """Create indexes on metadata JSONB for fast filtering and uniqueness."""
        try:
            with self._Session() as session:
                # Create index on notebook_id for O(log n) lookups
                session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_notebook_id
                    ON {self._actual_table_name} ((metadata_->>'notebook_id'))
                """))
                # Create index on source_id for document lookups
                session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_source_id
                    ON {self._actual_table_name} ((metadata_->>'source_id'))
                """))
                # Create unique index on text + notebook_id to prevent duplicates
                # This prevents the same text chunk from being added multiple times
                session.execute(text(f"""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_{self._table_name}_unique_text_notebook
                    ON {self._actual_table_name} (md5(text), (metadata_->>'notebook_id'))
                """))
                session.commit()
                logger.debug("Metadata indexes ensured")
        except Exception as e:
            # Table might not exist yet - that's OK
            logger.debug(f"Could not create metadata indexes (table may not exist yet): {e}")

    def _create_vector_store(self) -> LlamaPGVectorStore:
        """Create LlamaIndex PGVectorStore instance."""
        return LlamaPGVectorStore.from_params(
            database=self._db_name,
            host=self._db_host,
            port=str(self._db_port),
            user=self._db_user,
            password=self._db_password,
            table_name=self._table_name,
            embed_dim=self._embed_dim,
            hnsw_kwargs={
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_dist_method": "vector_cosine_ops",
            },
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

        try:
            # Create storage context with pgvector store
            storage_context = StorageContext.from_defaults(
                vector_store=self._vector_store
            )

            # Create index with nodes
            index = VectorStoreIndex(
                nodes=nodes,
                storage_context=storage_context
            )

            # Cache the index
            self._index_cache = index
            self._cached_node_count = len(nodes)

            logger.debug(f"Created pgvector index with {len(nodes)} nodes")
            return index

        except Exception as e:
            logger.error(f"Error creating pgvector index: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to in-memory index
            index = VectorStoreIndex(nodes=nodes)
            self._index_cache = index
            self._cached_node_count = len(nodes)
            return index

    def add_nodes(
        self,
        nodes: List[BaseNode],
        notebook_id: Optional[str] = None
    ) -> int:
        """
        Add nodes to the vector store incrementally with duplicate detection.

        This is O(n) for n new nodes, NOT O(total) like ChromaDB rebuild.
        Duplicates are detected using md5 hash of text + notebook_id.

        Args:
            nodes: List of nodes to add
            notebook_id: Optional notebook ID to set on all nodes

        Returns:
            Number of nodes actually added (after deduplication)
        """
        if not nodes:
            return 0

        try:
            # Add notebook_id to metadata if provided
            if notebook_id:
                for node in nodes:
                    if hasattr(node, 'metadata'):
                        node.metadata["notebook_id"] = notebook_id

            # Filter out duplicates by checking existing text hashes
            unique_nodes = self._filter_duplicate_nodes(nodes, notebook_id)

            if not unique_nodes:
                logger.info(f"All {len(nodes)} nodes already exist, skipping add")
                return 0

            if len(unique_nodes) < len(nodes):
                logger.info(f"Filtered {len(nodes) - len(unique_nodes)} duplicate nodes")

            # Add only unique nodes to pgvector store
            self._vector_store.add(unique_nodes)

            # Invalidate cache
            self._index_cache = None
            self._cached_node_count = 0

            logger.info(f"Added {len(unique_nodes)} nodes to pgvector store")
            return len(unique_nodes)

        except Exception as e:
            logger.error(f"Error adding nodes to pgvector: {e}")
            return 0

    def _filter_duplicate_nodes(
        self,
        nodes: List[BaseNode],
        notebook_id: Optional[str] = None
    ) -> List[BaseNode]:
        """
        Filter out nodes that already exist in the database.

        Uses md5 hash of text to efficiently check for duplicates.

        Args:
            nodes: List of nodes to check
            notebook_id: Notebook ID to check within

        Returns:
            List of nodes that don't exist in the database
        """
        import hashlib

        if not nodes:
            return []

        try:
            # Calculate md5 hashes for all nodes
            node_hashes = {}
            for node in nodes:
                text = node.get_content() if hasattr(node, 'get_content') else str(node.text)
                text_hash = hashlib.md5(text.encode()).hexdigest()
                node_hashes[text_hash] = node

            # Query existing hashes in one batch
            with self._Session() as session:
                if notebook_id:
                    result = session.execute(text(f"""
                        SELECT md5(text) as text_hash
                        FROM {self._actual_table_name}
                        WHERE metadata_->>'notebook_id' = :notebook_id
                        AND md5(text) = ANY(:hashes)
                    """), {"notebook_id": notebook_id, "hashes": list(node_hashes.keys())})
                else:
                    result = session.execute(text(f"""
                        SELECT md5(text) as text_hash
                        FROM {self._actual_table_name}
                        WHERE md5(text) = ANY(:hashes)
                    """), {"hashes": list(node_hashes.keys())})

                existing_hashes = {row[0] for row in result}

            # Return nodes that don't exist
            unique_nodes = [
                node for text_hash, node in node_hashes.items()
                if text_hash not in existing_hashes
            ]

            return unique_nodes

        except Exception as e:
            logger.warning(f"Error checking for duplicates, adding all nodes: {e}")
            return nodes

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

                # Check notebook_id filter (for notebook-based architecture)
                if offering_ids:
                    node_notebook_id = metadata.get("notebook_id")
                    if node_notebook_id and node_notebook_id in offering_ids:
                        filtered_nodes.append(node)
                        continue

                # Check offering filter (by name or id) - legacy support
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
                    f"offerings/notebooks={offering_ids}, practices={practice_names}"
                )
                return None

            logger.info(
                f"Filtered {len(filtered_nodes)} nodes from {len(nodes)} total "
                f"(offerings/notebooks={offering_ids}, practices={practice_names})"
            )

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
        """Clear all embeddings from the table."""
        try:
            with self._Session() as session:
                session.execute(text(f"TRUNCATE TABLE {self._actual_table_name}"))
                session.commit()

            self._index_cache = None
            self._cached_node_count = 0
            logger.info(f"Cleared table: {self._table_name}")
        except Exception as e:
            logger.warning(f"Error clearing table: {e}")

    def reset(self) -> None:
        """Reset the vector store (clear cache and collection)."""
        self.clear_collection()
        self._index_cache = None
        self._cached_node_count = 0

    def get_collection_stats(self) -> dict:
        """Get statistics about the embeddings table."""
        try:
            with self._Session() as session:
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM {self._actual_table_name}")
                )
                count = result.scalar() or 0

            return {
                "name": self._table_name,
                "count": count,
                "cached": self._index_cache is not None,
                "cached_node_count": self._cached_node_count,
                "database": self._db_name,
                "host": self._db_host,
                "port": self._db_port
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Notebook-Specific Methods (NotebookLM Architecture)
    # =========================================================================

    def get_nodes_by_notebook(
        self,
        nodes: List[BaseNode],
        notebook_id: str
    ) -> List[BaseNode]:
        """
        Filter nodes by notebook_id for NotebookLM-style isolation.

        Args:
            nodes: List of nodes to filter
            notebook_id: Notebook UUID to filter by

        Returns:
            List of nodes belonging to the specified notebook
        """
        return self.get_nodes_by_metadata(nodes, {"notebook_id": notebook_id})

    def get_index_by_notebook(
        self,
        nodes: List[BaseNode],
        notebook_id: str,
        force_rebuild: bool = False
    ) -> Optional[VectorStoreIndex]:
        """
        Get or create filtered vector index for a specific notebook.

        Args:
            nodes: List of all available nodes
            notebook_id: Notebook UUID to filter by
            force_rebuild: Force rebuild even if cached

        Returns:
            VectorStoreIndex with notebook-filtered nodes, or None if no matching nodes
        """
        filtered_nodes = self.get_nodes_by_notebook(nodes, notebook_id)

        if not filtered_nodes:
            logger.warning(f"No nodes found for notebook: {notebook_id}")
            return None

        logger.info(
            f"Filtered {len(filtered_nodes)} nodes for notebook {notebook_id} "
            f"from {len(nodes)} total"
        )

        return self.get_index(filtered_nodes, force_rebuild=force_rebuild)

    def delete_notebook_nodes(
        self,
        nodes: List[BaseNode],
        notebook_id: str
    ) -> List[BaseNode]:
        """
        Filter out nodes belonging to a specific notebook.

        Args:
            nodes: List of all nodes
            notebook_id: Notebook UUID to remove

        Returns:
            List of nodes NOT belonging to the specified notebook
        """
        remaining_nodes = [
            node for node in nodes
            if node.metadata.get("notebook_id") != notebook_id
        ]

        removed_count = len(nodes) - len(remaining_nodes)
        logger.info(
            f"Removed {removed_count} nodes for notebook {notebook_id}, "
            f"{len(remaining_nodes)} nodes remaining"
        )

        return remaining_nodes

    def get_notebook_document_count(
        self,
        nodes: List[BaseNode],
        notebook_id: str
    ) -> int:
        """
        Get count of unique documents in a notebook.

        Args:
            nodes: List of all nodes
            notebook_id: Notebook UUID

        Returns:
            Number of unique documents (source_ids) in the notebook
        """
        notebook_nodes = self.get_nodes_by_notebook(nodes, notebook_id)

        source_ids = set()
        for node in notebook_nodes:
            source_id = node.metadata.get("source_id")
            if source_id:
                source_ids.add(source_id)

        return len(source_ids)

    def load_all_nodes(self) -> List[BaseNode]:
        """
        Load all persisted nodes from PostgreSQL pgvector.

        Returns:
            List of all BaseNode objects stored in pgvector
        """
        try:
            with self._Session() as session:
                # Query all nodes from the embeddings table
                # The LlamaIndex PGVectorStore uses 'text' column for content
                result = session.execute(
                    text(f"""
                        SELECT id, text, metadata_, embedding
                        FROM {self._actual_table_name}
                    """)
                )
                rows = result.fetchall()

                if not rows:
                    logger.debug("No nodes found in pgvector table")
                    return []

                nodes = []
                for row in rows:
                    node_id, text_content, metadata, embedding = row

                    # Parse metadata if it's a string (JSON)
                    if isinstance(metadata, str):
                        import json
                        metadata = json.loads(metadata)

                    # Parse embedding - pgvector returns as string representation
                    parsed_embedding = None
                    if embedding is not None:
                        if isinstance(embedding, str):
                            # Parse string representation "[0.1, 0.2, ...]"
                            import json
                            parsed_embedding = json.loads(embedding)
                        elif hasattr(embedding, 'tolist'):
                            # numpy array
                            parsed_embedding = embedding.tolist()
                        else:
                            # Already a list or compatible type
                            parsed_embedding = list(embedding)

                    node = TextNode(
                        id_=str(node_id),
                        text=text_content or "",
                        metadata=metadata or {},
                        embedding=parsed_embedding
                    )
                    nodes.append(node)

                logger.info(f"Loaded {len(nodes)} nodes from pgvector")
                return nodes

        except Exception as e:
            logger.error(f"Error loading nodes from pgvector: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def delete_document_nodes(self, source_id: str) -> bool:
        """
        Delete all nodes for a specific document using SQL.

        O(1) operation using SQL DELETE with WHERE clause.

        Args:
            source_id: UUID of the document whose nodes should be deleted

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Deleting nodes for document {source_id} from pgvector")

            with self._Session() as session:
                # Use SQL to delete nodes by source_id in metadata
                # LlamaIndex stores metadata in 'metadata_' JSONB column
                result = session.execute(
                    text(f"""
                        DELETE FROM {self._actual_table_name}
                        WHERE metadata_->>'source_id' = :source_id
                    """),
                    {"source_id": source_id}
                )
                session.commit()
                deleted_count = result.rowcount

            # Invalidate cache
            self._index_cache = None
            self._cached_node_count = 0

            logger.info(
                f"Deleted {deleted_count} nodes for source_id={source_id} "
                f"using SQL DELETE"
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting document nodes from pgvector: {e}")
            return False

    def delete_notebook_nodes_sql(self, notebook_id: str) -> bool:
        """
        Delete all nodes for a specific notebook using SQL.

        O(1) operation using SQL DELETE with WHERE clause.

        Args:
            notebook_id: UUID of the notebook whose nodes should be deleted

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Deleting nodes for notebook {notebook_id} from pgvector")

            with self._Session() as session:
                result = session.execute(
                    text(f"""
                        DELETE FROM {self._actual_table_name}
                        WHERE metadata_->>'notebook_id' = :notebook_id
                    """),
                    {"notebook_id": notebook_id}
                )
                session.commit()
                deleted_count = result.rowcount

            # Invalidate cache
            self._index_cache = None
            self._cached_node_count = 0

            logger.info(
                f"Deleted {deleted_count} nodes for notebook_id={notebook_id} "
                f"using SQL DELETE"
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting notebook nodes from pgvector: {e}")
            return False

    def get_nodes_by_notebook_sql(self, notebook_id: str) -> List[BaseNode]:
        """
        Load nodes for a specific notebook using SQL filtering.

        O(log n) operation using SQL WHERE with indexed column.

        Args:
            notebook_id: Notebook UUID to filter by

        Returns:
            List of nodes belonging to the specified notebook
        """
        try:
            with self._Session() as session:
                result = session.execute(
                    text(f"""
                        SELECT id, text, metadata_, embedding
                        FROM {self._actual_table_name}
                        WHERE metadata_->>'notebook_id' = :notebook_id
                    """),
                    {"notebook_id": notebook_id}
                )
                rows = result.fetchall()

                nodes = []
                for row in rows:
                    node_id, text_content, metadata, embedding = row

                    if isinstance(metadata, str):
                        import json
                        metadata = json.loads(metadata)

                    # Parse embedding - pgvector returns as string representation
                    parsed_embedding = None
                    if embedding is not None:
                        if isinstance(embedding, str):
                            import json
                            parsed_embedding = json.loads(embedding)
                        elif hasattr(embedding, 'tolist'):
                            parsed_embedding = embedding.tolist()
                        else:
                            parsed_embedding = list(embedding)

                    node = TextNode(
                        id_=str(node_id),
                        text=text_content or "",
                        metadata=metadata or {},
                        embedding=parsed_embedding
                    )
                    nodes.append(node)

                logger.debug(f"Loaded {len(nodes)} nodes for notebook {notebook_id}")
                return nodes

        except Exception as e:
            logger.error(f"Error loading notebook nodes from pgvector: {e}")
            return []
