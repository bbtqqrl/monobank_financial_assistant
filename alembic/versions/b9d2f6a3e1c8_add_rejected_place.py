"""add rejected place to transactions

Revision ID: b9d2f6a3e1c8
Revises: a2e5c8f1d4b7
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9d2f6a3e1c8'
down_revision: Union[str, Sequence[str], None] = 'a2e5c8f1d4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('rejected_place_id', sa.Integer(), sa.ForeignKey('places.id', ondelete='SET NULL'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('transactions', 'rejected_place_id')
