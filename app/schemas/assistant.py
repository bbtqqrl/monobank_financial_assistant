from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_MESSAGE_LENGTH = 4000


class ClientContext(BaseModel):
    timezone: str | None = Field(default=None, max_length=64, description="IANA, наприклад Europe/Warsaw")
    # TODO: геолокація — додати location (lat, lon, accuracy), коли з'являться places

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown timezone")
        return value


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    context: ClientContext | None = None

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message is empty")
        return value


class ConversationResponse(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    has_more: bool


class PendingActionResponse(BaseModel):
    id: int
    action_type: str
    preview: dict
    status: Literal["pending", "confirmed", "rejected", "expired", "failed"]
    result: dict | None
    error: str | None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
