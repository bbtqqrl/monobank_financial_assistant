"""link transactions to their merchant mappings

Revision ID: b8e1d5c3a7f9
Revises: a6d4f8b2c9e3
Create Date: 2026-10-12 00:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e1d5c3a7f9'
down_revision: Union[str, Sequence[str], None] = 'a6d4f8b2c9e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NOISE = re.compile(r"[^a-zа-яіїєґ0-9\s]", re.IGNORECASE)
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")


def _merchant_key(description: str) -> str:
    text = _NOISE.sub(" ", description.strip().lower())
    text = _DIGITS.sub("", text)
    return _SPACES.sub(" ", text).strip()


def upgrade() -> None:
    bind = op.get_bind()
    mappings = {
        (user_id, mcc, key): mapping_id
        for mapping_id, user_id, mcc, key in bind.execute(sa.text(
            "SELECT id, user_id, mcc, merchant_key FROM merchant_category_mappings"
        )).all()
    }
    unlinked = bind.execute(sa.text("""
        SELECT id, user_id, mcc, description FROM transactions
        WHERE merchant_mapping_id IS NULL AND mcc IS NOT NULL AND source = 'monobank'
          AND coalesce(category_source, '') <> 'pair'
    """)).all()
    for transaction_id, user_id, mcc, description in unlinked:
        mapping_id = mappings.get((user_id, mcc, _merchant_key(description)))
        if mapping_id is not None:
            bind.execute(
                sa.text("UPDATE transactions SET merchant_mapping_id = :m WHERE id = :t"),
                {"m": mapping_id, "t": transaction_id},
            )


def downgrade() -> None:
    pass
