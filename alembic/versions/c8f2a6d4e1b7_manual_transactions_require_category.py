"""manual transactions require a category

Nothing categorizes a manual transaction after the fact (the AI pipeline and
the sweeper only handle Monobank ones), so the API now requires a category on
create and the database enforces it. Manual transactions created earlier
without one get the 'unknown' category, so the user can still see and fix
them.

Revision ID: c8f2a6d4e1b7
Revises: b5e9c2d7f1a3
Create Date: 2026-10-07 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f2a6d4e1b7'
down_revision: Union[str, Sequence[str], None] = 'b5e9c2d7f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        UPDATE transactions
        SET category_id = (SELECT id FROM categories WHERE kind = 'unknown' ORDER BY id LIMIT 1),
            category_source = 'user'
        WHERE source = 'manual' AND category_id IS NULL
    """)
    op.create_check_constraint(
        'ck_transactions_manual_has_category',
        'transactions',
        "source <> 'manual' OR category_id IS NOT NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_transactions_manual_has_category', 'transactions', type_='check')
