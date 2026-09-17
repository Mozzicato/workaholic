"""Token prices used to estimate benchmark cost.

Source: Azure Retail Prices API (https://prices.azure.com/api/retail/prices), region
francecentral, retrieved 2026-09-17. Standard processing, short context, USD per 1M tokens.
Reasoning tokens are billed as output tokens. Cached-input discounts are ignored, so
estimates err high. Re-check before relying on these numbers: prices change.
"""

from typing import Literal

PriceZone = Literal["global", "datazone"]

# (model, zone) -> (input USD per 1M tokens, output USD per 1M tokens)
PRICES_PER_MILLION: dict[tuple[str, PriceZone], tuple[float, float]] = {
    ("gpt-5-nano", "global"): (0.05, 0.40),
    ("gpt-5-nano", "datazone"): (0.055, 0.44),
    ("gpt-5-mini", "global"): (0.25, 2.00),
    ("gpt-5-mini", "datazone"): (0.275, 2.20),
    ("gpt-5.4-nano", "global"): (0.20, 1.25),
    ("gpt-5.4-mini", "global"): (0.75, 4.50),
    ("gpt-5.4-mini", "datazone"): (0.825, 4.95),
    ("gpt-5.6-luna", "global"): (0.20, 1.20),
    ("gpt-5.6-luna", "datazone"): (0.22, 1.32),
    ("gpt-4.1-nano", "global"): (0.10, 0.40),
    ("gpt-4.1-nano", "datazone"): (0.11, 0.44),
    ("gpt-4.1-mini", "global"): (0.40, 1.60),
    ("gpt-4.1-mini", "datazone"): (0.44, 1.76),
}


def estimate_cost_usd(
    model: str, zone: PriceZone, input_tokens: int, output_tokens: int
) -> float | None:
    prices = PRICES_PER_MILLION.get((model, zone))
    if prices is None:
        return None
    input_price, output_price = prices
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
