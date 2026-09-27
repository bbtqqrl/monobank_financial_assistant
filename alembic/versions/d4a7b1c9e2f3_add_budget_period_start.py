"""add budget period_start for monthly auto-reset

Revision ID: d4a7b1c9e2f3
Revises: c3e6a9b2d5f8
Create Date: 2026-09-27 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a7b1c9e2f3'
down_revision: Union[str, Sequence[str], None] = 'c3e6a9b2d5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('budgets', sa.Column('period_start', sa.Date(), nullable=True))
    op.execute("UPDATE budgets SET period_start = date_trunc('month', CURRENT_DATE)::date")
    op.alter_column('budgets', 'period_start', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('budgets', 'period_start')
