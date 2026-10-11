import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.tasks import spawn
from app.db.models.user import User
from app.db.session import SessionLocal
from app.repositories.transaction import TransactionRepository
from app.services.ai.factory import get_categorization_ai_client
from app.services.categorization_service import CategorizationAIError, CategorizationService
from app.services.exchange_rates import amount_uah
from app.services.statement_backfill_service import run_statement_backfill

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 5 * 60
# Webhook categorization retries in-process for ~10 minutes (see
# app.api.webhook); anything still uncategorized past this age had its
# in-memory task lost to a restart/deploy/crash.
STALE_AFTER = timedelta(minutes=20)
# While the AI keeps failing, keep retrying on each sweep for this long before
# giving up and flagging the transaction for manual review.
GIVE_UP_AFTER = timedelta(hours=24)
SWEEP_BATCH_SIZE = 200
CATCH_UP_INTERVAL_SECONDS = 24 * 60 * 60
SWEEP_CONCURRENCY = 4


async def sweep_uncategorized() -> None:
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        transaction_ids = await TransactionRepository(db).list_uncategorized_ids(
            created_before=now - STALE_AFTER, limit=SWEEP_BATCH_SIZE,
        )
    if not transaction_ids:
        return

    logger.info("Sweeper: categorizing %s stale uncategorized transaction(s)", len(transaction_ids))
    semaphore = asyncio.Semaphore(SWEEP_CONCURRENCY)

    async def _one(transaction_id: int) -> None:
        async with semaphore, SessionLocal() as db:
            service = CategorizationService(db, get_categorization_ai_client())
            try:
                await service.categorize(transaction_id)
            except CategorizationAIError:
                await db.rollback()
                transaction = await TransactionRepository(db).get_by_id(transaction_id)
                if transaction is not None and transaction.created_at < now - GIVE_UP_AFTER:
                    await service.mark_categorization_failed(transaction_id)
                else:
                    logger.warning("Sweeper: AI still failing for transaction id=%s, will retry", transaction_id)
            except Exception:
                logger.exception("Sweeper: unexpected error categorizing transaction id=%s", transaction_id)

    await asyncio.gather(*(_one(tid) for tid in transaction_ids))


async def fill_missing_amount_uah() -> None:
    async with SessionLocal() as db:
        rows = await TransactionRepository(db).list_missing_amount_uah(limit=SWEEP_BATCH_SIZE)
        filled = 0
        for transaction, currency in rows:
            value = await amount_uah(
                transaction.amount, transaction.operation_amount, currency, transaction.currency_code, transaction.time,
            )
            if value is not None:
                transaction.amount_uah = value
                filled += 1
        await db.commit()
    if rows:
        logger.info("Sweeper: filled amount_uah for %s of %s transaction(s)", filled, len(rows))


async def catch_up_statements() -> None:
    async with SessionLocal() as db:
        users = (await db.execute(
            select(User.id, User.mono_token).where(User.is_active.is_(True), User.mono_token.is_not(None))
        )).all()
    for user_id, token in users:
        spawn(run_statement_backfill(user_id, token, catch_up=True))
    if users:
        logger.info("Sweeper: started statement catch-up for %s user(s)", len(users))


async def run_sweeper_forever() -> None:
    last_catch_up: float | None = None
    while True:
        if last_catch_up is None or time.monotonic() - last_catch_up >= CATCH_UP_INTERVAL_SECONDS:
            try:
                await catch_up_statements()
                last_catch_up = time.monotonic()
            except Exception:
                logger.exception("Statement catch-up failed")
        try:
            await fill_missing_amount_uah()
        except Exception:
            logger.exception("amount_uah sweep failed")
        try:
            await sweep_uncategorized()
        except Exception:
            logger.exception("Categorization sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
