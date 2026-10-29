from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlaceResponse(BaseModel):
    provider: str
    place_id: str
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    distance_m: int
    type_name: str | None = None
    short_address: str | None = None
    city: str | None = None
    maps_url: str | None = None


class PlaceCandidatesResponse(BaseModel):
    searchable: bool
    candidates: list[PlaceResponse]
    chosen: PlaceResponse | None = None
    method: str | None = None


class PlaceBrief(BaseModel):
    id: int
    provider: str
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    type_name: str | None
    short_address: str | None
    city: str | None
    maps_url: str | None

    model_config = ConfigDict(from_attributes=True)


class PlaceSpending(BaseModel):
    place: PlaceBrief
    spent: int
    count: int
    last_time: int


class HomeLocation(BaseModel):
    latitude: float
    longitude: float
    source: Literal["auto", "user"]


class HomeCategorySpending(BaseModel):
    slug: str
    name: str
    spent: int
    count: int


class HomeSpending(BaseModel):
    location: HomeLocation | None
    spent: int
    count: int
    categories: list[HomeCategorySpending]


class PlacesMapResponse(BaseModel):
    places: list[PlaceSpending]
    home: HomeSpending


class SetLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PlaceFeedbackRequest(BaseModel):
    correct: bool
    place_id: str | None = Field(default=None, max_length=255)
