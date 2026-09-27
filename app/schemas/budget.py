from datetime import date

from pydantic import BaseModel, Field

from app.schemas.transaction import CategoryBrief


class BudgetResponse(BaseModel):
    id: int
    category: CategoryBrief
    amount: int
    current_amount: int
    period_start: date


class CreateBudgetRequest(BaseModel):
    category_id: int
    amount: int = Field(gt=0, description="In minor units (kopecks)")


class UpdateBudgetRequest(BaseModel):
    amount: int = Field(gt=0, description="In minor units (kopecks)")
