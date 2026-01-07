"""Add SQL Chat (Chat with Data) tables for Text-to-SQL feature

Revision ID: add_sql_chat_tables
Revises: add_raptor_support
Create Date: 2025-01-07

This migration adds support for the Chat with Data feature which enables
natural language queries against external databases (PostgreSQL, MySQL, SQLite).

Tables created:
1. database_connections - Store user's external database connections
2. sql_chat_sessions - Track chat sessions per connection
3. sql_query_history - Store executed queries and results
4. sql_few_shot_examples - Gretel dataset for few-shot learning (with vector index)
5. sql_query_telemetry - Query telemetry for observability
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_sql_chat_tables'
down_revision: Union[str, Sequence[str], None] = 'add_raptor_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create SQL Chat tables and indexes."""

    # 1. database_connections - Store user's external database connections
    op.create_table(
        'database_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('db_type', sa.String(20), nullable=False),  # postgresql, mysql, sqlite
        sa.Column('host', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database_name', sa.String(200), nullable=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('password_encrypted', sa.Text(), nullable=True),  # Fernet encrypted
        sa.Column('masking_policy', postgresql.JSONB(), nullable=True),  # {mask_columns, redact_columns, hash_columns}
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.TIMESTAMP(), nullable=True),
    )
    op.create_index('idx_db_connections_user', 'database_connections', ['user_id'])

    # 2. sql_chat_sessions - Track chat sessions per connection
    op.create_table(
        'sql_chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_query_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['connection_id'], ['database_connections.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_sql_sessions_user', 'sql_chat_sessions', ['user_id'])
    op.create_index('idx_sql_sessions_connection', 'sql_chat_sessions', ['connection_id'])

    # 3. sql_query_history - Store executed queries and results
    op.create_table(
        'sql_query_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('generated_sql', sa.Text(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['sql_chat_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_sql_history_session', 'sql_query_history', ['session_id'])
    op.create_index('idx_sql_history_created', 'sql_query_history', ['created_at'])

    # 4. sql_few_shot_examples - Gretel dataset for few-shot learning
    # Uses vector(768) to match HuggingFace nomic-embed-text-v1.5 dimensions
    op.create_table(
        'sql_few_shot_examples',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sql_prompt', sa.Text(), nullable=False),
        sa.Column('sql_query', sa.Text(), nullable=False),
        sa.Column('sql_context', sa.Text(), nullable=True),
        sa.Column('complexity', sa.String(50), nullable=True),  # basic SQL, joins, aggregation, etc.
        sa.Column('domain', sa.String(100), nullable=True),     # finance, healthcare, retail, etc.
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )

    # Add vector column for embeddings (768 dimensions for HuggingFace)
    op.execute("""
        ALTER TABLE sql_few_shot_examples
        ADD COLUMN embedding vector(768)
    """)

    # Create IVFFlat index for fast vector similarity search
    op.execute("""
        CREATE INDEX idx_few_shot_embedding ON sql_few_shot_examples
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # Index for domain-filtered queries
    op.create_index('idx_few_shot_domain', 'sql_few_shot_examples', ['domain'])
    op.create_index('idx_few_shot_complexity', 'sql_few_shot_examples', ['complexity'])

    # 5. sql_query_telemetry - Query telemetry for observability
    op.create_table(
        'sql_query_telemetry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=True),
        sa.Column('generated_sql', sa.Text(), nullable=True),
        sa.Column('intent', sa.String(50), nullable=True),  # lookup, aggregation, comparison, etc.
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('cost_estimate', sa.Float(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_telemetry_session', 'sql_query_telemetry', ['session_id'])
    op.create_index('idx_telemetry_created', 'sql_query_telemetry', ['created_at'])
    op.create_index('idx_telemetry_intent', 'sql_query_telemetry', ['intent'])


def downgrade() -> None:
    """Drop SQL Chat tables and indexes."""
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('sql_query_telemetry')
    op.drop_table('sql_few_shot_examples')
    op.drop_table('sql_query_history')
    op.drop_table('sql_chat_sessions')
    op.drop_table('database_connections')
