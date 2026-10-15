from datetime import date

from pydantic import BaseModel, Field

from app.schemas.transaction import CategoryBrief

# budgets.amount is a 32-bit Integer column.
MAX_BUDGET_AMOUNT = 2_147_483_647


class BudgetResponse(BaseModel):
    id: int
    category: CategoryBrief
    amount: int
    current_amount: int
    period_start: date


class CreateBudgetRequest(BaseModel):
    category_id: int
    amount: int = Field(gt=0, le=MAX_BUDGET_AMOUNT, description="In minor units (kopecks)")


class UpdateBudgetRequest(BaseModel):
    amount: int = Field(gt=0, le=MAX_BUDGET_AMOUNT, description="In minor units (kopecks)")
