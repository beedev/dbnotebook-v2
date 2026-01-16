"""
Schema Linker for SQL Chat.

Identifies relevant tables for a natural language query using
embedding similarity. This pre-filtering step reduces hallucination
by focusing the LLM on the most relevant subset of the schema.
"""

import logging
from typing import List, Optional, Set, Tuple

import numpy as np
from llama_index.core.embeddings import BaseEmbedding

from dbnotebook.core.sql_chat.types import SchemaInfo, TableInfo

logger = logging.getLogger(__name__)


class SchemaLinker:
    """Pre-filter relevant tables before SQL generation.

    Uses embedding similarity to identify which tables are most
    relevant to a natural language query. This reduces:
    - Hallucination from irrelevant tables
    - Token usage in prompts
    - Confusion in large schemas (>20 tables)

    The linker also expands selection to include FK-related tables
    to ensure JOIN paths are available.
    """

    # Default configuration
    DEFAULT_TOP_K = 5
    MIN_SIMILARITY_THRESHOLD = 0.3

    def __init__(
        self,
        embed_model: BaseEmbedding,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ):
        """Initialize schema linker.

        Args:
            embed_model: Embedding model for similarity computation
            top_k: Number of top tables to select
            similarity_threshold: Minimum similarity score to include
        """
        self._embed_model = embed_model
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

        # Cache for table embeddings (connection_id -> {table_name: embedding})
        self._embedding_cache: dict = {}

    def link_tables(
        self,
        query: str,
        schema: SchemaInfo,
        connection_id: Optional[str] = None,
        top_k: Optional[int] = None,
        expand_with_fk: bool = True
    ) -> List[str]:
        """Identify relevant tables for a query.

        Args:
            query: Natural language query
            schema: Database schema
            connection_id: Optional connection ID for embedding caching
            top_k: Override default top_k
            expand_with_fk: Whether to expand with FK-related tables

        Returns:
            List of relevant table names
        """
        if not schema.tables:
            return []

        k = top_k or self._top_k

        # For small schemas, return all tables
        if len(schema.tables) <= k:
            return [t.name for t in schema.tables]

        # Get or compute table embeddings
        table_embeddings = self._get_table_embeddings(schema, connection_id)

        # Compute query embedding
        query_embedding = self._embed_model.get_text_embedding(query)

        # Compute similarities
        similarities = []
        for table in schema.tables:
            table_emb = table_embeddings.get(table.name)
            if table_emb is not None:
                similarity = self._cosine_similarity(query_embedding, table_emb)
                similarities.append((table.name, similarity))
            else:
                similarities.append((table.name, 0.0))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Always select top-k tables (threshold is for additional expansion, not filtering)
        # This ensures we always have enough context for SQL generation
        selected = [table_name for table_name, score in similarities[:k]]

        logger.info(f"Schema linking: {len(selected)} tables selected from {len(schema.tables)}")
        logger.info(f"Top tables: {[(t, f'{s:.3f}') for t, s in similarities[:k]]}")

        # Expand with FK-related tables
        if expand_with_fk:
            selected = self._expand_with_fk_tables(selected, schema)

        return selected

    def _get_table_embeddings(
        self,
        schema: SchemaInfo,
        connection_id: Optional[str]
    ) -> dict:
        """Get or compute embeddings for all tables.

        Args:
            schema: Database schema
            connection_id: Optional connection ID for caching

        Returns:
            Dict mapping table name to embedding
        """
        cache_key = connection_id or "default"

        # Check cache
        if cache_key in self._embedding_cache:
            cached = self._embedding_cache[cache_key]
            # Verify cache is still valid (same tables)
            if set(cached.keys()) == {t.name for t in schema.tables}:
                return cached

        # Compute embeddings for all tables
        embeddings = {}
        for table in schema.tables:
            desc = self._create_table_description(table)
            try:
                emb = self._embed_model.get_text_embedding(desc)
                embeddings[table.name] = emb
            except Exception as e:
                logger.warning(f"Failed to embed table {table.name}: {e}")
                embeddings[table.name] = None

        # Cache embeddings
        self._embedding_cache[cache_key] = embeddings
        logger.debug(f"Computed embeddings for {len(embeddings)} tables")

        return embeddings

    def _create_table_description(self, table: TableInfo) -> str:
        """Create description string for table embedding.

        Args:
            table: Table information

        Returns:
            Description string optimized for embedding
        """
        # Include table name (potentially meaningful)
        parts = [table.name]

        # Include column names (expand underscore to space for better matching)
        for col in table.columns:
            col_name = col.name.replace('_', ' ')
            parts.append(col_name)

            # Include type hints for semantic meaning
            type_lower = col.type.lower()
            if 'timestamp' in type_lower or 'date' in type_lower:
                parts.append('date time')
            elif 'money' in type_lower or 'decimal' in type_lower:
                parts.append('amount price')

        # Include sample values if available (helps with entity matching)
        if table.sample_values:
            for col_name, values in list(table.sample_values.items())[:3]:
                for v in values[:2]:
                    if v and isinstance(v, str) and len(v) < 50:
                        parts.append(str(v))

        return ' '.join(parts)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0 to 1)
        """
        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _expand_with_fk_tables(
        self,
        tables: List[str],
        schema: SchemaInfo
    ) -> List[str]:
        """Expand table selection with FK-related tables.

        Ensures that tables needed for JOINs are included.

        Args:
            tables: Initially selected tables
            schema: Database schema

        Returns:
            Expanded list of tables
        """
        expanded = set(tables)
        tables_lower = {t.lower() for t in tables}

        # Add tables referenced by FKs from selected tables
        for rel in schema.relationships:
            if rel.from_table.lower() in tables_lower:
                expanded.add(rel.to_table)
            if rel.to_table.lower() in tables_lower:
                expanded.add(rel.from_table)

        if len(expanded) > len(tables):
            logger.debug(f"Expanded from {len(tables)} to {len(expanded)} tables via FK")

        return list(expanded)

    def filter_schema(
        self,
        schema: SchemaInfo,
        table_names: List[str]
    ) -> SchemaInfo:
        """Create a filtered schema with only selected tables.

        Args:
            schema: Full database schema
            table_names: Tables to include

        Returns:
            Filtered SchemaInfo
        """
        table_names_lower = {t.lower() for t in table_names}

        # Filter tables
        filtered_tables = [
            t for t in schema.tables
            if t.name.lower() in table_names_lower
        ]

        # Filter relationships (only include if both tables are selected)
        filtered_rels = [
            r for r in schema.relationships
            if r.from_table.lower() in table_names_lower
            and r.to_table.lower() in table_names_lower
        ]

        return SchemaInfo(
            tables=filtered_tables,
            relationships=filtered_rels,
            cached_at=schema.cached_at,
            database_name=schema.database_name
        )

    def get_table_scores(
        self,
        query: str,
        schema: SchemaInfo,
        connection_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get similarity scores for all tables.

        Useful for debugging and UI display.

        Args:
            query: Natural language query
            schema: Database schema
            connection_id: Optional connection ID for caching

        Returns:
            List of (table_name, similarity_score) sorted by score
        """
        if not schema.tables:
            return []

        # Get or compute table embeddings
        table_embeddings = self._get_table_embeddings(schema, connection_id)

        # Compute query embedding
        query_embedding = self._embed_model.get_text_embedding(query)

        # Compute similarities
        scores = []
        for table in schema.tables:
            table_emb = table_embeddings.get(table.name)
            if table_emb is not None:
                similarity = self._cosine_similarity(query_embedding, table_emb)
                scores.append((table.name, similarity))
            else:
                scores.append((table.name, 0.0))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores

    def clear_cache(self, connection_id: Optional[str] = None) -> None:
        """Clear embedding cache.

        Args:
            connection_id: Specific connection to clear, or None for all
        """
        if connection_id:
            self._embedding_cache.pop(connection_id, None)
        else:
            self._embedding_cache.clear()
