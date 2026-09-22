"""allow manual transactions (source column, nullable mono_transaction_id/raw_json)

Revision ID: c9a2e5f8d1b4
Revises: b7c1e4a8d3f2
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9a2e5f8d1b4'
down_revision: Union[str, Sequence[str], None] = 'b7c1e4a8d3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('source', sa.String(length=20), nullable=False, server_default='monobank'),
    )
    op.alter_column('transactions', 'mono_transaction_id', nullable=True)
    op.alter_column('transactions', 'raw_json', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('transactions', 'raw_json', nullable=False)
    op.alter_column('transactions', 'mono_transaction_id', nullable=False)
    op.drop_column('transactions', 'source')
