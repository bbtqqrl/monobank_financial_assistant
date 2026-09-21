import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MONO_WEBHOOK_VERIFY_SIGNATURE
from app.db.session import get_db, SessionLocal
from app.services.ai.mock_client import MockCategorizationAIClient
from app.services.categorization_service import CategorizationService
from app.services.monobank_signature import monobank_signature_verifier
from app.services.webhook_service import MonobankWebhookService
from app.schemas.monobank import MonoWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def run_categorization(transaction_id: int) -> None:
    async with SessionLocal() as db:
        service = CategorizationService(db, MockCategorizationAIClient())
        await service.categorize(transaction_id)


@router.post("/monobank")
async def monobank_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_sign: str | None = Header(default=None, alias="X-Sign"),
    x_key_id: str | None = Header(default=None, alias="X-Key-Id"),
):
    body = await request.body()

    if MONO_WEBHOOK_VERIFY_SIGNATURE:
        is_valid = await monobank_signature_verifier.verify(body, x_sign or "", x_key_id)
        if not is_valid:
            logger.warning("Rejected Monobank webhook with invalid signature")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = MonoWebhookPayload.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload")

    service = MonobankWebhookService(db)

    transaction = await service.process(payload)

    if transaction is not None:
        background_tasks.add_task(run_categorization, transaction.id)

    return {"status": "ok"}
