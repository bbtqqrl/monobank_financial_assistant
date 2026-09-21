from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import (
    CategoryBrief,
    TransactionDetail,
    TransactionListItem,
    TransactionListResponse,
    UpdateTransactionCategoryRequest,
)
from app.services.categorization_service import CategorizationService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _category_brief(category) -> CategoryBrief | None:
    return CategoryBrief.model_validate(category) if category is not None else None


def _to_list_item(transaction, category, source) -> TransactionListItem:
    return TransactionListItem(
        id=transaction.id,
        time=transaction.time,
        description=transaction.description,
        amount=transaction.amount,
        operation_amount=transaction.operation_amount,
        currency_code=transaction.currency_code,
        mcc=transaction.mcc,
        account_id=transaction.account_id,
        jar_id=transaction.jar_id,
        category=_category_brief(category),
        category_source=source,
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = None,
    category_id: int | None = None,
    type: Literal["expense", "income"] | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
):
    ts_from = int(datetime.combine(date_from, time.min, tzinfo=timezone.utc).timestamp()) if date_from else None
    ts_to = int(datetime.combine(date_to, time.max, tzinfo=timezone.utc).timestamp()) if date_to else None

    transactions = TransactionRepository(db)
    rows, total = await transactions.list_for_user(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        type_=type,
        date_from=ts_from,
        date_to=ts_to,
        search=search,
        page=page,
        limit=limit,
    )

    return TransactionListResponse(
        items=[_to_list_item(t, c, s) for t, c, s in rows],
        page=page,
        limit=limit,
        total=total,
    )


@router.get("/{transaction_id}", response_model=TransactionDetail)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = TransactionRepository(db)
    row = await transactions.get_detail_for_user(transaction_id, current_user.id)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    transaction, category, source = row

    return TransactionDetail(
        **_to_list_item(transaction, category, source).model_dump(),
        balance=transaction.balance,
        comment=transaction.comment,
        counter_name=transaction.counter_name,
        counter_edrpou=transaction.counter_edrpou,
        counter_iban=transaction.counter_iban,
    )


@router.patch("/{transaction_id}/category", response_model=TransactionDetail)
async def update_transaction_category(
    transaction_id: int,
    data: UpdateTransactionCategoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CategorizationService(db)

    try:
        transaction = await service.apply_user_category(
            transaction_id=transaction_id,
            user_id=current_user.id,
            category_id=data.category_id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")

    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    transactions = TransactionRepository(db)
    row = await transactions.get_detail_for_user(transaction_id, current_user.id)
    transaction, category, source = row

    return TransactionDetail(
        **_to_list_item(transaction, category, source).model_dump(),
        balance=transaction.balance,
        comment=transaction.comment,
        counter_name=transaction.counter_name,
        counter_edrpou=transaction.counter_edrpou,
        counter_iban=transaction.counter_iban,
    )
