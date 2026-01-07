"""
Database Schema Introspection for Chat with Data.

Extracts and caches database schema information for LLM context.
Provides formatted schema representations optimized for Text-to-SQL.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from dbnotebook.core.sql_chat.types import (
    ColumnInfo,
    ForeignKey,
    SchemaInfo,
    TableInfo,
)

logger = logging.getLogger(__name__)


class SchemaIntrospector:
    """Extract and cache database schema for LLM context.

    Provides:
    - Schema introspection for PostgreSQL, MySQL, SQLite
    - Sample value extraction for column context
    - Compact schema formatting for LLM prompts
    - TTL-based caching
    """

    CACHE_TTL_SECONDS = 3600  # 1 hour default

    def __init__(self, cache_ttl_seconds: int = 3600):
        """Initialize schema introspector.

        Args:
            cache_ttl_seconds: How long to cache schema (default 1 hour)
        """
        self._cache: Dict[str, SchemaInfo] = {}
        self._cache_ttl = cache_ttl_seconds

    def introspect(
        self,
        engine: Engine,
        connection_id: str,
        force_refresh: bool = False
    ) -> SchemaInfo:
        """Extract complete database schema.

        Args:
            engine: SQLAlchemy engine
            connection_id: Connection ID for caching
            force_refresh: Force cache refresh

        Returns:
            SchemaInfo with tables and relationships
        """
        # Check cache
        if not force_refresh and connection_id in self._cache:
            cached = self._cache[connection_id]
            if cached.cached_at:
                age = datetime.utcnow() - cached.cached_at
                if age < timedelta(seconds=self._cache_ttl):
                    logger.debug(f"Using cached schema for {connection_id}")
                    return cached

        logger.info(f"Introspecting schema for {connection_id}")

        inspector = inspect(engine)
        tables: List[TableInfo] = []
        relationships: List[ForeignKey] = []

        # Get all table names
        table_names = inspector.get_table_names()
        logger.debug(f"Found {len(table_names)} tables")

        for table_name in table_names:
            # Get columns
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append(ColumnInfo(
                    name=col['name'],
                    type=str(col['type']),
                    nullable=col.get('nullable', True),
                    primary_key=False,  # Will be updated below
                    comment=col.get('comment'),
                ))

            # Mark primary key columns
            pk_columns = set(inspector.get_pk_constraint(table_name).get('constrained_columns', []))
            for col in columns:
                if col.name in pk_columns:
                    col.primary_key = True

            # Get foreign keys
            for fk in inspector.get_foreign_keys(table_name):
                for i, col in enumerate(fk.get('constrained_columns', [])):
                    ref_cols = fk.get('referred_columns', [])
                    if i < len(ref_cols):
                        relationships.append(ForeignKey(
                            from_table=table_name,
                            from_column=col,
                            to_table=fk.get('referred_table', ''),
                            to_column=ref_cols[i],
                        ))
                        # Update column foreign key reference
                        for c in columns:
                            if c.name == col:
                                c.foreign_key = f"{fk.get('referred_table', '')}.{ref_cols[i]}"

            # Get row count (approximate for large tables)
            row_count = self._get_row_count(engine, table_name)

            # Get sample values
            sample_values = self._get_sample_values(engine, table_name, columns)

            tables.append(TableInfo(
                name=table_name,
                columns=columns,
                row_count=row_count,
                sample_values=sample_values,
            ))

        # Get database name
        db_name = ""
        try:
            db_name = engine.url.database or ""
        except Exception:
            pass

        schema = SchemaInfo(
            tables=tables,
            relationships=relationships,
            cached_at=datetime.utcnow(),
            database_name=db_name,
        )

        # Cache result
        self._cache[connection_id] = schema
        logger.info(f"Schema cached: {len(tables)} tables, {len(relationships)} relationships")

        return schema

    def _get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        """Get approximate row count for table.

        Uses EXPLAIN for PostgreSQL (fast), COUNT(*) for others.

        Args:
            engine: SQLAlchemy engine
            table_name: Table name

        Returns:
            Row count or None if unavailable
        """
        try:
            dialect = engine.dialect.name

            if dialect == 'postgresql':
                # Use pg_class for fast approximate count
                sql = text("""
                    SELECT reltuples::bigint AS count
                    FROM pg_class
                    WHERE relname = :table_name
                """)
                with engine.connect() as conn:
                    result = conn.execute(sql, {"table_name": table_name})
                    row = result.fetchone()
                    if row and row[0] > 0:
                        return int(row[0])

            # Fallback: actual count (limit for safety)
            sql = text(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
            with engine.connect() as conn:
                result = conn.execute(sql)
                row = result.fetchone()
                return int(row[0]) if row else None

        except Exception as e:
            logger.debug(f"Could not get row count for {table_name}: {e}")
            return None

    def _get_sample_values(
        self,
        engine: Engine,
        table_name: str,
        columns: List[ColumnInfo],
        limit: int = 5
    ) -> Dict[str, List[Any]]:
        """Get sample values for each column.

        Useful for LLM context (e.g., "US" -> "United States" disambiguation).

        Args:
            engine: SQLAlchemy engine
            table_name: Table name
            columns: List of columns
            limit: Number of sample values per column

        Returns:
            Dict mapping column name to list of sample values
        """
        samples: Dict[str, List[Any]] = {}

        try:
            # Get distinct values for each column
            for col in columns[:10]:  # Limit columns to sample
                # Skip large text/binary columns
                type_lower = col.type.lower()
                if any(t in type_lower for t in ['text', 'blob', 'bytea', 'clob']):
                    continue

                try:
                    sql = text(f"""
                        SELECT DISTINCT "{col.name}"
                        FROM "{table_name}"
                        WHERE "{col.name}" IS NOT NULL
                        LIMIT :limit
                    """)  # noqa: S608
                    with engine.connect() as conn:
                        result = conn.execute(sql, {"limit": limit})
                        values = [row[0] for row in result]
                        if values:
                            samples[col.name] = values
                except Exception:
                    # Skip columns that fail (e.g., reserved keywords)
                    pass

        except Exception as e:
            logger.debug(f"Could not get sample values for {table_name}: {e}")

        return samples

    def get_table_info(
        self,
        engine: Engine,
        connection_id: str,
        table_name: str
    ) -> Optional[TableInfo]:
        """Get detailed info for a single table.

        Args:
            engine: SQLAlchemy engine
            connection_id: Connection ID
            table_name: Table name

        Returns:
            TableInfo or None if not found
        """
        schema = self.introspect(engine, connection_id)
        for table in schema.tables:
            if table.name.lower() == table_name.lower():
                return table
        return None

    def format_for_llm(
        self,
        schema: SchemaInfo,
        include_samples: bool = True,
        include_relationships: bool = True,
        max_tables: int = 50
    ) -> str:
        """Format schema as compact string for LLM prompt.

        Args:
            schema: Schema to format
            include_samples: Include sample values
            include_relationships: Include foreign key info
            max_tables: Maximum tables to include

        Returns:
            Formatted schema string
        """
        lines = [f"Database: {schema.database_name or 'unknown'}"]
        lines.append(f"Tables: {len(schema.tables)}")
        lines.append("")

        for i, table in enumerate(schema.tables[:max_tables]):
            # Table header with row count
            row_info = f" (~{table.row_count:,} rows)" if table.row_count else ""
            lines.append(f"## {table.name}{row_info}")

            # Columns
            for col in table.columns:
                parts = [f"  - {col.name}: {col.type}"]
                if col.primary_key:
                    parts.append("PK")
                if col.foreign_key:
                    parts.append(f"FK->{col.foreign_key}")
                if not col.nullable:
                    parts.append("NOT NULL")
                lines.append(" ".join(parts))

            # Sample values
            if include_samples and table.sample_values:
                samples_str = []
                for col_name, values in list(table.sample_values.items())[:3]:
                    val_str = ", ".join(str(v)[:30] for v in values[:3])
                    samples_str.append(f"{col_name}: [{val_str}]")
                if samples_str:
                    lines.append(f"  Samples: {'; '.join(samples_str)}")

            lines.append("")

        # Relationships summary
        if include_relationships and schema.relationships:
            lines.append("## Relationships")
            for rel in schema.relationships[:20]:
                lines.append(f"  {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")

        return "\n".join(lines)

    def format_table_context(self, table: TableInfo) -> str:
        """Generate context string for a single table.

        Used by LlamaIndex SQLTableRetrieverQueryEngine.

        Args:
            table: Table to format

        Returns:
            Compact context string
        """
        cols = ", ".join([f"{c.name} ({c.type})" for c in table.columns])
        row_info = f" ~{table.row_count:,} rows" if table.row_count else ""
        return f"Table: {table.name}.{row_info} Columns: {cols}"

    def refresh_cache(
        self,
        engine: Engine,
        connection_id: str
    ) -> SchemaInfo:
        """Force refresh schema cache.

        Args:
            engine: SQLAlchemy engine
            connection_id: Connection ID

        Returns:
            Fresh SchemaInfo
        """
        return self.introspect(engine, connection_id, force_refresh=True)

    def clear_cache(self, connection_id: Optional[str] = None) -> None:
        """Clear schema cache.

        Args:
            connection_id: Specific connection to clear, or None for all
        """
        if connection_id:
            self._cache.pop(connection_id, None)
        else:
            self._cache.clear()
