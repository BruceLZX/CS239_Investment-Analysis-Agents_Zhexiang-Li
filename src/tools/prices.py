"""Daily price context from Yahoo Finance's public chart endpoint (no key, unofficial).

The skill's evidence rules require market data to state exchange, currency and timestamp,
so the summary always carries all three.
"""
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
RANGES = {'1mo', '3mo', '6mo', '1y', '2y', '5y'}


def fetch_chart(ticker: str, period: str) -> dict:
    response = httpx.get(CHART_URL.format(ticker=ticker), params={'range': period, 'interval': '1d'},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    response.raise_for_status()
    return response.json()


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec='minutes')


def price_summary(ticker: str, period: str = '1y',
                  fetch: Callable[[str, str], dict] = fetch_chart) -> str:
    if period not in RANGES:
        raise ValueError(f'period must be one of {sorted(RANGES)}')
    chart = fetch(ticker.strip().upper(), period)['chart']
    if chart.get('error') or not chart.get('result'):
        raise ValueError(f'No price data for {ticker!r}: {chart.get("error")}')
    result = chart['result'][0]
    meta = result['meta']
    points = [(t, c) for t, c in zip(result['timestamp'], result['indicators']['quote'][0]['close']) if c is not None]
    if not points:
        raise ValueError(f'No closing prices for {ticker!r}.')
    first, last = points[0], points[-1]
    closes = [close for _, close in points]
    change = (last[1] / first[1] - 1) * 100
    currency = meta.get('currency', '?')
    exchange = meta.get('fullExchangeName') or meta.get('exchangeName', '?')
    return '\n'.join([
        f"{meta['symbol']} on {exchange}, prices in {currency}.",
        f"Latest price: {meta['regularMarketPrice']:.2f} at {_iso(meta['regularMarketTime'])} (UTC).",
        f'{period} range of daily closes: low {min(closes):.2f}, high {max(closes):.2f}; '
        f'close {first[1]:.2f} on {_iso(first[0])[:10]} to {last[1]:.2f} on {_iso(last[0])[:10]} ({change:+.1f}%).',
        f"Source to register: Yahoo Finance chart data for {meta['symbol']} ({exchange}, {currency}), "
        f"retrieved {datetime.now(timezone.utc).isoformat(timespec='minutes')}, "
        f"https://finance.yahoo.com/quote/{meta['symbol']}",
    ])
