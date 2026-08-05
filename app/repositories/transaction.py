from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction import TransactionRaw


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

    async def create(self, user_id: int, account_id: int, transaction: dict):
        db_transaction = TransactionRaw(
            user_id=user_id,
            account_id=account_id,

            mono_transaction_id=transaction["id"],

            time=transaction["time"],
            description=transaction["description"],

            mcc=transaction.get("mcc"),
            original_mcc=transaction.get("originalMcc"),

            hold=transaction.get("hold"),

            amount=transaction["amount"],
            operation_amount=transaction.get("operationAmount"),

            currency_code=transaction["currencyCode"],

            commission_rate=transaction.get("commissionRate"),
            cashback_amount=transaction.get("cashbackAmount"),

            balance=transaction.get("balance"),

            comment=transaction.get("comment"),

            receipt_id=transaction.get("receiptId"),
            invoice_id=transaction.get("invoiceId"),

            counter_edrpou=transaction.get("counterEdrpou"),
            counter_iban=transaction.get("counterIban"),
            counter_name=transaction.get("counterName"),

            raw_json=transaction,
        )

        self.db.add(db_transaction)

        await self.db.flush()

        return db_transaction


