from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.schemas.place import PlaceResponse


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
