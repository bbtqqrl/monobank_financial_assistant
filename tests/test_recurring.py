from datetime import datetime
from itertools import count
from types import SimpleNamespace

from app.services.recurring_detection import (
    KYIV_TZ,
    REGULAR,
    SUBSCRIPTION,
    Charge,
    cluster_charges,
    detect_kind,
    monthly_amount,
    payment_state,
    typical_amounts,
)
from app.services.recurring_service import RecurringService, state

NOW = int(datetime(2026, 10, 29, 12, tzinfo=KYIV_TZ).timestamp())
ids = count(1)


def ts(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(hour=12, tzinfo=KYIV_TZ).timestamp())


def charges(name, days_amounts, mcc, slug, parent=None, currency=980, rate=1):
    return [
        Charge(
            transaction_id=next(ids), time=ts(day), merchant_key=name.lower(), description=name, mcc=mcc,
            category_id=1, category_slug=slug, parent_slug=parent, currency_code=currency,
            amount=amount, amount_uah=amount * rate,
        )
        for day, amount in days_amounts
    ]


def kinds(items, declined=None):
    return [detect_kind(cluster, declined) for cluster in cluster_charges(items)]


def single(items, declined=None):
    clusters = cluster_charges(items)
    assert len(clusters) == 1
    return clusters[0], detect_kind(clusters[0], declined)


SUBS = "onlain-servisy-ta-pidpysky"
SPOTIFY = charges("Spotify", [("2026-04-28", 499), ("2026-05-30", 499), ("2026-06-28", 499), ("2026-07-28", 499)],
                  5815, SUBS, currency=840, rate=45)
FRIENDLY = charges("Friendly Share", [("2026-08-11", 12900), ("2026-09-11", 12900), ("2026-10-11", 12900)], 5968, SUBS)
VODAFONE = charges("Vodafone", [("2026-05-14", 21200), ("2026-06-18", 26000), ("2026-07-19", 26000),
                                ("2026-08-20", 26000), ("2026-09-20", 26000), ("2026-09-20", 2300),
                                ("2026-10-21", 26000)], 4814, "mobilnyi-zviazok", "komunalni-posluhy")
INTERNET = charges("Інтернет і ТБ", [("2026-04-27", 37000), ("2026-05-22", 50840), ("2026-08-01", 50000),
                                     ("2026-10-01", 20000)], 4900, "internet", "komunalni-posluhy")


def test_two_monthly_charges_with_same_amount_make_a_subscription():
    cluster, kind = single(charges("Claude", [("2026-09-20", 2400), ("2026-10-22", 2400)], 5734, SUBS, currency=840))
    assert kind == SUBSCRIPTION
    assert payment_state(cluster.last.time, cluster.period_days, kind, NOW) == "active"


def test_single_charges_and_top_ups_are_not_subscriptions():
    assert kinds(charges("Anthropic", [("2026-09-05", 1200)], 5734, SUBS, currency=840)) == [None]
    assert kinds(charges("DeepSeek", [("2026-08-01", 530), ("2026-10-14", 530)], 4816, SUBS, currency=840)) == [None]


def test_usage_billing_with_changing_amount_is_not_a_subscription():
    aws = charges("AWS EMEA", [("2026-09-02", 1705), ("2026-10-02", 1655)], 7399, SUBS, currency=840)
    assert kinds(aws) == [None]


def test_two_apple_subscriptions_split_by_amount():
    items = charges("Apple", [("2026-09-03", 4900), ("2026-09-03", 19900), ("2026-10-03", 19900), ("2026-10-03", 4900)],
                    5818, SUBS)
    clusters = cluster_charges(items)
    assert sorted(c.last.amount for c in clusters) == [4900, 19900]
    assert all(detect_kind(c) == SUBSCRIPTION for c in clusters)


def test_price_increase_on_schedule_stays_the_same_subscription():
    cluster, kind = single(charges("Netflix", [("2026-07-05", 25000), ("2026-08-05", 25000), ("2026-09-05", 32000)],
                                   4899, SUBS))
    assert kind == SUBSCRIPTION and typical_amounts(cluster, kind)[0] == 32000


def test_subscription_gets_mark_then_hides_unless_confirmed():
    last = ts("2026-09-10")
    assert payment_state(last, 30, SUBSCRIPTION, NOW) == "missing"
    cluster, kind = single(SPOTIFY)
    assert kind == SUBSCRIPTION
    assert payment_state(cluster.last.time, cluster.period_days, kind, NOW) == "inactive"
    assert payment_state(cluster.last.time, cluster.period_days, kind, NOW, confirmed=True) == "missing"


def test_vodafone_is_regular_with_outlier_kept():
    cluster, kind = single(VODAFONE)
    assert kind == REGULAR
    assert typical_amounts(cluster, kind)[0] == 26000


def test_internet_every_two_months_is_regular():
    cluster, kind = single(INTERNET)
    assert kind == REGULAR
    assert cluster.period_days == 61
    assert typical_amounts(cluster, kind)[0] == 50000
    assert monthly_amount(50000, 61) == 25000
    assert monthly_amount(240000, 32) == 240000
    assert payment_state(cluster.last.time, cluster.period_days, kind, NOW) == "active"


def test_games_transfers_and_groceries_are_never_regular():
    steam = charges("Steam", [("2026-07-19", 17300), ("2026-08-19", 17300), ("2026-09-19", 17300)], 5816, "ihry", "rozvahy")
    person = charges("Катерина Г.", [("2026-08-10", 10000), ("2026-09-10", 10000), ("2026-10-10", 10000)], 4829,
                     "perekazy-liudiam")
    shop = charges("Близенько", [(f"2026-{m:02d}-{d:02d}", 5000) for m in (8, 9, 10) for d in (3, 17)], 5499, "produkty")
    assert set(kinds(steam) + kinds(person) + kinds(shop)) == {None}


def test_frequent_unstable_or_rare_payments_are_not_regular():
    frequent = charges("Кіно", [(f"2026-{m:02d}-{d:02d}", 20000) for m in (9, 10) for d in (2, 9, 16)], 7832, "kino", "rozvahy")
    unstable = charges("Нова пошта", [("2026-08-01", 2300), ("2026-09-01", 9000), ("2026-10-01", 18300)], 4215,
                       "poshta-ta-dostavka")
    rare = charges("EVA", [("2026-07-01", 20000), ("2026-09-24", 20500)], 5977, "krasa-ta-hihiiena")
    assert set(kinds(frequent) + kinds(unstable) + kinds(rare)) == {None}


def test_declined_subscription_falls_back_to_regular():
    cluster, _ = single(FRIENDLY)
    assert detect_kind(cluster, SUBSCRIPTION) == REGULAR
    assert detect_kind(cluster, REGULAR) is None


def test_cancelled_subscription_hides_even_if_confirmed():
    row = SimpleNamespace(last_charge_at=ts("2026-07-01"), period_days=30, kind=SUBSCRIPTION, user_kind=SUBSCRIPTION,
                          cancelled_at=None)
    assert state(row, NOW) == "missing"
    row.cancelled_at = ts("2026-07-10")
    assert state(row, NOW) == "inactive"


def test_regular_goes_inactive():
    assert payment_state(ts("2026-07-01"), 30, REGULAR, NOW) == "inactive"


class FakeRepo:

    def __init__(self, items, rows=()):
        self.items = items
        self.rows = list(rows)
        self.links = {}

    async def lock_user(self, user_id):
        return None

    async def charges(self, user_id, since):
        return self.items

    async def list_for_user(self, user_id):
        return list(self.rows)

    async def unlink_except(self, user_id, keep_ids):
        self.links = {k: v for k, v in self.links.items() if k in keep_ids}

    async def link(self, transaction_ids, payment_id):
        self.links.update({transaction_id: payment_id for transaction_id in transaction_ids})


def service(repo):
    new_ids = count(100)

    async def flush():
        for row in repo.rows:
            row.id = row.id or next(new_ids)

    async def noop():
        return None

    async def delete(row):
        repo.rows.remove(row)

    db = SimpleNamespace(add=repo.rows.append, delete=delete, flush=flush, commit=noop)
    result = RecurringService(db)
    result.repo = repo
    return result


async def test_refresh_creates_links_and_keeps_user_decisions():
    repo = FakeRepo(SPOTIFY + FRIENDLY + VODAFONE)
    created = await service(repo).refresh(5, NOW)
    by_name = {row.name: row for row in created}
    assert set(by_name) == {"Friendly Share", "Vodafone"}
    assert repo.links[VODAFONE[0].transaction_id] == by_name["Vodafone"].id

    friendly = by_name["Friendly Share"]
    friendly.declined_kind = SUBSCRIPTION
    assert await service(repo).refresh(5, NOW) == []
    assert friendly.kind == REGULAR and friendly in repo.rows

    repo.items = VODAFONE
    await service(repo).refresh(5, NOW)
    assert friendly in repo.rows and friendly.kind is None
    assert FRIENDLY[0].transaction_id not in repo.links

    repo.items = []
    await service(repo).refresh(5, NOW)
    assert by_name["Vodafone"] not in repo.rows


async def test_assistant_tool_splits_totals_by_kind(monkeypatch):
    from app.services.assistant import tools

    def row(id, kind, name, amount, last, cancelled_at=None):
        return SimpleNamespace(
            id=id, kind=kind, name=name, category=None, mcc=None, currency_code=980, amount=amount, amount_uah=amount,
            period_days=30, first_charge_at=ts(last), last_charge_at=ts(last), charges_count=3, user_kind=None,
            cancelled_at=cancelled_at,
        )

    rows = [
        row(1, SUBSCRIPTION, "Claude", 108000, "2026-10-22"),
        row(2, SUBSCRIPTION, "Old", 5000, "2026-10-01", cancelled_at=ts("2026-10-05")),
        row(3, REGULAR, "Vodafone", 26000, "2026-10-21"),
    ]

    async def fake_list(self, user_id, kind=None, now=None):
        return [r for r in rows if kind is None or r.kind == kind]

    monkeypatch.setattr(RecurringService, "list", fake_list)
    ctx = tools.ToolContext(db=None, user_id=5, timezone="Europe/Kyiv")
    result = await tools.get_recurring(ctx, tools.RecurringArgs())
    assert (result["subscription_monthly"], result["regular_monthly"]) == (108000, 26000)
    assert result["items"][0]["name"] == "Claude" and result["items"][0]["next_charge"] == "2026-11-21"
    only_regular = await tools.get_recurring(ctx, tools.RecurringArgs(kind="regular"))
    assert set(only_regular) == {"regular_monthly", "items"} and len(only_regular["items"]) == 1
