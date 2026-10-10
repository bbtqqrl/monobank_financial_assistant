"""categorize transfer pairs by rule

Revision ID: e4b8d2f6a1c9
Revises: d1a7c3e9f2b5
Create Date: 2026-10-10 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4b8d2f6a1c9'
down_revision: Union[str, Sequence[str], None] = 'd1a7c3e9f2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        WITH legs AS (
            SELECT t.id, t.transfer_pair_id, t.jar_id, t.category_source,
                   coalesce(a.currency_code, j.currency_code, t.currency_code) AS currency,
                   (t.account_id IS NOT NULL OR t.jar_id IS NOT NULL) AS has_holder
            FROM transactions t
            LEFT JOIN mono_accounts a ON a.id = t.account_id
            LEFT JOIN mono_jars j ON j.id = t.jar_id
        ),
        targets AS (
            SELECT me.id,
                   CASE
                       WHEN me.jar_id IS NOT NULL OR other.jar_id IS NOT NULL THEN 'zaoshchadzhennia'
                       WHEN me.currency <> other.currency THEN 'obmin-valiut'
                       ELSE 'mizh-svoimy-rakhunkamy'
                   END AS slug
            FROM legs me
            JOIN legs other ON other.id = me.transfer_pair_id
            WHERE me.has_holder AND other.has_holder
              AND me.category_source IS DISTINCT FROM 'user'
        )
        UPDATE transactions t
        SET category_id = c.id,
            category_source = 'pair',
            category_confidence = NULL,
            merchant_mapping_id = NULL
        FROM targets
        JOIN categories c ON c.slug = targets.slug
        WHERE t.id = targets.id
    """)


def downgrade() -> None:
    pass
