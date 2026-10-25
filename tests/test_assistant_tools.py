import json
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.services.analytics_service import Period, PeriodError
from app.services.assistant.tools import (
    MEMORY_TOOLS,
    READ_TOOLS,
    CompareArgs,
    Tool,
    ToolContext,
    ToolRegistry,
    _comparison,
    _to_major_units,
)

CTX = ToolContext(db=None, user_id=1, timezone="Europe/Kyiv")


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


async def echo(ctx, args):
    return {"amount": args.value, "count": args.value}


async def period_error(ctx, args):
    raise PeriodError("The period is in the future")


async def crash(ctx, args):
    raise RuntimeError("database is down")


REGISTRY = ToolRegistry((
    Tool("echo", "Echo", "", EchoArgs, echo),
    Tool("period_error", "Period", "", EchoArgs, period_error),
    Tool("crash", "Crash", "", EchoArgs, crash),
))


def test_money_is_converted_to_major_units_recursively():
    data = {
        "total": 1248050,
        "transaction_count": 12,
        "share": 33.3,
        "items": [{"amount": -39596, "operation_amount": -3300, "id": 5}],
        "comparison": {"expected": 100, "days": 30},
    }
    assert _to_major_units(data) == {
        "total": 12480.5,
        "transaction_count": 12,
        "share": 33.3,
        "items": [{"amount": -395.96, "operation_amount": -33.0, "id": 5}],
        "comparison": {"expected": 1.0, "days": 30},
    }


async def test_successful_tool_returns_json_in_major_units():
    content, is_error = await REGISTRY.run(CTX, "echo", {"value": 1050})
    assert not is_error
    assert json.loads(content) == {"amount": 10.5, "count": 1050}


async def test_invalid_and_extra_arguments_are_errors():
    content, is_error = await REGISTRY.run(CTX, "echo", {"value": "abc"})
    assert is_error and "Invalid arguments" in content
    content, is_error = await REGISTRY.run(CTX, "echo", {"value": 1, "user_id": 6})
    assert is_error and "extra_forbidden" in content


async def test_expected_errors_reach_the_model():
    assert await REGISTRY.run(CTX, "period_error", {"value": 1}) == ("The period is in the future", True)
    assert await REGISTRY.run(CTX, "missing", {}) == ("Unknown tool: missing", True)


async def test_unexpected_errors_are_hidden():
    content, is_error = await REGISTRY.run(CTX, "crash", {"value": 1})
    assert is_error and "database" not in content


def test_month_compares_with_previous_month_by_default():
    period = Period(date(2026, 10, 1), date(2026, 10, 22))
    assert _comparison(period, CompareArgs(month="2026-10")).type == "previous_month"
    assert _comparison(period, CompareArgs(date_from=period.start, date_to=period.end)).type == "previous_period"


def test_tools_have_unique_names_and_object_schemas():
    names = [tool.name for tool in READ_TOOLS + MEMORY_TOOLS]
    assert len(names) == len(set(names))
    for tool in READ_TOOLS + MEMORY_TOOLS:
        definition = tool.definition()
        assert definition["input_schema"]["type"] == "object"
        assert "user_id" not in json.dumps(definition["input_schema"])
