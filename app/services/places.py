import asyncio
import logging
import math
import time

import httpx
import jwt

from app.core.config import (
    APPLE_MAPS_KEY_ID, APPLE_MAPS_PRIVATE_KEY, APPLE_MAPS_TEAM_ID, APPLE_MAPS_TOKEN, GOOGLE_PLACES_API_KEY,
)
from app.schemas.place import NearbyPlacesResponse, PlaceResponse
from app.services.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)

APPLE_MAPS_URL = "https://maps-api.apple.com/v1"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1"
GOOGLE_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.primaryType"
SIGNED_TOKEN_TTL_SECONDS = 3600
ACCESS_TOKEN_MARGIN_SECONDS = 60
MERCHANT_RADIUS_M = 300
NEAREST_RADIUS_M = 150
GOOGLE_MAX_RESULTS = 10
EARTH_RADIUS_M = 6_371_000
METERS_PER_DEGREE = 111_320
APPLE_NOT_PLACES = {
    None, "Landmark", "Park", "NationalPark", "Beach", "Marina", "Campground", "Castle", "Fortress",
    "PublicTransport", "Parking", "Restroom", "ATM", "FireStation", "Police", "School", "University", "Library",
}
GOOGLE_NOT_PLACES = {
    None, "apartment_building", "apartment_complex", "condominium_complex", "housing_complex", "route",
    "street_address", "premise", "subpremise", "park", "plaza", "tourist_attraction", "monument",
    "historical_landmark", "historical_place", "bus_stop", "transit_station", "parking", "atm", "school",
    "university", "library", "city_hall", "local_government_office", "church", "place_of_worship", "lodging",
    "corporate_office",
}

GOOGLE_PLACE_TYPES = [
    "restaurant", "cafe", "coffee_shop", "bar", "bakery", "fast_food_restaurant", "meal_takeaway", "supermarket",
    "grocery_store", "convenience_store", "food_store", "liquor_store", "store", "shopping_mall", "pharmacy",
    "drugstore", "gas_station", "gym", "beauty_salon", "hair_care", "movie_theater", "night_club", "car_wash",
    "car_repair", "dentist", "doctor", "hospital", "hotel",
]

_apple_access_token ={"value": None, "expires_at": 0.0}


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    dlat, dlon = (lat2 - lat1) * p, (lon2 - lon1) * p
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def search_region(latitude: float, longitude: float, radius_m: float) -> str:
    dlat = radius_m / METERS_PER_DEGREE
    dlon = radius_m / (METERS_PER_DEGREE * math.cos(math.radians(latitude)))
    return f"{latitude + dlat},{longitude + dlon},{latitude - dlat},{longitude - dlon}"


def _closest(places: list[PlaceResponse], radius_m: float) -> PlaceResponse | None:
    return min((p for p in places if p.distance_m <= radius_m), key=lambda p: p.distance_m, default=None)


def _place(
    provider: str, place_id: str | None, name: str, category: str | None, address: str | None,
    point_lat: float, point_lon: float, latitude: float, longitude: float, matched: bool,
) -> PlaceResponse:
    return PlaceResponse(
        provider=provider,
        place_id=place_id,
        name=name,
        category=category,
        address=address,
        latitude=point_lat,
        longitude=point_lon,
        distance_m=round(distance_m(latitude, longitude, point_lat, point_lon)),
        matched_merchant=matched,
    )


def _apple_auth_token() -> str:
    if APPLE_MAPS_PRIVATE_KEY and APPLE_MAPS_KEY_ID and APPLE_MAPS_TEAM_ID:
        now = int(time.time())
        return jwt.encode(
            {"iss": APPLE_MAPS_TEAM_ID, "iat": now, "exp": now + SIGNED_TOKEN_TTL_SECONDS},
            APPLE_MAPS_PRIVATE_KEY, algorithm="ES256", headers={"kid": APPLE_MAPS_KEY_ID, "typ": "JWT"},
        )
    if APPLE_MAPS_TOKEN:
        return APPLE_MAPS_TOKEN
    raise ServiceUnavailableError("Apple Maps is not configured")


class AppleMapsProvider:
    name = "apple"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    @staticmethod
    def configured() -> bool:
        return bool(APPLE_MAPS_TOKEN or (APPLE_MAPS_PRIVATE_KEY and APPLE_MAPS_KEY_ID and APPLE_MAPS_TEAM_ID))

    async def nearest(self, latitude: float, longitude: float, merchant: str | None, lang: str) -> PlaceResponse | None:
        if merchant:
            place = await self._closest(merchant, latitude, longitude, MERCHANT_RADIUS_M, lang, True)
            if place:
                return place
        return await self._closest("*", latitude, longitude, NEAREST_RADIUS_M, lang, False)

    async def _closest(
        self, query: str, latitude: float, longitude: float, radius_m: float, lang: str, matched: bool,
    ) -> PlaceResponse | None:
        results = await self.search(query, latitude, longitude, radius_m, lang)
        return _closest([
            _place(
                self.name, result.get("id"), result.get("name", ""), result.get("poiCategory"),
                ", ".join((result.get("formattedAddressLines") or [])[:2]) or None,
                result["coordinate"]["latitude"], result["coordinate"]["longitude"], latitude, longitude, matched,
            )
            for result in results
            if result.get("poiCategory") not in APPLE_NOT_PLACES and result.get("coordinate")
        ], radius_m)

    async def search(self, query: str, latitude: float, longitude: float, radius_m: float, lang: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(base_url=APPLE_MAPS_URL, timeout=10, transport=self._transport) as client:
                token = await self._access_token(client)
                response = await client.get("/search", headers={"Authorization": f"Bearer {token}"}, params={
                    "q": query, "searchRegion": search_region(latitude, longitude, radius_m), "lang": lang,
                })
                response.raise_for_status()
                return response.json().get("results", [])
        except httpx.HTTPError:
            logger.warning("Apple Maps search failed", exc_info=True)
            raise ServiceUnavailableError("Apple Maps is unavailable")

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if _apple_access_token["value"] and _apple_access_token["expires_at"] > time.time():
            return _apple_access_token["value"]
        response = await client.get("/token", headers={"Authorization": f"Bearer {_apple_auth_token()}"})
        response.raise_for_status()
        data = response.json()
        _apple_access_token["value"] = data["accessToken"]
        _apple_access_token["expires_at"] = (
            time.time() + data.get("expiresInSeconds", 1800) - ACCESS_TOKEN_MARGIN_SECONDS
        )
        return _apple_access_token["value"]


class GooglePlacesProvider:
    name = "google"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    @staticmethod
    def configured() -> bool:
        return bool(GOOGLE_PLACES_API_KEY)

    async def nearest(self, latitude: float, longitude: float, merchant: str | None, lang: str) -> PlaceResponse | None:
        if merchant:
            place = await self._closest("searchText", {
                "textQuery": merchant, "pageSize": GOOGLE_MAX_RESULTS, "rankPreference": "DISTANCE",
                "locationBias": _circle(latitude, longitude, MERCHANT_RADIUS_M),
            }, latitude, longitude, MERCHANT_RADIUS_M, lang, True)
            if place:
                return place
        return await self._closest("searchNearby", {
            "includedTypes": GOOGLE_PLACE_TYPES, "maxResultCount": GOOGLE_MAX_RESULTS, "rankPreference": "DISTANCE",
            "locationRestriction": _circle(latitude, longitude, NEAREST_RADIUS_M),
        }, latitude, longitude, NEAREST_RADIUS_M, lang, False)

    async def _closest(
        self, method: str, body: dict, latitude: float, longitude: float, radius_m: float, lang: str, matched: bool,
    ) -> PlaceResponse | None:
        results = await self.search(method, {**body, "languageCode": lang})
        return _closest([
            _place(
                self.name, result.get("id"), (result.get("displayName") or {}).get("text", ""),
                result.get("primaryType"), result.get("formattedAddress"),
                result["location"]["latitude"], result["location"]["longitude"], latitude, longitude, matched,
            )
            for result in results
            if result.get("primaryType") not in GOOGLE_NOT_PLACES and result.get("location")
        ], radius_m)

    async def search(self, method: str, body: dict) -> list[dict]:
        try:
            async with httpx.AsyncClient(base_url=GOOGLE_PLACES_URL, timeout=10, transport=self._transport) as client:
                response = await client.post(f"/places:{method}", json=body, headers={
                    "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": GOOGLE_FIELD_MASK,
                })
                response.raise_for_status()
                return response.json().get("places", [])
        except httpx.HTTPError:
            logger.warning("Google Places search failed", exc_info=True)
            raise ServiceUnavailableError("Google Places is unavailable")


def _circle(latitude: float, longitude: float, radius_m: float) -> dict:
    return {"circle": {"center": {"latitude": latitude, "longitude": longitude}, "radius": radius_m}}


class PlaceService:
    def __init__(self, providers: list | None = None):
        self._providers = providers if providers is not None else [
            p for p in (AppleMapsProvider(), GooglePlacesProvider()) if p.configured()
        ]

    # TODO: після порівняння лишити Google основним, а Apple — запасним при вичерпанні ліміту чи помилках
    async def nearest(
        self, latitude: float, longitude: float, merchant: str | None = None, lang: str = "uk-UA",
    ) -> NearbyPlacesResponse:
        if not self._providers:
            raise ServiceUnavailableError("Place search is not configured")
        merchant = merchant.strip() if merchant and merchant.strip() else None
        results = await asyncio.gather(
            *(p.nearest(latitude, longitude, merchant, lang) for p in self._providers), return_exceptions=True,
        )
        found = {}
        for provider, result in zip(self._providers, results):
            if isinstance(result, BaseException):
                if not isinstance(result, ServiceUnavailableError):
                    logger.warning("%s place lookup failed", provider.name, exc_info=result)
                result = None
            found[provider.name] = result
        return NearbyPlacesResponse(**found)
