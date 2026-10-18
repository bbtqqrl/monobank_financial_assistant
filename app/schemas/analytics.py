from typing import Literal

from pydantic import BaseModel

Comparison = Literal["full_month", "same_day"]


class CategoryRef(BaseModel):
    id: int
    name: str
    slug: str


class DailyPoint(BaseModel):
    date: str
    amount: int


class CategoryShare(BaseModel):
    category_id: int
    name: str
    slug: str
    amount: int
    share: float


class OtherShare(BaseModel):
    amount: int
    share: float


class CategoryBreakdown(BaseModel):
    top: list[CategoryShare]
    other: OtherShare


class MerchantItem(BaseModel):
    merchant_key: str
    name: str
    purchase_count: int
    amount: int
    category: CategoryRef | None


class SummaryResponse(BaseModel):
    month: str
    total_spent: int
    previous_total: int
    change_pct: float | None
    comparison: Comparison
    daily_cumulative: list[DailyPoint]
    categories: CategoryBreakdown
    top_merchants: list[MerchantItem]


class CategoryItem(BaseModel):
    category_id: int
    name: str
    slug: str
    amount: int
    share: float
    transaction_count: int
    previous_amount: int
    change_pct: float | None


class CategoriesResponse(BaseModel):
    month: str
    transaction_count: int
    total_spent: int
    comparison: Comparison
    items: list[CategoryItem]


class MerchantsResponse(BaseModel):
    month: str
    total: int
    limit: int
    offset: int
    items: list[MerchantItem]


class MonthTotal(BaseModel):
    month: str
    total: int
    has_data: bool
    complete: bool


class CategoryChange(BaseModel):
    category_id: int
    name: str
    slug: str
    current: int
    previous: int
    change_pct: float | None


class InsightAction(BaseModel):
    type: Literal["open_transactions"]
    category_id: int
    month: str


class Insight(BaseModel):
    type: Literal["category_growth_streak"]
    category_id: int
    category_name: str
    streak_months: int
    current: int
    baseline: int
    diff: int
    text: str
    action: InsightAction


class TrendsResponse(BaseModel):
    month: str
    monthly: list[MonthTotal]
    average: int | None
    selected_vs_average: Literal["below", "above", "equal"] | None
    comparison: Comparison
    changes_vs_previous: list[CategoryChange]
    insights: list[Insight]
