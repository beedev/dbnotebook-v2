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
    """Enable pgvector extension."""
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Disable pgvector extension (note: this will fail if tables use vector type)."""
    op.execute("DROP EXTENSION IF EXISTS vector CASCADE")
