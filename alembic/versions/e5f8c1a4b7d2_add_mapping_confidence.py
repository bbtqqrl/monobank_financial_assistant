"""add confidence to merchant_category_mappings

Revision ID: e5f8c1a4b7d2
Revises: d4a7b1c9e2f3
Create Date: 2026-09-27 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f8c1a4b7d2'
down_revision: Union[str, Sequence[str], None] = 'd4a7b1c9e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('merchant_category_mappings', sa.Column('confidence', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('merchant_category_mappings', 'confidence')
