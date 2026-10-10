"""link cross-currency transfer pairs

Revision ID: d1a7c3e9f2b5
Revises: c8f2a6d4e1b7
Create Date: 2026-10-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1a7c3e9f2b5'
down_revision: Union[str, Sequence[str], None] = 'c8f2a6d4e1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANDIDATES = sa.text("""
    SELECT t1.id, t2.id
    FROM transactions t1
    JOIN transactions t2 ON t2.user_id = t1.user_id AND t2.id > t1.id
    WHERE t1.transfer_pair_id IS NULL AND t2.transfer_pair_id IS NULL
      AND t2.amount = -coalesce(t1.operation_amount, t1.amount)
      AND coalesce(t2.operation_amount, t2.amount) = -t1.amount
      AND abs(t2.time - t1.time) <= 5
      AND NOT (t1.account_id IS NOT DISTINCT FROM t2.account_id AND t1.jar_id IS NOT DISTINCT FROM t2.jar_id)
    ORDER BY abs(t2.time - t1.time), t1.id, t2.id
""")

LINK = sa.text("UPDATE transactions SET transfer_pair_id = :pair WHERE id = :id")


def upgrade() -> None:
    bind = op.get_bind()
    used: set[int] = set()
    for first, second in bind.execute(CANDIDATES).all():
        if first in used or second in used:
            continue
        used.update((first, second))
        bind.execute(LINK, {'id': first, 'pair': second})
        bind.execute(LINK, {'id': second, 'pair': first})


def downgrade() -> None:
    pass
