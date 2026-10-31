from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pending_action import PendingAction
from app.repositories.budget import BudgetRepository
from app.repositories.category import CategoryRepository
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.repositories.message import MessageRepository
from app.repositories.pending_action import PendingActionRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.assistant import PendingActionResponse
from app.schemas.budget import MAX_BUDGET_AMOUNT
from app.schemas.transaction import MAX_ABS_AMOUNT, MAX_TIME
from app.services.categorization_service import (
    CategorizationService,
    CategoryDirectionError,
    check_category_fits_amount,
)
from app.services.errors import ConflictError, InvalidRequestError, NotFoundError, ServiceError
from app.services.recurring_service import RecurringService
from app.services.transaction_service import TransactionService

ACTION_TTL = timedelta(hours=24)
ACTION_UPDATE_PREFIX = "<action_update>"
MAX_BUDGET_ITEMS = 30
MAX_RECATEGORIZE_ITEMS = 50


class BudgetChange(BaseModel):
    category_id: int
    amount: int | None = Field(default=None, gt=0, le=MAX_BUDGET_AMOUNT)


class BudgetsPayload(BaseModel):
    items: list[BudgetChange] = Field(min_length=1, max_length=MAX_BUDGET_ITEMS)


class TransactionCreatePayload(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: int = Field(ge=-MAX_ABS_AMOUNT, le=MAX_ABS_AMOUNT)
    category_id: int
    time: int | None = Field(default=None, ge=0, le=MAX_TIME)
    comment: str | None = Field(default=None, max_length=500)


class CategoryChange(BaseModel):
    transaction_id: int
    category_id: int


class RecategorizePayload(BaseModel):
    items: list[CategoryChange] = Field(min_length=1, max_length=MAX_RECATEGORIZE_ITEMS)


class TransactionEditPayload(BaseModel):
    transaction_id: int
    description: str | None = Field(default=None, min_length=1, max_length=500)
    amount: int | None = Field(default=None, ge=-MAX_ABS_AMOUNT, le=MAX_ABS_AMOUNT)
    category_id: int | None = None
    time: int | None = Field(default=None, ge=0, le=MAX_TIME)
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def has_changes(self):
        if all(getattr(self, name) is None for name in ("description", "amount", "category_id", "time", "comment")):
            raise ValueError("Nothing to change")
        return self


class TransactionDeletePayload(BaseModel):
    transaction_id: int


class RecurringMarkPayload(BaseModel):
    transaction_id: int
    kind: Literal["subscription", "regular"]


@dataclass(frozen=True)
class ActionType:
    name: str
    title: str
    payload: type[BaseModel]
    preview: Callable[[AsyncSession, int, BaseModel, ZoneInfo], Awaitable[dict]]
    execute: Callable[[AsyncSession, int, BaseModel, ZoneInfo], Awaitable[dict]]


def _local_time(timestamp: int, zone: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp, zone).isoformat(timespec="minutes")


async def _category(db: AsyncSession, category_id: int, amount: int):
    category = await CategoryRepository(db).get_selectable_by_id(category_id)
    if category is None:
        raise InvalidRequestError(f"Category {category_id} not found")
    try:
        check_category_fits_amount(category.kind, amount)
    except CategoryDirectionError as e:
        raise InvalidRequestError(str(e))
    return category


async def _transaction(db: AsyncSession, user_id: int, transaction_id: int, manual: bool = False):
    row = await TransactionRepository(db).get_detail_for_user(transaction_id, user_id)
    if row is None:
        raise InvalidRequestError(f"Transaction {transaction_id} not found")
    transaction, category, _ = row
    if manual and transaction.source != "manual":
        raise InvalidRequestError("Only manually added transactions can be edited or deleted; Monobank ones only get a new category")
    return transaction, category


def _brief(transaction, category, zone: ZoneInfo) -> dict:
    return {
        "transaction_id": transaction.id,
        "description": transaction.description,
        "amount": transaction.amount,
        "time": _local_time(transaction.time, zone),
        "category_name": category.name if category else None,
    }


async def preview_budgets(db: AsyncSession, user_id: int, payload: BudgetsPayload, zone: ZoneInfo) -> dict:
    category_ids = [item.category_id for item in payload.items]
    if len(set(category_ids)) != len(category_ids):
        raise InvalidRequestError("Each category can appear only once")
    existing = {budget.category_id: budget for budget, _ in await BudgetRepository(db).list_for_user(user_id)}
    categories = CategoryRepository(db)

    items = []
    for item in payload.items:
        category = await categories.get_selectable_by_id(item.category_id)
        if category is None:
            raise InvalidRequestError(f"Category {item.category_id} not found")
        if category.kind != "expense":
            raise InvalidRequestError(f"Budgets can only be set on expense categories, not on {category.name}")
        budget = existing.get(category.id)
        if item.amount is None and budget is None:
            raise InvalidRequestError(f"There is no budget for {category.name} to delete")
        items.append({
            "category_id": category.id,
            "category_name": category.name,
            "change": "delete" if item.amount is None else "update" if budget else "create",
            "old_amount": budget.amount if budget else None,
            "new_amount": item.amount,
        })
    return {"items": items}


async def execute_budgets(db: AsyncSession, user_id: int, payload: BudgetsPayload, zone: ZoneInfo) -> dict:
    preview = await preview_budgets(db, user_id, payload, zone)
    budgets = BudgetRepository(db)
    existing = {budget.category_id: budget for budget, _ in await budgets.list_for_user(user_id)}
    for item in payload.items:
        budget = existing.get(item.category_id)
        if item.amount is None:
            await budgets.delete(budget)
        elif budget is not None:
            budgets.update_amount(budget, item.amount)
        else:
            await budgets.create(user_id, item.category_id, item.amount)
    return preview


async def preview_transaction_create(
    db: AsyncSession, user_id: int, payload: TransactionCreatePayload, zone: ZoneInfo,
) -> dict:
    if payload.amount == 0:
        raise InvalidRequestError("Amount cannot be zero")
    category = await _category(db, payload.category_id, payload.amount)
    time = payload.time if payload.time is not None else int(datetime.now(timezone.utc).timestamp())
    return {
        "description": payload.description,
        "amount": payload.amount,
        "category_name": category.name,
        "time": _local_time(time, zone),
        "comment": payload.comment,
    }


async def execute_transaction_create(
    db: AsyncSession, user_id: int, payload: TransactionCreatePayload, zone: ZoneInfo,
) -> dict:
    preview = await preview_transaction_create(db, user_id, payload, zone)
    transaction = await TransactionService(db, user_id).create_manual(
        description=payload.description,
        amount=payload.amount,
        category_id=payload.category_id,
        time=payload.time,
        comment=payload.comment,
    )
    return {**preview, "transaction_id": transaction.id}


async def preview_recategorize(db: AsyncSession, user_id: int, payload: RecategorizePayload, zone: ZoneInfo) -> dict:
    transaction_ids = [item.transaction_id for item in payload.items]
    if len(set(transaction_ids)) != len(transaction_ids):
        raise InvalidRequestError("Each transaction can appear only once")
    items = []
    for item in payload.items:
        transaction, old_category = await _transaction(db, user_id, item.transaction_id)
        new_category = await _category(db, item.category_id, transaction.amount)
        items.append({**_brief(transaction, old_category, zone), "new_category_name": new_category.name})
    return {"items": items}


async def execute_recategorize(db: AsyncSession, user_id: int, payload: RecategorizePayload, zone: ZoneInfo) -> dict:
    preview = await preview_recategorize(db, user_id, payload, zone)
    service = CategorizationService(db)
    for item in payload.items:
        await service.apply_user_category(item.transaction_id, user_id, item.category_id)
    return preview


async def preview_transaction_edit(
    db: AsyncSession, user_id: int, payload: TransactionEditPayload, zone: ZoneInfo,
) -> dict:
    transaction, category = await _transaction(db, user_id, payload.transaction_id, manual=True)
    amount = payload.amount if payload.amount is not None else transaction.amount
    if amount == 0:
        raise InvalidRequestError("Amount cannot be zero")
    new_category = await _category(db, payload.category_id or transaction.category_id, amount)
    before = {**_brief(transaction, category, zone), "comment": transaction.comment}
    after = {
        **before,
        "description": payload.description or transaction.description,
        "amount": amount,
        "time": _local_time(payload.time if payload.time is not None else transaction.time, zone),
        "category_name": new_category.name,
        "comment": payload.comment if payload.comment is not None else transaction.comment,
    }
    return {"before": before, "after": after}


async def execute_transaction_edit(
    db: AsyncSession, user_id: int, payload: TransactionEditPayload, zone: ZoneInfo,
) -> dict:
    preview = await preview_transaction_edit(db, user_id, payload, zone)
    await CategorizationService(db).edit_manual_transaction(
        transaction_id=payload.transaction_id,
        user_id=user_id,
        description=payload.description,
        amount=payload.amount,
        category_id=payload.category_id,
        comment=payload.comment,
        time=payload.time,
    )
    return preview


async def preview_transaction_delete(
    db: AsyncSession, user_id: int, payload: TransactionDeletePayload, zone: ZoneInfo,
) -> dict:
    transaction, category = await _transaction(db, user_id, payload.transaction_id, manual=True)
    return _brief(transaction, category, zone)


async def execute_transaction_delete(
    db: AsyncSession, user_id: int, payload: TransactionDeletePayload, zone: ZoneInfo,
) -> dict:
    preview = await preview_transaction_delete(db, user_id, payload, zone)
    await CategorizationService(db).delete_manual_transaction(payload.transaction_id, user_id)
    return preview


async def preview_recurring_mark(
    db: AsyncSession, user_id: int, payload: RecurringMarkPayload, zone: ZoneInfo,
) -> dict:
    transaction, category = await _transaction(db, user_id, payload.transaction_id)
    if transaction.amount >= 0:
        raise InvalidRequestError("Only expenses can be marked as recurring")
    return {**_brief(transaction, category, zone), "kind": payload.kind}


async def execute_recurring_mark(
    db: AsyncSession, user_id: int, payload: RecurringMarkPayload, zone: ZoneInfo,
) -> dict:
    preview = await preview_recurring_mark(db, user_id, payload, zone)
    row = await RecurringService(db).mark(payload.transaction_id, user_id, payload.kind)
    return {**preview, "recurring_id": row.id, "name": row.name, "charges_count": row.charges_count}


ACTION_TYPES = {
    action.name: action
    for action in (
        ActionType("budgets", "Бюджети", BudgetsPayload, preview_budgets, execute_budgets),
        ActionType(
            "transaction_create", "Нова транзакція", TransactionCreatePayload,
            preview_transaction_create, execute_transaction_create,
        ),
        ActionType(
            "transaction_category", "Категорії транзакцій", RecategorizePayload,
            preview_recategorize, execute_recategorize,
        ),
        ActionType(
            "transaction_edit", "Зміна транзакції", TransactionEditPayload,
            preview_transaction_edit, execute_transaction_edit,
        ),
        ActionType(
            "transaction_delete", "Видалення транзакції", TransactionDeletePayload,
            preview_transaction_delete, execute_transaction_delete,
        ),
        ActionType(
            "recurring_mark", "Регулярний платіж", RecurringMarkPayload,
            preview_recurring_mark, execute_recurring_mark,
        ),
    )
}


class ActionService:

    def __init__(self, db: AsyncSession, user_id: int, timezone_name: str = DEFAULT_TIMEZONE):
        self.db = db
        self.user_id = user_id
        self.zone = ZoneInfo(timezone_name)
        self.actions = PendingActionRepository(db)
        self.messages = MessageRepository(db)

    async def propose(
        self, conversation_id: int, tool_use_id: str | None, action_type: str, payload: BaseModel,
    ) -> PendingAction:
        preview = await ACTION_TYPES[action_type].preview(self.db, self.user_id, payload, self.zone)
        action = await self.actions.create(
            self.user_id, conversation_id, tool_use_id, action_type,
            payload.model_dump(mode="json"), preview, datetime.now(timezone.utc) + ACTION_TTL,
        )
        await self.db.commit()
        return action

    async def list_for_conversation(self, conversation_id: int) -> list[PendingActionResponse]:
        actions = await self.actions.list_for_conversation(conversation_id)
        return [PendingActionResponse.model_validate(action) for action in actions]

    async def confirm(self, action_id: int, report: bool = True) -> PendingActionResponse:
        action = await self._get_pending(action_id)
        action_type = ACTION_TYPES[action.action_type]
        payload = action_type.payload.model_validate(action.payload)
        try:
            result = await action_type.execute(self.db, self.user_id, payload, self.zone)
        except ServiceError as e:
            await self.db.rollback()
            action = await self.get(action_id)
            self.actions.resolve(action, "failed", error=e.message)
            if report:
                await self._report(action, f"не вдалося виконати: {e.message}")
        else:
            self.actions.resolve(action, "confirmed", result=result)
            if report:
                await self._report(action, "користувач підтвердив, зміни застосовано")
        await self.db.commit()
        await self.db.refresh(action)
        return PendingActionResponse.model_validate(action)

    async def reject(self, action_id: int) -> PendingActionResponse:
        action = await self._get_pending(action_id)
        self.actions.resolve(action, "rejected")
        await self._report(action, "користувач відхилив, нічого не змінено")
        await self.db.commit()
        await self.db.refresh(action)
        return PendingActionResponse.model_validate(action)

    async def get(self, action_id: int) -> PendingAction:
        action = await self.actions.get_for_user(action_id, self.user_id)
        if action is None:
            raise NotFoundError("Action not found")
        return action

    async def _get_pending(self, action_id: int) -> PendingAction:
        action = await self.get(action_id)
        if action.status == "pending" and action.expires_at <= datetime.now(timezone.utc):
            self.actions.resolve(action, "expired")
            await self._report(action, "минув час на підтвердження, нічого не змінено")
            await self.db.commit()
        if action.status != "pending":
            raise ConflictError(f"Action is already {action.status}")
        return action

    async def _report(self, action: PendingAction, outcome: str) -> None:
        title = ACTION_TYPES[action.action_type].title
        await self.messages.add(action.conversation_id, "user", [
            {"type": "text", "text": f"{ACTION_UPDATE_PREFIX}Дія #{action.id} ({title}): {outcome}.</action_update>"},
        ])
