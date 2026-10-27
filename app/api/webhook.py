import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MONO_WEBHOOK_VERIFY_SIGNATURE
from app.db.session import get_db
from app.services.monobank_signature import monobank_signature_verifier
from app.services.transaction_pipeline import process_new_transaction
from app.services.webhook_service import MonobankWebhookService
from app.schemas.monobank import MonoWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/monobank")
async def monobank_webhook_check():
    """Monobank sends a GET to the webhook URL when it's being registered
    and expects a plain 200 back."""
    return {"status": "ok"}


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

    created_id = await service.process(payload)

    if created_id is not None:
        background_tasks.add_task(process_new_transaction, created_id)

    return {"status": "ok"}
