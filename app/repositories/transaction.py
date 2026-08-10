from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction import TransactionRaw
from app.schemas.monobank import MonoTransactionSchema


class TransactionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

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


