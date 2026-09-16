from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction_categories import TransactionCategory


class TransactionCategoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

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
