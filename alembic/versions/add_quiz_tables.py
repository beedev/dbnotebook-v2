"""Add Quiz tables for adaptive Q&A feature

Revision ID: add_quiz_tables
Revises: add_rbac_tables
Create Date: 2025-01-31

Tables created:
1. quizzes - Quiz configuration (notebook source, settings, creator)
2. quiz_attempts - Individual quiz attempts with answers and scores
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_quiz_tables'
down_revision: Union[str, None] = 'add_rbac_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create quizzes table
    op.create_table(
        'quizzes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notebook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('num_questions', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('difficulty_mode', sa.String(20), nullable=False, server_default='adaptive'),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['notebook_id'], ['notebooks.notebook_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_quizzes_user', 'quizzes', ['user_id'])
    op.create_index('idx_quizzes_notebook', 'quizzes', ['notebook_id'])
    op.create_index('idx_quizzes_created', 'quizzes', ['created_at'])

    # Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quiz_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('taker_name', sa.String(255), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('answers_json', postgresql.JSONB, nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('current_question', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_difficulty', sa.Integer(), nullable=False, server_default='2'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_quiz_attempts_quiz', 'quiz_attempts', ['quiz_id'])
    op.create_index('idx_quiz_attempts_started', 'quiz_attempts', ['started_at'])


def downgrade() -> None:
    op.drop_table('quiz_attempts')
    op.drop_table('quizzes')
