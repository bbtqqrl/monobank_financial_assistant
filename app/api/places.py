from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.mcc_place_type import MccPlaceTypeRepository
from app.schemas.place import PlaceCandidatesResponse
from app.services.place_matching import choose_place
from app.services.places import PLACE_SEARCH_RADIUS_M, PlaceService

router = APIRouter(prefix="/places", tags=["Places"])


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
        return PlaceCandidatesResponse(searchable=False, providers={})
    search = await PlaceService(compare=True).search(latitude, longitude, place_filter, radius_m, lang)
    chosen, method = choose_place(search.candidates, merchant)
    return PlaceCandidatesResponse(searchable=True, providers=search.results, chosen=chosen, method=method)
