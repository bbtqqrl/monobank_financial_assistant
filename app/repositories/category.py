from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category


class CategoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def get_selectable_categories(self, kinds: tuple[str, ...] | None = None) -> list[Category]:
        query = select(Category).where(Category.is_active.is_(True))
        if kinds is not None:
            query = query.where(Category.kind.in_(kinds))
        result = await self.db.execute(query.order_by(Category.id))
        return list(result.scalars().all())

    async def get_selectable_by_id(self, category_id: int) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id, Category.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_unknown_category(self) -> Category:
        result = await self.db.execute(
            select(Category).where(Category.kind == "unknown", Category.is_active.is_(True)).limit(1)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise RuntimeError("No active category of kind 'unknown' in the database")
        return category
