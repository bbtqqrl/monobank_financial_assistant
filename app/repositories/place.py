from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.place import Place
from app.db.models.transaction import TransactionRaw
from app.schemas.place import PlaceResponse

HOME_CATEGORY_SLUGS = ("onlain-servisy-ta-pidpysky", "dostavka-izhi", "marketpleisy")


def not_home_category():
    return or_(Category.id.is_(None), Category.slug.not_in(HOME_CATEGORY_SLUGS))


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
            not_home_category(),
            *_period(date_from, date_to),
        ]
        if place_id is not None:
            conditions.append(Place.id == place_id)
        result = await self.db.execute(
            select(Place, spent, func.count(TransactionRaw.id), func.max(TransactionRaw.time))
            .join(TransactionRaw, TransactionRaw.place_id == Place.id)
            .outerjoin(Category, Category.id == TransactionRaw.category_id)
            .where(*conditions)
            .group_by(Place.id)
            .order_by(spent.desc())
        )
        return [tuple(row) for row in result.all()]

    async def home_spending(
        self, user_id: int, date_from: int | None = None, date_to: int | None = None,
    ) -> list[tuple[str, str, int, int]]:
        spent = func.sum(-TransactionRaw.amount_uah)
        result = await self.db.execute(
            select(Category.slug, Category.name, spent, func.count(TransactionRaw.id))
            .join(Category, Category.id == TransactionRaw.category_id)
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.amount_uah < 0,
                Category.slug.in_(HOME_CATEGORY_SLUGS),
                *_period(date_from, date_to),
            )
            .group_by(Category.slug, Category.name)
            .order_by(spent.desc())
        )
        return [tuple(row) for row in result.all()]

    async def unplaced_points(self, user_id: int, since: int, limit: int) -> list[tuple[float, float]]:
        result = await self.db.execute(
            select(TransactionRaw.latitude, TransactionRaw.longitude)
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.latitude.is_not(None),
                TransactionRaw.longitude.is_not(None),
                TransactionRaw.place_id.is_(None),
                TransactionRaw.time >= since,
            )
            .order_by(TransactionRaw.time.desc())
            .limit(limit)
        )
        return [tuple(row) for row in result.all()]


def _period(date_from: int | None, date_to: int | None) -> list:
    conditions = []
    if date_from is not None:
        conditions.append(TransactionRaw.time >= date_from)
    if date_to is not None:
        conditions.append(TransactionRaw.time <= date_to)
    return conditions
