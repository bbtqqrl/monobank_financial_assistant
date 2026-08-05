from pydantic import BaseModel
from typing import Any

class ConnectMonobankRequest(BaseModel):
    token: str


class ConnectMonobankResponse(BaseModel):
    success: bool
    message: str

class MonoAccountSchema(BaseModel):
    id: str
    currency_code: int
    balance: int
    masked_pan: list[str]

class MonoJarSchema(BaseModel):
    id: str
    title: str
    balance: int
    goal: int | None = None


class MonoClientInfo(BaseModel):
    client_id: str
    name: str
    accounts: list[MonoAccountSchema]
    jars: list[MonoJarSchema]


class MonoWebhookPayload(BaseModel):
    type: str
    data: dict[str, Any]

