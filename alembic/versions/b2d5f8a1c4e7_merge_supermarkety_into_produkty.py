"""merge supermarkety category into produkty

Revision ID: b2d5f8a1c4e7
Revises: a1c4e7f9b3d6
Create Date: 2026-09-27 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d5f8a1c4e7'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f9b3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


categories_table = sa.table(
    'categories',
    sa.column('id', sa.Integer),
    sa.column('slug', sa.String),
    sa.column('is_active', sa.Boolean),
)
transactions_table = sa.table(
    'transactions',
    sa.column('category_id', sa.Integer),
)
merchant_mappings_table = sa.table(
    'merchant_category_mappings',
    sa.column('category_id', sa.Integer),
)


def _category_id(bind, slug: str) -> int:
    result = bind.execute(
        sa.select(categories_table.c.id).where(categories_table.c.slug == slug)
    )
    return result.scalar_one()


def upgrade() -> None:
    """Upgrade schema."""
    # "Продукти" (general) and "Супермаркети та магазини" (any grocery store
    # format) ended up meaning the same thing for an ordinary grocery-store
    # purchase, which made the AI split confidence between two equally
    # correct answers. Fold the store-format category into its general
    # parent and deactivate it, keeping only product-type children distinct.
    bind = op.get_bind()
    produkty_id = _category_id(bind, 'produkty')
    supermarkety_id = _category_id(bind, 'supermarkety')

    bind.execute(
        transactions_table.update()
        .where(transactions_table.c.category_id == supermarkety_id)
        .values(category_id=produkty_id)
    )
    bind.execute(
        merchant_mappings_table.update()
        .where(merchant_mappings_table.c.category_id == supermarkety_id)
        .values(category_id=produkty_id)
    )
    bind.execute(
        categories_table.update()
        .where(categories_table.c.id == supermarkety_id)
        .values(is_active=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reactivates the category, but does not restore which transactions/
    # mappings previously pointed at it - that assignment history is lost.
    bind = op.get_bind()
    bind.execute(
        categories_table.update()
        .where(categories_table.c.slug == 'supermarkety')
        .values(is_active=True)
    )
