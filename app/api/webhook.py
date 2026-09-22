import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MONO_WEBHOOK_VERIFY_SIGNATURE
from app.db.session import get_db, SessionLocal
from app.services.ai.factory import get_categorization_ai_client
from app.services.categorization_service import CategorizationAIError, CategorizationService
from app.services.monobank_signature import monobank_signature_verifier
from app.services.webhook_service import MonobankWebhookService
from app.schemas.monobank import MonoWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

MAX_CATEGORIZATION_ATTEMPTS = 3
CATEGORIZATION_RETRY_DELAY_SECONDS = 300


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
                asyncio.create_task(_retry_categorization_later(transaction_id, attempt + 1))
            else:
                logger.error(
                    "Categorization failed for transaction id=%s after %s attempts, giving up",
                    transaction_id, MAX_CATEGORIZATION_ATTEMPTS,
                    exc_info=True,
                )
                await service.mark_categorization_failed(transaction_id)


async def _retry_categorization_later(transaction_id: int, attempt: int) -> None:
    await asyncio.sleep(CATEGORIZATION_RETRY_DELAY_SECONDS)
    await run_categorization(transaction_id, attempt=attempt)


@router.post("/monobank")
async def monobank_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_sign: str | None = Header(default=None, alias="X-Sign"),
    x_key_id: str | None = Header(default=None, alias="X-Key-Id"),
):
    body = await request.body()

    is_valid = await monobank_signature_verifier.verify(body, x_sign or "", x_key_id)
    if not is_valid:
        if MONO_WEBHOOK_VERIFY_SIGNATURE:
            logger.warning("Rejected Monobank webhook with invalid signature")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        else:
            logger.warning(
                "Monobank webhook signature check FAILED but MONO_WEBHOOK_VERIFY_SIGNATURE is off - "
                "processing anyway (diagnostic mode)"
            )

    try:
        payload = MonoWebhookPayload.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload")

    service = MonobankWebhookService(db)

    transaction = await service.process(payload)

    if transaction is not None:
        background_tasks.add_task(run_categorization, transaction.id)

    return {"status": "ok"}
