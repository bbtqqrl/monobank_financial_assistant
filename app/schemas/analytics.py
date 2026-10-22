from datetime import date
from typing import Literal

from pydantic import BaseModel

ComparePreset = Literal["previous_period", "previous_month", "year_ago", "last_3_months", "last_6_months", "last_year"]


class CategoryRef(BaseModel):
    id: int
    name: str
    slug: str


class PeriodInfo(BaseModel):
    start: date
    end: date
    days: int


class ComparisonInfo(BaseModel):
    type: ComparePreset | Literal["custom"]
    start: date
    end: date
    days: int
    scaled: bool
    complete: bool
    total: int
    expected: int


class DailyPoint(BaseModel):
    date: date
    amount: int


class SpendingResponse(BaseModel):
    period: PeriodInfo
    total: int
    comparison: ComparisonInfo
    change_pct: float | None
    daily: list[DailyPoint]


class CategoryItem(BaseModel):
    category_id: int
    name: str
    slug: str
    amount: int
    share: float
    transaction_count: int
    expected: int
    change_pct: float | None


class OtherShare(BaseModel):
    amount: int
    share: float


class CategoriesResponse(BaseModel):
    period: PeriodInfo
    total: int
    transaction_count: int
    comparison: ComparisonInfo
    items: list[CategoryItem]
    other: OtherShare | None


class MerchantItem(BaseModel):
    merchant_key: str
    name: str
    purchase_count: int
    amount: int
    category: CategoryRef | None
    logo_url: str | None = None


class MerchantsResponse(BaseModel):
    period: PeriodInfo
    total: int
    limit: int
    offset: int
    items: list[MerchantItem]


class CategoryChange(BaseModel):
    category_id: int
    name: str
    slug: str
    amount: int
    expected: int
    change_pct: float | None


class ChangesResponse(BaseModel):
    period: PeriodInfo
    comparison: ComparisonInfo
    items: list[CategoryChange]


class MonthTotal(BaseModel):
    month: str
    total: int
    has_data: bool
    complete: bool


class MonthlyResponse(BaseModel):
    month: str
    months: list[MonthTotal]
    average: int | None
    selected_vs_average: Literal["below", "above", "equal"] | None


class InsightAction(BaseModel):
    type: Literal["open_transactions"]
    category_id: int
    month: str


class Insight(BaseModel):
    type: Literal["category_growth_streak"]
    category_id: int
    category_name: str
    title: str
    text: str
    streak_months: int
    current: int
    baseline: int
    diff: int
    action: InsightAction


class InsightsResponse(BaseModel):
    month: str
    items: list[Insight]


class CategoryMonth(BaseModel):
    month: str
    amount: int


class CategoryHistoryItem(BaseModel):
    category_id: int
    name: str
    slug: str
    months: list[CategoryMonth]
    median: int
    average: int
    active_months: int


class CategoryHistoryResponse(BaseModel):
    month: str
    months: list[MonthTotal]
    items: list[CategoryHistoryItem]


class RecurringItem(BaseModel):
    merchant_key: str
    name: str
    category: CategoryRef
    months_seen: int
    payment_count: int
    typical_amount: int
    monthly_amount: int
    stable_amount: bool
    last_date: date


class RecurringResponse(BaseModel):
    months: list[str]
    items: list[RecurringItem]


class CurrencyItem(BaseModel):
    currency: str
    transaction_count: int
    amount: int
    amount_uah: int
    share: float


class CurrenciesResponse(BaseModel):
    period: PeriodInfo
    total_uah: int
    items: list[CurrencyItem]
