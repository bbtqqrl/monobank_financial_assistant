from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.monobank import (ConnectMonobankRequest,ConnectMonobankResponse,)
from services.sync_service import MonobankSyncService

router = APIRouter(prefix="/monobank", tags=["Monobank"])


@router.post("/connect",response_model=ConnectMonobankResponse,)
async def connect_monobank(data: ConnectMonobankRequest,db: AsyncSession = Depends(get_db),):
    try:
        service = MonobankSyncService(db)

        client_info = await service.connect(data.token)

        return ConnectMonobankResponse(
            success=True,
            message=f"Monobank connected successfully for client \n\n{client_info}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
