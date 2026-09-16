from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, SessionLocal
from app.services.ai.mock_client import MockCategorizationAIClient
from app.services.categorization_service import CategorizationService
from app.services.webhook_service import MonobankWebhookService
from app.schemas.monobank import MonoWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def run_categorization(transaction_id: int) -> None:
    async with SessionLocal() as db:
        service = CategorizationService(db, MockCategorizationAIClient())
        await service.categorize(transaction_id)


@router.post("/monobank")
async def monobank_webhook(
    payload: MonoWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    service = MonobankWebhookService(db)

    transaction = await service.process(payload)

    if transaction is not None:
        background_tasks.add_task(run_categorization, transaction.id)

    return {"status": "ok"}
