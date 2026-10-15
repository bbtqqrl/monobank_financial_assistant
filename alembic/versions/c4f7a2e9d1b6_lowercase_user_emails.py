"""lowercase user emails

Revision ID: c4f7a2e9d1b6
Revises: b8e1d5c3a7f9
Create Date: 2026-10-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c4f7a2e9d1b6'
down_revision: Union[str, Sequence[str], None] = 'b8e1d5c3a7f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Login now looks emails up lower-case, so a mixed-case one stored earlier
    # would lock its owner out. Skipped where lower-casing would collide with
    # another account - those need a manual merge.
    op.execute("""
        UPDATE users u
        SET email = lower(u.email)
        WHERE u.email <> lower(u.email)
          AND NOT EXISTS (
              SELECT 1 FROM users other
              WHERE other.id <> u.id AND lower(other.email) = lower(u.email)
          )
    """)


def downgrade() -> None:
    pass
