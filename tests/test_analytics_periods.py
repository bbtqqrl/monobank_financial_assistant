from datetime import date

import pytest

from app.services.analytics_service import (
    PeriodError,
    add_months,
    change_pct,
    format_uah,
    growth_streak,
    is_stable,
    resolve_comparison,
    resolve_period,
    share,
)

TODAY = date(2026, 10, 22)


def test_default_period_is_last_30_days():
    period = resolve_period(TODAY, None, None, None)
    assert (period.start, period.end, period.days) == (date(2026, 9, 23), TODAY, 30)


def test_current_month_is_cut_at_today():
    period = resolve_period(TODAY, "2026-10", None, None)
    assert (period.start, period.end) == (date(2026, 10, 1), TODAY)


def test_past_month_is_full():
    period = resolve_period(TODAY, "2026-02", None, None)
    assert (period.start, period.end) == (date(2026, 2, 1), date(2026, 2, 28))


@pytest.mark.parametrize(
    ("month", "date_from", "date_to", "message"),
    [
        ("2026-09", date(2026, 9, 1), date(2026, 9, 5), "either month or from/to"),
        (None, date(2026, 9, 1), None, "given together"),
        (None, date(2026, 9, 5), date(2026, 9, 1), "must not be after"),
        ("2027-03", None, None, "in the future"),
        (None, date(2020, 1, 1), date(2026, 10, 1), "can't be longer"),
    ],
)
def test_invalid_periods(month, date_from, date_to, message):
    with pytest.raises(PeriodError, match=message):
        resolve_period(TODAY, month, date_from, date_to)


def test_previous_period_has_same_length():
    period = resolve_period(TODAY, None, date(2026, 10, 17), date(2026, 10, 18))
    comparison = resolve_comparison(period, "previous_period", None, None)
    assert (comparison.period.start, comparison.period.end, comparison.scaled) == (
        date(2026, 10, 15), date(2026, 10, 16), False,
    )


def test_previous_month_for_partial_month_takes_same_days():
    period = resolve_period(TODAY, "2026-10", None, None)
    comparison = resolve_comparison(period, "previous_month", None, None)
    assert (comparison.period.start, comparison.period.end) == (date(2026, 9, 1), date(2026, 9, 22))


def test_previous_month_for_full_month_takes_whole_month():
    period = resolve_period(TODAY, "2026-09", None, None)
    comparison = resolve_comparison(period, "previous_month", None, None)
    assert (comparison.period.start, comparison.period.end) == (date(2026, 8, 1), date(2026, 8, 31))


def test_long_presets_are_scaled():
    period = resolve_period(TODAY, "2026-09", None, None)
    comparison = resolve_comparison(period, "last_3_months", None, None)
    assert (comparison.period.start, comparison.period.end, comparison.scaled) == (
        date(2026, 6, 1), date(2026, 8, 31), True,
    )


def test_custom_comparison_overrides_preset():
    period = resolve_period(TODAY, "2026-09", None, None)
    comparison = resolve_comparison(period, "year_ago", date(2026, 1, 1), date(2026, 1, 31))
    assert (comparison.type, comparison.period.start, comparison.scaled) == ("custom", date(2026, 1, 1), True)


def test_add_months_clamps_day():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 3, 15), -12) == date(2025, 3, 15)


def test_number_helpers():
    assert change_pct(150, 100) == 50.0
    assert change_pct(100, 0) is None
    assert share(25, 200) == 12.5
    assert share(10, 0) == 0.0
    assert format_uah(1248060) == "12 481 ₴"
    assert growth_streak([1, 2, 3, 4]) == 3
    assert growth_streak([5, 1, 2]) == 1
    assert growth_streak([3, 2]) == 0


@pytest.mark.parametrize(
    ("amounts", "typical", "expected"),
    [
        ([26000, 26000, 26000, 50000], 26000, True),
        ([26000, 50000, 50000, 26000], 38000, False),
        ([10000, 20000, 30000], 20000, False),
        ([0, 0], 0, False),
    ],
)
def test_is_stable(amounts, typical, expected):
    assert is_stable(amounts, typical) is expected
