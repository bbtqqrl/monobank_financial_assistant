"""place details and place feedback

Revision ID: a2e5c8f1d4b7
Revises: d4a7e1c9b2f3
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2e5c8f1d4b7'
down_revision: Union[str, Sequence[str], None] = 'd4a7e1c9b2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('places', sa.Column('type_name', sa.String(100), nullable=True))
    op.add_column('places', sa.Column('short_address', sa.String(255), nullable=True))
    op.add_column('places', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('places', sa.Column('maps_url', sa.String(500), nullable=True))
    op.add_column('transactions', sa.Column('place_confirmed', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'place_confirmed')
    op.drop_column('places', 'maps_url')
    op.drop_column('places', 'city')
    op.drop_column('places', 'short_address')
    op.drop_column('places', 'type_name')
