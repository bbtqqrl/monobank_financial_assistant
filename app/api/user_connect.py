import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import SessionLocal, get_db
from app.schemas.monobank import ConnectMonobankRequest, ConnectMonobankResponse, MonobankRefreshResponse
from app.services.statement_backfill_service import StatementBackfillService
from app.services.sync_service import MonobankNotConnectedError, MonobankSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monobank", tags=["Monobank"])


# Users with a backfill already running in this process. A second one would
# only compete for the same 1-per-60s statement rate limit.
_backfilling_users: set[int] = set()


async def run_statement_backfill(user_id: int, token: str) -> None:
    if user_id in _backfilling_users:
        logger.info("Statement backfill already running for user_id=%s, skipping", user_id)
        return
    _backfilling_users.add(user_id)
    try:
        async with SessionLocal() as db:
            await StatementBackfillService(db).backfill(user_id, token)
    except Exception:
        logger.exception("Statement backfill crashed for user_id=%s", user_id)
    finally:
        _backfilling_users.discard(user_id)


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


@router.post("/debug/client-info", response_model=MonobankRefreshResponse)
async def refresh_client_info(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-sync the user's cards and jars from Monobank using their stored
    token and return them."""
    try:
        accounts, jars = await MonobankSyncService(db).refresh(current_user)
    except MonobankNotConnectedError:
        raise HTTPException(status_code=400, detail="Monobank is not connected")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            # client-info is limited to one call per 60s per token
            raise HTTPException(status_code=429, detail="Monobank rate limit, try again in a minute")
        logger.warning(
            "Monobank rejected stored token for user_id=%s status=%s", current_user.id, e.response.status_code,
        )
        raise HTTPException(status_code=400, detail="Invalid or expired Monobank token")

    # A card or jar opened since connecting has no history yet.
    if any(a.is_active and a.statement_backfilled_at is None for a in accounts) or any(
        j.is_active and j.statement_backfilled_at is None for j in jars
    ):
        background_tasks.add_task(run_statement_backfill, current_user.id, current_user.mono_token)

    return MonobankRefreshResponse(accounts=accounts, jars=jars)
