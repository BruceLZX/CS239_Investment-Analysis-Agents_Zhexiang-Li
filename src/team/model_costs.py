"""What DeepSeek bills for a model call, from the token counts it reported.

Rakazo's usage records price every call at DeepSeek's peak rate, but DeepSeek charges half outside its
peak hours: 01:00-04:00 and 06:00-10:00 UTC, Monday to Friday. Traces and the dashboard therefore price
each call by the time it was made. DeepSeek also bills Chinese public holidays at the off-peak rate all
day; that isn't modelled, since no holiday falls between this project's runs and the end of the course.

Prices are from https://api-docs.deepseek.com/quick_start/pricing as of 2026-10-28.
"""
from datetime import datetime, timezone

# USD per million tokens at the peak rate: cache-hit input, cache-miss input, output (thinking included).
PEAK_PRICES = {
    'deepseek-v4-pro': (0.044, 1.32, 3.96),
    'deepseek-flash': (0.006, 0.3, 1.2),
}
# Retired names that DeepSeek still accepts and bills at the Flash price.
ALIASES = {'deepseek-v4-flash': 'deepseek-flash', 'deepseek-v4-flash-vision-exp': 'deepseek-flash'}


def is_peak(at_ms: int) -> bool:
    at = datetime.fromtimestamp(at_ms / 1000, timezone.utc)
    return at.weekday() < 5 and (1 <= at.hour < 4 or 6 <= at.hour < 10)


def call_cost(model: str | None, cache_hit: int, cache_miss: int, output: int, at_ms: int) -> float | None:
    """USD for one call made at at_ms (epoch milliseconds), or None for a model with no price here."""
    prices = PEAK_PRICES.get(ALIASES.get(model, model))
    if prices is None:
        return None
    hit, miss, out = prices
    cost = (cache_hit * hit + cache_miss * miss + output * out) / 1_000_000
    return cost if is_peak(at_ms) else cost / 2
