"""users.mono_name, marketplaces category, money from other banks counted as income

Revision ID: a6d4f8b2c9e3
Revises: f7c2e5a9b3d1
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6d4f8b2c9e3'
down_revision: Union[str, Sequence[str], None] = 'f7c2e5a9b3d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mono_name', sa.String(), nullable=True))
    op.execute("""
        INSERT INTO categories (name, slug, parent_id, kind, is_active)
        VALUES ('Маркетплейси', 'marketpleisy', NULL, 'expense', true)
        ON CONFLICT (slug) DO NOTHING
    """)
    op.execute("""
        UPDATE categories SET name = 'Надходження з інших банків', kind = 'income', parent_id = NULL
        WHERE slug = 'popovnennia-rakhunku'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE categories
        SET name = 'Поповнення з інших банків', kind = 'transfer',
            parent_id = (SELECT id FROM categories WHERE slug = 'rukh-koshtiv')
        WHERE slug = 'popovnennia-rakhunku'
    """)
    op.execute("DELETE FROM categories WHERE slug = 'marketpleisy'")
    op.drop_column('users', 'mono_name')
