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
from app.services.place_matching import PlaceMethod
from app.services.places import AppleMapsProvider, GooglePlacesProvider, PlaceService, distance_m
from app.services.transaction_location_service import TransactionLocationService

LAT, LON = 49.8395, 24.0297
FOOD = SimpleNamespace(google_types=["restaurant", "cafe"], apple_categories=["Restaurant", "Cafe"], searchable=True)


def apple(name, lat, lon, category="Restaurant"):
    return {"id": f"I{name}", "name": name, "poiCategory": category, "coordinate": {"latitude": lat, "longitude": lon},
            "formattedAddressLines": ["Галицька вулиця, 9", "Львів", "Україна"]}


def google(name, lat, lon, category="restaurant"):
    return {"id": f"G{name}", "displayName": {"text": name}, "primaryType": category,
            "location": {"latitude": lat, "longitude": lon}, "formattedAddress": "вулиця Шевченка, 44, Львів"}


def found(name="Кава", distance=5, provider="google"):
    return PlaceResponse(provider=provider, place_id=f"G{name}", name=name, category="cafe", address=None,
                         latitude=LAT, longitude=LON, distance_m=distance)


def test_distance():
    assert round(distance_m(LAT, LON, LAT + 0.001, LON)) == 111


async def test_google_returns_candidates_within_radius(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")
    bodies = []

    def handler(request):
        assert request.headers["X-Goog-Api-Key"] == "gkey"
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"places": [
            google("Шаурма", LAT + 0.0002, LON), google("Кава 44", LAT + 0.0001, LON, "cafe"),
            google("Далеко", LAT + 0.01, LON),
        ]})

    found_places = await GooglePlacesProvider(httpx.MockTransport(handler)).search(LAT, LON, FOOD, 30, "uk")
    assert [(p.name, p.distance_m) for p in found_places] == [("Кава 44", 11), ("Шаурма", 22)]
    assert bodies[0]["includedTypes"] == ["restaurant", "cafe"]
    assert bodies[0]["rankPreference"] == "DISTANCE"
    assert bodies[0]["locationRestriction"]["circle"]["radius"] == 30


async def test_providers_skip_request_without_types():
    def handler(request):
        raise AssertionError("no request expected")

    no_types = SimpleNamespace(google_types=[], apple_categories=[])
    assert await GooglePlacesProvider(httpx.MockTransport(handler)).search(LAT, LON, no_types, 30, "uk") == []
    assert await AppleMapsProvider(httpx.MockTransport(handler)).search(LAT, LON, no_types, 30, "uk") == []


async def test_apple_filters_by_categories(monkeypatch):
    monkeypatch.setattr(places, "_apple_access_token", {"value": "access", "expires_at": 1e12})

    def handler(request):
        assert request.url.params["q"] == "*"
        assert request.url.params["includePoiCategories"] == "Restaurant,Cafe"
        return httpx.Response(200, json={"results": [apple("Шаурма", LAT + 0.0001, LON), apple("Далеко", LAT + 0.01, LON)]})

    found_places = await AppleMapsProvider(httpx.MockTransport(handler)).search(LAT, LON, FOOD, 30, "uk")
    assert [(p.name, p.address) for p in found_places] == [("Шаурма", "Галицька вулиця, 9, Львів")]


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
    await provider.search(LAT, LON, FOOD, 30, "uk")
    await provider.search(LAT, LON, FOOD, 30, "uk")
    assert calls == ["/v1/token", "/v1/search", "/v1/search"]


async def test_provider_errors_become_unavailable(monkeypatch):
    monkeypatch.setattr(places, "_apple_access_token", {"value": "access", "expires_at": 1e12})
    with pytest.raises(ServiceUnavailableError):
        await AppleMapsProvider(httpx.MockTransport(lambda request: httpx.Response(500))).search(LAT, LON, FOOD, 30, "uk")


class Provider:
    def __init__(self, name, result=(), fails=False):
        self.name, self.result, self.fails, self.calls = name, list(result), fails, 0

    async def search(self, latitude, longitude, place_filter, radius_m, lang):
        self.calls += 1
        if self.fails:
            raise ServiceUnavailableError("down")
        return self.result


async def test_service_falls_back_to_second_provider():
    search = await PlaceService([Provider("google", fails=True), Provider("apple", [found("Шаурма")])], compare=False).search(LAT, LON, FOOD)
    assert [p.name for p in search.candidates] == ["Шаурма"]
    search = await PlaceService([Provider("google"), Provider("apple", [found("Кава")])], compare=False).search(LAT, LON, FOOD)
    assert [p.name for p in search.candidates] == ["Кава"]
    unused = Provider("apple", [found("Друге")])
    search = await PlaceService([Provider("google", [found("Перше")]), unused], compare=False).search(LAT, LON, FOOD)
    assert ([p.name for p in search.candidates], unused.calls, list(search.results)) == (["Перше"], 0, ["google"])


async def test_compare_mode_asks_every_provider():
    google_provider, apple_provider = Provider("google", [found("Перше")]), Provider("apple", fails=True)
    search = await PlaceService([google_provider, apple_provider], compare=True).search(LAT, LON, FOOD)
    assert (google_provider.calls, apple_provider.calls) == (1, 1)
    assert search.results["apple"] is None
    assert [p.name for p in search.candidates] == ["Перше"]


async def test_service_nothing_found_or_all_down():
    search = await PlaceService([Provider("google"), Provider("apple")], compare=False).search(LAT, LON, FOOD)
    assert (search.candidates, search.unavailable) == ([], False)
    search = await PlaceService([Provider("google", fails=True)], compare=False).search(LAT, LON, FOOD)
    assert search.unavailable
    with pytest.raises(ServiceUnavailableError):
        await PlaceService([]).search(LAT, LON, FOOD)


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


def location_service(transaction, candidates=(), fails=False, linked=(), mcc_type=FOOD, compare=False):
    provider = Provider("google", candidates, fails)
    service = TransactionLocationService(FakeDb(), 5, PlaceService([provider], compare=compare))
    calls = {"upserted": [], "links": [], "provider": provider}

    async def get_by_id_for_user(transaction_id, user_id):
        return transaction if transaction and transaction_id == transaction.id and user_id == 5 else None

    async def get_mcc(mcc):
        return mcc_type

    async def list_near(merchant_key, latitude, longitude, radius_m):
        return list(linked)

    async def link(merchant_key, place_id):
        calls["links"].append((merchant_key, place_id))

    async def upsert(place):
        calls["upserted"].append(place)
        return SimpleNamespace(id=99, latitude=place.latitude, longitude=place.longitude, name=place.name)

    service.transactions = SimpleNamespace(get_by_id_for_user=get_by_id_for_user)
    service.mcc_types = SimpleNamespace(get=get_mcc)
    service.links = SimpleNamespace(list_near=list_near, link=link)
    service.place_repo = SimpleNamespace(upsert=upsert)
    return service, calls


def transaction(description="KREDENS CAFE", mcc=5812):
    return SimpleNamespace(id=1, description=description, mcc=mcc, latitude=None, longitude=None, place=None,
                           place_method=None)


async def test_location_skips_mcc_without_search():
    tx = transaction(mcc=4829)
    service, calls = location_service(tx, candidates=[found()], mcc_type=SimpleNamespace(searchable=False))
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.place_method, tx.latitude, calls["provider"].calls) == (None, PlaceMethod.SKIPPED, LAT, 0)


async def test_location_skips_unknown_mcc():
    tx = transaction(mcc=1234)
    service, _ = location_service(tx, candidates=[found()], mcc_type=None)
    await service.set_location(1, LAT, LON)
    assert tx.place_method == PlaceMethod.SKIPPED


async def test_location_uses_saved_link_without_search():
    tx = transaction()
    near = SimpleNamespace(id=3, latitude=LAT + 0.0002, longitude=LON)
    far = SimpleNamespace(id=4, latitude=LAT + 0.01, longitude=LON)
    service, calls = location_service(tx, candidates=[found()], linked=[far, near])
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.place_method, calls["provider"].calls, calls["upserted"]) == (near, PlaceMethod.LINK, 0, [])


async def test_confident_place_is_linked_to_merchant():
    tx = transaction()
    service, calls = location_service(tx, candidates=[found("Буденні бомбони", 3), found("KREDENS CAFE на Валовій", 11)])
    await service.set_location(1, LAT, LON)
    assert (tx.place.name, tx.place_method, calls["links"]) == (
        "KREDENS CAFE на Валовій", PlaceMethod.NAME_MATCH, [("kredens cafe", 99)],
    )


async def test_nearest_place_is_not_linked():
    tx = transaction("ФОП Петренко О.І.")
    service, calls = location_service(tx, candidates=[found("Шаурма", 12), found("Кава", 4)])
    await service.set_location(1, LAT, LON)
    assert (tx.place.name, tx.place_method, calls["links"]) == ("Кава", PlaceMethod.NEAREST, [])


async def test_location_without_candidates():
    tx = transaction()
    service, calls = location_service(tx)
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.place_method, tx.latitude, calls["upserted"]) == (None, PlaceMethod.NOT_FOUND, LAT, [])


async def test_location_saved_even_when_search_is_down():
    tx = transaction()
    service, _ = location_service(tx, fails=True)
    await service.set_location(1, LAT, LON)
    assert (tx.place, tx.place_method, tx.latitude, service.db.commits) == (None, None, LAT, 1)


async def test_location_for_foreign_transaction():
    service, _ = location_service(None)
    with pytest.raises(NotFoundError):
        await service.set_location(1, LAT, LON)


async def test_compare_log_is_written(monkeypatch, tmp_path):
    log = tmp_path / "places.jsonl"
    monkeypatch.setattr(places, "PLACES_COMPARE_LOG", str(log))
    tx = transaction()
    service, _ = location_service(tx, candidates=[found("KREDENS CAFE")], compare=True)
    await service.set_location(1, LAT, LON)
    record = json.loads(log.read_text(encoding="utf-8"))
    assert (record["transaction_id"], record["method"], record["chosen"]["name"]) == (1, "single", "KREDENS CAFE")
    assert [p["name"] for p in record["providers"]["google"]] == ["KREDENS CAFE"]
