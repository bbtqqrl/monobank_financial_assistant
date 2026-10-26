from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.db.models.user import User
from app.schemas.place import NearbyPlacesResponse
from app.services.places import PlaceService

router = APIRouter(prefix="/places", tags=["Places"])


@router.get("/nearest", response_model=NearbyPlacesResponse)
async def nearest_place(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    merchant: str | None = Query(None, max_length=100),
    lang: str = Query("uk-UA", max_length=10),
    current_user: User = Depends(get_current_user),
):
    return await PlaceService().nearest(latitude, longitude, merchant, lang)
