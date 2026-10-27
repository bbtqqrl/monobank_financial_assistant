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


class PlaceCandidatesResponse(BaseModel):
    searchable: bool
    providers: dict[str, list[PlaceResponse] | None]
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

    model_config = ConfigDict(from_attributes=True)


class SetLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
