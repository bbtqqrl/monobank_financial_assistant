from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.webhook_service import MonobankWebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/monobank")
async def monobank_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    service = MonobankWebhookService(db)

    await service.process(payload)

    return {"status": "ok"}