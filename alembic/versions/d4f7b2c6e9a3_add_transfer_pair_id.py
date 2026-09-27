"""add transfer_pair_id to link the two legs of an internal transfer

Revision ID: d4f7b2c6e9a3
Revises: c9a2e5f8d1b4
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f7b2c6e9a3'
down_revision: Union[str, Sequence[str], None] = 'c9a2e5f8d1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('transfer_pair_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_transactions_transfer_pair_id'), 'transactions', ['transfer_pair_id'], unique=False)
    op.create_foreign_key(
        'fk_transactions_transfer_pair_id_transactions',
        'transactions', 'transactions',
        ['transfer_pair_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_transactions_transfer_pair_id_transactions', 'transactions', type_='foreignkey')
    op.drop_index(op.f('ix_transactions_transfer_pair_id'), table_name='transactions')
    op.drop_column('transactions', 'transfer_pair_id')
