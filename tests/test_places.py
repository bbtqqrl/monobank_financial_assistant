import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.place import PlaceRepository
from app.schemas.place import PlaceResponse
from app.services import places
from app.services.errors import InvalidRequestError, NotFoundError, ServiceUnavailableError
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


async def test_google_place_details(monkeypatch):
    monkeypatch.setattr(places, "GOOGLE_PLACES_API_KEY", "gkey")
    detailed = google("Сільпо", LAT, LON, "supermarket") | {
        "primaryTypeDisplayName": {"text": "Супермаркет", "languageCode": "uk"},
        "shortFormattedAddress": "вулиця Шевченка, 44",
        "addressComponents": [
            {"longText": "44", "types": ["street_number"]},
            {"longText": "Львів", "types": ["locality", "political"]},
        ],
        "googleMapsUri": "https://maps.google.com/?cid=1",
    }
    mask = []

    def handler(request):
        mask.append(request.headers["X-Goog-FieldMask"])
        return httpx.Response(200, json={"places": [detailed, google("Без деталей", LAT, LON)]})

    rich, bare = await PlaceService(httpx.MockTransport(handler)).search(LAT, LON, FOOD, 30)
    assert (rich.type_name, rich.short_address, rich.city, rich.maps_url) == (
        "Супермаркет", "вулиця Шевченка, 44", "Львів", "https://maps.google.com/?cid=1",
    )
    assert (bare.type_name, bare.city, bare.maps_url) == (None, None, None)
    assert "places.googleMapsUri" in mask[0]
    assert not {"places.rating", "places.priceRange", "places.regularOpeningHours"} & set(mask[0].split(","))


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

    async def search(self, latitude, longitude, place_filter, radius_m=None):
        self.calls += 1
        self.radius_m = radius_m
        if self.fails:
            raise ServiceUnavailableError("down")
        return self.candidates


def location_service(transaction, candidates=(), fails=False, linked=(), mcc_type=FOOD):
    fake_places = FakePlaces(candidates, fails)
    service = TransactionLocationService(FakeDb(), 5, fake_places)
    calls = {"upserted": [], "links": [], "unlinks": [], "places": fake_places}

    async def get_by_id_for_user(transaction_id, user_id):
        return transaction if transaction and transaction_id == transaction.id and user_id == 5 else None

    async def get_mcc(mcc):
        return mcc_type

    async def list_near(merchant_key, latitude, longitude, radius_m):
        return list(linked)

    async def link(merchant_key, place_id):
        calls["links"].append((merchant_key, place_id))

    async def unlink(merchant_key, place_id):
        calls["unlinks"].append((merchant_key, place_id))

    async def upsert(place):
        calls["upserted"].append(place)
        return SimpleNamespace(id=99, latitude=place.latitude, longitude=place.longitude, name=place.name)

    service.transactions = SimpleNamespace(get_by_id_for_user=get_by_id_for_user)
    service.mcc_types = SimpleNamespace(get=get_mcc)
    service.links = SimpleNamespace(list_near=list_near, link=link, unlink=unlink)
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


def located(place=None):
    tx = transaction()
    tx.latitude, tx.longitude, tx.place, tx.place_confirmed = LAT, LON, place, None
    return tx


async def test_candidates_are_searched_around_transaction():
    service, calls = location_service(located(), candidates=[found("Кава")])
    assert [p.name for p in await service.place_candidates(1)] == ["Кава"]
    assert calls["places"].radius_m == 50


async def test_candidates_need_location():
    service, _ = location_service(transaction())
    with pytest.raises(InvalidRequestError):
        await service.place_candidates(1)


async def test_confirmed_place_is_linked():
    tx = located(SimpleNamespace(id=7))
    service, calls = location_service(tx)
    await service.give_feedback(1, correct=True)
    assert (tx.place_confirmed, calls["links"], service.db.commits) == (True, [("kredens cafe", 7)], 1)


async def test_rejected_place_is_kept_but_unlinked():
    wrong = SimpleNamespace(id=7)
    tx = located(wrong)
    service, calls = location_service(tx)
    await service.give_feedback(1, correct=False)
    assert (tx.place, tx.place_confirmed, calls["unlinks"], calls["links"]) == (wrong, False, [("kredens cafe", 7)], [])


async def test_rejected_place_replaced_by_chosen_candidate():
    tx = located(SimpleNamespace(id=7))
    service, calls = location_service(tx, candidates=[found("Сусід"), found("KREDENS CAFE")])
    await service.give_feedback(1, correct=False, place_id="GKREDENS CAFE")
    assert (tx.place.id, tx.place.name, tx.place_confirmed) == (99, "KREDENS CAFE", False)
    assert (calls["unlinks"], calls["links"]) == ([("kredens cafe", 7)], [("kredens cafe", 99)])


async def test_feedback_validation():
    service, _ = location_service(located(None))
    with pytest.raises(InvalidRequestError):
        await service.give_feedback(1, correct=True)
    service, _ = location_service(located(SimpleNamespace(id=7)), candidates=[found("Кава")])
    with pytest.raises(InvalidRequestError):
        await service.give_feedback(1, correct=False, place_id="Gчужий")
    with pytest.raises(InvalidRequestError):
        await service.give_feedback(1, correct=True, place_id="GКава")


async def test_spending_query_skips_rejected_places_and_income():
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(all=lambda: [("place", 12000, 3, 1_800_000_000)])

    rows = await PlaceRepository(SimpleNamespace(execute=execute)).spending_for_user(5, 100, 200, place_id=7)
    assert rows == [("place", 12000, 3, 1_800_000_000)]
    sql = statements[0]
    assert "transactions.amount_uah < 0" in sql
    assert "transactions.place_confirmed IS NOT false" in sql
    assert "places.id = 7" in sql and "transactions.time >= 100" in sql and "transactions.time <= 200" in sql
    assert "ORDER BY sum(-transactions.amount_uah) DESC" in sql
