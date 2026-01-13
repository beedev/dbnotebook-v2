"""Add api_key column to users table and create default user

Revision ID: add_api_key_to_users
Revises: 9d7c2dc6ed6f
Create Date: 2026-01-13

Adds api_key column to users table for per-user programmatic API access.
Also creates the default user with an auto-generated API key.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_api_key_to_users'
down_revision: Union[str, Sequence[str], None] = '9d7c2dc6ed6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default user ID used throughout the application
DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    """Add api_key column to users table and create default user."""
    # Add api_key column
    op.add_column('users', sa.Column('api_key', sa.String(255), nullable=True))

    # Create index for fast API key lookups
    op.create_index('idx_users_api_key', 'users', ['api_key'], unique=True)

    # Create default user if not exists (with generated API key)
    # Uses gen_random_uuid() for API key generation (PostgreSQL 13+)
    op.execute(f"""
        INSERT INTO users (user_id, username, email, api_key, created_at, last_active)
        VALUES (
            '{DEFAULT_USER_ID}'::uuid,
            'default',
            'default@dbnotebook.local',
            'dbn_' || replace(gen_random_uuid()::text, '-', ''),
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO UPDATE SET
            api_key = COALESCE(users.api_key, 'dbn_' || replace(gen_random_uuid()::text, '-', ''))
    """)


def downgrade() -> None:
    """Remove api_key column from users table."""
    op.drop_index('idx_users_api_key', table_name='users')
    op.drop_column('users', 'api_key')
    # Note: We don't delete the default user on downgrade to preserve data
