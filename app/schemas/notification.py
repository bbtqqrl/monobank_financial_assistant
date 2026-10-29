from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class NotificationType(StrEnum):
    SUBSCRIPTION_PRICE = "subscription_price"
    NEW_SUBSCRIPTION = "new_subscription"
    MONTH_PACE = "month_pace"
    WEEKLY_SUMMARY = "weekly_summary"
    INSIGHTS = "insights"


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
