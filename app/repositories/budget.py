from datetime import date, timezone, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.budget import Budget
from app.db.models.categories import Category


def _current_period_start() -> date:
    return datetime.now(timezone.utc).date().replace(day=1)


class BudgetRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, category_id: int, amount: int) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period_start=_current_period_start(),
        )
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def get_by_id_for_user(self, budget_id: int, user_id: int) -> Optional[Budget]:
        result = await self.db.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        budget = result.scalar_one_or_none()
        if budget is not None:
            await self._reset_if_new_period(budget)
        return budget

    async def get_by_category_for_user(self, user_id: int, category_id: int) -> Optional[Budget]:
        result = await self.db.execute(
            select(Budget).where(Budget.user_id == user_id, Budget.category_id == category_id)
        )
        budget = result.scalar_one_or_none()
        if budget is not None:
            await self._reset_if_new_period(budget)
        return budget

    async def list_for_user(self, user_id: int) -> list[tuple[Budget, Category]]:
        result = await self.db.execute(
            select(Budget, Category)
            .join(Category, Category.id == Budget.category_id)
            .where(Budget.user_id == user_id)
        )
        rows = list(result.all())
        for budget, _ in rows:
            await self._reset_if_new_period(budget)
        return rows

    async def _reset_if_new_period(self, budget: Budget) -> None:
        """A budget's `current_amount` covers one calendar month. Rather than
        run a scheduled job to zero every budget on the 1st, we lazily catch
        up whenever a budget is next read or written: if it's still carrying
        a past month's period, reset it before it's used."""
        current_period = _current_period_start()
        if budget.period_start == current_period:
            return
        budget.current_amount = 0
        budget.period_start = current_period
        await self.db.commit()

    @staticmethod
    def update_amount(budget: Budget, amount: int) -> None:
        budget.amount = amount

    @staticmethod
    def adjust_current_amount(budget: Budget, delta: int) -> None:
        budget.current_amount += delta

    async def delete(self, budget: Budget) -> None:
        await self.db.delete(budget)
