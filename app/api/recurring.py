import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.currencies import alpha_code
from app.db.models.recurring_payment import RecurringPayment
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.recurring import (
    MarkRecurringRequest,
    RecurringCharge,
    RecurringPaymentDetail,
    RecurringPaymentsResponse,
    UpdateRecurringPaymentRequest,
)
from app.services.recurring_detection import SUBSCRIPTION
from app.services.recurring_service import RecurringService, payment_item, payments_summary

router = APIRouter(prefix="/recurring", tags=["Recurring payments"])


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
    return RecurringPaymentDetail(**payment_item(row, int(time.time())).model_dump(), charges=charges)


@router.get("", response_model=RecurringPaymentsResponse)
async def list_recurring(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = int(time.time())
    return payments_summary(await RecurringService(db).list(current_user.id, SUBSCRIPTION, now), now)


@router.post("", response_model=RecurringPaymentDetail)
async def mark_recurring(
    data: MarkRecurringRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    return await _detail(service, await service.mark(data.transaction_id, current_user.id, SUBSCRIPTION))


@router.get("/{payment_id}", response_model=RecurringPaymentDetail)
async def get_recurring(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    return await _detail(service, await service.get_subscription(payment_id, current_user.id))


@router.patch("/{payment_id}", response_model=RecurringPaymentDetail | None)
async def update_recurring(
    payment_id: int,
    data: UpdateRecurringPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    row = await service.update(payment_id, current_user.id, data.answer, data.name)
    return await _detail(service, row) if row.kind == SUBSCRIPTION else None
