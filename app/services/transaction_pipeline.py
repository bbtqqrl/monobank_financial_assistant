import asyncio
import logging
import time

from app.core.tasks import spawn
from app.db.models.transaction import TransactionRaw
from app.db.session import SessionLocal
from app.repositories.transaction import TransactionRepository
from app.services.ai.factory import get_categorization_ai_client
from app.services.categorization_service import CategorizationAIError, CategorizationService
from app.services.push import PushService

logger = logging.getLogger(__name__)

MAX_CATEGORIZATION_ATTEMPTS = 3
CATEGORIZATION_RETRY_DELAY_SECONDS = 300
LOCATION_WAIT_SECONDS = 90
LOCATION_MAX_AGE_SECONDS = 10 * 60
LOCATION_REQUEST = "location_request"


def needs_location(transaction: TransactionRaw, now: float | None = None) -> bool:
    return (
        transaction.source == "monobank"
        and transaction.amount < 0
        and transaction.mcc is not None
        and transaction.counter_iban is None
        and transaction.latitude is None
        and (now or time.time()) - transaction.time <= LOCATION_MAX_AGE_SECONDS
    )


async def process_new_transaction(transaction_id: int) -> None:
    async with SessionLocal() as db:
        transaction = await TransactionRepository(db).get_by_id(transaction_id)
        if transaction is not None and needs_location(transaction):
            requested = await PushService(db).send_silent(
                transaction.user_id, {"type": LOCATION_REQUEST, "transaction_id": transaction_id},
            )
            if requested:
                logger.info("Location requested for transaction id=%s", transaction_id)
                spawn(_categorize_later(transaction_id, LOCATION_WAIT_SECONDS))
                return
    await run_categorization(transaction_id)


async def run_categorization(transaction_id: int, attempt: int = 1) -> None:
    async with SessionLocal() as db:
        service = CategorizationService(db, get_categorization_ai_client())
        try:
            await service.categorize(transaction_id)
        except CategorizationAIError:
            if attempt < MAX_CATEGORIZATION_ATTEMPTS:
                logger.warning(
                    "Categorization failed for transaction id=%s, retrying in %ss (attempt %s/%s)",
                    transaction_id, CATEGORIZATION_RETRY_DELAY_SECONDS, attempt, MAX_CATEGORIZATION_ATTEMPTS,
                    exc_info=True,
                )
                spawn(_categorize_later(transaction_id, CATEGORIZATION_RETRY_DELAY_SECONDS, attempt + 1))
            else:
                logger.error(
                    "Categorization failed for transaction id=%s after %s attempts, giving up",
                    transaction_id, MAX_CATEGORIZATION_ATTEMPTS,
                    exc_info=True,
                )
                await service.mark_categorization_failed(transaction_id)


async def _categorize_later(transaction_id: int, delay_seconds: float, attempt: int = 1) -> None:
    await asyncio.sleep(delay_seconds)
    await run_categorization(transaction_id, attempt=attempt)
