from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.budget import Budget
from app.db.models.categories import Category
from app.repositories.budget import BudgetRepository, current_period
from app.repositories.category import CategoryRepository
from app.schemas.budget import BudgetResponse
from app.schemas.transaction import CategoryBrief
from app.services.errors import ConflictError, InvalidRequestError, NotFoundError


class BudgetService:

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.budgets = BudgetRepository(db)
        self.categories = CategoryRepository(db)

    async def list_all(self) -> list[BudgetResponse]:
        return await self._to_responses(await self.budgets.list_for_user(self.user_id))

    async def create(self, category_id: int, amount: int) -> BudgetResponse:
        category = await self.categories.get_selectable_by_id(category_id)
        if category is None:
            raise InvalidRequestError("Category not found or not selectable")
        if category.kind != "expense":
            raise InvalidRequestError("Budgets can only be set on expense categories")

        try:
            budget = await self.budgets.create(self.user_id, category.id, amount)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("Budget for this category already exists")

        [response] = await self._to_responses([(budget, category)])
        return response

    async def update_amount(self, budget_id: int, amount: int) -> BudgetResponse:
        budget = await self._get(budget_id)
        self.budgets.update_amount(budget, amount)
        await self.db.commit()

        category = await self.categories.get_by_id(budget.category_id)
        [response] = await self._to_responses([(budget, category)])
        return response

    async def delete(self, budget_id: int) -> None:
        budget = await self._get(budget_id)
        await self.budgets.delete(budget)
        await self.db.commit()

    async def _get(self, budget_id: int) -> Budget:
        budget = await self.budgets.get_by_id_for_user(budget_id, self.user_id)
        if budget is None:
            raise NotFoundError("Budget not found")
        return budget

    async def _to_responses(self, rows: list[tuple[Budget, Category]]) -> list[BudgetResponse]:
        period_start, from_ts, to_ts = current_period()
        spent = await self.budgets.spent_by_category(
            self.user_id, [budget.category_id for budget, _ in rows], from_ts, to_ts,
        )
        return [
            BudgetResponse(
                id=budget.id,
                category=CategoryBrief.model_validate(category),
                amount=budget.amount,
                current_amount=spent.get(budget.category_id, 0),
                period_start=period_start,
            )
            for budget, category in rows
        ]
