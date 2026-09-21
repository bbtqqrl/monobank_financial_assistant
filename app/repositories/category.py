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

    async def get_leaf_categories(self) -> list[Category]:
        parent_ids = select(Category.parent_id).where(Category.parent_id.is_not(None)).distinct()
        result = await self.db.execute(
            select(Category).where(
                Category.is_active.is_(True),
                Category.id.not_in(parent_ids),
            )
        )
        return list(result.scalars().all())

    async def get_unknown_category(self) -> Category:
        category = await self.get_by_slug("nevidome")
        if category is None:
            raise RuntimeError("Fallback category 'nevidome' is missing from the database")
        return category
