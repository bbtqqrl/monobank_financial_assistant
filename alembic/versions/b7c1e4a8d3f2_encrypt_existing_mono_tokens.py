"""encrypt existing plaintext mono_token values

Revision ID: b7c1e4a8d3f2
Revises: f3a6d9b2c5e8
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.crypto import encrypt_value


# revision identifiers, used by Alembic.
revision: str = 'b7c1e4a8d3f2'
down_revision: Union[str, Sequence[str], None] = 'f3a6d9b2c5e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

users_table = sa.table(
    'users',
    sa.column('id', sa.Integer),
    sa.column('mono_token', sa.String),
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(users_table.c.id, users_table.c.mono_token).where(
            users_table.c.mono_token.is_not(None)
        )
    ).all()

    for row in rows:
        bind.execute(
            users_table.update()
            .where(users_table.c.id == row.id)
            .values(mono_token=encrypt_value(row.mono_token))
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Plaintext values were not preserved; affected users must reconnect Monobank.
    pass
