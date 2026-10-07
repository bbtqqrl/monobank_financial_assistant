from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.budget import Budget
from app.db.models.categories import Category
from app.db.models.transaction import TransactionRaw

# Budgets follow the user's calendar month, not UTC's - otherwise a purchase
# at 01:30 Kyiv time on the 1st would land in the previous month.
BUDGET_TZ = ZoneInfo("Europe/Kyiv")


def current_period() -> tuple[date, int, int]:
    """(first day of the current month, its start and the next month's start
    as unix timestamps) in BUDGET_TZ."""
    now = datetime.now(BUDGET_TZ)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.date(), int(start.timestamp()), int(end.timestamp())


class BudgetRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, category_id: int, amount: int) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
        )
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def get_by_id_for_user(self, budget_id: int, user_id: int) -> Optional[Budget]:
        result = await self.db.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[tuple[Budget, Category]]:
        result = await self.db.execute(
            select(Budget, Category)
            .join(Category, Category.id == Budget.category_id)
            .where(Budget.user_id == user_id)
        )
        return list(result.all())

    async def spent_by_category(
        self, user_id: int, category_ids: list[int], from_ts: int, to_ts: int,
    ) -> dict[int, int]:
        """Net spending (as positive kopecks) per category within
        [from_ts, to_ts). Refunds - positive amounts in an expense category -
        offset it; a month with more refunds than spending reports 0."""
        if not category_ids:
            return {}

        result = await self.db.execute(
            select(TransactionRaw.category_id, func.sum(-TransactionRaw.amount))
            .where(
                TransactionRaw.user_id == user_id,
                TransactionRaw.category_id.in_(category_ids),
                TransactionRaw.time >= from_ts,
                TransactionRaw.time < to_ts,
            )
            .group_by(TransactionRaw.category_id)
        )
        return {category_id: max(int(total), 0) for category_id, total in result.all()}

    @staticmethod
    def update_amount(budget: Budget, amount: int) -> None:
        budget.amount = amount

    async def delete(self, budget: Budget) -> None:
        await self.db.delete(budget)
