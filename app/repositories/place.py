from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.schemas.place import PlaceResponse

MAX_MERCHANT_PLACES = 50


class PlaceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, found: PlaceResponse) -> Place:
        values = {
            "name": found.name,
            "category": found.category,
            "address": found.address,
            "latitude": found.latitude,
            "longitude": found.longitude,
        }
        statement = (
            pg_insert(Place)
            .values(provider=found.provider, provider_place_id=found.place_id, **values)
            .on_conflict_do_update(constraint="uq_places_provider_place", set_={**values, "updated_at": func.now()})
            .returning(Place)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(statement)).scalar_one()

    async def list_for_merchant(self, user_id: int, merchant_mapping_id: int) -> list[Place]:
        result = await self.db.execute(
            select(Place)
            .where(Place.id.in_(
                select(TransactionRaw.place_id).where(
                    TransactionRaw.user_id == user_id,
                    TransactionRaw.merchant_mapping_id == merchant_mapping_id,
                    TransactionRaw.place_id.is_not(None),
                )
            ))
            .limit(MAX_MERCHANT_PLACES)
        )
        return list(result.scalars().all())
