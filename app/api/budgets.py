from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.budget import Budget
from app.db.models.categories import Category
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.budget import BudgetRepository, current_period
from app.repositories.category import CategoryRepository
from app.schemas.budget import BudgetResponse, CreateBudgetRequest, UpdateBudgetRequest
from app.schemas.transaction import CategoryBrief

router = APIRouter(prefix="/budgets", tags=["Budgets"])


async def _to_responses(
    repo: BudgetRepository, user_id: int, rows: list[tuple[Budget, Category]],
) -> list[BudgetResponse]:
    period_start, from_ts, to_ts = current_period()
    spent = await repo.spent_by_category(user_id, [budget.category_id for budget, _ in rows], from_ts, to_ts)
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


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BudgetRepository(db)
    rows = await repo.list_for_user(current_user.id)
    return await _to_responses(repo, current_user.id, rows)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: CreateBudgetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await CategoryRepository(db).get_selectable_by_id(data.category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or not selectable")

    repo = BudgetRepository(db)
    try:
        budget = await repo.create(current_user.id, category.id, data.amount)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Budget for this category already exists")

    [response] = await _to_responses(repo, current_user.id, [(budget, category)])
    return response


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: int,
    data: UpdateBudgetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BudgetRepository(db)
    budget = await repo.get_by_id_for_user(budget_id, current_user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    repo.update_amount(budget, data.amount)
    await db.commit()

    category = await CategoryRepository(db).get_by_id(budget.category_id)
    [response] = await _to_responses(repo, current_user.id, [(budget, category)])
    return response


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BudgetRepository(db)
    budget = await repo.get_by_id_for_user(budget_id, current_user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    await repo.delete(budget)
    await db.commit()
