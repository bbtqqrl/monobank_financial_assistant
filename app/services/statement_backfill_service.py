import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
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
AI_CONCURRENCY = 8


class StatementBackfillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
        self.transactions = TransactionRepository(db)

    async def backfill(self, user_id: int, token: str) -> None:
        accounts = [
            a for a in await self.accounts.list_for_user(user_id)
            if a.is_active and a.statement_backfilled_at is None
        ]
        jars = [
            j for j in await self.jars.list_for_user(user_id)
            if j.is_active and j.statement_backfilled_at is None
        ]
        if not accounts and not jars:
            return

        to_ts = int(datetime.now(timezone.utc).timestamp())
        from_ts = to_ts - BACKFILL_DAYS * 86400

        created_ids: list[int] = []
        try:
            first = True
            for account in accounts:
                if not first:
                    await asyncio.sleep(STATEMENT_RATE_LIMIT_SECONDS)
                first = False
                created_ids += await self._backfill_account(user_id, token, account, from_ts, to_ts)

            for jar in jars:
                if not first:
                    await asyncio.sleep(STATEMENT_RATE_LIMIT_SECONDS)
                first = False
                created_ids += await self._backfill_jar(user_id, token, jar, from_ts, to_ts)
        finally:
            await self.api.close()

        await self._categorize_all(created_ids)

    async def _backfill_account(self, user_id: int, token: str, account, from_ts: int, to_ts: int) -> list[int]:
        created_ids = await self._fetch_and_store(
            user_id, token, account.mono_account_id, from_ts, to_ts,
            account_id=account.id, jar_id=None,
        )
        if created_ids is not None:
            self.accounts.mark_backfilled(account, datetime.now(timezone.utc))
            await self.db.commit()
        return created_ids or []

    async def _backfill_jar(self, user_id: int, token: str, jar, from_ts: int, to_ts: int) -> list[int]:
        created_ids = await self._fetch_and_store(
            user_id, token, jar.mono_jar_id, from_ts, to_ts,
            account_id=None, jar_id=jar.id,
        )
        if created_ids is not None:
            self.jars.mark_backfilled(jar, datetime.now(timezone.utc))
            await self.db.commit()
        return created_ids or []

    async def _fetch_and_store(
        self,
        user_id: int,
        token: str,
        mono_id: str,
        from_ts: int,
        to_ts: int,
        account_id: int | None,
        jar_id: int | None,
    ) -> list[int] | None:
        try:
            items = await self.api.get_statement(token, mono_id, from_ts, to_ts)
        except Exception:
            logger.exception(
                "Statement backfill request failed for mono_id=%s user_id=%s", mono_id, user_id,
            )
            return None

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
        semaphore = asyncio.Semaphore(AI_CONCURRENCY)

        async def _categorize_one(transaction_id: int) -> None:
            async with semaphore, SessionLocal() as db:
                service = CategorizationService(db, get_categorization_ai_client())
                try:
                    await service.categorize(transaction_id)
                except CategorizationAIError:
                    logger.warning(
                        "Backfill categorization failed for transaction id=%s, flagging for manual review",
                        transaction_id, exc_info=True,
                    )
                    await service.mark_categorization_failed(transaction_id)
                except Exception:
                    logger.exception(
                        "Unexpected error categorizing transaction id=%s during backfill", transaction_id,
                    )

        await asyncio.gather(*(_categorize_one(tid) for tid in transaction_ids))
