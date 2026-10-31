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


def trip_row(day, place_id, name, city, amount, count=1):
    return {"day": day, "place_id": place_id, "place_name": name, "place_type": None, "place_city": city,
            "sum": -amount, "count": count}


class TripRepo:
    def __init__(self, rows, home_days):
        self.rows = rows
        self.home_days = home_days
        self.calls = []

    async def aggregate(self, user_id, filters, timezone, group_by=None, metrics=None):
        self.calls.append((group_by, filters))
        if group_by == ["day", "city"]:
            return self.home_days
        return self.rows


def trips_service(rows, home_days, **scope):
    analytics = AnalyticsService(None, 5, "Europe/Kyiv", **scope)
    analytics.repo = TripRepo(rows, home_days)
    return analytics


HOME_DAYS = [
    {"day": f"2026-09-{d:02d}", "city": "Київ", "count": 1} for d in range(1, 11)
] + [{"day": "2026-10-03", "city": "Львів", "count": 2}, {"day": None, "city": None, "count": 5}]


async def test_trips_split_by_gap_and_skip_home_city():
    rows = [
        trip_row("2026-10-03", 1, "KREDENS", "Львів", 30000),
        trip_row("2026-10-03", 2, "Рукавичка", "Львів", 10000, 2),
        trip_row("2026-10-05", 1, "KREDENS", "Львів", 20000),
        trip_row("2026-10-04", 9, "Сільпо", "Київ", 50000),
        trip_row("2026-10-20", 3, "Копальня", "Львів", 5000),
        trip_row("2026-10-10", 4, "Хінкальня", "Одеса", 70000),
        trip_row("2026-10-11", None, None, None, 99999),
    ]
    result = await trips_service(rows, HOME_DAYS).trips(PERIOD, "date")
    assert result.home_city == "Київ"
    assert [(t.city, t.start.day, t.end.day, t.days, t.amount, t.transaction_count) for t in result.items] == [
        ("Львів", 20, 20, 1, 5000, 1), ("Одеса", 10, 10, 1, 70000, 1), ("Львів", 3, 5, 3, 60000, 4),
    ]
    assert [(p.name, p.amount, p.transaction_count) for p in result.items[2].places] == [
        ("KREDENS", 50000, 2), ("Рукавичка", 10000, 2),
    ]


async def test_trip_breaks_after_more_than_two_empty_days():
    rows = [trip_row("2026-10-01", 1, "A", "Львів", 100), trip_row("2026-10-04", 1, "A", "Львів", 100),
            trip_row("2026-10-08", 1, "A", "Львів", 100)]
    result = await trips_service(rows, HOME_DAYS).trips(PERIOD, "date")
    assert [(t.start.day, t.end.day) for t in result.items] == [(8, 8), (1, 4)]


async def test_trips_sorting_and_refund_only_trip_is_skipped():
    rows = [
        trip_row("2026-10-03", 1, "A", "Львів", 30000),
        trip_row("2026-10-10", 2, "B", "Одеса", 70000),
        trip_row("2026-10-20", 3, "C", "Львів", 5000),
        trip_row("2026-10-25", 4, "D", "Ужгород", -3000),
    ]
    by_amount = await trips_service(rows, HOME_DAYS).trips(PERIOD, "amount")
    assert [(t.city, t.amount) for t in by_amount.items] == [("Одеса", 70000), ("Львів", 30000), ("Львів", 5000)]
    by_city = await trips_service(rows, HOME_DAYS).trips(PERIOD, "city")
    assert [(t.city, t.start.day) for t in by_city.items] == [("Львів", 20), ("Львів", 3), ("Одеса", 10)]


async def test_home_city_ignores_scope_and_is_none_without_places():
    analytics = trips_service([trip_row("2026-10-03", 1, "A", "Львів", 100)], [], account_ids=[2], cities=["Львів"])
    result = await analytics.trips(PERIOD, "date")
    assert result.home_city is None and [t.city for t in result.items] == ["Львів"]
    home_filter = next(f for group_by, f in analytics.repo.calls if group_by == ["day", "city"])
    assert home_filter.account_ids is None and home_filter.cities is None
    trips_filter = next(f for group_by, f in analytics.repo.calls if group_by == ["day", "place"])
    assert trips_filter.account_ids == [2] and trips_filter.cities == ["Львів"]


async def test_trip_queries_compile():
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect())))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))

    analytics = AnalyticsService(SimpleNamespace(execute=execute), 5, "Europe/Kyiv")
    result = await analytics.trips(PERIOD, "date")
    assert result.items == [] and len(statements) == 2
    assert "GROUP BY to_char" in statements[0] and "places.city" in statements[0]


async def test_trip_crossing_period_border_is_shown_whole():
    rows = [
        trip_row("2026-09-10", 1, "A", "Одеса", 100),
        trip_row("2026-09-29", 2, "B", "Львів", 100),
        trip_row("2026-10-02", 2, "B", "Львів", 300),
        trip_row("2026-10-30", 3, "C", "Ужгород", 100),
        trip_row("2026-11-01", 3, "C", "Ужгород", 100),
        trip_row("2026-11-05", 4, "D", "Одеса", 100),
    ]
    analytics = trips_service(rows, HOME_DAYS)
    result = await analytics.trips(PERIOD, "date")
    assert [(t.city, t.start, t.end, t.amount) for t in result.items] == [
        ("Ужгород", date(2026, 10, 30), date(2026, 11, 1), 200),
        ("Львів", date(2026, 9, 29), date(2026, 10, 2), 400),
    ]
    trips_filter = next(f for group_by, f in analytics.repo.calls if group_by == ["day", "place"])
    assert (trips_filter.date_from, trips_filter.date_to) == analytics._bounds(Period(date(2026, 8, 2), date(2026, 12, 30)))
