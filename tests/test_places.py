import json
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.dialects import postgresql

from app.repositories.place import PlaceRepository
from app.schemas.place import PlaceResponse
from app.services import places
from app.services.errors import NotFoundError, ServiceUnavailableError
from app.services.places import AppleMapsProvider, GooglePlacesProvider, PlaceService, distance_m
from app.services.transaction_location_service import TransactionLocationService

LAT, LON = 49.8395, 24.0297


def apple(name, lat, lon, category="Restaurant"):
    return {"id": f"I{name}", "name": name, "poiCategory": category, "coordinate": {"latitude": lat, "longitude": lon},
            "formattedAddressLines": ["Галицька вулиця, 9", "Львів", "Україна"]}


def google(name, lat, lon, category="restaurant"):
    return {"id": f"G{name}", "displayName": {"text": name}, "primaryType": category,
            "location": {"latitude": lat, "longitude": lon}, "formattedAddress": "вулиця Шевченка, 44, Львів"}


def found(name="Кава", distance=5):
    return PlaceResponse(provider="google", place_id=f"G{name}", name=name, category="cafe", address=None,
                         latitude=LAT, longitude=LON, distance_m=distance)


def test_distance():
    assert round(distance_m(LAT, LON, LAT + 0.001, LON)) == 111


async def test_google_nearest_by_distance(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")
    bodies = []

    def handler(request):
        assert request.headers["X-Goog-Api-Key"] == "gkey"
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"places": [
            google("Далеко", LAT + 0.01, LON), google("Кава 44", LAT + 0.0003, LON, "coffee_shop"),
            google("Шаурма", LAT + 0.0006, LON),
        ]})

    place = await GooglePlacesProvider(httpx.MockTransport(handler)).nearest(LAT, LON, "uk")
    assert (place.provider, place.place_id, place.name, place.category, place.distance_m) == (
        "google", "GКава 44", "Кава 44", "coffee_shop", 33,
    )
    assert bodies[0]["rankPreference"] == "DISTANCE"
    assert bodies[0]["includedTypes"] == places.GOOGLE_PLACE_TYPES
    assert bodies[0]["locationRestriction"]["circle"]["radius"] == places.NEAREST_RADIUS_M


async def test_apple_skips_landmarks(monkeypatch):
    monkeypatch.setattr(places, "_apple_access_token", {"value": "access", "expires_at": 1e12})

    def handler(request):
        assert request.url.params["q"] == "*"
        return httpx.Response(200, json={"results": [
            apple("Площа", LAT, LON, None), apple("Пам'ятник", LAT + 0.0002, LON, "Landmark"),
            apple("Шаурма", LAT + 0.0005, LON),
        ]})

    place = await AppleMapsProvider(httpx.MockTransport(handler)).nearest(LAT, LON, "uk")
    assert (place.name, place.address) == ("Шаурма", "Галицька вулиця, 9, Львів")


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
        return httpx.Response(200, json={"results": [apple("Сільпо", LAT, LON)]})

    provider = AppleMapsProvider(httpx.MockTransport(handler))
    await provider.nearest(LAT, LON, "uk")
    await provider.nearest(LAT, LON, "uk")
    assert calls == ["/v1/token", "/v1/search", "/v1/search"]


async def test_provider_errors_become_unavailable(monkeypatch):
    monkeypatch.setattr(places, "_apple_access_token", {"value": "access", "expires_at": 1e12})
    with pytest.raises(ServiceUnavailableError):
        await AppleMapsProvider(httpx.MockTransport(lambda request: httpx.Response(500))).nearest(LAT, LON, "uk")


class Provider:
    def __init__(self, result=None, fails=False):
        self.result, self.fails, self.calls = result, fails, 0

    async def nearest(self, latitude, longitude, lang):
        self.calls += 1
        if self.fails:
            raise ServiceUnavailableError("down")
        return self.result


async def test_service_falls_back_to_second_provider():
    google_down, apple_ok = Provider(fails=True), Provider(found("Шаурма"))
    assert (await PlaceService([google_down, apple_ok]).nearest(LAT, LON)).name == "Шаурма"
    empty, second = Provider(None), Provider(found("Кава"))
    assert (await PlaceService([empty, second]).nearest(LAT, LON)).name == "Кава"
    first, unused = Provider(found("Перше")), Provider(found("Друге"))
    assert (await PlaceService([first, unused]).nearest(LAT, LON)).name == "Перше"
    assert unused.calls == 0


async def test_service_nothing_found_or_all_down():
    assert await PlaceService([Provider(None), Provider(None)]).nearest(LAT, LON) is None
    with pytest.raises(ServiceUnavailableError):
        await PlaceService([Provider(fails=True)]).nearest(LAT, LON)
    with pytest.raises(ServiceUnavailableError):
        await PlaceService([]).nearest(LAT, LON)


async def test_upsert_statement_compiles():
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect())))
        return SimpleNamespace(scalar_one=lambda: "place")

    assert await PlaceRepository(SimpleNamespace(execute=execute)).upsert(found()) == "place"
    assert "ON CONFLICT ON CONSTRAINT uq_places_provider_place DO UPDATE" in statements[0]
    assert "RETURNING places.id" in statements[0]


class FakeDb:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def location_service(transaction, known=(), result=None, fails=False):
    service = TransactionLocationService(FakeDb(), 5, PlaceService([Provider(result, fails)]))
    upserted = []

    async def get_by_id_for_user(transaction_id, user_id):
        return transaction if transaction and transaction_id == transaction.id and user_id == 5 else None

    async def list_for_merchant(user_id, mapping_id):
        return list(known)

    async def upsert(place):
        upserted.append(place)
        return SimpleNamespace(id=99, latitude=place.latitude, longitude=place.longitude, name=place.name)

    service.transactions = SimpleNamespace(get_by_id_for_user=get_by_id_for_user)
    service.place_repo = SimpleNamespace(list_for_merchant=list_for_merchant, upsert=upsert)
    return service, upserted


def transaction(mapping_id=7):
    return SimpleNamespace(id=1, merchant_mapping_id=mapping_id, latitude=None, longitude=None, place=None)


async def test_location_reuses_known_merchant_place():
    tx = transaction()
    known = SimpleNamespace(id=3, latitude=LAT + 0.0002, longitude=LON)
    far = SimpleNamespace(id=4, latitude=LAT + 0.01, longitude=LON)
    service, upserted = location_service(tx, known=[far, known], result=found())
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.latitude, tx.longitude, upserted, service.db.commits) == (known, LAT, LON, [], 1)


async def test_location_looks_up_nearest_place():
    tx = transaction(mapping_id=None)
    service, upserted = location_service(tx, result=found("Кава"))
    await service.set_location(1, LAT, LON)
    assert tx.place.id == 99
    assert [p.name for p in upserted] == ["Кава"]


async def test_location_saved_even_when_search_is_down():
    tx = transaction()
    service, _ = location_service(tx, fails=True)
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.latitude, service.db.commits) == (None, LAT, 1)


async def test_location_for_foreign_transaction():
    service, _ = location_service(None)
    with pytest.raises(NotFoundError):
        await service.set_location(1, LAT, LON)
