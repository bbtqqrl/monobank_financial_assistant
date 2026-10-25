"""add user memories

Revision ID: a4d8f2c6e1b9
Revises: e7a3c9f1b5d2
Create Date: 2026-10-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4d8f2c6e1b9'
down_revision: Union[str, Sequence[str], None] = 'e7a3c9f1b5d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_memories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('text', sa.String(300), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_user_memories_user_id', 'user_memories', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_memories_user_id', table_name='user_memories')
    op.drop_table('user_memories')
