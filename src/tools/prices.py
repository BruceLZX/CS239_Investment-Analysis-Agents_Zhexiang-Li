"""Daily price context from Yahoo Finance's public chart endpoint (no key, unofficial).

The skill's evidence rules require market data to state exchange, currency and timestamp,
so the summary always carries all three, along with the market's backdrop: the S&P 500, the VIX and the
10-year Treasury yield.
"""
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import httpx

from .retrieved import Retrieved, source

CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
RANGES = {'1mo', '3mo', '6mo', '1y', '2y', '5y'}
RETURN_MONTHS = (1, 3, 6, 12)
BENCHMARKS = (('^GSPC', 'S&P 500'), ('^VIX', 'VIX'), ('^TNX', '10-year Treasury yield'))

Fetch = Callable[[str, str], dict]


def fetch_chart(ticker: str, period: str) -> dict:
    response = httpx.get(CHART_URL.format(ticker=ticker), params={'range': period, 'interval': '1d'},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    response.raise_for_status()
    return response.json()


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec='minutes')


def chart(ticker: str, period: str, fetch: Fetch = fetch_chart) -> tuple[dict, list[tuple[int, float]]]:
    """The chart's metadata and its daily closes, skipping days without one."""
    data = fetch(ticker.strip().upper(), period)['chart']
    if data.get('error') or not data.get('result'):
        raise ValueError(f'No price data for {ticker!r}: {data.get("error")}')
    result = data['result'][0]
    points = [(t, c) for t, c in zip(result.get('timestamp') or [], result['indicators']['quote'][0]['close'])
              if c is not None]
    if not points:
        raise ValueError(f'No closing prices for {ticker!r}.')
    return result['meta'], points


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


def _returns(points: list[tuple[int, float]], price: float, at: int) -> list[str]:
    """The change from the close 1, 3, 6 and 12 months before the latest price, where the history reaches."""
    latest = datetime.fromtimestamp(at, timezone.utc)
    found = []
    for months in RETURN_MONTHS:
        then = latest - timedelta(days=round(months * 30.44))
        # A one-year chart starts a day or two short of twelve months.
        start = close_on_or_before(points, then) or (points[0][1] if points[0][0] - then.timestamp() < 5 * 86400 else None)
        if start:
            found.append(f'{months} month{"s" if months > 1 else ""} {(price / start - 1) * 100:+.1f}%')
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
