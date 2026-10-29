"""add notifications

Revision ID: e3b8c6f1a9d5
Revises: d7f3b9e2a6c4
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e3b8c6f1a9d5'
down_revision: Union[str, Sequence[str], None] = 'd7f3b9e2a6c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('dedupe_key', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'dedupe_key', name='uq_notifications_user_dedupe_key'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.add_column('users', sa.Column(
        'disabled_notifications', sa.JSON(), nullable=False, server_default=sa.text("'[]'"),
    ))


def downgrade() -> None:
    op.drop_column('users', 'disabled_notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
