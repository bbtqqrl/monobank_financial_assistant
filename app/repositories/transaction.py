from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.transaction import TransactionRaw
from app.schemas.monobank import MonoTransactionSchema
from app.services.transfer_mcc import TRANSFER_MCC_CODES


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
    ) -> Optional[tuple[TransactionRaw, Optional[Category]]]:
        result = await self.db.execute(
            select(TransactionRaw, Category)
            .join(Category, Category.id == TransactionRaw.category_id, isouter=True)
            .where(TransactionRaw.id == transaction_id, TransactionRaw.user_id == user_id)
        )

        return result.one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        account_id: int | None = None,
        jar_id: int | None = None,
        category_id: int | None = None,
        type_: Literal["expense", "income", "transfer"] | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 30,
    ) -> tuple[list[tuple[TransactionRaw, Optional[Category]]], int]:
        conditions = [TransactionRaw.user_id == user_id]

        if account_id is not None:
            conditions.append(TransactionRaw.account_id == account_id)
        if jar_id is not None:
            conditions.append(TransactionRaw.jar_id == jar_id)
        if type_ in ("expense", "income"):
            conditions.append(TransactionRaw.amount < 0 if type_ == "expense" else TransactionRaw.amount > 0)
            conditions.append(TransactionRaw.mcc.is_not(None))
            conditions.append(TransactionRaw.mcc.not_in(TRANSFER_MCC_CODES))
        elif type_ == "transfer":
            conditions.append(or_(TransactionRaw.mcc.is_(None), TransactionRaw.mcc.in_(TRANSFER_MCC_CODES)))
        if date_from is not None:
            conditions.append(TransactionRaw.time >= date_from)
        if date_to is not None:
            conditions.append(TransactionRaw.time <= date_to)
        if search:
            conditions.append(TransactionRaw.description.ilike(f"%{search}%"))
        if category_id is not None:
            conditions.append(TransactionRaw.category_id == category_id)

        base = (
            select(TransactionRaw, Category)
            .join(Category, Category.id == TransactionRaw.category_id, isouter=True)
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

    async def find_unpaired_transfer_candidate(
        self,
        user_id: int,
        amount: int,
        time: int,
        exclude_id: int,
        window_seconds: int = 5,
    ) -> Optional[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw)
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.id != exclude_id,
                TransactionRaw.amount == amount,
                TransactionRaw.transfer_pair_id.is_(None),
                TransactionRaw.time.between(time - window_seconds, time + window_seconds),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def update_manual_fields(
        transaction: TransactionRaw,
        description: str | None = None,
        amount: int | None = None,
        comment: str | None = None,
        time: int | None = None,
    ) -> None:
        if description is not None:
            transaction.description = description
        if amount is not None:
            transaction.amount = amount
            transaction.operation_amount = amount
        if comment is not None:
            transaction.comment = comment
        if time is not None:
            transaction.time = time

    async def delete(self, transaction: TransactionRaw) -> None:
        await self.db.delete(transaction)

    @staticmethod
    def set_category(
        transaction: TransactionRaw,
        category_id: int,
        source: str,
        confidence: float | None = None,
        merchant_mapping_id: int | None = None,
    ) -> None:
        transaction.category_id = category_id
        transaction.category_source = source
        transaction.category_confidence = confidence
        transaction.merchant_mapping_id = merchant_mapping_id

    async def get_by_mono_id(self, mono_transaction_id: str) -> Optional[TransactionRaw]:
        result = await self.db.execute(
            select(TransactionRaw).where(
                TransactionRaw.mono_transaction_id == mono_transaction_id
            )
        )

        return result.scalar_one_or_none()

    async def update_from_webhook(self, existing: TransactionRaw, transaction: MonoTransactionSchema) -> bool:
        changed = (
            existing.hold != transaction.hold
            or existing.amount != transaction.amount
            or existing.operation_amount != transaction.operationAmount
            or existing.balance != transaction.balance
            or existing.commission_rate != transaction.commissionRate
            or existing.cashback_amount != transaction.cashbackAmount
            or existing.comment != transaction.comment
            or existing.mcc != transaction.mcc
        )

        existing.hold = transaction.hold
        existing.amount = transaction.amount
        existing.operation_amount = transaction.operationAmount
        existing.balance = transaction.balance
        existing.commission_rate = transaction.commissionRate
        existing.cashback_amount = transaction.cashbackAmount
        existing.comment = transaction.comment
        existing.receipt_id = transaction.receiptId
        existing.invoice_id = transaction.invoiceId
        existing.counter_edrpou = transaction.counterEdrpou
        existing.counter_iban = transaction.counterIban
        existing.counter_name = transaction.counterName
        existing.mcc = transaction.mcc
        existing.raw_json = transaction.model_dump()

        return changed

    async def insert_from_mono(
        self, user_id: int, account_id: int | None, jar_id: int | None, transaction: MonoTransactionSchema,
    ) -> int | None:
        """Insert a Monobank transaction unless one with the same Monobank id
        already exists. Returns the new row's id, or None if it was already
        there - the webhook and the statement backfill can deliver the same
        transaction concurrently, and a check-then-insert would race."""
        result = await self.db.execute(
            pg_insert(TransactionRaw)
            .values(
                user_id=user_id,
                account_id=account_id,
                jar_id=jar_id,
                source="monobank",
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
            .on_conflict_do_nothing(index_elements=[TransactionRaw.mono_transaction_id])
            .returning(TransactionRaw.id)
        )
        return result.scalar_one_or_none()

    async def get_for_categorization(self, transaction_id: int) -> Optional[TransactionRaw]:
        """Lock the row for the rest of the DB transaction. Returns None if it
        doesn't exist or another worker already holds it."""
        result = await self.db.execute(
            select(TransactionRaw)
            .where(TransactionRaw.id == transaction_id)
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def list_uncategorized_ids(self, created_before: datetime, limit: int) -> list[int]:
        result = await self.db.execute(
            select(TransactionRaw.id)
            .where(
                TransactionRaw.source == "monobank",
                TransactionRaw.category_id.is_(None),
                TransactionRaw.created_at < created_before,
            )
            .order_by(TransactionRaw.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_manual(
        self,
        user_id: int,
        account_id: int | None,
        jar_id: int | None,
        description: str,
        amount: int,
        currency_code: int,
        time: int,
        comment: str | None,
    ) -> TransactionRaw:
        db_transaction = TransactionRaw(
            user_id=user_id,
            account_id=account_id,
            jar_id=jar_id,
            source="manual",
            mono_transaction_id=None,
            time=time,
            description=description,
            amount=amount,
            operation_amount=amount,
            currency_code=currency_code,
            comment=comment,
            raw_json=None,
        )
        self.db.add(db_transaction)
        await self.db.flush()
        return db_transaction


