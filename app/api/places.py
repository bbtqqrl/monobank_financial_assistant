from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.mcc_place_type import MccPlaceTypeRepository
from app.repositories.place import PlaceRepository
from app.schemas.place import (
    HomeCategorySpending,
    HomeLocation,
    HomeSpending,
    PlaceBrief,
    PlaceCandidatesResponse,
    PlaceSpending,
    PlacesMapResponse,
    SetLocationRequest,
)
from app.services.home_location import Home, HomeService
from app.services.place_matching import choose_place
from app.services.places import PLACE_SEARCH_RADIUS_M, PlaceService

router = APIRouter(prefix="/places", tags=["Places"])

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def _bounds(date_from: date | None, date_to: date | None) -> tuple[int | None, int | None]:
    return (
        int(datetime.combine(date_from, time.min, tzinfo=KYIV_TZ).timestamp()) if date_from else None,
        int(datetime.combine(date_to, time.max, tzinfo=KYIV_TZ).timestamp()) if date_to else None,
    )


def _home_location(home: Home | None) -> HomeLocation | None:
    return HomeLocation(latitude=home.latitude, longitude=home.longitude, source=home.source) if home else None


def _spending(row) -> PlaceSpending:
    place, spent, count, last_time = row
    return PlaceSpending(place=PlaceBrief.model_validate(place), spent=spent, count=count, last_time=last_time)


@router.get("/candidates", response_model=PlaceCandidatesResponse)
async def place_candidates(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    mcc: int = Query(ge=0),
    merchant: str = Query("", max_length=255),
    radius_m: int = Query(PLACE_SEARCH_RADIUS_M, ge=5, le=500),
    lang: str = Query("uk", max_length=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    place_filter = await MccPlaceTypeRepository(db).get(mcc)
    if place_filter is None or not place_filter.searchable:
        return PlaceCandidatesResponse(searchable=False, candidates=[])
    candidates = await PlaceService().search(latitude, longitude, place_filter, radius_m, lang)
    chosen, method = choose_place(candidates, merchant)
    return PlaceCandidatesResponse(searchable=True, candidates=candidates, chosen=chosen, method=method)


@router.get("/map", response_model=PlacesMapResponse)
async def places_map(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ts_from, ts_to = _bounds(date_from, date_to)
    places = PlaceRepository(db)
    rows = await places.spending_for_user(current_user.id, ts_from, ts_to)
    categories = [
        HomeCategorySpending(slug=slug, name=name, spent=spent, count=count)
        for slug, name, spent, count in await places.home_spending(current_user.id, ts_from, ts_to)
    ]
    home = HomeSpending(
        location=_home_location(await HomeService(db, current_user).location()),
        spent=sum(category.spent for category in categories),
        count=sum(category.count for category in categories),
        categories=categories,
    )
    return PlacesMapResponse(places=[_spending(row) for row in rows], home=home)


@router.get("/home", response_model=HomeLocation | None)
async def get_home(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _home_location(await HomeService(db, current_user).location())


@router.put("/home", response_model=HomeLocation)
async def set_home(
    data: SetLocationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _home_location(await HomeService(db, current_user).set(data.latitude, data.longitude))


@router.delete("/home", status_code=status.HTTP_204_NO_CONTENT)
async def reset_home(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await HomeService(db, current_user).reset()


@router.get("/{place_id}", response_model=PlaceSpending)
async def place_spending(
    place_id: int,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ts_from, ts_to = _bounds(date_from, date_to)
    rows = await PlaceRepository(db).spending_for_user(current_user.id, ts_from, ts_to, place_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return _spending(rows[0])
