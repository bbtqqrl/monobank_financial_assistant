"""derive budget spend from transactions; add transactions.created_at

Budget spend is now summed from transactions on read, so the stored
counter and its period marker go away. created_at lets the categorization
sweeper spot transactions whose in-memory categorization was lost.

Revision ID: a3d7e1f4b8c2
Revises: f6b3d8a1c9e4
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d7e1f4b8c2'
down_revision: Union[str, Sequence[str], None] = 'f6b3d8a1c9e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.drop_column('budgets', 'current_amount')
    op.drop_column('budgets', 'period_start')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('budgets', sa.Column('period_start', sa.Date(), nullable=True))
    op.execute("UPDATE budgets SET period_start = date_trunc('month', CURRENT_DATE)::date")
    op.alter_column('budgets', 'period_start', nullable=False)
    op.add_column('budgets', sa.Column('current_amount', sa.Integer(), server_default='0', nullable=False))
    op.drop_column('transactions', 'created_at')
