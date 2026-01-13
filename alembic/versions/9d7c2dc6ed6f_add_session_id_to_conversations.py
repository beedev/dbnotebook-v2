"""add_session_id_to_conversations

Revision ID: 9d7c2dc6ed6f
Revises: add_rbac_tables
Create Date: 2026-01-13 07:46:23.302862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d7c2dc6ed6f'
down_revision: Union[str, Sequence[str], None] = 'add_rbac_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add session_id column to conversations table for API chat sessions."""
    # Add session_id column to group messages into conversations
    op.add_column('conversations', sa.Column('session_id', sa.UUID(), nullable=True))

    # Create index for efficient session lookups
    op.create_index('idx_session_conversations', 'conversations', ['session_id', 'timestamp'], unique=False)


def downgrade() -> None:
    """Remove session_id column from conversations table."""
    op.drop_index('idx_session_conversations', table_name='conversations')
    op.drop_column('conversations', 'session_id')
