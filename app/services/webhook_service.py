import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transaction import TransactionRaw
from app.repositories.account import AccountRepository
from app.repositories.budget import BudgetRepository
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
        self.budgets = BudgetRepository(db)

    async def process(self, payload: MonoWebhookPayload) -> TransactionRaw | None:
        logger.debug("Monobank webhook received: %s", payload)

        mono_id  = payload.data.account
        transaction = payload.data.statementItem
        account_id = None
        jar_id = None

        existing = await self.transactions.get_by_mono_id(transaction.id)

        if existing is not None:
            old_amount = existing.amount
            changed = await self.transactions.update_from_webhook(existing, transaction)

            # A hold is often categorized (and budgeted) before Monobank sends
            # the final settled amount. If that later update changes the
            # amount, the budget it already contributed to needs the
            # difference, not the old hold amount.
            if changed and existing.category_id is not None and old_amount != existing.amount:
                budget = await self.budgets.get_by_category_for_user(existing.user_id, existing.category_id)
                if budget is not None:
                    old_spend = -old_amount if old_amount < 0 else 0
                    new_spend = -existing.amount if existing.amount < 0 else 0
                    self.budgets.adjust_current_amount(budget, new_spend - old_spend)

            await self.db.commit()
            if changed:
                logger.info(
                    "Transaction updated: id=%s hold=%s amount=%s",
                    transaction.id, transaction.hold, transaction.amount,
                )
            else:
                logger.info("Transaction already exists, no changes: id=%s", transaction.id)
            return None

        logger.info("Transaction received: id=%s, account=%s", transaction.id, mono_id)
        logger.debug(
            "Transaction details: id=%s, description=%s, amount=%s, currency=%s",
            transaction.id,
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
                return None

            jar_id = jar.id
            user_id = jar.user_id

        db_transaction = await self.transactions.create(
            user_id=user_id,
            account_id=account_id,
            jar_id=jar_id,
            transaction=transaction,
        )

        await self.db.commit()

        logger.info("Transaction saved successfully: id=%s", transaction.id)

        return db_transaction