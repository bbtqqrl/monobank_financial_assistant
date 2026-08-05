from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository


class MonobankWebhookService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)

    async def process(self, payload: dict):
        account_id = payload["data"]["account"]
        transaction = payload["data"]["statementItem"]

        account = await self.accounts.get_by_mono_id(account_id)

        if account is None:
            return

        exists = await self.transactions.exists(transaction["id"])

        if exists:
            return

        await self.transactions.create(
            user_id=account.user_id,
            account_id=account.id,
            transaction=transaction,
        )

        await self.db.commit()