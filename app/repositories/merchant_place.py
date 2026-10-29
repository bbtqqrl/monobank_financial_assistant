import math

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.merchant_place import MerchantPlace
from app.db.models.place import Place
from app.services.places import METERS_PER_DEGREE


class MerchantPlaceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_near(self, merchant_key: str, latitude: float, longitude: float, radius_m: float) -> list[Place]:
        dlat = radius_m / METERS_PER_DEGREE
        dlon = dlat / math.cos(math.radians(latitude))
        result = await self.db.execute(
            select(Place)
            .join(MerchantPlace, MerchantPlace.place_id == Place.id)
            .where(
                MerchantPlace.merchant_key == merchant_key,
                Place.latitude.between(latitude - dlat, latitude + dlat),
                Place.longitude.between(longitude - dlon, longitude + dlon),
            )
        )
        return list(result.scalars().all())

    async def link(self, merchant_key: str, place_id: int) -> None:
        await self.db.execute(
            pg_insert(MerchantPlace)
            .values(merchant_key=merchant_key, place_id=place_id)
            .on_conflict_do_update(constraint="uq_merchant_places_merchant_place", set_={"updated_at": func.now()})
        )

    async def unlink(self, merchant_key: str, place_id: int) -> None:
        await self.db.execute(
            delete(MerchantPlace).where(MerchantPlace.merchant_key == merchant_key, MerchantPlace.place_id == place_id)
        )
