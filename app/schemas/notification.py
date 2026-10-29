from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.services.notifications import NotificationType


class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    body: str
    data: dict
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationsResponse(BaseModel):
    unread_count: int
    items: list[NotificationItem]


class NotificationSettings(BaseModel):
    enabled: dict[NotificationType, bool]
