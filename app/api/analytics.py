from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.analytics import DEFAULT_TIMEZONE
from app.schemas.analytics import CategoriesResponse, MerchantsResponse, SummaryResponse, TrendsResponse
from app.services.analytics_service import AnalyticsService, parse_month

router = APIRouter(prefix="/analytics", tags=["Analytics"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def _service(db: AsyncSession, user: User, account_ids: list[int] | None) -> AnalyticsService:
    return AnalyticsService(db, user.id, DEFAULT_TIMEZONE, account_ids)


@router.get("/summary", response_model=SummaryResponse)
async def analytics_summary(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    top: int = Query(default=4, ge=1, le=10),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.summary(parse_month(month or service.current_month_key()), top)


@router.get("/categories", response_model=CategoriesResponse)
async def analytics_categories(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    sort: Literal["amount", "count", "change"] = "amount",
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.categories(parse_month(month or service.current_month_key()), sort)


@router.get("/merchants", response_model=MerchantsResponse)
async def analytics_merchants(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.merchants(parse_month(month or service.current_month_key()), limit, offset)


@router.get("/trends", response_model=TrendsResponse)
async def analytics_trends(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    months: int = Query(default=6, ge=2, le=12),
    account_ids: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db, current_user, account_ids)
    return await service.trends(parse_month(month or service.current_month_key()), months)
