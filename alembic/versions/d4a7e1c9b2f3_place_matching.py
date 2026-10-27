"""place matching: mcc place types, merchant places, place method

Revision ID: d4a7e1c9b2f3
Revises: c3f8a1d5e2b7
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4a7e1c9b2f3'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1d5e2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROCERY = ["supermarket", "grocery_store", "convenience_store", "food_store"]
FOOD = ["restaurant", "cafe", "coffee_shop", "bar", "fast_food_restaurant"]
BAKERY = ["bakery", "cafe"]
PHARMACY = ["pharmacy", "drugstore"]
LIQUOR = ["liquor_store"]
STORE = ["store", "department_store", "drugstore"]
CLOTHES = ["clothing_store", "shoe_store"]
ELECTRONICS = ["electronics_store"]
GAS = ["gas_station"]
MEDICAL = ["dentist", "doctor", "hospital"]
CINEMA = ["movie_theater"]
ARCADE = ["video_arcade", "amusement_center"]
BEAUTY = ["hair_care", "beauty_salon"]
GYM = ["gym"]
SKIP = []

MCC_PLACE_TYPES = {
    5411: GROCERY, 5499: GROCERY,
    5812: FOOD, 5813: FOOD, 5814: FOOD,
    5462: BAKERY,
    5912: PHARMACY,
    5921: LIQUOR,
    5310: STORE, 5311: STORE, 5331: STORE, 5977: STORE, 5993: STORE,
    5651: CLOTHES, 5661: CLOTHES, 5691: CLOTHES, 5699: CLOTHES, 5931: CLOTHES,
    5732: ELECTRONICS,
    5541: GAS, 5542: GAS,
    8011: MEDICAL, 8021: MEDICAL, 8062: MEDICAL,
    7832: CINEMA,
    7994: ARCADE,
    7230: BEAUTY, 7298: BEAUTY,
    7997: GYM,
    4111: SKIP, 4112: SKIP, 4121: SKIP, 4131: SKIP, 4215: SKIP, 4722: SKIP, 4789: SKIP, 4814: SKIP,
    4829: SKIP, 4900: SKIP, 5399: SKIP, 5734: SKIP, 5811: SKIP, 5815: SKIP, 5816: SKIP, 5817: SKIP,
    5818: SKIP, 5968: SKIP, 6011: SKIP, 6012: SKIP, 7011: SKIP, 7399: SKIP, 7922: SKIP, 7999: SKIP,
    8398: SKIP,
}


def upgrade() -> None:
    table = op.create_table(
        'mcc_place_types',
        sa.Column('mcc', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('google_types', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
    )
    op.bulk_insert(table, [
        {'mcc': mcc, 'google_types': google}
        for mcc, google in MCC_PLACE_TYPES.items()
    ])
    op.create_table(
        'merchant_places',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('merchant_key', sa.String(255), nullable=False),
        sa.Column('place_id', sa.Integer(), sa.ForeignKey('places.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('merchant_key', 'place_id', name='uq_merchant_places_merchant_place'),
    )
    op.create_index('ix_merchant_places_merchant_key', 'merchant_places', ['merchant_key'])
    op.add_column('transactions', sa.Column('place_method', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'place_method')
    op.drop_index('ix_merchant_places_merchant_key', table_name='merchant_places')
    op.drop_table('merchant_places')
    op.drop_table('mcc_place_types')
