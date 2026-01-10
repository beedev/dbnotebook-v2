"""Enable pgvector extension for embeddings

Revision ID: add_pgvector_embeddings
Revises: cd1227a8d5da
Create Date: 2024-12-16

Enables the pgvector extension for vector similarity search.

NOTE: The embeddings table (data_embeddings) is managed by LlamaIndex PGVectorStore,
which automatically creates it with HNSW indexes. This migration only ensures the
pgvector extension is available.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_pgvector_embeddings'
down_revision: Union[str, Sequence[str], None] = 'cd1227a8d5da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pgvector extension and create embeddings table."""
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create data_embeddings table (matches LlamaIndex PGVectorStore schema)
    # IF NOT EXISTS prevents conflict when LlamaIndex also tries to create it
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            text TEXT,
            metadata_ JSONB,
            node_id VARCHAR,
            embedding vector(768)
        )
    """)

    # Create index for node_id lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_data_embeddings_node_id
        ON data_embeddings(node_id)
    """)


def downgrade() -> None:
    """Drop embeddings table and disable pgvector extension."""
    op.execute("DROP INDEX IF EXISTS idx_data_embeddings_node_id")
    op.execute("DROP TABLE IF EXISTS data_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector CASCADE")
