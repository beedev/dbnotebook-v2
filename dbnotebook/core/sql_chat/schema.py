"""
Database Schema Introspection for Chat with Data.

Extracts and caches database schema information for LLM context.
Provides formatted schema representations optimized for Text-to-SQL.
Includes fingerprinting for fast change detection.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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
    """Extract database schema for LLM context.

    Provides:
    - Schema introspection for PostgreSQL, MySQL, SQLite
    - Sample value extraction for column context
    - Compact schema formatting for LLM prompts
    - Fingerprint-based caching for performance

    Caching Strategy:
    - Uses fast fingerprint (~10ms) to detect schema changes
    - Only performs full introspection when fingerprint changes
    - Balances accuracy with performance
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize schema introspector.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)
        """
        self._cache: Dict[str, Tuple[SchemaInfo, str, datetime]] = {}  # conn_id -> (schema, fingerprint, timestamp)
        self._cache_ttl = cache_ttl_seconds

    def get_fingerprint(self, engine: Engine) -> str:
        """Get fast fingerprint for schema change detection (~10ms).

        Uses database-specific queries to compute a hash of table/column structure
        without fetching full schema details.

        Args:
            engine: SQLAlchemy engine

        Returns:
            MD5 hash of schema structure
        """
        try:
            dialect = engine.dialect.name

            if dialect == 'postgresql':
                sql = text("""
                    SELECT string_agg(
                        table_name || ':' || column_count::text,
                        ',' ORDER BY table_name
                    )
                    FROM (
                        SELECT table_name, COUNT(*) as column_count
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        GROUP BY table_name
                    ) t
                """)
            elif dialect == 'mysql':
                sql = text("""
                    SELECT GROUP_CONCAT(
                        CONCAT(table_name, ':', column_count)
                        ORDER BY table_name
                        SEPARATOR ','
                    )
                    FROM (
                        SELECT table_name, COUNT(*) as column_count
                        FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        GROUP BY table_name
                    ) t
                """)
            else:  # sqlite
                # SQLite doesn't have information_schema, use pragma
                tables_sql = text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                with engine.connect() as conn:
                    tables = conn.execute(tables_sql).fetchall()
                    parts = []
                    for (table_name,) in tables:
                        if table_name.startswith('sqlite_'):
                            continue
                        col_sql = text(f"SELECT COUNT(*) FROM pragma_table_info('{table_name}')")
                        result = conn.execute(col_sql)
                        col_count = result.scalar() or 0
                        parts.append(f"{table_name}:{col_count}")
                    fingerprint_str = ','.join(parts)
                    return hashlib.md5(fingerprint_str.encode()).hexdigest()

            with engine.connect() as conn:
                result = conn.execute(sql)
                fingerprint_str = result.scalar() or ""
                return hashlib.md5(fingerprint_str.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Failed to get fingerprint: {e}")
            # Return empty string to force full introspection
            return ""

    def introspect(
        self,
        engine: Engine,
        connection_id: str,
        force_refresh: bool = False,
        include_samples: bool = False
    ) -> SchemaInfo:
        """Extract complete database schema with fingerprint-based caching.

        Args:
            engine: SQLAlchemy engine
            connection_id: Connection ID for caching
            force_refresh: Force full introspection even if fingerprint matches
            include_samples: Include sample values for columns (slow, default False)

        Returns:
            SchemaInfo with tables and relationships
        """
        # Check cache first (unless force_refresh)
        if not force_refresh and connection_id in self._cache:
            cached_schema, cached_fp, cached_time = self._cache[connection_id]

            # Check TTL
            age = (datetime.utcnow() - cached_time).total_seconds()
            if age < self._cache_ttl:
                # Check fingerprint
                current_fp = self.get_fingerprint(engine)
                if current_fp and current_fp == cached_fp:
                    logger.debug(f"Using cached schema for {connection_id} (age: {age:.1f}s)")
                    return cached_schema
                elif current_fp:
                    logger.info(f"Schema fingerprint changed for {connection_id}, refreshing")

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

            # Get sample values only if requested (slow for remote DBs)
            if include_samples:
                sample_values = self._get_sample_values(engine, table_name, columns)
            else:
                sample_values = {}

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

        # Cache schema with fingerprint
        fingerprint = self.get_fingerprint(engine)
        self._cache[connection_id] = (schema, fingerprint, datetime.utcnow())

        logger.info(f"Schema introspected: {len(tables)} tables, {len(relationships)} relationships")

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
                    SELECT CAST(reltuples AS bigint) AS count
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
            # Get distinct values for each column (all columns, 5 rows each)
            for col in columns:
                # Skip only truly binary/large object columns
                # NOTE: TEXT columns are allowed - they often contain valuable
                # entity names (customer_name, employee_name, etc.) for SQL Chat
                type_lower = col.type.lower()
                if any(t in type_lower for t in ['blob', 'bytea', 'clob', 'binary']):
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
                        values = []
                        for row in result:
                            val = row[0]
                            # Truncate long text values
                            if isinstance(val, str) and len(val) > 50:
                                val = val[:47] + "..."
                            values.append(val)
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
            logger.debug(f"Cleared cache for {connection_id}")
        else:
            self._cache.clear()
            logger.debug("Cleared all schema cache")

    def get_cached_schema(self, connection_id: str) -> Optional[SchemaInfo]:
        """Get cached schema without introspection.

        Used by skip_schema_refresh optimization to avoid redundant
        introspection when frontend already loaded schema via selectConnection.

        Args:
            connection_id: Connection ID

        Returns:
            Cached SchemaInfo or None if not cached
        """
        if connection_id in self._cache:
            schema, _, cached_time = self._cache[connection_id]
            age = (datetime.utcnow() - cached_time).total_seconds()
            if age < self._cache_ttl:
                logger.debug(f"Returning cached schema for {connection_id} (age: {age:.1f}s)")
                return schema
            else:
                logger.debug(f"Cached schema expired for {connection_id} (age: {age:.1f}s)")
        return None

    def has_schema_changed(self, engine: Engine, connection_id: str) -> bool:
        """Check if schema has changed since last introspection.

        Args:
            engine: SQLAlchemy engine
            connection_id: Connection ID

        Returns:
            True if schema has changed or no cached version exists.
            Returns False if fingerprint check fails (assume no change).
        """
        if connection_id not in self._cache:
            return True

        _, cached_fp, _ = self._cache[connection_id]
        current_fp = self.get_fingerprint(engine)

        # If fingerprint check failed (returns ""), assume no change
        # This prevents unnecessary schema refresh on network timeouts
        if not current_fp:
            logger.debug(f"Fingerprint check failed for {connection_id}, assuming no schema change")
            return False

        return current_fp != cached_fp

    # ========== Batch Dictionary Generation ==========

    def generate_schema_dictionary(self, engine: Engine, connection_name: str) -> str:
        """Generate markdown dictionary of schema structure.

        Fast method that only queries schema metadata (no sample values).
        Used for batch dictionary file generation.

        Args:
            engine: SQLAlchemy engine
            connection_name: Human-readable connection name

        Returns:
            Markdown string for schema_dictionary.md
        """
        lines = [f"# Database Schema: {connection_name}\n"]

        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        for table_name in table_names:
            lines.append(f"## Table: {table_name}")

            # Get columns
            columns = inspector.get_columns(table_name)
            pk_cols = set(inspector.get_pk_constraint(table_name).get('constrained_columns', []))

            for col in columns:
                parts = [f"- **{col['name']}** ({col['type']}"]
                if col['name'] in pk_cols:
                    parts.append(", PK")
                parts.append(")")
                lines.append("".join(parts))

            lines.append("")

        # Add relationships section
        lines.append("## Relationships")
        for table_name in table_names:
            for fk in inspector.get_foreign_keys(table_name):
                for i, col in enumerate(fk.get('constrained_columns', [])):
                    ref_cols = fk.get('referred_columns', [])
                    if i < len(ref_cols):
                        lines.append(f"- {table_name}.{col} → {fk['referred_table']}.{ref_cols[i]}")

        logger.info(f"Generated schema dictionary for {connection_name}: {len(table_names)} tables")
        return "\n".join(lines)

    def generate_sample_values(
        self,
        engine: Engine,
        connection_name: str,
        limit: int = 5
    ) -> str:
        """Generate markdown with sample values for each table.

        Efficient method using ONE query per table (SELECT * LIMIT 5)
        instead of one query per column.

        Args:
            engine: SQLAlchemy engine
            connection_name: Human-readable connection name
            limit: Number of sample rows per table

        Returns:
            Markdown string for sample_values.md
        """
        lines = [f"# Sample Data: {connection_name}\n"]

        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        tables_sampled = 0

        for table_name in table_names:
            try:
                # ONE query per table - much faster than per-column
                sql = text(f'SELECT * FROM "{table_name}" LIMIT :limit')  # noqa: S608
                with engine.connect() as conn:
                    result = conn.execute(sql, {"limit": limit})
                    rows = result.fetchall()
                    columns = list(result.keys())

                if not rows:
                    continue

                tables_sampled += 1
                lines.append(f"## Table: {table_name} ({len(rows)} sample rows)\n")

                # Header row
                lines.append("| " + " | ".join(columns) + " |")
                lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

                # Data rows
                for row in rows:
                    values = []
                    for val in row:
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, str) and len(val) > 30:
                            values.append(val[:27] + "...")
                        else:
                            # Escape pipe characters in markdown
                            val_str = str(val).replace("|", "\\|")
                            values.append(val_str)
                    lines.append("| " + " | ".join(values) + " |")

                lines.append("")

            except Exception as e:
                logger.debug(f"Could not sample {table_name}: {e}")

        logger.info(f"Generated sample values for {connection_name}: {tables_sampled}/{len(table_names)} tables")
        return "\n".join(lines)
