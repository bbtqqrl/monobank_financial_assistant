"""add places and transaction location

Revision ID: b7e2d9a4c1f6
Revises: a4d8f2c6e1b9
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7e2d9a4c1f6'
down_revision: Union[str, Sequence[str], None] = 'a4d8f2c6e1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'places',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_place_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('provider', 'provider_place_id', name='uq_places_provider_place'),
    )
    op.add_column('transactions', sa.Column('place_id', sa.Integer(), sa.ForeignKey('places.id', ondelete='SET NULL'), nullable=True))
    op.add_column('transactions', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('transactions', sa.Column('longitude', sa.Float(), nullable=True))
    op.create_index('ix_transactions_place_id', 'transactions', ['place_id'])


def downgrade() -> None:
    op.drop_index('ix_transactions_place_id', table_name='transactions')
    op.drop_column('transactions', 'longitude')
    op.drop_column('transactions', 'latitude')
    op.drop_column('transactions', 'place_id')
    op.drop_table('places')
