import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.services import places
from app.services.errors import ServiceUnavailableError
from app.services.places import AppleMapsProvider, GooglePlacesProvider, PlaceService, distance_m

LAT, LON = 49.8395, 24.0297


def apple(name, lat, lon, category="Restaurant"):
    return {"id": f"I{name}", "name": name, "poiCategory": category, "coordinate": {"latitude": lat, "longitude": lon},
            "formattedAddressLines": ["Галицька вулиця, 9", "Львів", "Україна"]}


def google(name, lat, lon, category="restaurant"):
    return {"id": f"G{name}", "displayName": {"text": name}, "primaryType": category,
            "location": {"latitude": lat, "longitude": lon}, "formattedAddress": "вулиця Шевченка, 44, Львів"}


class FakeApple(AppleMapsProvider):
    def __init__(self, by_query):
        super().__init__()
        self.by_query = by_query
        self.queries = []

    async def search(self, query, latitude, longitude, radius_m, lang):
        self.queries.append(query)
        return self.by_query.get(query, [])


def test_distance():
    assert round(distance_m(LAT, LON, LAT + 0.001, LON)) == 111


async def test_apple_merchant_nearby_wins():
    provider = FakeApple({"Сільпо": [apple("Сільпо далеко", LAT + 0.02, LON), apple("Сільпо", LAT + 0.001, LON, "FoodMarket")]})
    place = await provider.nearest(LAT, LON, "Сільпо", "uk-UA")
    assert (place.name, place.matched_merchant, place.distance_m, place.address) == ("Сільпо", True, 111, "Галицька вулиця, 9, Львів")
    assert provider.queries == ["Сільпо"]


async def test_apple_falls_back_to_nearest_business():
    provider = FakeApple({
        "ФОП Петро": [apple("Театр", LAT + 0.004, LON, "Theater")],
        "*": [apple("Площа", LAT, LON, None), apple("Пам'ятник", LAT + 0.0002, LON, "Landmark"),
              apple("Кав'ярня", LAT + 0.0009, LON, "Cafe"), apple("Шаурма", LAT + 0.0005, LON)],
    })
    place = await provider.nearest(LAT, LON, "ФОП Петро", "uk-UA")
    assert (place.name, place.matched_merchant) == ("Шаурма", False)
    assert provider.queries == ["ФОП Петро", "*"]


async def test_apple_nothing_close():
    assert await FakeApple({"*": [apple("Далеко", LAT + 0.01, LON)]}).nearest(LAT, LON, None, "uk-UA") is None


async def test_apple_signs_token_and_caches_it(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    monkeypatch.setattr(places, "APPLE_MAPS_PRIVATE_KEY", pem)
    monkeypatch.setattr(places, "APPLE_MAPS_KEY_ID", "KEY123")
    monkeypatch.setattr(places, "APPLE_MAPS_TEAM_ID", "TEAM123")
    monkeypatch.setattr(places, "_apple_access_token", {"value": None, "expires_at": 0.0})
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/v1/token":
            signed = request.headers["Authorization"].removeprefix("Bearer ")
            assert jwt.get_unverified_header(signed)["kid"] == "KEY123"
            assert jwt.decode(signed, key.public_key(), algorithms=["ES256"])["iss"] == "TEAM123"
            return httpx.Response(200, json={"accessToken": "access", "expiresInSeconds": 1800})
        assert request.headers["Authorization"] == "Bearer access"
        assert request.url.params["q"] == "Сільпо"
        return httpx.Response(200, json={"results": [apple("Сільпо", LAT, LON)]})

    provider = AppleMapsProvider(httpx.MockTransport(handler))
    assert len(await provider.search("Сільпо", LAT, LON, 300, "uk-UA")) == 1
    await provider.search("Сільпо", LAT, LON, 300, "uk-UA")
    assert calls == ["/v1/token", "/v1/search", "/v1/search"]


async def test_apple_errors_become_unavailable(monkeypatch):
    monkeypatch.setattr(places, "_apple_access_token", {"value": "access", "expires_at": 1e12})
    provider = AppleMapsProvider(httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(ServiceUnavailableError):
        await provider.search("*", LAT, LON, 150, "uk-UA")


async def test_google_merchant_then_nearest(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")
    bodies = []

    def handler(request):
        assert request.headers["X-Goog-Api-Key"] == "gkey"
        body = json.loads(request.content)
        bodies.append((request.url.path, body))
        if request.url.path.endswith(":searchText"):
            return httpx.Response(200, json={"places": [google("Сільпо", LAT + 0.01, LON, "supermarket")]})
        return httpx.Response(200, json={"places": [
            google("Будинок", LAT, LON, "apartment_building"), google("Кава 44", LAT + 0.0003, LON, "coffee_shop"),
        ]})

    place = await GooglePlacesProvider(httpx.MockTransport(handler)).nearest(LAT, LON, "Сільпо", "uk-UA")
    assert (place.provider, place.name, place.category, place.matched_merchant, place.distance_m) == (
        "google", "Кава 44", "coffee_shop", False, 33,
    )
    assert [path for path, _ in bodies] == ["/v1/places:searchText", "/v1/places:searchNearby"]
    assert bodies[1][1]["rankPreference"] == "DISTANCE"
    assert bodies[1][1]["includedTypes"] == places.GOOGLE_PLACE_TYPES
    assert bodies[1][1]["locationRestriction"]["circle"]["radius"] == places.NEAREST_RADIUS_M


async def test_service_returns_both_and_survives_failures():
    class Broken:
        name = "google"

        async def nearest(self, *args):
            raise ServiceUnavailableError("down")

    result = await PlaceService([FakeApple({"*": [apple("Шаурма", LAT, LON)]}), Broken()]).nearest(LAT, LON)
    assert result.apple.name == "Шаурма"
    assert result.google is None


async def test_service_not_configured():
    with pytest.raises(ServiceUnavailableError):
        await PlaceService([]).nearest(LAT, LON)
