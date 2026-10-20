from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.budget import BudgetResponse, CreateBudgetRequest, UpdateBudgetRequest
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BudgetService(db, current_user.id).list_all()


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: CreateBudgetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BudgetService(db, current_user.id).create(data.category_id, data.amount)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: int,
    data: UpdateBudgetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BudgetService(db, current_user.id).update_amount(budget_id, data.amount)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await BudgetService(db, current_user.id).delete(budget_id)
