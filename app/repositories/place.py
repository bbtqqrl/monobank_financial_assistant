from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.schemas.place import PlaceResponse


class PlaceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, found: PlaceResponse) -> Place:
        values = found.model_dump(exclude={"provider", "place_id", "distance_m"})
        statement = (
            pg_insert(Place)
            .values(provider=found.provider, provider_place_id=found.place_id, **values)
            .on_conflict_do_update(constraint="uq_places_provider_place", set_={**values, "updated_at": func.now()})
            .returning(Place)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(statement)).scalar_one()

    async def spending_for_user(
        self, user_id: int, date_from: int | None = None, date_to: int | None = None, place_id: int | None = None,
    ) -> list[tuple[Place, int, int, int]]:
        spent = func.sum(-TransactionRaw.amount_uah)
        conditions = [
            TransactionRaw.user_id == user_id,
            TransactionRaw.amount_uah < 0,
            TransactionRaw.place_confirmed.is_not(False),
        ]
        if date_from is not None:
            conditions.append(TransactionRaw.time >= date_from)
        if date_to is not None:
            conditions.append(TransactionRaw.time <= date_to)
        if place_id is not None:
            conditions.append(Place.id == place_id)
        result = await self.db.execute(
            select(Place, spent, func.count(TransactionRaw.id), func.max(TransactionRaw.time))
            .join(TransactionRaw, TransactionRaw.place_id == Place.id)
            .where(*conditions)
            .group_by(Place.id)
            .order_by(spent.desc())
        )
        return [tuple(row) for row in result.all()]
