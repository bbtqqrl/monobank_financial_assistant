import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.monobank import MonoTransactionSchema
from app.services.ai.factory import get_categorization_ai_client
from app.services.api_client import MonobankAPIClient
from app.services.categorization_service import CategorizationAIError, CategorizationService

logger = logging.getLogger(__name__)

BACKFILL_DAYS = 30
STATEMENT_RATE_LIMIT_SECONDS = 60


class StatementBackfillService:
    """Pulls the last BACKFILL_DAYS of Monobank history for a newly
    connected user, so they see real data instead of an empty screen."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
        self.transactions = TransactionRepository(db)

    async def backfill(self, user_id: int, token: str) -> None:
        accounts = [a for a in await self.accounts.list_for_user(user_id) if a.is_active]
        jars = [j for j in await self.jars.list_for_user(user_id) if j.is_active]

        # (internal account_id, internal jar_id, Monobank's own id for the API call)
        targets = (
            [(account.id, None, account.mono_account_id) for account in accounts]
            + [(None, jar.id, jar.mono_jar_id) for jar in jars]
        )
        if not targets:
            return

        to_ts = int(datetime.now(timezone.utc).timestamp())
        from_ts = to_ts - BACKFILL_DAYS * 86400

        created_ids: list[int] = []
        try:
            for i, (account_id, jar_id, mono_id) in enumerate(targets):
                # Monobank allows this endpoint at most once every 60 seconds,
                # regardless of which account/jar it's called for.
                if i > 0:
                    await asyncio.sleep(STATEMENT_RATE_LIMIT_SECONDS)
                created_ids += await self._backfill_one(
                    user_id, token, account_id, jar_id, mono_id, from_ts, to_ts,
                )
        finally:
            await self.api.close()

        await self._categorize_all(created_ids)

    async def _backfill_one(
        self,
        user_id: int,
        token: str,
        account_id: int | None,
        jar_id: int | None,
        mono_id: str,
        from_ts: int,
        to_ts: int,
    ) -> list[int]:
        try:
            items = await self.api.get_statement(token, mono_id, from_ts, to_ts)
        except Exception:
            logger.exception(
                "Statement backfill request failed for mono_id=%s user_id=%s", mono_id, user_id,
            )
            return []

        created_ids = []
        for raw in items:
            transaction = MonoTransactionSchema.model_validate(raw)
            if await self.transactions.get_by_mono_id(transaction.id) is not None:
                continue
            db_transaction = await self.transactions.create(
                user_id=user_id, account_id=account_id, jar_id=jar_id, transaction=transaction,
            )
            created_ids.append(db_transaction.id)

        await self.db.commit()
        logger.info(
            "Backfilled %s new transactions for mono_id=%s user_id=%s", len(created_ids), mono_id, user_id,
        )
        return created_ids

    async def _categorize_all(self, transaction_ids: list[int]) -> None:
        service = CategorizationService(self.db, get_categorization_ai_client())
        for transaction_id in transaction_ids:
            try:
                await service.categorize(transaction_id)
            except CategorizationAIError:
                logger.warning(
                    "Backfill categorization failed for transaction id=%s, flagging for manual review",
                    transaction_id, exc_info=True,
                )
                await service.mark_categorization_failed(transaction_id)
