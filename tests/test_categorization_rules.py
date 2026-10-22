from types import SimpleNamespace

import pytest

from app.core.currencies import alpha_code, known_amount_uah
from app.services.categorization_service import (
    PERSON_IN_SLUG,
    PERSON_OUT_SLUG,
    CategoryDirectionError,
    _mapping_fits_direction,
    _person_transfer_slug,
    check_category_fits_amount,
)
from app.services.merchant_key import build_merchant_key


def test_income_category_rejects_outgoing_money():
    with pytest.raises(CategoryDirectionError):
        check_category_fits_amount("income", -100)
    check_category_fits_amount("expense", 100)
    check_category_fits_amount("income", 100)


@pytest.mark.parametrize(
    ("kind", "amount", "fits"),
    [("expense", -100, True), ("expense", 100, False), ("income", 100, True), ("income", -100, False), ("transfer", 5, True)],
)
def test_mapping_direction(kind, amount, fits):
    assert _mapping_fits_direction(kind, amount) is fits


@pytest.mark.parametrize(
    ("mcc", "amount", "description", "slug"),
    [
        (4829, 50000, "Від: Олена Петренко", PERSON_IN_SLUG),
        (4829, -50000, "Олена П.", PERSON_OUT_SLUG),
        (4829, -50000, "Сільпо", None),
        (5411, -50000, "Олена П.", None),
        (4829, 50000, "Від: monobank", None),
    ],
)
def test_person_transfer_rule(mcc, amount, description, slug):
    transaction = SimpleNamespace(mcc=mcc, amount=amount, description=description)
    assert _person_transfer_slug(transaction) == slug


def test_merchant_key_drops_digits_and_noise():
    assert build_merchant_key("  061 SUPER-PHARM POLAND A ") == "super pharm poland a"
    assert build_merchant_key("Сільпо #123") == "сільпо"


def test_amount_in_uah():
    assert known_amount_uah(-1000, -40, 980, 985) == -1000
    assert known_amount_uah(-10, -500, 978, 980) == -500
    assert known_amount_uah(-10, -12, 978, 840) is None


def test_currency_letters():
    assert alpha_code(985) == "PLN"
    assert alpha_code(999) == "999"
