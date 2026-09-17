"""replace telegram auth with email/password auth

Revision ID: e2f5c8a1b4d7
Revises: a9f2c4d7b1e6
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f5c8a1b4d7'
down_revision: Union[str, Sequence[str], None] = 'a9f2c4d7b1e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Backfill any pre-auth rows so email/password_hash can become NOT NULL.
    # These accounts have no usable password and cannot log in as-is.
    op.execute(
        "UPDATE users SET email = 'legacy-user-' || id || '@placeholder.local', "
        "password_hash = '!' WHERE email IS NULL"
    )

    op.alter_column('users', 'email', nullable=False)
    op.alter_column('users', 'password_hash', nullable=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.drop_constraint('users_telegram_id_key', 'users', type_='unique')
    op.drop_column('users', 'telegram_id')

    op.alter_column('users', 'mono_client_id', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'mono_client_id', nullable=False)

    op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.execute("UPDATE users SET telegram_id = id")
    op.alter_column('users', 'telegram_id', nullable=False)
    op.create_unique_constraint('users_telegram_id_key', 'users', ['telegram_id'])

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
    op.drop_column('users', 'is_active')
