import logging
import math
from typing import Protocol

import httpx

from app.core.config import GOOGLE_PLACES_API_KEY, PLACE_SEARCH_RADIUS_M
from app.schemas.place import PlaceResponse
from app.services.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1"
GOOGLE_FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.location", "places.primaryType",
    "places.primaryTypeDisplayName", "places.shortFormattedAddress", "places.addressComponents", "places.googleMapsUri",
])
GOOGLE_MAX_RESULTS = 20
EARTH_RADIUS_M = 6_371_000
METERS_PER_DEGREE = 111_320


class PlaceFilter(Protocol):
    google_types: list[str]


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    dlat, dlon = (lat2 - lat1) * p, (lon2 - lon1) * p
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


class PlaceService:
    provider = "google"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def search(
        self, latitude: float, longitude: float, place_filter: PlaceFilter,
        radius_m: float = PLACE_SEARCH_RADIUS_M, lang: str = "uk",
    ) -> list[PlaceResponse]:
        if not GOOGLE_PLACES_API_KEY:
            raise ServiceUnavailableError("Place search is not configured")
        if not place_filter.google_types:
            return []
        try:
            async with httpx.AsyncClient(base_url=GOOGLE_PLACES_URL, timeout=10, transport=self._transport) as client:
                response = await client.post("/places:searchNearby", headers={
                    "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": GOOGLE_FIELD_MASK,
                }, json={
                    "includedTypes": place_filter.google_types,
                    "maxResultCount": GOOGLE_MAX_RESULTS,
                    "rankPreference": "DISTANCE",
                    "languageCode": lang,
                    "locationRestriction": {"circle": {
                        "center": {"latitude": latitude, "longitude": longitude}, "radius": radius_m,
                    }},
                })
                response.raise_for_status()
                results = response.json().get("places", [])
        except httpx.HTTPError:
            logger.warning("Google Places search failed", exc_info=True)
            raise ServiceUnavailableError("Place search is unavailable")
        places = [
            _google_place(result, latitude, longitude) for result in results if result.get("id") and result.get("location")
        ]
        return sorted((p for p in places if p.distance_m <= radius_m), key=lambda p: p.distance_m)


def _text(value: dict | None) -> str | None:
    return (value or {}).get("text") or None


def _city(components: list[dict]) -> str | None:
    for wanted in ("locality", "postal_town", "administrative_area_level_2"):
        for component in components:
            if wanted in component.get("types", []):
                return component.get("longText")
    return None


def _google_place(result: dict, latitude: float, longitude: float) -> PlaceResponse:
    location = result["location"]
    return PlaceResponse(
        provider=PlaceService.provider,
        place_id=result["id"],
        name=_text(result.get("displayName")) or "",
        category=result.get("primaryType"),
        address=result.get("formattedAddress"),
        latitude=location["latitude"],
        longitude=location["longitude"],
        distance_m=round(distance_m(latitude, longitude, location["latitude"], location["longitude"])),
        type_name=_text(result.get("primaryTypeDisplayName")),
        short_address=result.get("shortFormattedAddress"),
        city=_city(result.get("addressComponents") or []),
        maps_url=result.get("googleMapsUri"),
    )
