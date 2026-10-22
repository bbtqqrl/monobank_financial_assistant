"""add assistant tables

Revision ID: e7a3c9f1b5d2
Revises: d8b3e6f1a2c7
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e7a3c9f1b5d2'
down_revision: Union[str, Sequence[str], None] = 'd8b3e6f1a2c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_conversations_user_updated', 'conversations', ['user_id', 'updated_at'])

    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='ck_messages_role'),
    )
    op.create_index('ix_messages_conversation_id_id', 'messages', ['conversation_id', 'id'])

    op.create_table(
        'pending_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_use_id', sa.String(64), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('preview', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected', 'expired', 'failed')",
            name='ck_pending_actions_status',
        ),
    )
    op.create_index('ix_pending_actions_conversation_id', 'pending_actions', ['conversation_id'])
    op.create_index('ix_pending_actions_user_status', 'pending_actions', ['user_id', 'status'])

    op.create_table(
        'llm_usage',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('purpose', sa.String(30), nullable=False),
        sa.Column('model', sa.String(64), nullable=False),
        sa.Column('request_id', sa.String(64), nullable=True),
        sa.Column('is_batch', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cache_read_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cache_write_tokens', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cost_usd', sa.Numeric(12, 6), server_default='0', nullable=False),
        sa.Column('stop_reason', sa.String(30), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_llm_usage_user_id', 'llm_usage', ['user_id'])
    op.create_index('ix_llm_usage_conversation_id', 'llm_usage', ['conversation_id'])
    op.create_index('ix_llm_usage_created_at', 'llm_usage', ['created_at'])


def downgrade() -> None:
    op.drop_table('llm_usage')
    op.drop_table('pending_actions')
    op.drop_table('messages')
    op.drop_table('conversations')
