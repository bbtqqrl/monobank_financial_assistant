import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx
import jwt

from app.core.config import (
    APPLE_MAPS_KEY_ID, APPLE_MAPS_PRIVATE_KEY, APPLE_MAPS_TEAM_ID, APPLE_MAPS_TOKEN, GOOGLE_PLACES_API_KEY,
    PLACE_SEARCH_RADIUS_M, PLACES_COMPARE_LOG,
)
from app.schemas.place import PlaceResponse
from app.services.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)

APPLE_MAPS_URL = "https://maps-api.apple.com/v1"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1"
GOOGLE_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.primaryType"
SIGNED_TOKEN_TTL_SECONDS = 3600
ACCESS_TOKEN_MARGIN_SECONDS = 60
GOOGLE_MAX_RESULTS = 20
EARTH_RADIUS_M = 6_371_000
METERS_PER_DEGREE = 111_320

_apple_access_token = {"value": None, "expires_at": 0.0}


class PlaceFilter(Protocol):
    google_types: list[str]
    apple_categories: list[str]


@dataclass
class PlaceSearch:
    results: dict[str, list[PlaceResponse] | None]

    @property
    def candidates(self) -> list[PlaceResponse]:
        return next((found for found in self.results.values() if found), [])

    @property
    def unavailable(self) -> bool:
        return all(found is None for found in self.results.values())


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    dlat, dlon = (lat2 - lat1) * p, (lon2 - lon1) * p
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def search_region(latitude: float, longitude: float, radius_m: float) -> str:
    dlat = radius_m / METERS_PER_DEGREE
    dlon = radius_m / (METERS_PER_DEGREE * math.cos(math.radians(latitude)))
    return f"{latitude + dlat},{longitude + dlon},{latitude - dlat},{longitude - dlon}"


def _within(places: list[PlaceResponse], radius_m: float) -> list[PlaceResponse]:
    return sorted((p for p in places if p.distance_m <= radius_m), key=lambda p: p.distance_m)


def _place(
    provider: str, place_id: str, name: str, category: str | None, address: str | None,
    point_lat: float, point_lon: float, latitude: float, longitude: float,
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


class GooglePlacesProvider:
    name = "google"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    @staticmethod
    def configured() -> bool:
        return bool(GOOGLE_PLACES_API_KEY)

    async def search(
        self, latitude: float, longitude: float, place_filter: PlaceFilter, radius_m: float, lang: str,
    ) -> list[PlaceResponse]:
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
            raise ServiceUnavailableError("Google Places is unavailable")
        return _within([
            _place(
                self.name, result["id"], (result.get("displayName") or {}).get("text", ""),
                result.get("primaryType"), result.get("formattedAddress"),
                result["location"]["latitude"], result["location"]["longitude"], latitude, longitude,
            )
            for result in results
            if result.get("id") and result.get("location")
        ], radius_m)


class AppleMapsProvider:
    name = "apple"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    @staticmethod
    def configured() -> bool:
        return bool(APPLE_MAPS_TOKEN or (APPLE_MAPS_PRIVATE_KEY and APPLE_MAPS_KEY_ID and APPLE_MAPS_TEAM_ID))

    async def search(
        self, latitude: float, longitude: float, place_filter: PlaceFilter, radius_m: float, lang: str,
    ) -> list[PlaceResponse]:
        if not place_filter.apple_categories:
            return []
        try:
            async with httpx.AsyncClient(base_url=APPLE_MAPS_URL, timeout=10, transport=self._transport) as client:
                token = await self._access_token(client)
                response = await client.get("/search", headers={"Authorization": f"Bearer {token}"}, params={
                    "q": "*",
                    "searchRegion": search_region(latitude, longitude, radius_m),
                    "includePoiCategories": ",".join(place_filter.apple_categories),
                    "lang": lang,
                })
                response.raise_for_status()
                results = response.json().get("results", [])
        except httpx.HTTPError:
            logger.warning("Apple Maps search failed", exc_info=True)
            raise ServiceUnavailableError("Apple Maps is unavailable")
        return _within([
            _place(
                self.name, result["id"], result.get("name", ""), result.get("poiCategory"),
                ", ".join((result.get("formattedAddressLines") or [])[:2]) or None,
                result["coordinate"]["latitude"], result["coordinate"]["longitude"], latitude, longitude,
            )
            for result in results
            if result.get("id") and result.get("coordinate")
        ], radius_m)

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


class PlaceService:
    def __init__(self, providers: list | None = None, compare: bool | None = None):
        self._providers = providers if providers is not None else [
            p for p in (GooglePlacesProvider(), AppleMapsProvider()) if p.configured()
        ]
        self.compare = bool(PLACES_COMPARE_LOG) if compare is None else compare

    async def search(
        self, latitude: float, longitude: float, place_filter: PlaceFilter,
        radius_m: float = PLACE_SEARCH_RADIUS_M, lang: str = "uk",
    ) -> PlaceSearch:
        if not self._providers:
            raise ServiceUnavailableError("Place search is not configured")
        if self.compare:
            found = await asyncio.gather(*(
                self._search(p, latitude, longitude, place_filter, radius_m, lang) for p in self._providers
            ))
            return PlaceSearch(dict(zip((p.name for p in self._providers), found)))
        results = {}
        for provider in self._providers:
            results[provider.name] = await self._search(provider, latitude, longitude, place_filter, radius_m, lang)
            if results[provider.name]:
                break
        return PlaceSearch(results)

    @staticmethod
    async def _search(provider, latitude, longitude, place_filter, radius_m, lang) -> list[PlaceResponse] | None:
        try:
            return await provider.search(latitude, longitude, place_filter, radius_m, lang)
        except ServiceUnavailableError:
            return None


def write_compare_log(record: dict) -> None:
    if not PLACES_COMPARE_LOG:
        return
    line = json.dumps({"at": datetime.now(timezone.utc).isoformat(), **record}, ensure_ascii=False, default=str)
    try:
        with open(PLACES_COMPARE_LOG, "a", encoding="utf-8") as log:
            log.write(line + "\n")
    except OSError:
        logger.warning("Could not write places compare log to %s", PLACES_COMPARE_LOG, exc_info=True)
