from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.services import transaction_pipeline as pipeline
from app.services.categorization_service import CategorizationService

NOW = 1_800_000_000


def purchase(**overrides):
    values = {"id": 1, "user_id": 5, "source": "monobank", "amount": -8000, "mcc": 5814, "counter_iban": None,
              "latitude": None, "time": NOW - 5}
    return SimpleNamespace(**{**values, **overrides})


def test_needs_location_only_for_fresh_card_purchases():
    assert pipeline.needs_location(purchase(), NOW)
    assert not pipeline.needs_location(purchase(amount=5000), NOW)
    assert not pipeline.needs_location(purchase(mcc=None), NOW)
    assert not pipeline.needs_location(purchase(counter_iban="UA00"), NOW)
    assert not pipeline.needs_location(purchase(source="manual"), NOW)
    assert not pipeline.needs_location(purchase(latitude=49.8), NOW)
    assert not pipeline.needs_location(purchase(time=NOW - 3600), NOW)


def patch_pipeline(monkeypatch, transaction, push_ok):
    calls = {"push": [], "now": [], "later": []}

    @asynccontextmanager
    async def session():
        yield SimpleNamespace()

    class Repo:
        def __init__(self, db):
            pass

        async def get_by_id(self, transaction_id):
            return transaction

    class Push:
        def __init__(self, db):
            pass

        async def send_silent(self, user_id, data):
            calls["push"].append((user_id, data))
            return push_ok

    async def run_now(transaction_id):
        calls["now"].append(transaction_id)

    async def later(transaction_id, delay):
        calls["later"].append((transaction_id, delay))

    monkeypatch.setattr(pipeline, "SessionLocal", session)
    monkeypatch.setattr(pipeline, "TransactionRepository", Repo)
    monkeypatch.setattr(pipeline, "PushService", Push)
    monkeypatch.setattr(pipeline, "run_categorization", run_now)
    monkeypatch.setattr(pipeline, "_categorize_later", later)
    monkeypatch.setattr(pipeline, "spawn", lambda coro: coro.close() or calls["later"].append("spawned"))
    monkeypatch.setattr(pipeline.time, "time", lambda: NOW)
    return calls


async def test_purchase_waits_for_location(monkeypatch):
    calls = patch_pipeline(monkeypatch, purchase(), push_ok=True)
    await pipeline.process_new_transaction(1)
    assert calls["push"] == [(5, {"type": "location_request", "transaction_id": 1})]
    assert calls["now"] == []
    assert calls["later"] == ["spawned"]


async def test_no_device_categorizes_right_away(monkeypatch):
    calls = patch_pipeline(monkeypatch, purchase(), push_ok=False)
    await pipeline.process_new_transaction(1)
    assert calls["now"] == [1]


async def test_transfer_skips_location(monkeypatch):
    calls = patch_pipeline(monkeypatch, purchase(counter_iban="UA00"), push_ok=True)
    await pipeline.process_new_transaction(1)
    assert (calls["push"], calls["now"]) == ([], [1])


async def test_place_becomes_categorization_hint():
    service = CategorizationService.__new__(CategorizationService)
    place = SimpleNamespace(name="Каву єнайдено", category="coffee_shop", address="вулиця Шевченка, 44, Львів")
    transaction = SimpleNamespace(jar_id=None, account_id=None, counter_iban=None, place=place)
    hints = await service._build_hints(transaction)
    assert hints == [
        "The phone was at «Каву єнайдено» (place type: coffee_shop, вулиця Шевченка, 44, Львів) "
        "when this payment happened - most likely that is where the money was spent."
    ]
