"""add recurring payments

Revision ID: d7f3b9e2a6c4
Revises: c5e1a7d3f9b2
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7f3b9e2a6c4'
down_revision: Union[str, Sequence[str], None] = 'c5e1a7d3f9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recurring_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('merchant_key', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('mcc', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=20), nullable=True),
        sa.Column('user_kind', sa.String(length=20), nullable=True),
        sa.Column('declined_kind', sa.String(length=20), nullable=True),
        sa.Column('cancelled_at', sa.BigInteger(), nullable=True),
        sa.Column('currency_code', sa.Integer(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('amount_uah', sa.BigInteger(), nullable=False),
        sa.Column('period_days', sa.Integer(), nullable=False),
        sa.Column('first_charge_at', sa.BigInteger(), nullable=False),
        sa.Column('last_charge_at', sa.BigInteger(), nullable=False),
        sa.Column('charges_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_recurring_payments_user_id', 'recurring_payments', ['user_id'])
    op.add_column('transactions', sa.Column(
        'recurring_payment_id', sa.Integer(),
        sa.ForeignKey('recurring_payments.id', ondelete='SET NULL', name='fk_transactions_recurring_payment_id'),
        nullable=True,
    ))
    op.create_index('ix_transactions_recurring_payment_id', 'transactions', ['recurring_payment_id'])


def downgrade() -> None:
    op.drop_index('ix_transactions_recurring_payment_id', table_name='transactions')
    op.drop_constraint('fk_transactions_recurring_payment_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'recurring_payment_id')
    op.drop_index('ix_recurring_payments_user_id', table_name='recurring_payments')
    op.drop_table('recurring_payments')
