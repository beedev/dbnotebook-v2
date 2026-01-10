"""Add schema_name column to database_connections table

Revision ID: add_schema_column_connections
Revises: add_sql_chat_tables
Create Date: 2025-01-09

Adds support for PostgreSQL schema selection when connecting to databases.
Users can specify which schema(s) to use, e.g., 'public', 'sales', or 'sales,hr'.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_schema_column_connections'
down_revision: Union[str, Sequence[str], None] = 'add_sql_chat_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add schema_name column to database_connections table."""
    op.add_column(
        'database_connections',
        sa.Column('schema_name', sa.String(500), nullable=True)
    )


def downgrade() -> None:
    """Remove schema_name column from database_connections table."""
    op.drop_column('database_connections', 'schema_name')
