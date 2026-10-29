"""Daily price context from Yahoo Finance's public chart endpoint (no key, unofficial).

The skill's evidence rules require market data to state exchange, currency and timestamp,
so the summary always carries all three, along with the market's backdrop: the S&P 500, the VIX and the
10-year Treasury yield. Charts are cached for 15 minutes beside the SEC responses, since the market regime and a
stock's trading snapshot read the same charts.
"""
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import json
import time

import httpx

from .retrieved import Retrieved, source
from .sec_edgar import CACHE as SEC_CACHE

CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
RANGES = {'1mo', '3mo', '6mo', '1y', '2y', '5y'}
RETURN_MONTHS = (1, 3, 6, 12)
BENCHMARKS = (('^GSPC', 'S&P 500'), ('^VIX', 'VIX'), ('^TNX', '10-year Treasury yield'))
CACHE = SEC_CACHE.parent / 'yahoo'
CACHE_SECONDS = 15 * 60

Fetch = Callable[[str, str], dict]


def fetch_chart(ticker: str, period: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{ticker.replace('/', '_')}_{period}.json"
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        return json.loads(path.read_text())
    response = httpx.get(CHART_URL.format(ticker=ticker), params={'range': period, 'interval': '1d'},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    response.raise_for_status()
    path.write_text(response.text)
    return response.json()


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec='minutes')


def daily(ticker: str, period: str, fetch: Fetch = fetch_chart) -> tuple[dict, list[tuple[int, float, float | None]]]:
    """The chart's metadata and its days as (time, close, volume), skipping days without a close."""
    data = fetch(ticker.strip().upper(), period)['chart']
    if data.get('error') or not data.get('result'):
        raise ValueError(f'No price data for {ticker!r}: {data.get("error")}')
    result = data['result'][0]
    quote = result['indicators']['quote'][0]
    closes = quote['close']
    volumes = list(quote.get('volume') or [])
    volumes += [None] * (len(closes) - len(volumes))  # a missing volume never drops a close
    rows = [(t, c, v) for t, c, v in zip(result.get('timestamp') or [], closes, volumes) if c is not None]
    if not rows:
        raise ValueError(f'No closing prices for {ticker!r}.')
    return result['meta'], rows


def chart(ticker: str, period: str, fetch: Fetch = fetch_chart) -> tuple[dict, list[tuple[int, float]]]:
    """The chart's metadata and its daily closes, skipping days without one."""
    meta, rows = daily(ticker, period, fetch)
    return meta, [(t, close) for t, close, _ in rows]


def close_on_or_before(points: list[tuple[int, float]], when: datetime) -> float | None:
    earlier = [close for t, close in points if t <= when.timestamp()]
    return earlier[-1] if earlier else None


def quote_url(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol.replace('^', '%5E')}"


def chart_source(meta: dict, claims: str) -> dict:
    retrieved = datetime.now(timezone.utc).isoformat(timespec='minutes')
    exchange = meta.get('fullExchangeName') or meta.get('exchangeName', '?')
    return source(f"Yahoo Finance chart data for {meta['symbol']} ({exchange}, {meta.get('currency', '?')})",
                  'market data', quote_url(meta['symbol']), retrieved, claims,
                  f"Yahoo Finance chart data for {meta['symbol']}, retrieved {retrieved}",
                  confidence='medium')  # an unofficial endpoint


def close_months_before(points: list[tuple[int, float]], at: int, months: int) -> float | None:
    """The close `months` months before `at`, where the history reaches."""
    then = datetime.fromtimestamp(at, timezone.utc) - timedelta(days=round(months * 30.44))
    # A one-year chart starts a day or two short of twelve months.
    return close_on_or_before(points, then) or (points[0][1] if points[0][0] - then.timestamp() < 5 * 86400 else None)


def change(points: list[tuple[int, float]], price: float, at: int, months: int) -> float | None:
    """The percent change from the close `months` months before `at` to `price`, where the history reaches."""
    start = close_months_before(points, at, months)
    return (price / start - 1) * 100 if start else None


def _returns(points: list[tuple[int, float]], price: float, at: int) -> list[str]:
    """The change from the close 1, 3, 6 and 12 months before the latest price, where the history reaches."""
    found = []
    for months in RETURN_MONTHS:
        if (percent := change(points, price, at, months)) is not None:
            found.append(f'{months} month{"s" if months > 1 else ""} {percent:+.1f}%')
    return found


def _backdrop(fetch: Fetch) -> tuple[str, list[dict]]:
    """The market's level and 12-month change for each benchmark; one that fails to load is left out."""
    parts, sources = [], []
    for symbol, name in BENCHMARKS:
        try:
            meta, points = chart(symbol, '1y', fetch)
        except (ValueError, httpx.HTTPError):
            continue
        level = meta.get('regularMarketPrice') or points[-1][1]
        if symbol == '^GSPC':
            parts.append(f'{name} ({symbol}) {level:,.2f}, {(level / points[0][1] - 1) * 100:+.1f}% over 12 months')
        else:  # a volatility index and a yield change by points, not by percent
            unit = '%' if symbol == '^TNX' else ''
            parts.append(f'{name} ({symbol}) {level:.2f}{unit}, {level - points[0][1]:+.2f} points over 12 months')
        sources.append(chart_source(meta, f'{name} level and 12-month change'))
    return ('Market backdrop: ' + '; '.join(parts) + '.') if parts else '', sources


def price_summary(ticker: str, period: str = '1y', fetch: Fetch = fetch_chart, backdrop: bool = True) -> Retrieved:
    if period not in RANGES:
        raise ValueError(f'period must be one of {sorted(RANGES)}')
    meta, points = chart(ticker, period, fetch)
    first, last = points[0], points[-1]
    closes = [close for _, close in points]
    change = (last[1] / first[1] - 1) * 100
    currency = meta.get('currency', '?')
    exchange = meta.get('fullExchangeName') or meta.get('exchangeName', '?')
    lines = [
        f"{meta['symbol']} on {exchange}, prices in {currency}.",
        f"Latest price: {meta['regularMarketPrice']:.2f} at {_iso(meta['regularMarketTime'])} (UTC).",
        f'{period} range of daily closes: low {min(closes):.2f}, high {max(closes):.2f}; '
        f'close {first[1]:.2f} on {_iso(first[0])[:10]} to {last[1]:.2f} on {_iso(last[0])[:10]} ({change:+.1f}%).',
    ]
    if meta.get('fiftyTwoWeekLow') and meta.get('fiftyTwoWeekHigh'):
        lines.append(f"52-week range: {meta['fiftyTwoWeekLow']:.2f} to {meta['fiftyTwoWeekHigh']:.2f}.")
    if returns := _returns(points, meta['regularMarketPrice'], meta['regularMarketTime']):
        lines.append('Change to the latest price: ' + ', '.join(returns) + '.')
    sources = [chart_source(meta, f'price, range and returns over {period}')]
    if backdrop:
        text, benchmark_sources = _backdrop(fetch)
        if text:
            lines.append(text)
            sources += benchmark_sources
    return Retrieved('\n'.join(lines), sources)
