import math

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.user_place import UserPlace
from app.services.places import METERS_PER_DEGREE


class UserPlaceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_near(
        self, user_id: int, merchant_key: str, latitude: float, longitude: float, radius_m: float,
    ) -> list[Place]:
        dlat = radius_m / METERS_PER_DEGREE
        dlon = dlat / math.cos(math.radians(latitude))
        result = await self.db.execute(
            select(Place)
            .join(UserPlace, UserPlace.place_id == Place.id)
            .where(
                UserPlace.user_id == user_id,
                UserPlace.merchant_key == merchant_key,
                UserPlace.rejected.is_(False),
                Place.latitude.between(latitude - dlat, latitude + dlat),
                Place.longitude.between(longitude - dlon, longitude + dlon),
            )
        )
        return list(result.scalars().all())

    async def rejected_provider_ids(self, user_id: int, merchant_key: str) -> set[str]:
        result = await self.db.execute(
            select(Place.provider_place_id)
            .join(UserPlace, UserPlace.place_id == Place.id)
            .where(UserPlace.user_id == user_id, UserPlace.merchant_key == merchant_key, UserPlace.rejected.is_(True))
        )
        return set(result.scalars().all())

    async def save(self, user_id: int, merchant_key: str, place_id: int, rejected: bool) -> None:
        await self.db.execute(
            pg_insert(UserPlace)
            .values(user_id=user_id, merchant_key=merchant_key, place_id=place_id, rejected=rejected)
            .on_conflict_do_update(
                constraint="uq_user_places_user_merchant_place",
                set_={"rejected": rejected, "updated_at": func.now()},
            )
        )
