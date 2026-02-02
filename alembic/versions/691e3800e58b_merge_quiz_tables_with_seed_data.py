"""merge quiz tables with seed data

Revision ID: 691e3800e58b
Revises: add_quiz_tables, seed_default_data
Create Date: 2026-01-31 17:01:58.835310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '691e3800e58b'
down_revision: Union[str, Sequence[str], None] = ('add_quiz_tables', 'seed_default_data')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
