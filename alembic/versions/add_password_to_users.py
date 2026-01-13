"""Add password_hash column to users table

Revision ID: add_password_to_users
Revises: add_rbac_tables, add_api_key_to_users
Create Date: 2026-01-13

Adds password_hash column for authentication.
Sets default admin password (admin123) for default user.
Also assigns admin role to default user.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt


# revision identifiers, used by Alembic.
revision: str = 'add_password_to_users'
down_revision: Union[str, Sequence[str], None] = ('add_rbac_tables', 'add_api_key_to_users')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default user constants
DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_USERNAME = 'admin'
DEFAULT_EMAIL = 'admin@dbnotebook.local'
DEFAULT_PASSWORD = 'admin123'
DEFAULT_API_KEY = 'dbn_00000000000000000000000000000001'


def upgrade() -> None:
    """Add password_hash column and set default admin password."""
    # Add password_hash column
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))

    # Generate bcrypt hash for default password
    password_hash = bcrypt.hashpw(DEFAULT_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create or update default admin user (idempotent)
    op.execute(f"""
        INSERT INTO users (user_id, username, email, api_key, password_hash, created_at, last_active)
        VALUES (
            '{DEFAULT_USER_ID}'::uuid,
            '{DEFAULT_USERNAME}',
            '{DEFAULT_EMAIL}',
            '{DEFAULT_API_KEY}',
            '{password_hash}',
            NOW(),
            NOW()
        )
        ON CONFLICT (user_id) DO UPDATE SET
            password_hash = EXCLUDED.password_hash
    """)

    # Assign admin role to default user (if roles exist)
    op.execute(f"""
        INSERT INTO user_roles (user_id, role_id, assigned_at)
        SELECT '{DEFAULT_USER_ID}'::uuid, role_id, NOW()
        FROM roles
        WHERE name = 'admin'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    """Remove password_hash column."""
    op.drop_column('users', 'password_hash')
