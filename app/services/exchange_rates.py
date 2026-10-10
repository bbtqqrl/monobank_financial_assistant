import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from app.core.currencies import ISO_ALPHA, known_amount_uah

logger = logging.getLogger(__name__)

NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"
KYIV_TZ = ZoneInfo("Europe/Kyiv")

_rates: dict[tuple[int, date], float] = {}


async def nbu_rate(currency: int, on: date) -> float | None:
    key = (currency, on)
    if key in _rates:
        return _rates[key]

    code = ISO_ALPHA.get(currency)
    if code is None:
        logger.warning("No ISO alpha code for currency %s, cannot fetch NBU rate", currency)
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(NBU_URL, params={"valcode": code, "date": on.strftime("%Y%m%d"), "json": ""})
            response.raise_for_status()
            data = response.json()
    except Exception:
        logger.warning("Failed to fetch NBU rate for %s on %s", code, on, exc_info=True)
        return None

    if not data:
        logger.warning("NBU has no rate for %s on %s", code, on)
        return None

    rate = float(data[0]["rate"])
    _rates[key] = rate
    return rate


async def amount_uah(
    amount: int, operation_amount: int | None, currency: int, operation_currency: int, time: int,
) -> int | None:
    known = known_amount_uah(amount, operation_amount, currency, operation_currency)
    if known is not None:
        return known

    rate = await nbu_rate(currency, datetime.fromtimestamp(time, KYIV_TZ).date())
    if rate is None:
        return None
    return round(amount * rate)
