from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.device import DeviceRepository
from app.schemas.device import RegisterDeviceRequest

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(
    data: RegisterDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DeviceRepository(db).upsert(current_user.id, data.push_token, data.platform)
    await db.commit()


@router.delete("/{push_token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(
    push_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DeviceRepository(db).delete_for_user(current_user.id, push_token)
    await db.commit()
