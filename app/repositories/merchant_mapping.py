from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.merchant_category_mappings import MerchantCategoryMapping


class MerchantCategoryMappingRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, user_id: int, merchant_key: str, mcc: int) -> Optional[MerchantCategoryMapping]:
        result = await self.db.execute(
            select(MerchantCategoryMapping).where(
                MerchantCategoryMapping.user_id == user_id,
                MerchantCategoryMapping.merchant_key == merchant_key,
                MerchantCategoryMapping.mcc == mcc,
                MerchantCategoryMapping.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, mapping_id: int, user_id: int) -> Optional[MerchantCategoryMapping]:
        result = await self.db.execute(
            select(MerchantCategoryMapping).where(
                MerchantCategoryMapping.id == mapping_id,
                MerchantCategoryMapping.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[tuple[MerchantCategoryMapping, Category]]:
        result = await self.db.execute(
            select(MerchantCategoryMapping, Category)
            .join(Category, Category.id == MerchantCategoryMapping.category_id)
            .where(MerchantCategoryMapping.user_id == user_id)
            .order_by(MerchantCategoryMapping.id.desc())
        )
        return list(result.all())

    async def upsert(
        self,
        user_id: int,
        merchant_key: str,
        mcc: int,
        category_id: int,
        source: str,
        confidence: float | None = None,
    ) -> MerchantCategoryMapping:
        result = await self.db.execute(
            select(MerchantCategoryMapping).where(
                MerchantCategoryMapping.user_id == user_id,
                MerchantCategoryMapping.merchant_key == merchant_key,
                MerchantCategoryMapping.mcc == mcc,
            )
        )
        mapping = result.scalar_one_or_none()

        if mapping:
            mapping.category_id = category_id
            mapping.source = source
            mapping.confidence = confidence
            mapping.is_active = True
            return mapping

        mapping = MerchantCategoryMapping(
            user_id=user_id,
            merchant_key=merchant_key,
            mcc=mcc,
            category_id=category_id,
            source=source,
            confidence=confidence,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    @staticmethod
    def update_category(mapping: MerchantCategoryMapping, category_id: int) -> None:
        mapping.category_id = category_id
        mapping.source = "user"
        mapping.confidence = None

    @staticmethod
    def deactivate(mapping: MerchantCategoryMapping) -> None:
        mapping.is_active = False
