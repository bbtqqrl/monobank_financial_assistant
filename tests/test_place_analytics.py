from datetime import date
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.dialects import postgresql

from app.repositories.analytics import AnalyticsRepository, TransactionFilter
from app.services.analytics_service import AnalyticsService, Period
from app.services.assistant.tools import _transaction_item

PERIOD = Period(date(2026, 10, 1), date(2026, 10, 31))


class FakeRepo:
    def __init__(self):
        self.filters = []

    async def aggregate(self, user_id, filters, timezone, group_by=None, metrics=None):
        self.filters.append(filters)
        if group_by == ["place"]:
            return [
                {"place_id": 1, "place_name": "Рукавичка", "place_type": "Супермаркет", "place_city": "Львів",
                 "sum": -30000, "count": 3},
                {"place_id": 2, "place_name": "KREDENS", "place_type": "Кав'ярня", "place_city": "Львів",
                 "sum": -50000, "count": 1},
                {"place_id": 3, "place_name": "Повернення", "place_type": None, "place_city": "Львів",
                 "sum": 4000, "count": 1},
                {"place_id": None, "place_name": None, "place_type": None, "place_city": None,
                 "sum": -20000, "count": 4},
            ]
        if group_by == ["city"]:
            return [{"city": "Львів", "sum": -80000, "count": 4}, {"city": None, "sum": -20000, "count": 4}]
        return [{"sum": -100000, "count": 8}]


def service(**scope):
    analytics = AnalyticsService(None, 5, "Europe/Kyiv", **scope)
    analytics.repo = FakeRepo()
    return analytics


async def test_places_are_sorted_and_unlocated_is_the_rest():
    result = await service().places(PERIOD, limit=10, offset=0)
    assert [(item.name, item.amount, item.share) for item in result.items] == [
        ("KREDENS", 50000, 50.0), ("Рукавичка", 30000, 30.0),
    ]
    assert (result.total, result.unlocated_amount, result.place_count) == (100000, 20000, 2)


async def test_cities_skip_transactions_without_place():
    result = await service().cities(PERIOD)
    assert [(item.city, item.amount, item.transaction_count) for item in result.items] == [("Львів", 80000, 4)]
    assert result.unlocated_amount == 20000


async def test_place_and_city_scope_reaches_every_query():
    analytics = service(place_ids=[1], cities=["Львів"])
    await analytics.places(PERIOD, limit=10, offset=0)
    assert all(f.place_ids == [1] and f.cities == ["Львів"] for f in analytics.repo.filters)


async def test_place_filters_compile_with_rejected_places_excluded():
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect())))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))

    repo = AnalyticsRepository(SimpleNamespace(execute=execute))
    await repo.aggregate(5, TransactionFilter(place_ids=[1], cities=["Львів"]), "Europe/Kyiv", group_by=["city"])
    sql = statements[0]
    assert "LEFT OUTER JOIN places ON places.id = transactions.place_id AND transactions.place_confirmed IS NOT false" in sql
    assert "places.id IN" in sql and "places.city IN" in sql and "GROUP BY places.city" in sql


def assistant_transaction(**overrides):
    values = {
        "id": 1, "time": 1_800_000_000, "description": "KREDENS", "amount": -8000, "currency_code": 980,
        "operation_amount": None, "amount_uah": -8000, "account_id": 2, "jar_id": None, "source": "monobank",
        "comment": None, "place_confirmed": None,
        "place": SimpleNamespace(id=7, name="KREDENS CAFE", type_name="Кав'ярня", city="Львів"),
    }
    return SimpleNamespace(**{**values, **overrides})


def test_assistant_sees_place_unless_rejected():
    zone = ZoneInfo("Europe/Kyiv")
    item = _transaction_item(assistant_transaction(), None, 980, zone)
    assert item["place"] == {"id": 7, "name": "KREDENS CAFE", "type": "Кав'ярня", "city": "Львів"}
    assert "place" not in _transaction_item(assistant_transaction(place_confirmed=False), None, 980, zone)
    assert "place" not in _transaction_item(assistant_transaction(place=None), None, 980, zone)
