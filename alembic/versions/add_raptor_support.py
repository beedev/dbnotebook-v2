"""Add RAPTOR hierarchical tree support to notebook_sources and data_embeddings

Revision ID: add_raptor_support
Revises: add_ai_transformations
Create Date: 2025-12-27

This migration adds support for RAPTOR (Recursive Abstractive Processing for
Tree-Organized Retrieval) which builds hierarchical summaries from document chunks.

Changes:
1. Adds RAPTOR status fields to notebook_sources:
   - raptor_status: pending|building|completed|failed
   - raptor_error: Error message if RAPTOR build failed
   - raptor_built_at: Timestamp when RAPTOR tree was built

2. Creates indexes on data_embeddings for tree metadata:
   - idx_tree_level: Fast queries by tree level (0=chunk, 1+=summary)
   - idx_tree_root: Fast queries by tree root (for document-specific trees)
   - idx_source_tree_level: Compound index for source + level queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_raptor_support'
down_revision: Union[str, Sequence[str], None] = 'add_ai_transformations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add RAPTOR fields and tree indexes."""
    # Add RAPTOR status fields to notebook_sources
    op.add_column('notebook_sources',
        sa.Column('raptor_status', sa.String(length=20), nullable=False, server_default='pending')
    )
    op.add_column('notebook_sources',
        sa.Column('raptor_error', sa.Text(), nullable=True)
    )
    op.add_column('notebook_sources',
        sa.Column('raptor_built_at', sa.TIMESTAMP(), nullable=True)
    )

    # Create indexes on data_embeddings for tree metadata queries
    # These use JSONB path extraction for efficient tree-level queries
    # Note: Not using CONCURRENTLY as Alembic runs in a transaction

    # Index for querying by tree level (0=chunk, 1+=summary)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tree_level
        ON data_embeddings ((metadata_->>'tree_level'))
        WHERE metadata_->>'tree_level' IS NOT NULL
    """)

    # Index for querying by tree root (document-specific tree)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tree_root
        ON data_embeddings ((metadata_->>'tree_root_id'))
        WHERE metadata_->>'tree_root_id' IS NOT NULL
    """)

    # Compound index for source_id + tree_level (common query pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_tree_level
        ON data_embeddings ((metadata_->>'source_id'), (metadata_->>'tree_level'))
        WHERE metadata_->>'tree_level' IS NOT NULL
    """)


def downgrade() -> None:
    """Remove RAPTOR fields and tree indexes."""
    # Drop tree indexes
    op.execute("DROP INDEX IF EXISTS idx_source_tree_level")
    op.execute("DROP INDEX IF EXISTS idx_tree_root")
    op.execute("DROP INDEX IF EXISTS idx_tree_level")

    # Remove RAPTOR columns from notebook_sources
    op.drop_column('notebook_sources', 'raptor_built_at')
    op.drop_column('notebook_sources', 'raptor_error')
    op.drop_column('notebook_sources', 'raptor_status')
