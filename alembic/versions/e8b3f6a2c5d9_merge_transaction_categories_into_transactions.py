"""merge transaction_categories into transactions

Collapses the strictly 1-to-1 transaction_categories table into four
columns directly on transactions (category_id, category_source,
category_confidence, merchant_mapping_id). No category history was ever
kept (rows were upserted in place), so a join-free column layout is
simpler with no loss of information.

Revision ID: e8b3f6a2c5d9
Revises: d4f7b2c6e9a3
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b3f6a2c5d9'
down_revision: Union[str, Sequence[str], None] = 'd4f7b2c6e9a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('category_source', sa.String(length=30), nullable=True))
    op.add_column('transactions', sa.Column('category_confidence', sa.Float(), nullable=True))
    op.add_column('transactions', sa.Column('merchant_mapping_id', sa.Integer(), nullable=True))

    op.create_index(op.f('ix_transactions_category_id'), 'transactions', ['category_id'], unique=False)
    op.create_index(op.f('ix_transactions_merchant_mapping_id'), 'transactions', ['merchant_mapping_id'], unique=False)

    op.create_foreign_key(
        'fk_transactions_category_id_categories',
        'transactions', 'categories',
        ['category_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_transactions_merchant_mapping_id_merchant_category_mappings',
        'transactions', 'merchant_category_mappings',
        ['merchant_mapping_id'], ['id'],
        ondelete='SET NULL',
    )

    op.execute(
        """
        UPDATE transactions t
        SET category_id = tc.category_id,
            category_source = tc.source,
            category_confidence = tc.confidence,
            merchant_mapping_id = tc.merchant_mapping_id
        FROM transaction_categories tc
        WHERE tc.transaction_id = t.id
        """
    )

    op.drop_table('transaction_categories')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'transaction_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('merchant_mapping_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['merchant_mapping_id'], ['merchant_category_mappings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_transaction_categories_transaction_id'), 'transaction_categories', ['transaction_id'], unique=True,
    )
    op.create_index(
        op.f('ix_transaction_categories_category_id'), 'transaction_categories', ['category_id'], unique=False,
    )
    op.create_index(
        op.f('ix_transaction_categories_merchant_mapping_id'), 'transaction_categories', ['merchant_mapping_id'], unique=False,
    )

    op.execute(
        """
        INSERT INTO transaction_categories (transaction_id, category_id, merchant_mapping_id, source, confidence)
        SELECT id, category_id, merchant_mapping_id, category_source, category_confidence
        FROM transactions
        WHERE category_id IS NOT NULL
        """
    )

    op.drop_constraint(
        'fk_transactions_merchant_mapping_id_merchant_category_mappings', 'transactions', type_='foreignkey',
    )
    op.drop_constraint('fk_transactions_category_id_categories', 'transactions', type_='foreignkey')
    op.drop_index(op.f('ix_transactions_merchant_mapping_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_category_id'), table_name='transactions')
    op.drop_column('transactions', 'merchant_mapping_id')
    op.drop_column('transactions', 'category_confidence')
    op.drop_column('transactions', 'category_source')
    op.drop_column('transactions', 'category_id')
