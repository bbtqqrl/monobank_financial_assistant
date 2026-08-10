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


class MonoTransactionSchema(BaseModel):
    id: str
    time: int
    description: str
    mcc: int | None = None
    originalMcc: int | None = None
    hold: bool | None = None
    amount: int
    operationAmount: int | None = None
    currencyCode: int
    commissionRate: int | None = None
    cashbackAmount: int | None = None
    balance: int | None = None
    comment: str | None = None
    receiptId: str | None = None
    invoiceId: str | None = None
    counterEdrpou: str | None = None
    counterIban: str | None = None
    counterName: str | None = None


class MonoWebhookData(BaseModel):
    account: str
    statementItem: MonoTransactionSchema


class MonoWebhookPayload(BaseModel):
    type: str
    data: MonoWebhookData