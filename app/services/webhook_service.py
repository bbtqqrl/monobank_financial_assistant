import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.monobank import MonoTransactionSchema, MonoWebhookPayload

logger = logging.getLogger(__name__)


class MonobankWebhookService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.jars = JarRepository(db)
        self.accounts = AccountRepository(db)
        self.transactions = TransactionRepository(db)

    async def process(self, payload: MonoWebhookPayload) -> int | None:
        """Store or update the transaction. Returns the id of a newly created
        transaction (which still needs categorizing), otherwise None."""
        logger.debug("Monobank webhook received: %s", payload)

        mono_id = payload.data.account
        transaction = payload.data.statementItem

        if await self._update_existing(transaction):
            return None

        logger.info("Transaction received: id=%s, account=%s", transaction.id, mono_id)
        logger.debug(
            "Transaction details: id=%s, description=%s, amount=%s, currency=%s",
            transaction.id,
            transaction.description,
            transaction.amount,
            transaction.currencyCode,
        )

        account_id = None
        jar_id = None

        account = await self.accounts.get_by_mono_id(mono_id)

        if account:
            account_id = account.id
            user_id = account.user_id
        else:
            jar = await self.jars.get_by_mono_id(mono_id)

            if jar is None:
                logger.warning("Account or jar not found: mono_id=%s", mono_id)
                return None

            jar_id = jar.id
            user_id = jar.user_id

        created_id = await self.transactions.insert_from_mono(
            user_id=user_id,
            account_id=account_id,
            jar_id=jar_id,
            transaction=transaction,
        )
        await self.db.commit()

        if created_id is None:
            # The statement backfill inserted it between our lookup and the
            # insert - apply this (possibly newer) version on top of it.
            await self._update_existing(transaction)
            return None

        logger.info("Transaction saved successfully: id=%s", transaction.id)
        return created_id

    async def _update_existing(self, transaction: MonoTransactionSchema) -> bool:
        existing = await self.transactions.get_by_mono_id(transaction.id)
        if existing is None:
            return False

        # Budgets are summed from transactions on read, so a hold settling at a
        # different amount needs nothing beyond updating the row itself.
        changed = await self.transactions.update_from_webhook(existing, transaction)
        await self.db.commit()

        if changed:
            logger.info(
                "Transaction updated: id=%s hold=%s amount=%s",
                transaction.id, transaction.hold, transaction.amount,
            )
        else:
            logger.info("Transaction already exists, no changes: id=%s", transaction.id)
        return True
