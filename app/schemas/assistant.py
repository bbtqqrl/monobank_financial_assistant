from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_MESSAGE_LENGTH = 4000


class ClientContext(BaseModel):
    timezone: str | None = Field(default=None, max_length=64)
    # TODO: геолокація — додати location (lat, lon, accuracy), коли з'являться places


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    context: ClientContext | None = None


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


class PendingActionResponse(BaseModel):
    id: int
    action_type: str
    preview: dict
    status: Literal["pending", "confirmed", "rejected", "expired", "failed"]
    result: dict | None
    error: str | None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
