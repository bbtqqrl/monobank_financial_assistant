import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

MILLION = Decimal(1_000_000)
CACHE_WRITE_MULTIPLIER = Decimal("1.25")
CACHE_READ_MULTIPLIER = Decimal("0.1")
BATCH_MULTIPLIER = Decimal("0.5")


@dataclass(frozen=True)
class ModelPrice:
    input: Decimal
    output: Decimal
    long_input: Decimal
    long_output: Decimal
    long_context_threshold: int


PRICES = {
    "claude-haiku-5-5": ModelPrice(
        input=Decimal("0.10"),
        output=Decimal("0.50"),
        long_input=Decimal("0.50"),
        long_output=Decimal("2.50"),
        long_context_threshold=100_000,
    ),
}


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_write_tokens: int,
    is_batch: bool = False,
) -> Decimal:
    price = PRICES.get(model)
    if price is None:
        logger.warning("No price for model %r, cost recorded as 0", model)
        return Decimal(0)

    prompt_tokens = input_tokens + cache_read_tokens + cache_write_tokens
    is_long = prompt_tokens > price.long_context_threshold
    input_price = price.long_input if is_long else price.input
    output_price = price.long_output if is_long else price.output

    cost = (
        input_tokens * input_price
        + cache_write_tokens * input_price * CACHE_WRITE_MULTIPLIER
        + cache_read_tokens * input_price * CACHE_READ_MULTIPLIER
        + output_tokens * output_price
    ) / MILLION
    if is_batch:
        cost *= BATCH_MULTIPLIER
    return cost.quantize(Decimal("0.000001"))
