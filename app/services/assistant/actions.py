from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pending_action import PendingAction
from app.repositories.budget import BudgetRepository
from app.repositories.category import CategoryRepository
from app.repositories.message import MessageRepository
from app.repositories.pending_action import PendingActionRepository
from app.schemas.assistant import PendingActionResponse
from app.schemas.budget import MAX_BUDGET_AMOUNT
from app.services.errors import ConflictError, InvalidRequestError, NotFoundError, ServiceError

ACTION_TTL = timedelta(hours=24)
ACTION_UPDATE_PREFIX = "<action_update>"
MAX_BUDGET_ITEMS = 30


class BudgetChange(BaseModel):
    category_id: int
    amount: int | None = Field(default=None, gt=0, le=MAX_BUDGET_AMOUNT)


class BudgetsPayload(BaseModel):
    items: list[BudgetChange] = Field(min_length=1, max_length=MAX_BUDGET_ITEMS)


@dataclass(frozen=True)
class ActionType:
    name: str
    title: str
    payload: type[BaseModel]
    preview: Callable[[AsyncSession, int, BaseModel], Awaitable[dict]]
    execute: Callable[[AsyncSession, int, BaseModel], Awaitable[dict]]


async def preview_budgets(db: AsyncSession, user_id: int, payload: BudgetsPayload) -> dict:
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


async def execute_budgets(db: AsyncSession, user_id: int, payload: BudgetsPayload) -> dict:
    preview = await preview_budgets(db, user_id, payload)
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


ACTION_TYPES = {
    action.name: action
    for action in (
        ActionType("budgets", "Бюджети", BudgetsPayload, preview_budgets, execute_budgets),
    )
}


class ActionService:

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.actions = PendingActionRepository(db)
        self.messages = MessageRepository(db)

    async def propose(
        self, conversation_id: int, tool_use_id: str | None, action_type: str, payload: BaseModel,
    ) -> PendingAction:
        preview = await ACTION_TYPES[action_type].preview(self.db, self.user_id, payload)
        action = await self.actions.create(
            self.user_id, conversation_id, tool_use_id, action_type,
            payload.model_dump(mode="json"), preview, datetime.now(timezone.utc) + ACTION_TTL,
        )
        await self.db.commit()
        return action

    async def list_for_conversation(self, conversation_id: int) -> list[PendingActionResponse]:
        actions = await self.actions.list_for_conversation(conversation_id)
        return [PendingActionResponse.model_validate(action) for action in actions]

    async def confirm(self, action_id: int) -> PendingActionResponse:
        action = await self._get_pending(action_id)
        action_type = ACTION_TYPES[action.action_type]
        try:
            result = await action_type.execute(self.db, self.user_id, action_type.payload.model_validate(action.payload))
        except ServiceError as e:
            await self.db.rollback()
            action = await self.get(action_id)
            self.actions.resolve(action, "failed", error=e.message)
            await self._report(action, f"не вдалося виконати: {e.message}")
        else:
            self.actions.resolve(action, "confirmed", result=result)
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
