"""add user places, drop shared merchant places

Revision ID: a8c3e5f7d2b4
Revises: f6a2d8c4b1e7
Create Date: 2026-10-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8c3e5f7d2b4'
down_revision: Union[str, Sequence[str], None] = 'f6a2d8c4b1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_places',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('merchant_key', sa.String(255), nullable=False),
        sa.Column('place_id', sa.Integer(), sa.ForeignKey('places.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rejected', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'merchant_key', 'place_id', name='uq_user_places_user_merchant_place'),
    )
    op.drop_index('ix_merchant_places_merchant_key', table_name='merchant_places')
    op.drop_table('merchant_places')


def downgrade() -> None:
    op.create_table(
        'merchant_places',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('merchant_key', sa.String(255), nullable=False),
        sa.Column('place_id', sa.Integer(), sa.ForeignKey('places.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('merchant_key', 'place_id', name='uq_merchant_places_merchant_place'),
    )
    op.create_index('ix_merchant_places_merchant_key', 'merchant_places', ['merchant_key'])
    op.drop_table('user_places')
