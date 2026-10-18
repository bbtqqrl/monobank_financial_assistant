import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
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

# TODO: глибина історії має залежати від плану користувача (free — місяць, pro — рік)
BACKFILL_DAYS = 183
STATEMENT_WINDOW_SECONDS = 31 * 86400
STATEMENT_RATE_LIMIT_SECONDS = 60
# Monobank returns at most this many items per statement request, newest
# first; a full page means there's more to fetch further back.
STATEMENT_PAGE_SIZE = 500
AI_CONCURRENCY = 8
CATCH_UP_OVERLAP_SECONDS = 3600

_backfilling_users: set[int] = set()


async def run_statement_backfill(user_id: int, token: str, catch_up: bool = False) -> None:
    if user_id in _backfilling_users:
        logger.info("Statement backfill already running for user_id=%s, skipping", user_id)
        return
    _backfilling_users.add(user_id)
    try:
        async with SessionLocal() as db:
            await StatementBackfillService(db).backfill(user_id, token, catch_up=catch_up)
    except Exception:
        logger.exception("Statement backfill crashed for user_id=%s", user_id)
    finally:
        _backfilling_users.discard(user_id)


class StatementBackfillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = MonobankAPIClient()
        self.accounts = AccountRepository(db)
        self.jars = JarRepository(db)
        self.transactions = TransactionRepository(db)
        self._last_statement_call: float | None = None
        self._ai_semaphore = asyncio.Semaphore(AI_CONCURRENCY)

    async def backfill(self, user_id: int, token: str, catch_up: bool = False) -> None:
        to_ts = int(datetime.now(timezone.utc).timestamp())
        oldest_ts = to_ts - BACKFILL_DAYS * 86400

        holders = [
            (account, self.accounts, account.mono_account_id, account.id, None, account.currency_code)
            for account in await self.accounts.list_for_user(user_id)
            if account.is_active and self._needs_backfill(account, catch_up, oldest_ts)
        ] + [
            (jar, self.jars, jar.mono_jar_id, None, jar.id, jar.currency_code)
            for jar in await self.jars.list_for_user(user_id)
            if jar.is_active and self._needs_backfill(jar, catch_up, oldest_ts)
        ]
        if not holders:
            return

        # Each account's transactions are categorized as soon as they're
        # stored, overlapping with the rate-limit wait before the next account,
        # rather than all at the end where a crash would lose the lot.
        categorization_tasks: list[asyncio.Task] = []
        try:
            for holder, repository, mono_id, account_id, jar_id, currency in holders:
                created_ids, covered_from, ok = await self._backfill_holder(
                    user_id, token, holder, mono_id, account_id, jar_id, currency, oldest_ts, to_ts, catch_up,
                )
                if ok:
                    repository.mark_backfilled(holder, datetime.now(timezone.utc), covered_from)
                await self.db.commit()
                if created_ids:
                    categorization_tasks.append(asyncio.create_task(self._categorize_all(created_ids)))
        finally:
            await self.api.close()
            await asyncio.gather(*categorization_tasks)

    @staticmethod
    def _needs_backfill(holder, catch_up: bool, oldest_ts: int) -> bool:
        if catch_up or holder.statement_backfilled_at is None:
            return True
        return holder.statement_backfilled_from is None or holder.statement_backfilled_from > oldest_ts

    async def _backfill_holder(
        self,
        user_id: int,
        token: str,
        holder,
        mono_id: str,
        account_id: int | None,
        jar_id: int | None,
        currency: int,
        oldest_ts: int,
        to_ts: int,
        catch_up: bool,
    ) -> tuple[list[int], int | None, bool]:
        covered_from = holder.statement_backfilled_from
        ranges: list[tuple[int, int, bool]] = []

        if holder.statement_backfilled_at is None:
            ranges.append((oldest_ts, to_ts, True))
        else:
            backfilled_at_ts = int(holder.statement_backfilled_at.timestamp())
            if catch_up:
                anchor = await self.transactions.last_mono_time(account_id, jar_id) or backfilled_at_ts
                ranges.append((max(anchor - CATCH_UP_OVERLAP_SECONDS, oldest_ts), to_ts, False))
            if covered_from is None or covered_from > oldest_ts:
                upper = covered_from or await self.transactions.first_mono_time(account_id, jar_id) or backfilled_at_ts
                if upper > oldest_ts:
                    ranges.append((oldest_ts, upper + CATCH_UP_OVERLAP_SECONDS, True))
                else:
                    covered_from = oldest_ts

        created_ids: list[int] = []
        for from_ts, range_to, deepens in ranges:
            ids, reached = await self._fetch_range(
                user_id, token, mono_id, from_ts, range_to, account_id, jar_id, currency,
            )
            created_ids += ids
            if reached is None:
                return created_ids, covered_from, False
            if deepens:
                covered_from = reached

        logger.info(
            "Backfilled %s new transactions for mono_id=%s user_id=%s, history from %s",
            len(created_ids), mono_id, user_id,
            datetime.fromtimestamp(covered_from, timezone.utc).date() if covered_from else None,
        )
        return created_ids, covered_from, True

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

    async def _fetch_range(
        self,
        user_id: int,
        token: str,
        mono_id: str,
        from_ts: int,
        to_ts: int,
        account_id: int | None,
        jar_id: int | None,
        currency: int,
    ) -> tuple[list[int], int | None]:
        created_ids: list[int] = []
        window_to = to_ts
        while window_to > from_ts:
            window_from = max(from_ts, window_to - STATEMENT_WINDOW_SECONDS)
            try:
                created_ids += await self._fetch_window(
                    user_id, token, mono_id, window_from, window_to, account_id, jar_id, currency,
                )
            except httpx.HTTPStatusError as e:
                await self.db.commit()
                if e.response.status_code == 400:
                    logger.warning(
                        "Monobank refused statement for mono_id=%s before %s: %s",
                        mono_id, datetime.fromtimestamp(window_to, timezone.utc).date(), e.response.text[:300],
                    )
                    return created_ids, from_ts
                logger.exception("Statement backfill request failed for mono_id=%s user_id=%s", mono_id, user_id)
                return created_ids, None
            except Exception:
                await self.db.commit()
                logger.exception("Statement backfill request failed for mono_id=%s user_id=%s", mono_id, user_id)
                return created_ids, None
            window_to = window_from
        return created_ids, from_ts

    async def _fetch_window(
        self,
        user_id: int,
        token: str,
        mono_id: str,
        from_ts: int,
        to_ts: int,
        account_id: int | None,
        jar_id: int | None,
        currency: int,
    ) -> list[int]:
        created_ids: list[int] = []
        page_to = to_ts

        while True:
            items = await self._get_statement(token, mono_id, from_ts, page_to)

            for raw in items:
                transaction = MonoTransactionSchema.model_validate(raw)
                created_id = await self.transactions.insert_from_mono(
                    user_id=user_id, account_id=account_id, jar_id=jar_id, currency=currency,
                    transaction=transaction,
                )
                if created_id is not None:
                    created_ids.append(created_id)
            await self.db.commit()

            if len(items) < STATEMENT_PAGE_SIZE:
                return created_ids

            # Items sharing the oldest second may straddle the page boundary,
            # so the next page includes that second again; duplicates are
            # dropped by insert_from_mono. If a whole page is one second,
            # step past it to guarantee progress.
            oldest = min(item["time"] for item in items)
            page_to = oldest if oldest < page_to else page_to - 1
            if page_to <= from_ts:
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
