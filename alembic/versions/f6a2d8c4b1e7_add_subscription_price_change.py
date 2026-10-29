"""add subscription price change

Revision ID: f6a2d8c4b1e7
Revises: e3b8c6f1a9d5
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a2d8c4b1e7'
down_revision: Union[str, Sequence[str], None] = 'e3b8c6f1a9d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recurring_payments', sa.Column('previous_amount', sa.BigInteger(), nullable=True))
    op.add_column('recurring_payments', sa.Column('price_changed_at', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('recurring_payments', 'price_changed_at')
    op.drop_column('recurring_payments', 'previous_amount')
