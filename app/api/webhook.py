from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.webhook_service import MonobankWebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/monobank")
async def monobank_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    service = MonobankWebhookService(db)

    await service.process(payload)

    return {"status": "ok"}