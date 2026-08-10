import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.monobank import MonoWebhookPayload
from app.repositories.jar import JarRepository

logger = logging.getLogger(__name__)


class MonobankWebhookService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.jars = JarRepository(db)
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)

    async def process(self, payload: MonoWebhookPayload):
        logger.info("Monobank webhook received: %s", payload)

        mono_id  = payload.data.account
        transaction = payload.data.statementItem
        account_id = None
        jar_id = None

        exists = await self.transactions.exists(transaction.id)

        if exists:
            logger.info("Transaction already exists: id=%s", transaction.id)
            return

        logger.info(
            "Transaction received: id=%s, account=%s, description=%s, amount=%s, currency=%s",
            transaction.id,
            mono_id ,
            transaction.description,
            transaction.amount,
            transaction.currencyCode,
        )

        account = await self.accounts.get_by_mono_id(mono_id)

        if account:
            account_id = account.id
            user_id = account.user_id
        else:
            jar = await self.jars.get_by_mono_id(mono_id)

            if jar is None:
                logger.warning("Account or jar not found: mono_id=%s", mono_id)
                return

            jar_id = jar.id
            user_id = jar.user_id

        await self.transactions.create(
            user_id=user_id,
            account_id=account_id,
            jar_id=jar_id,
            transaction=transaction,
        )

        await self.db.commit()

        logger.info("Transaction saved successfully: id=%s", transaction.id)