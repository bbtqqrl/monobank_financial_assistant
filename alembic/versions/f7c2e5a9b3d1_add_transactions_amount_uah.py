"""add transactions.amount_uah

Revision ID: f7c2e5a9b3d1
Revises: e4b8d2f6a1c9
Create Date: 2026-10-10 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7c2e5a9b3d1'
down_revision: Union[str, Sequence[str], None] = 'e4b8d2f6a1c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('amount_uah', sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE transactions t
        SET amount_uah = CASE
            WHEN coalesce(a.currency_code, j.currency_code, t.currency_code) = 980 THEN t.amount
            WHEN t.currency_code = 980 THEN t.operation_amount
        END
        FROM transactions src
        LEFT JOIN mono_accounts a ON a.id = src.account_id
        LEFT JOIN mono_jars j ON j.id = src.jar_id
        WHERE src.id = t.id
    """)


def downgrade() -> None:
    op.drop_column('transactions', 'amount_uah')
