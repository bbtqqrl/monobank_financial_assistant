from pydantic import BaseModel


class PlaceResponse(BaseModel):
    provider: str
    place_id: str | None
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    distance_m: int
    matched_merchant: bool


class NearbyPlacesResponse(BaseModel):
    apple: PlaceResponse | None = None
    google: PlaceResponse | None = None
