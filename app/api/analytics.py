from dataclasses import dataclass
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.schemas.analytics import (
    CategoriesResponse,
    ChangesResponse,
    ComparePreset,
    InsightsResponse,
    MerchantsResponse,
    MonthlyResponse,
    SpendingResponse,
)
from app.services.analytics_service import (
    AnalyticsService,
    Comparison,
    Period,
    PeriodError,
    parse_month,
    resolve_comparison,
    resolve_period,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@dataclass
class PeriodQuery:
    month: str | None
    date_from: date | None
    date_to: date | None


@dataclass
class CompareQuery:
    preset: ComparePreset
    compare_from: date | None
    compare_to: date | None


def period_query(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> PeriodQuery:
    return PeriodQuery(month, date_from, date_to)


def compare_query(
    compare: ComparePreset = "previous_period",
    compare_from: date | None = None,
    compare_to: date | None = None,
) -> CompareQuery:
    return CompareQuery(compare, compare_from, compare_to)


def _service(db: AsyncSession, user: User, account_ids: list[int] | None) -> AnalyticsService:
    return AnalyticsService(db, user.id, DEFAULT_TIMEZONE, account_ids)


def _resolve(
    service: AnalyticsService, period: PeriodQuery, compare: CompareQuery | None = None,
) -> tuple[Period, Comparison | None]:
    try:
        resolved = resolve_period(service.today, period.month, period.date_from, period.date_to)
        comparison = None
        if compare is not None:
            comparison = resolve_comparison(resolved, compare.preset, compare.compare_from, compare.compare_to)
    except PeriodError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return resolved, comparison


def _month(service: AnalyticsService, month: str | None) -> date:
    selected = parse_month(month) if month else service.current_month
    if selected > service.current_month:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The month is in the future")
    return selected


@router.get("/spending", response_model=SpendingResponse)
async def analytics_spending(
    period: PeriodQuery = Depends(period_query),
    compare: CompareQuery = Depends(compare_query),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    resolved, comparison = _resolve(service, period, compare)
    return await service.spending(resolved, comparison)


@router.get("/categories", response_model=CategoriesResponse)
async def analytics_categories(
    period: PeriodQuery = Depends(period_query),
    compare: CompareQuery = Depends(compare_query),
    top: int | None = Query(default=None, ge=1, le=50),
    sort: Literal["amount", "count", "change"] = "amount",
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    resolved, comparison = _resolve(service, period, compare)
    return await service.categories(resolved, comparison, top, sort)


@router.get("/merchants", response_model=MerchantsResponse)
async def analytics_merchants(
    period: PeriodQuery = Depends(period_query),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    resolved, _ = _resolve(service, period)
    return await service.merchants(resolved, limit, offset)


@router.get("/changes", response_model=ChangesResponse)
async def analytics_changes(
    period: PeriodQuery = Depends(period_query),
    compare: CompareQuery = Depends(compare_query),
    limit: int = Query(default=4, ge=1, le=20),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    resolved, comparison = _resolve(service, period, compare)
    return await service.changes(resolved, comparison, limit)


@router.get("/monthly", response_model=MonthlyResponse)
async def analytics_monthly(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    months: int = Query(default=6, ge=2, le=12),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.monthly(_month(service, month), months)


@router.get("/insights", response_model=InsightsResponse)
async def analytics_insights(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.insights(_month(service, month))
