from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.transaction import TransactionRaw
from app.db.models.transaction_categories import TransactionCategory
from app.schemas.monobank import MonoTransactionSchema


class TransactionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, transaction_id: int) -> Optional[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw).where(TransactionRaw.id == transaction_id)
        )

        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, transaction_id: int, user_id: int) -> Optional[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw).where(
                TransactionRaw.id == transaction_id,
                TransactionRaw.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_detail_for_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[tuple[TransactionRaw, Optional[Category], Optional[str]]]:
        result = await self.db.execute(
            select(TransactionRaw, Category, TransactionCategory.source)
            .join(TransactionCategory, TransactionCategory.transaction_id == TransactionRaw.id, isouter=True)
            .join(Category, Category.id == TransactionCategory.category_id, isouter=True)
            .where(TransactionRaw.id == transaction_id, TransactionRaw.user_id == user_id)
        )

        return result.one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        account_id: int | None = None,
        category_id: int | None = None,
        type_: Literal["expense", "income"] | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 30,
    ) -> tuple[list[tuple[TransactionRaw, Optional[Category], Optional[str]]], int]:
        conditions = [TransactionRaw.user_id == user_id]

        if account_id is not None:
            conditions.append(TransactionRaw.account_id == account_id)
        if type_ == "expense":
            conditions.append(TransactionRaw.amount < 0)
        elif type_ == "income":
            conditions.append(TransactionRaw.amount > 0)
        if date_from is not None:
            conditions.append(TransactionRaw.time >= date_from)
        if date_to is not None:
            conditions.append(TransactionRaw.time <= date_to)
        if search:
            conditions.append(TransactionRaw.description.ilike(f"%{search}%"))
        if category_id is not None:
            conditions.append(TransactionCategory.category_id == category_id)

        base = (
            select(TransactionRaw, Category, TransactionCategory.source)
            .join(TransactionCategory, TransactionCategory.transaction_id == TransactionRaw.id, isouter=True)
            .join(Category, Category.id == TransactionCategory.category_id, isouter=True)
            .where(*conditions)
        )

        count_result = await self.db.execute(
            select(func.count()).select_from(base.with_only_columns(TransactionRaw.id).subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            base.order_by(TransactionRaw.time.desc()).offset((page - 1) * limit).limit(limit)
        )

        return list(result.all()), total

    async def get_by_mono_id(self, mono_transaction_id: str) -> Optional[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw).where(
                TransactionRaw.mono_transaction_id == mono_transaction_id
            )
        )

        return result.scalar_one_or_none()

    async def exists(self, mono_transaction_id: str) -> bool:
        transaction = await self.get_by_mono_id(mono_transaction_id)

        return transaction is not None

    async def create(self, user_id: int, account_id: int | None, jar_id: int | None, transaction: MonoTransactionSchema):
        db_transaction = TransactionRaw(
            user_id=user_id,
            account_id=account_id,
            jar_id=jar_id,
            mono_transaction_id=transaction.id,
            time=transaction.time,
            description=transaction.description,
            mcc=transaction.mcc,
            original_mcc=transaction.originalMcc,
            hold=transaction.hold,
            amount=transaction.amount,
            operation_amount=transaction.operationAmount,
            currency_code=transaction.currencyCode,
            commission_rate=transaction.commissionRate,
            cashback_amount=transaction.cashbackAmount,
            balance=transaction.balance,
            comment=transaction.comment,
            receipt_id=transaction.receiptId,
            invoice_id=transaction.invoiceId,
            counter_edrpou=transaction.counterEdrpou,
            counter_iban=transaction.counterIban,
            counter_name=transaction.counterName,
            raw_json=transaction.model_dump(),
        )


        self.db.add(db_transaction)

        await self.db.flush()

        return db_transaction


