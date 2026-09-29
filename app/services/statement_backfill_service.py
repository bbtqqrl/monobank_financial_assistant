import asyncio
import logging
import time
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
# Monobank returns at most this many items per statement request, newest
# first; a full page means there's more to fetch further back.
STATEMENT_PAGE_SIZE = 500
AI_CONCURRENCY = 8


class StatementBackfillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
        self.transactions = TransactionRepository(db)
        self._last_statement_call: float | None = None
        self._ai_semaphore = asyncio.Semaphore(AI_CONCURRENCY)

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

        # Each account's transactions are categorized as soon as they're
        # stored, overlapping with the rate-limit wait before the next account,
        # rather than all at the end where a crash would lose the lot.
        categorization_tasks: list[asyncio.Task] = []
        try:
            for account in accounts:
                created_ids = await self._fetch_and_store(
                    user_id, token, account.mono_account_id, from_ts, to_ts,
                    account_id=account.id, jar_id=None,
                )
                if created_ids is not None:
                    self.accounts.mark_backfilled(account, datetime.now(timezone.utc))
                    await self.db.commit()
                    categorization_tasks.append(asyncio.create_task(self._categorize_all(created_ids)))

            for jar in jars:
                created_ids = await self._fetch_and_store(
                    user_id, token, jar.mono_jar_id, from_ts, to_ts,
                    account_id=None, jar_id=jar.id,
                )
                if created_ids is not None:
                    self.jars.mark_backfilled(jar, datetime.now(timezone.utc))
                    await self.db.commit()
                    categorization_tasks.append(asyncio.create_task(self._categorize_all(created_ids)))
        finally:
            await self.api.close()
            await asyncio.gather(*categorization_tasks)

    async def _get_statement(self, token: str, mono_id: str, from_ts: int, to_ts: int) -> list[dict]:
        """Monobank allows one statement request per 60s per token, across
        all of that token's accounts - so the wait is tracked per call, not
        per account (an account can take several paged calls)."""
        if self._last_statement_call is not None:
            wait = STATEMENT_RATE_LIMIT_SECONDS - (time.monotonic() - self._last_statement_call)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            return await self.api.get_statement(token, mono_id, from_ts, to_ts)
        finally:
            self._last_statement_call = time.monotonic()

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
        """Returns ids of newly stored transactions, or None if any page
        failed to download (the account then stays pending and is retried on
        the next startup; what was stored so far is kept and deduplicated)."""
        created_ids: list[int] = []
        page_to = to_ts

        while True:
            try:
                items = await self._get_statement(token, mono_id, from_ts, page_to)
            except Exception:
                logger.exception(
                    "Statement backfill request failed for mono_id=%s user_id=%s", mono_id, user_id,
                )
                await self.db.commit()
                return None

            for raw in items:
                transaction = MonoTransactionSchema.model_validate(raw)
                created_id = await self.transactions.insert_from_mono(
                    user_id=user_id, account_id=account_id, jar_id=jar_id, transaction=transaction,
                )
                if created_id is not None:
                    created_ids.append(created_id)
            await self.db.commit()

            if len(items) < STATEMENT_PAGE_SIZE:
                break

            # Items sharing the oldest second may straddle the page boundary,
            # so the next page includes that second again; duplicates are
            # dropped by insert_from_mono. If a whole page is one second,
            # step past it to guarantee progress.
            oldest = min(item["time"] for item in items)
            page_to = oldest if oldest < page_to else page_to - 1
            if page_to <= from_ts:
                break

        logger.info(
            "Backfilled %s new transactions for mono_id=%s user_id=%s", len(created_ids), mono_id, user_id,
        )
        return created_ids

    async def _categorize_all(self, transaction_ids: list[int]) -> None:
        async def _categorize_one(transaction_id: int) -> None:
            async with self._ai_semaphore, SessionLocal() as db:
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
