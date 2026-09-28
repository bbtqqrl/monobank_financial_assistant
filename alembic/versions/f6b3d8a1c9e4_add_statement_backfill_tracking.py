"""add statement_backfilled_at to accounts and jars

Revision ID: f6b3d8a1c9e4
Revises: e5f8c1a4b7d2
Create Date: 2026-09-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6b3d8a1c9e4'
down_revision: Union[str, Sequence[str], None] = 'e5f8c1a4b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('mono_accounts', sa.Column('statement_backfilled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mono_jars', sa.Column('statement_backfilled_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('mono_jars', 'statement_backfilled_at')
    op.drop_column('mono_accounts', 'statement_backfilled_at')
