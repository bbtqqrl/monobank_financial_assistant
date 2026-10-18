"""add statement_backfilled_from

Revision ID: d8b3e6f1a2c7
Revises: c4f7a2e9d1b6
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8b3e6f1a2c7'
down_revision: Union[str, Sequence[str], None] = 'c4f7a2e9d1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mono_accounts', sa.Column('statement_backfilled_from', sa.BigInteger(), nullable=True))
    op.add_column('mono_jars', sa.Column('statement_backfilled_from', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('mono_jars', 'statement_backfilled_from')
    op.drop_column('mono_accounts', 'statement_backfilled_from')
