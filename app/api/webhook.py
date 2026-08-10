from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.webhook_service import MonobankWebhookService
from app.schemas.monobank import MonoWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/monobank")
async def monobank_webhook(payload: MonoWebhookPayload, db: AsyncSession = Depends(get_db)):
    service = MonobankWebhookService(db)

    await service.process(payload)

    return {"status": "ok"}