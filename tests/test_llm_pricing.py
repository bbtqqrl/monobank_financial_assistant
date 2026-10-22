from decimal import Decimal

from app.services.llm.pricing import cost_usd

MODEL = "claude-haiku-5-5"


def test_regular_prompt():
    assert cost_usd(MODEL, 120, 40, 3000, 0) == Decimal("0.000062")


def test_cache_write_costs_more_than_input():
    assert cost_usd(MODEL, 0, 0, 0, 50_000) == Decimal("0.00625")


def test_long_context_price_applies_to_whole_prompt():
    assert cost_usd(MODEL, 90_000, 1000, 20_000, 0) == Decimal("0.0485")


def test_batch_is_half_price():
    assert cost_usd(MODEL, 1000, 1000, 0, 0, is_batch=True) == Decimal("0.0003")


def test_unknown_model_costs_nothing():
    assert cost_usd("some-other-model", 1000, 1000, 0, 0) == Decimal(0)
