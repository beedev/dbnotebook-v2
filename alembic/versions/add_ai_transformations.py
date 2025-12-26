"""Add AI transformation fields to notebook_sources and embedding_config table

Revision ID: add_ai_transformations
Revises: add_studio_content
Create Date: 2025-12-25

This migration:
1. Adds AI transformation fields to notebook_sources:
   - dense_summary: 300-500 word comprehensive summary
   - key_insights: JSON array of 5-10 actionable insights
   - reflection_questions: JSON array of 5-7 thought-provoking questions
   - transformation_status: pending|processing|completed|failed
   - transformation_error: Error message if transformation failed
   - transformed_at: Timestamp when transformation completed

2. Creates embedding_config table to track active embedding model
   (prevents mixing incompatible embeddings from different models)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_ai_transformations'
down_revision: Union[str, Sequence[str], None] = 'add_studio_content'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add transformation fields and embedding_config table."""
    # Add AI transformation fields to notebook_sources
    op.add_column('notebook_sources',
        sa.Column('dense_summary', sa.Text(), nullable=True)
    )
    op.add_column('notebook_sources',
        sa.Column('key_insights', JSONB(), nullable=True)
    )
    op.add_column('notebook_sources',
        sa.Column('reflection_questions', JSONB(), nullable=True)
    )
    op.add_column('notebook_sources',
        sa.Column('transformation_status', sa.String(length=20), nullable=False, server_default='pending')
    )
    op.add_column('notebook_sources',
        sa.Column('transformation_error', sa.Text(), nullable=True)
    )
    op.add_column('notebook_sources',
        sa.Column('transformed_at', sa.TIMESTAMP(), nullable=True)
    )

    # Create embedding_config table
    op.create_table('embedding_config',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Remove transformation fields and embedding_config table."""
    # Drop embedding_config table
    op.drop_table('embedding_config')

    # Remove transformation columns from notebook_sources
    op.drop_column('notebook_sources', 'transformed_at')
    op.drop_column('notebook_sources', 'transformation_error')
    op.drop_column('notebook_sources', 'transformation_status')
    op.drop_column('notebook_sources', 'reflection_questions')
    op.drop_column('notebook_sources', 'key_insights')
    op.drop_column('notebook_sources', 'dense_summary')
