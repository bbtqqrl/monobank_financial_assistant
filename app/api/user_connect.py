import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import SessionLocal, get_db
from app.schemas.monobank import (ConnectMonobankRequest,ConnectMonobankResponse,)
from app.services.api_client import MonobankAPIClient
from app.services.statement_backfill_service import StatementBackfillService
from app.services.sync_service import MonobankSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monobank", tags=["Monobank"])


async def run_statement_backfill(user_id: int, token: str) -> None:
    async with SessionLocal() as db:
        try:
            await StatementBackfillService(db).backfill(user_id, token)
        except Exception:
            logger.exception("Statement backfill crashed for user_id=%s", user_id)


@router.post("/connect",response_model=ConnectMonobankResponse,)
async def connect_monobank(
    data: ConnectMonobankRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = MonobankSyncService(db)

        client_info = await service.connect(current_user, data.token)

        background_tasks.add_task(run_statement_backfill, current_user.id, data.token)

        return ConnectMonobankResponse(
            success=True,
            message="Monobank connected successfully",
        )

    except httpx.HTTPStatusError:
        logger.warning("Monobank rejected token for user_id=%s", current_user.id)
        raise HTTPException(status_code=400, detail="Invalid or expired Monobank token")

    except Exception:
        logger.exception("Failed to connect Monobank for user_id=%s", current_user.id)
        raise HTTPException(status_code=400, detail="Failed to connect Monobank account")

@router.post("/debug/client-info")
async def client_info(data: ConnectMonobankRequest, current_user: User = Depends(get_current_user)):
    service = MonobankAPIClient()
    try:
        return await service.get_client_info(data.token)
    finally:
        await service.close()
