"""Add generated_content table and active column to notebook_sources

Revision ID: add_studio_content
Revises: add_pgvector_embeddings
Create Date: 2025-12-23

This migration:
1. Adds 'active' column to notebook_sources for toggling document inclusion in RAG
2. Creates generated_content table for Content Studio (infographics, mind maps, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_studio_content'
down_revision: Union[str, Sequence[str], None] = 'add_pgvector_embeddings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add active column and generated_content table."""
    # Add 'active' column to notebook_sources with default True
    op.add_column('notebook_sources',
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true')
    )

    # Create generated_content table for Content Studio
    op.create_table('generated_content',
        sa.Column('content_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('source_notebook_id', sa.UUID(), nullable=True),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('thumbnail_path', sa.String(length=1000), nullable=True),
        sa.Column('content_metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_notebook_id'], ['notebooks.notebook_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('content_id')
    )

    # Create indexes for efficient querying
    op.create_index('idx_generated_content_user', 'generated_content', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_generated_content_notebook', 'generated_content', ['source_notebook_id', 'created_at'], unique=False)
    op.create_index('idx_generated_content_type', 'generated_content', ['content_type', 'created_at'], unique=False)


def downgrade() -> None:
    """Remove generated_content table and active column."""
    # Drop indexes first
    op.drop_index('idx_generated_content_type', table_name='generated_content')
    op.drop_index('idx_generated_content_notebook', table_name='generated_content')
    op.drop_index('idx_generated_content_user', table_name='generated_content')

    # Drop generated_content table
    op.drop_table('generated_content')

    # Remove active column from notebook_sources
    op.drop_column('notebook_sources', 'active')
