from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.transaction import CategoryBrief

RecurringKind = Literal["subscription", "regular"]


class RecurringPaymentItem(BaseModel):
    id: int
    kind: RecurringKind
    name: str
    category: CategoryBrief | None
    mcc: int | None
    currency: str
    amount: int
    amount_uah: int
    monthly_amount_uah: int
    period_days: int
    first_charge_at: int
    last_charge_at: int
    next_charge_at: int
    charges_count: int
    state: Literal["active", "missing", "inactive"]
    confirmed: bool
    cancelled: bool


class RecurringPaymentsResponse(BaseModel):
    monthly_total_uah: int
    items: list[RecurringPaymentItem]


class RecurringCharge(BaseModel):
    id: int
    time: int
    description: str
    amount: int
    amount_uah: int | None
    currency: str


class RecurringPaymentDetail(RecurringPaymentItem):
    charges: list[RecurringCharge]


class UpdateRecurringPaymentRequest(BaseModel):
    answer: Literal["confirm", "decline", "cancel", "resume"] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)


class MarkRecurringRequest(BaseModel):
    transaction_id: int
