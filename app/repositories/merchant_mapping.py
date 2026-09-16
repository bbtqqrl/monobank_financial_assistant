from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: int,
        merchant_key: str,
        mcc: int,
        category_id: int,
        source: str,
    ) -> MerchantCategoryMapping:
        mapping = await self.get(user_id, merchant_key, mcc)

        if mapping:
            mapping.category_id = category_id
            mapping.source = source
            return mapping

        mapping = MerchantCategoryMapping(
            user_id=user_id,
            merchant_key=merchant_key,
            mcc=mcc,
            category_id=category_id,
            source=source,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping
