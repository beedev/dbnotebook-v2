"""Add extended quiz fields for code questions and extended sources

Revision ID: add_quiz_extended_fields
Revises: 691e3800e58b
Create Date: 2025-02-01

New columns added to quizzes table:
1. question_source - 'notebook_only' (default) or 'extended' for questions beyond notebook content
2. include_code_questions - Boolean flag to enable code-based questions (output, fill-blank, bug-fix)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_quiz_extended_fields'
down_revision: Union[str, None] = '691e3800e58b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add question_source column with default 'notebook_only'
    op.add_column(
        'quizzes',
        sa.Column('question_source', sa.String(20), nullable=False, server_default='notebook_only')
    )

    # Add include_code_questions column with default False
    op.add_column(
        'quizzes',
        sa.Column('include_code_questions', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('quizzes', 'include_code_questions')
    op.drop_column('quizzes', 'question_source')
