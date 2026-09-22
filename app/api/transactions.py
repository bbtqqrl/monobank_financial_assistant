from datetime import date, datetime, time, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.account import AccountRepository
from app.repositories.category import CategoryRepository
from app.repositories.jar import JarRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import (
    CategoryBrief,
    CreateTransactionRequest,
    TransactionDetail,
    TransactionListItem,
    TransactionListResponse,
    UpdateTransactionCategoryRequest,
)
from app.services.categorization_service import CategorizationService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def _category_brief(category) -> CategoryBrief | None:
    return CategoryBrief.model_validate(category) if category is not None else None


def _to_list_item(transaction, category, source) -> TransactionListItem:
    return TransactionListItem(
        id=transaction.id,
        source=transaction.source,
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
    type: Literal["expense", "income", "transfer"] | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
):
    ts_from = int(datetime.combine(date_from, time.min, tzinfo=KYIV_TZ).timestamp()) if date_from else None
    ts_to = int(datetime.combine(date_to, time.max, tzinfo=KYIV_TZ).timestamp()) if date_to else None

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


@router.post("", response_model=TransactionDetail, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: CreateTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.account_id is not None and data.jar_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A transaction can belong to an account or a jar, not both",
        )

    if data.account_id is not None:
        account = await AccountRepository(db).get_by_id_for_user(data.account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if data.jar_id is not None:
        jar = await JarRepository(db).get_by_id_for_user(data.jar_id, current_user.id)
        if jar is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jar not found")

    if data.category_id is not None:
        category = await CategoryRepository(db).get_selectable_by_id(data.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or not selectable")

    transactions = TransactionRepository(db)
    transaction = await transactions.create_manual(
        user_id=current_user.id,
        account_id=data.account_id,
        jar_id=data.jar_id,
        description=data.description,
        amount=data.amount,
        currency_code=data.currency_code,
        time=data.time if data.time is not None else int(datetime.now(timezone.utc).timestamp()),
        comment=data.comment,
    )
    await db.commit()

    if data.category_id is not None:
        service = CategorizationService(db)
        await service.apply_user_category(
            transaction_id=transaction.id,
            user_id=current_user.id,
            category_id=data.category_id,
        )

    row = await transactions.get_detail_for_user(transaction.id, current_user.id)
    transaction, category, source = row

    return TransactionDetail(
        **_to_list_item(transaction, category, source).model_dump(),
        balance=transaction.balance,
        comment=transaction.comment,
        counter_name=transaction.counter_name,
        counter_edrpou=transaction.counter_edrpou,
        counter_iban=transaction.counter_iban,
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
