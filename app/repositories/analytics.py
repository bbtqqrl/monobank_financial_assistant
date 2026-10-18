from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import Integer, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models.categories import Category
from app.db.models.transaction import TransactionRaw

# TODO: брати таймзону з налаштувань користувача, коли вони з'являться
DEFAULT_TIMEZONE = "Europe/Kyiv"

Dimension = Literal["category", "leaf_category", "day", "week", "month", "weekday"]
Metric = Literal["sum", "count", "avg", "min", "max"]


def month_bounds(month: date, timezone: str) -> tuple[int, int]:
    tz = ZoneInfo(timezone)
    start = datetime(month.year, month.month, 1, tzinfo=tz)
    end = datetime(month.year + month.month // 12, month.month % 12 + 1, 1, tzinfo=tz)
    return int(start.timestamp()), int(end.timestamp())


@dataclass
class TransactionFilter:
    date_from: int | None = None
    date_to: int | None = None
    kinds: tuple[str, ...] | None = None
    category_ids: list[int] | None = None
    account_ids: list[int] | None = None
    jar_ids: list[int] | None = None
    search: str | None = None
    min_amount: int | None = None
    max_amount: int | None = None
    weekdays: list[int] | None = None


class AnalyticsRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def aggregate(
        self,
        user_id: int,
        filters: TransactionFilter,
        timezone: str,
        group_by: list[Dimension] | None = None,
        metrics: list[Metric] | None = None,
    ) -> list[dict]:
        group_by = group_by or []
        metrics = metrics or ["sum", "count"]

        group_category = aliased(Category)
        local_time = func.timezone(timezone, func.to_timestamp(TransactionRaw.time))
        weekday = cast(func.extract("isodow", local_time), Integer)
        dimension_columns = {
            "category": [
                group_category.id.label("category_id"),
                group_category.name.label("category_name"),
                group_category.slug.label("category_slug"),
            ],
            "leaf_category": [
                Category.id.label("leaf_category_id"),
                Category.name.label("leaf_category_name"),
                Category.slug.label("leaf_category_slug"),
            ],
            "day": [func.to_char(local_time, "YYYY-MM-DD").label("day")],
            "week": [func.to_char(func.date_trunc("week", local_time), "YYYY-MM-DD").label("week")],
            "month": [func.to_char(local_time, "YYYY-MM").label("month")],
            "weekday": [weekday.label("weekday")],
        }
        metric_columns = {
            "sum": func.coalesce(func.sum(TransactionRaw.amount_uah), 0).label("sum"),
            "count": func.count(TransactionRaw.id).label("count"),
            "avg": func.round(func.avg(TransactionRaw.amount_uah)).label("avg"),
            "min": func.min(TransactionRaw.amount_uah).label("min"),
            "max": func.max(TransactionRaw.amount_uah).label("max"),
        }

        group_columns = [column for dimension in group_by for column in dimension_columns[dimension]]
        query = self._select(
            [*group_columns, *(metric_columns[metric] for metric in metrics)],
            user_id, filters, group_category, weekday,
        )
        if group_columns:
            query = query.group_by(*group_columns).order_by(*group_columns)

        result = await self.db.execute(query)
        return [self._to_ints(dict(row)) for row in result.mappings().all()]

    async def list_transactions(
        self,
        user_id: int,
        filters: TransactionFilter,
        timezone: str,
        limit: int | None = None,
    ) -> list[dict]:
        group_category = aliased(Category)
        local_time = func.timezone(timezone, func.to_timestamp(TransactionRaw.time))
        weekday = cast(func.extract("isodow", local_time), Integer)
        query = self._select(
            [
                TransactionRaw.id,
                TransactionRaw.time,
                TransactionRaw.description,
                TransactionRaw.amount_uah,
                group_category.id.label("category_id"),
                group_category.name.label("category_name"),
                group_category.slug.label("category_slug"),
            ],
            user_id, filters, group_category, weekday,
        ).order_by(TransactionRaw.time.desc(), TransactionRaw.id.desc())
        if limit is not None:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def first_transaction_time(self, user_id: int) -> int | None:
        result = await self.db.execute(
            select(func.min(TransactionRaw.time)).where(TransactionRaw.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _select(self, columns: list, user_id: int, filters: TransactionFilter, group_category, weekday):
        return (
            select(*columns)
            .select_from(TransactionRaw)
            .join(Category, Category.id == TransactionRaw.category_id)
            .join(group_category, group_category.id == func.coalesce(Category.parent_id, Category.id))
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.amount_uah.is_not(None),
                *self._conditions(filters, weekday),
            )
        )

    @staticmethod
    def _conditions(filters: TransactionFilter, weekday) -> list:
        conditions = []
        if filters.date_from is not None:
            conditions.append(TransactionRaw.time >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(TransactionRaw.time < filters.date_to)
        if filters.kinds:
            conditions.append(Category.kind.in_(filters.kinds))
        if filters.category_ids:
            conditions.append(or_(
                Category.id.in_(filters.category_ids),
                Category.parent_id.in_(filters.category_ids),
            ))
        if filters.account_ids:
            conditions.append(TransactionRaw.account_id.in_(filters.account_ids))
        if filters.jar_ids:
            conditions.append(TransactionRaw.jar_id.in_(filters.jar_ids))
        if filters.search:
            conditions.append(TransactionRaw.description.ilike(f"%{filters.search}%"))
        if filters.min_amount is not None:
            conditions.append(TransactionRaw.amount_uah >= filters.min_amount)
        if filters.max_amount is not None:
            conditions.append(TransactionRaw.amount_uah <= filters.max_amount)
        if filters.weekdays:
            conditions.append(weekday.in_(filters.weekdays))
        return conditions

    @staticmethod
    def _to_ints(row: dict) -> dict:
        for key in ("sum", "avg", "min", "max"):
            if row.get(key) is not None:
                row[key] = int(row[key])
        return row
