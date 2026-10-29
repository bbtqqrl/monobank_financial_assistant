"""add user home location

Revision ID: c5e1a7d3f9b2
Revises: b9d2f6a3e1c8
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5e1a7d3f9b2'
down_revision: Union[str, Sequence[str], None] = 'b9d2f6a3e1c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('home_latitude', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('home_longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'home_longitude')
    op.drop_column('users', 'home_latitude')
