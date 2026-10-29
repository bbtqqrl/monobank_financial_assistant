from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.notification import NotificationItem, NotificationSettings, NotificationsResponse
from app.services.notifications import NotificationService, NotificationType

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _settings(user: User) -> NotificationSettings:
    return NotificationSettings(enabled={kind: kind not in user.disabled_notifications for kind in NotificationType})


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    unread, items = await NotificationService(db).list(current_user.id, limit, offset)
    return NotificationsResponse(unread_count=unread, items=[NotificationItem.model_validate(item) for item in items])


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService(db).mark_read(current_user.id)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService(db).mark_read(current_user.id, notification_id)


@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    return _settings(current_user)


@router.patch("/settings", response_model=NotificationSettings)
async def update_notification_settings(
    data: NotificationSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService(db).set_enabled(current_user, data.enabled)
    return _settings(current_user)
