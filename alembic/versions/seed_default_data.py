"""Seed default data for DBNotebook

Revision ID: seed_default_data
Revises: add_password_to_users
Create Date: 2026-01-13

This migration consolidates all default/seed data:
- Default admin user with fixed credentials
- Default roles with permissions
- Admin role assignment

Uses constants from dbnotebook.core.constants for consistency.
All operations are idempotent (safe to run multiple times).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt
import json


# revision identifiers, used by Alembic.
revision: str = 'seed_default_data'
down_revision: Union[str, Sequence[str], None] = 'add_password_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# =============================================================================
# Default Values (mirrored from dbnotebook.core.constants)
# Note: We duplicate here because Alembic migrations should be self-contained
# =============================================================================

DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'
DEFAULT_USERNAME = 'admin'
DEFAULT_EMAIL = 'admin@dbnotebook.local'
DEFAULT_PASSWORD = 'admin123'
DEFAULT_API_KEY = 'dbn_00000000000000000000000000000001'

# Role definitions
ROLES = {
    'admin': {
        'description': 'Full access to all features and user management',
        'permissions': [
            'manage_users',
            'manage_roles',
            'manage_notebooks',
            'manage_connections',
            'view_all',
            'edit_all',
            'delete_all',
        ],
    },
    'user': {
        'description': 'Standard access to own notebooks and assigned resources',
        'permissions': [
            'create_notebook',
            'create_connection',
            'view_assigned',
            'edit_assigned',
        ],
    },
    'viewer': {
        'description': 'Read-only access to assigned notebooks',
        'permissions': [
            'view_assigned',
        ],
    },
}


def upgrade() -> None:
    """Ensure all default data is properly seeded."""

    # Generate password hash
    password_hash = bcrypt.hashpw(
        DEFAULT_PASSWORD.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # 1. Update default user with consistent values
    # Uses ON CONFLICT to handle both insert and update cases
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
            username = EXCLUDED.username,
            email = EXCLUDED.email,
            api_key = EXCLUDED.api_key,
            password_hash = EXCLUDED.password_hash
    """)

    # 2. Ensure roles exist with correct permissions
    for role_name, role_data in ROLES.items():
        permissions_json = json.dumps(role_data['permissions'])
        op.execute(f"""
            INSERT INTO roles (role_id, name, description, permissions, created_at)
            VALUES (
                gen_random_uuid(),
                '{role_name}',
                '{role_data["description"]}',
                '{permissions_json}'::jsonb,
                NOW()
            )
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                permissions = EXCLUDED.permissions
        """)

    # 3. Assign admin role to default user (if not already assigned)
    op.execute(f"""
        INSERT INTO user_roles (user_id, role_id, assigned_at)
        SELECT '{DEFAULT_USER_ID}'::uuid, role_id, NOW()
        FROM roles
        WHERE name = 'admin'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    """Remove seed data (optional - usually we don't remove default user)."""
    # We intentionally don't remove the default user on downgrade
    # to preserve any data/notebooks they may have created.
    #
    # If you need to completely reset, manually run:
    # DELETE FROM user_roles WHERE user_id = '00000000-0000-0000-0000-000000000001'::uuid;
    # DELETE FROM users WHERE user_id = '00000000-0000-0000-0000-000000000001'::uuid;
    pass
