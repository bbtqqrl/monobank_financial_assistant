from typing import Literal, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.categories import Category
from app.db.models.transaction import TransactionRaw
from app.db.models.transaction_categories import TransactionCategory
from app.schemas.monobank import MonoTransactionSchema

# MCC codes that represent money movement between the user's own means
# (card-to-card transfers, cash withdrawals, account top-ups) rather than an
# actual expense or income - excluded from expense/income filters so they
# don't inflate those totals, and selectable via type="transfer".
TRANSFER_MCC_CODES = {4829, 6010, 6011, 6050, 6051, 6532, 6533, 6536, 6537, 6538, 6540}


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
        type_: Literal["expense", "income", "transfer"] | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 30,
    ) -> tuple[list[tuple[TransactionRaw, Optional[Category], Optional[str]]], int]:
        conditions = [TransactionRaw.user_id == user_id]

        if account_id is not None:
            conditions.append(TransactionRaw.account_id == account_id)
        if type_ in ("expense", "income"):
            conditions.append(TransactionRaw.amount < 0 if type_ == "expense" else TransactionRaw.amount > 0)
            conditions.append(or_(TransactionRaw.mcc.is_(None), TransactionRaw.mcc.not_in(TRANSFER_MCC_CODES)))
        elif type_ == "transfer":
            conditions.append(TransactionRaw.mcc.in_(TRANSFER_MCC_CODES))
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

    async def update_from_webhook(self, existing: TransactionRaw, transaction: MonoTransactionSchema) -> bool:
        """Apply a re-delivered webhook (hold settling, amended amount/comment,
        etc.) to an already-stored transaction. Returns whether anything changed."""
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

    async def create(self, user_id: int, account_id: int | None, jar_id: int | None, transaction: MonoTransactionSchema):
        db_transaction = TransactionRaw(
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


        self.db.add(db_transaction)

        await self.db.flush()

        return db_transaction

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


