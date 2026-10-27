import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.place import PlaceRepository
from app.schemas.place import PlaceResponse
from app.services import places
from app.services.errors import NotFoundError, ServiceUnavailableError
from app.services.place_matching import PlaceMethod
from app.services.places import PlaceService, distance_m
from app.services.transaction_location_service import TransactionLocationService

LAT, LON = 49.8395, 24.0297
FOOD = SimpleNamespace(google_types=["restaurant", "cafe"], searchable=True)


def google(name, lat, lon, category="restaurant"):
    return {"id": f"G{name}", "displayName": {"text": name}, "primaryType": category,
            "location": {"latitude": lat, "longitude": lon}, "formattedAddress": "вулиця Шевченка, 44, Львів"}


def found(name="Кава", distance=5):
    return PlaceResponse(provider="google", place_id=f"G{name}", name=name, category="cafe", address=None,
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

    candidates = await PlaceService(httpx.MockTransport(handler)).search(LAT, LON, FOOD, 30)
    assert [(p.name, p.distance_m, p.address) for p in candidates] == [
        ("Кава 44", 11, "вулиця Шевченка, 44, Львів"), ("Шаурма", 22, "вулиця Шевченка, 44, Львів"),
    ]
    assert bodies[0]["includedTypes"] == ["restaurant", "cafe"]
    assert bodies[0]["rankPreference"] == "DISTANCE"
    assert bodies[0]["locationRestriction"]["circle"]["radius"] == 30


async def test_google_skips_request_without_types(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")

    def handler(request):
        raise AssertionError("no request expected")

    no_types = SimpleNamespace(google_types=[])
    assert await PlaceService(httpx.MockTransport(handler)).search(LAT, LON, no_types) == []


async def test_google_errors_become_unavailable(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")
    with pytest.raises(ServiceUnavailableError):
        await PlaceService(httpx.MockTransport(lambda request: httpx.Response(500))).search(LAT, LON, FOOD)
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", None)
    with pytest.raises(ServiceUnavailableError):
        await PlaceService().search(LAT, LON, FOOD)


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


class FakePlaces:
    def __init__(self, candidates=(), fails=False):
        self.candidates, self.fails, self.calls = list(candidates), fails, 0

    async def search(self, latitude, longitude, place_filter):
        self.calls += 1
        if self.fails:
            raise ServiceUnavailableError("down")
        return self.candidates


def location_service(transaction, candidates=(), fails=False, linked=(), mcc_type=FOOD):
    fake_places = FakePlaces(candidates, fails)
    service = TransactionLocationService(FakeDb(), 5, fake_places)
    calls = {"upserted": [], "links": [], "places": fake_places}

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
    assert (tx.place, tx.place_method, tx.latitude, calls["places"].calls) == (None, PlaceMethod.SKIPPED, LAT, 0)


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
    assert (tx.place, tx.place_method, calls["places"].calls, calls["upserted"]) == (near, PlaceMethod.LINK, 0, [])


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
