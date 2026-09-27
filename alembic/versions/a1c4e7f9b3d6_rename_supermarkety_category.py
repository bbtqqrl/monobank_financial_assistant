"""rename supermarkety category

Revision ID: a1c4e7f9b3d6
Revises: e8b3f6a2c5d9
Create Date: 2026-09-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7f9b3d6'
down_revision: Union[str, Sequence[str], None] = 'e8b3f6a2c5d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


categories_table = sa.table(
    'categories',
    sa.column('name', sa.String),
    sa.column('slug', sa.String),
)

OLD_NAME = 'Супермаркети'
NEW_NAME = 'Супермаркети та магазини'


def upgrade() -> None:
    """Upgrade schema."""
    # "Супермаркети" was the only child of "Продукти" organized by store
    # format rather than product type, which made it compete with the
    # parent category for any grocery-store purchase that isn't a big-box
    # supermarket (e.g. a small convenience-store chain). Broadening the
    # name to cover any grocery store removes that ambiguity.
    op.execute(
        categories_table.update()
        .where(categories_table.c.slug == 'supermarkety')
        .values(name=NEW_NAME)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        categories_table.update()
        .where(categories_table.c.slug == 'supermarkety')
        .values(name=OLD_NAME)
    )
