from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction_categories import TransactionCategory


class TransactionCategoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_transaction_id(self, transaction_id: int) -> Optional[TransactionCategory]:
        result = await self.db.execute(
            select(TransactionCategory).where(TransactionCategory.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        transaction_id: int,
        category_id: int,
        source: str,
        confidence: float | None = None,
        merchant_mapping_id: int | None = None,
    ) -> TransactionCategory:
        record = TransactionCategory(
            transaction_id=transaction_id,
            category_id=category_id,
            source=source,
            confidence=confidence,
            merchant_mapping_id=merchant_mapping_id,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def upsert(
        self,
        transaction_id: int,
        category_id: int,
        source: str,
        confidence: float | None = None,
        merchant_mapping_id: int | None = None,
    ) -> TransactionCategory:
        existing = await self.get_by_transaction_id(transaction_id)

        if existing:
            existing.category_id = category_id
            existing.source = source
            existing.confidence = confidence
            existing.merchant_mapping_id = merchant_mapping_id
            return existing

        return await self.create(
            transaction_id=transaction_id,
            category_id=category_id,
            source=source,
            confidence=confidence,
            merchant_mapping_id=merchant_mapping_id,
        )
