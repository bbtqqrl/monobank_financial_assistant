from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.repositories.place import PlaceRepository
from app.services.home_location import HomeService, infer_home
from app.services.places import distance_m

HOME = (49.84951, 24.00707)
OFFICE = (49.8397, 24.0316)


def around(center, count, step=0.0001):
    return [(center[0] + (i % 3 - 1) * step, center[1] + (i // 3 - 1) * step) for i in range(count)]


def test_home_is_the_densest_cluster():
    points = around(HOME, 8) + around(OFFICE, 5) + [(50.45, 30.52), (48.92, 24.71)]
    found = infer_home(points)
    assert distance_m(*found, *HOME) < 15


def test_no_home_without_enough_close_points():
    assert infer_home(around(HOME, 4)) is None
    assert infer_home([(HOME[0] + i * 0.01, HOME[1]) for i in range(10)]) is None


def home_service(user, points=()):
    service = HomeService(SimpleNamespace(commit=_noop), user)

    async def unplaced_points(user_id, since, limit):
        return list(points)

    service.places = SimpleNamespace(unplaced_points=unplaced_points)
    return service


async def _noop():
    return None


async def test_user_home_wins_over_auto():
    user = SimpleNamespace(id=5, home_latitude=50.0, home_longitude=30.0)
    home = await home_service(user, around(HOME, 8)).location()
    assert (home.latitude, home.longitude, home.source) == (50.0, 30.0, "user")


async def test_auto_home_and_reset():
    user = SimpleNamespace(id=5, home_latitude=50.0, home_longitude=30.0)
    service = home_service(user, around(HOME, 8))
    await service.reset()
    home = await service.location()
    assert home.source == "auto" and distance_m(home.latitude, home.longitude, *HOME) < 15
    assert await home_service(SimpleNamespace(id=5, home_latitude=None, home_longitude=None)).location() is None


async def test_home_spending_and_places_split_by_category():
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(all=lambda: [])

    repo = PlaceRepository(SimpleNamespace(execute=execute))
    await repo.home_spending(5, 100, 200)
    await repo.spending_for_user(5)
    home_sql, places_sql = statements
    assert "categories.slug IN ('onlain-servisy-ta-pidpysky', 'dostavka-izhi', 'marketpleisy')" in home_sql
    assert "categories.slug NOT IN ('onlain-servisy-ta-pidpysky', 'dostavka-izhi', 'marketpleisy')" in places_sql


def test_home_does_not_drift_towards_a_shop_nearby():
    shop = (HOME[0] + 0.0007, HOME[1])
    found = infer_home(around(HOME, 8, step=0.00008) + around(shop, 6, step=0.00008))
    assert distance_m(*found, *HOME) < 5


async def test_place_transactions_hide_rejected_and_home_categories():
    from app.repositories.transaction import TransactionRepository
    statements = []

    async def execute(statement):
        statements.append(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(scalar_one=lambda: 0, all=lambda: [])

    await TransactionRepository(SimpleNamespace(execute=execute)).list_for_user(5, place_id=7)
    sql = statements[-1]
    assert "transactions.place_id = 7" in sql and "transactions.place_confirmed IS NOT false" in sql
    assert "categories.slug NOT IN ('onlain-servisy-ta-pidpysky', 'dostavka-izhi', 'marketpleisy')" in sql
