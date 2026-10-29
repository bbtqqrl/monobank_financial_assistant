import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.currencies import alpha_code
from app.db.models.recurring_payment import RecurringPayment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.recurring import (
    RecurringCharge,
    RecurringKind,
    RecurringPaymentDetail,
    RecurringPaymentItem,
    RecurringPaymentsResponse,
    UpdateRecurringPaymentRequest,
)
from app.schemas.transaction import CategoryBrief
from app.services.recurring_detection import DAY_SECONDS, monthly_amount
from app.services.recurring_service import RecurringService, state

router = APIRouter(prefix="/recurring", tags=["Recurring payments"])


def _item(row: RecurringPayment, now: int) -> dict:
    return dict(
        id=row.id,
        kind=row.kind,
        name=row.name,
        category=CategoryBrief.model_validate(row.category) if row.category is not None else None,
        mcc=row.mcc,
        currency=alpha_code(row.currency_code),
        amount=row.amount,
        amount_uah=row.amount_uah,
        monthly_amount_uah=monthly_amount(row.amount_uah, row.period_days),
        period_days=row.period_days,
        first_charge_at=row.first_charge_at,
        last_charge_at=row.last_charge_at,
        next_charge_at=row.last_charge_at + row.period_days * DAY_SECONDS,
        charges_count=row.charges_count,
        state=state(row, now),
        confirmed=row.user_kind is not None,
        cancelled=row.cancelled_at is not None,
    )


async def _detail(service: RecurringService, row: RecurringPayment) -> RecurringPaymentDetail:
    charges = [
        RecurringCharge(
            id=transaction.id,
            time=transaction.time,
            description=transaction.description,
            amount=abs(transaction.operation_amount if transaction.operation_amount is not None else transaction.amount),
            amount_uah=-transaction.amount_uah if transaction.amount_uah is not None else None,
            currency=alpha_code(transaction.currency_code),
        )
        for transaction in await service.transactions(row.id)
    ]
    return RecurringPaymentDetail(**_item(row, int(time.time())), charges=charges)


@router.get("", response_model=RecurringPaymentsResponse)
async def list_recurring(
    kind: RecurringKind | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = int(time.time())
    items = [RecurringPaymentItem(**_item(row, now)) for row in await RecurringService(db).list(current_user.id, kind)]
    total = sum(item.monthly_amount_uah for item in items if not item.cancelled and item.state != "inactive")
    items.sort(key=lambda item: (item.state == "inactive", item.cancelled, -item.monthly_amount_uah))
    return RecurringPaymentsResponse(monthly_total_uah=total, items=items)


# TODO: ручка, щоб юзер сам позначив транзакцію як підписку, не чекаючи другого списання
@router.get("/{payment_id}", response_model=RecurringPaymentDetail)
async def get_recurring(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    return await _detail(service, await service.get(payment_id, current_user.id))


@router.patch("/{payment_id}", response_model=RecurringPaymentDetail | None)
async def update_recurring(
    payment_id: int,
    data: UpdateRecurringPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    row = await service.update(payment_id, current_user.id, data.answer, data.kind, data.name)
    return await _detail(service, row) if row.kind is not None else None
