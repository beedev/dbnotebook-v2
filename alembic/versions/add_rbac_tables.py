"""Add RBAC (Role-Based Access Control) tables

Revision ID: add_rbac_tables
Revises: add_schema_column_connections
Create Date: 2025-01-13

Adds support for role-based access control across all features:
- API endpoints
- Notebook Chat
- SQL Chat

Tables created:
1. roles - Role definitions with permissions
2. user_roles - Maps users to roles
3. notebook_access - Grants users access to specific notebooks
4. sql_connection_access - Grants users access to SQL connections

Also creates default roles:
- admin: Full access to all features and user management
- user: Standard access to own notebooks and assigned resources
- viewer: Read-only access to assigned notebooks
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_rbac_tables'
down_revision: Union[str, None] = 'add_schema_column_connections'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('permissions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('name')
    )

    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role')
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])

    # Create notebook_access table
    op.create_table(
        'notebook_access',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('notebook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_level', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granted_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.notebook_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notebook_access_notebook', 'notebook_access', ['notebook_id'])
    op.create_index('idx_notebook_access_user', 'notebook_access', ['user_id'])

    # Create sql_connection_access table
    op.create_table(
        'sql_connection_access',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_level', sa.String(20), nullable=False, server_default='user'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granted_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['connection_id'], ['database_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sql_access_connection', 'sql_connection_access', ['connection_id'])
    op.create_index('idx_sql_access_user', 'sql_connection_access', ['user_id'])

    # Insert default roles (idempotent with ON CONFLICT)
    op.execute("""
        INSERT INTO roles (role_id, name, description, permissions) VALUES
        (gen_random_uuid(), 'admin', 'Full access to all features and user management',
         '["manage_users", "manage_roles", "manage_notebooks", "manage_connections", "view_all", "edit_all", "delete_all"]'::jsonb)
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            permissions = EXCLUDED.permissions
    """)
    op.execute("""
        INSERT INTO roles (role_id, name, description, permissions) VALUES
        (gen_random_uuid(), 'user', 'Standard access to own notebooks and assigned resources',
         '["create_notebook", "create_connection", "view_assigned", "edit_assigned"]'::jsonb)
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            permissions = EXCLUDED.permissions
    """)
    op.execute("""
        INSERT INTO roles (role_id, name, description, permissions) VALUES
        (gen_random_uuid(), 'viewer', 'Read-only access to assigned notebooks',
         '["view_assigned"]'::jsonb)
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            permissions = EXCLUDED.permissions
    """)


def downgrade() -> None:
    op.drop_table('sql_connection_access')
    op.drop_table('notebook_access')
    op.drop_table('user_roles')
    op.drop_table('roles')
