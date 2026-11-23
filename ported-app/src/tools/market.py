"""The market regime and a stock's trading context, from Yahoo Finance charts and FRED's public CSV download.

The Lead reads the regime before the analysts write: the major indices, volatility, Treasury yields and the curve,
credit spreads, the policy rate, the dollar, commodities and which sectors lead. Each figure carries its own as-of
time, since markets close, futures settle and FRED publishes at different times. FRED needs no key; its series are
cached for six hours beside the SEC responses, and its requests carry a generic User-Agent with no personal details.
"""
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
import time

import httpx

from . import prices
from .retrieved import Retrieved, source
from .sec_edgar import CACHE as SEC_CACHE

FRED_CSV = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
FRED_PAGE = 'https://fred.stlouisfed.org/series/{series}'
CACHE = SEC_CACHE.parent / 'fred'
CACHE_SECONDS = 6 * 3600
HEADERS = {'User-Agent': 'investment-research-agents/1.0'}
INDICES = (('^GSPC', 'S&P 500'), ('^IXIC', 'Nasdaq Composite'))
YIELDS = (('^IRX', '3-month Treasury bill yield'), ('^TNX', '10-year Treasury yield'))
FRED = {'DGS2': '2-year Treasury yield', 'T10Y2Y': '10-year minus 2-year Treasury yield',
        'DFEDTARU': 'Federal funds target range, upper limit',
        'BAMLC0A0CM': 'ICE BofA US Corporate Index option-adjusted spread (investment grade)',
        'BAMLH0A0HYM2': 'ICE BofA US High Yield Index option-adjusted spread'}
# (symbol, name, decimals)
CROSS_ASSET = (('DX-Y.NYB', 'US Dollar Index', 2), ('CNY=X', 'USD/CNY', 4),
               ('CL=F', 'WTI crude oil, front-month future (USD a barrel)', 2),
               ('GC=F', 'Gold, front-month future (USD a troy ounce)', 1),
               ('HG=F', 'Copper, front-month future (USD a pound)', 3))
SECTORS = (('XLK', 'Technology'), ('XLY', 'Consumer Discretionary'), ('XLC', 'Communication Services'),
           ('XLF', 'Financials'), ('XLV', 'Health Care'), ('XLI', 'Industrials'), ('XLE', 'Energy'),
           ('XLB', 'Materials'), ('XLU', 'Utilities'), ('XLRE', 'Real Estate'), ('XLP', 'Consumer Staples'))
SECTOR_BENCHMARK = 'SPY'
LOAD_ERRORS = (ValueError, KeyError, IndexError, httpx.HTTPError)

FetchFred = Callable[[str], str]


def fetch_fred(series: str) -> str:
    """A FRED series as CSV (observation_date,value) from about 13 months ago, cached for six hours."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f'{series}.csv'
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        return path.read_text()
    start = (date.today() - timedelta(days=400)).isoformat()
    response = httpx.get(FRED_CSV, params={'id': series, 'cosd': start}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    path.write_text(response.text)
    return response.text


def fred_series(series: str, fetch: FetchFred = fetch_fred) -> list[tuple[str, float]]:
    """The series' (date, value) observations, skipping days without a value (FRED leaves holidays blank)."""
    lines = fetch(series).strip().splitlines()
    if not lines or not lines[0].lower().startswith(('observation_date,', 'date,')):
        raise ValueError(f'FRED returned no CSV for {series}.')
    points = []
    for line in lines[1:]:
        day, _, value = line.partition(',')
        try:
            points.append((day, float(value)))
        except ValueError:  # '' or '.'
            continue
    if not points:
        raise ValueError(f'FRED series {series} has no observations.')
    return points


def fred_source(series: str, claims: str) -> dict:
    retrieved = datetime.now(timezone.utc).isoformat(timespec='minutes')
    return source(f'FRED series {series}: {FRED[series]}', 'market data', FRED_PAGE.format(series=series), retrieved,
                  claims, f'FRED {series} ({FRED[series]}), retrieved {retrieved}')


def _when(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def _day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()


def _signed(value: float) -> str:
    return f'{round(value, 1) + 0.0:+.1f}'  # + 0.0 turns -0.0 into 0.0


def _pct(value: float | None) -> str:
    return 'n/a' if value is None else f'{_signed(value)}%'


def _year_start(points: list[tuple[int, float]], at: int) -> tuple[int, float] | None:
    """The last close of the previous calendar year: the base of a year-to-date change."""
    year_end = datetime(datetime.fromtimestamp(at, timezone.utc).year - 1, 12, 31, 23, 59, tzinfo=timezone.utc)
    earlier = [point for point in points if point[0] <= year_end.timestamp()]
    return earlier[-1] if earlier else None


def _ytd(points: list[tuple[int, float]], level: float, at: int, decimals: int = 2) -> str:
    base = _year_start(points, at)
    if not base:
        return 'YTD n/a'
    return f'YTD {(level / base[1] - 1) * 100:+.1f}% (from {base[1]:,.{decimals}f}, the {_day(base[0])} close)'


def _fred_before(points: list[tuple[str, float]], days: int) -> tuple[str, float] | None:
    """The observation `days` before the latest one, or the last before that."""
    target = (date.fromisoformat(points[-1][0]) - timedelta(days=days)).isoformat()
    earlier = [point for point in points if point[0] <= target]
    return earlier[-1] if earlier else None


def _index_line(symbol: str, name: str, meta: dict, points: list[tuple[int, float]]) -> str:
    level, at = meta['regularMarketPrice'], meta['regularMarketTime']
    closes = [close for _, close in points]
    high, low = meta.get('fiftyTwoWeekHigh') or max(closes), meta.get('fiftyTwoWeekLow') or min(closes)
    return (f'- {name} ({symbol}): {level:,.2f} at {_when(at)}; {_ytd(points, level, at)}; '
            f'{(1 - level / high) * 100:.1f}% below its 52-week high of {high:,.2f} and '
            f'{(level / low - 1) * 100:.1f}% above its 52-week low of {low:,.2f}.')


def _vix_line(meta: dict, points: list[tuple[int, float]]) -> str:
    level, at = meta['regularMarketPrice'], meta['regularMarketTime']
    closes = [close for _, close in points]
    percentile = sum(close < level for close in closes) / len(closes) * 100
    return (f'- VIX (^VIX): {level:.2f} at {_when(at)}; 1-year percentile {percentile:.0f} (above {percentile:.0f}% '
            f"of the past year's {len(closes)} daily closes, which ranged {min(closes):.2f} to {max(closes):.2f}).")


def _yield_line(symbol: str, name: str, meta: dict, points: list[tuple[int, float]]) -> str:
    level, at = meta['regularMarketPrice'], meta['regularMarketTime']
    then = prices.close_months_before(points, at, 12)
    year = f'; {level - then:+.2f} points over 12 months' if then is not None else ''
    return f'- {name} ({symbol}): {level:.2f}% at {_when(at)}{year}.'


def _fred_line(series: str, points: list[tuple[str, float]]) -> str:
    day, value = points[-1]
    then = _fred_before(points, 365)
    if series.startswith('BAML'):  # spreads in percent, shown in basis points
        recent = [v for d, v in points if d >= (date.fromisoformat(day) - timedelta(days=365)).isoformat()]
        earlier = f'; 12 months earlier {then[1] * 100:.0f} bp' if then else ''
        return (f'- {FRED[series]} (FRED {series}): {value * 100:.0f} bp on {day}{earlier}; 1-year range '
                f'{min(recent) * 100:.0f} to {max(recent) * 100:.0f} bp.')
    if series == 'T10Y2Y':
        shape = ' (inverted: the 2-year yields more)' if value < 0 else ''
        earlier = f'; 12 months earlier {then[1] * 100:+.0f} bp' if then else ''
        return f'- 2s10s curve, {FRED[series]} (FRED {series}): {value * 100:+.0f} bp on {day}{shape}{earlier}.'
    earlier = f'; {value - then[1]:+.2f} points over 12 months' if then else ''
    return f'- {FRED[series]} (FRED {series}): {value:.2f}% on {day}{earlier}.'


def _cross_asset_line(symbol: str, name: str, decimals: int, meta: dict, points: list[tuple[int, float]]) -> str:
    level, at = meta['regularMarketPrice'], meta['regularMarketTime']
    changes = ', '.join(f'{label} {_pct(prices.change(points, level, at, months))}'
                        for label, months in (('1 month', 1), ('12 months', 12)))
    return f'- {name} ({symbol}): {level:,.{decimals}f} at {_when(at)}; {_ytd(points, level, at, decimals)}; {changes}.'


def _sector_table(charts: dict[str, tuple[dict, list]]) -> list[str]:
    """Each sector ETF's 1- and 3-month return, and its relative strength: its return less SPY's."""
    meta, points = charts[SECTOR_BENCHMARK]
    spy = {months: prices.change(points, meta['regularMarketPrice'], meta['regularMarketTime'], months)
           for months in (1, 3)}
    rows = []
    for symbol, name in SECTORS:
        if symbol not in charts:
            continue
        etf_meta, etf_points = charts[symbol]
        own = {months: prices.change(etf_points, etf_meta['regularMarketPrice'], etf_meta['regularMarketTime'], months)
               for months in (1, 3)}
        relative = {months: own[months] - spy[months] if own[months] is not None and spy[months] is not None
                    else None for months in (1, 3)}
        rows.append((relative[3] if relative[3] is not None else float('-inf'), symbol, name, own, relative))
    rows.sort(key=lambda row: row[0], reverse=True)
    lines = [f"Sector leadership: each SPDR sector ETF's return less SPY's, in percentage points; SPY "
             f"{meta['regularMarketPrice']:,.2f} at {_when(meta['regularMarketTime'])}, 1 month {_pct(spy[1])}, "
             f'3 months {_pct(spy[3])}. Sorted by the 3-month figure.',
             '| ETF | Sector | 1 month | 3 months | vs SPY, 1 month | vs SPY, 3 months |', '|---|---|---|---|---|---|']
    for _, symbol, name, own, relative in rows:
        gaps = ['n/a' if relative[m] is None else _signed(relative[m]) for m in (1, 3)]
        lines.append(f'| {symbol} | {name} | {_pct(own[1])} | {_pct(own[3])} | {gaps[0]} | {gaps[1]} |')
    return lines


def market_regime(fetch_chart: prices.Fetch = prices.fetch_chart, fetch_fred: FetchFred = fetch_fred) -> Retrieved:
    """The public-equity market regime, each figure with its as-of time: the S&P 500 and Nasdaq (level, year to date,
    distance from the 52-week high and low), the VIX and its 1-year percentile, 3-month, 2-year and 10-year Treasury
    yields and the 2s10s curve, investment-grade and high-yield credit spreads, the fed funds target, the dollar
    index, USD/CNY, WTI, gold and copper, and the 1- and 3-month relative strength of the 11 sector ETFs against SPY.
    A figure that fails to load is named as not available; the rest still come back."""
    charts, missing, sources = {}, [], []
    symbols = ([s for s, _ in INDICES] + ['^VIX'] + [s for s, _ in YIELDS] + [s for s, _, _ in CROSS_ASSET]
               + [SECTOR_BENCHMARK] + [s for s, _ in SECTORS])
    for symbol in symbols:
        try:
            charts[symbol] = prices.chart(symbol, '1y', fetch_chart)
        except LOAD_ERRORS as exc:
            missing.append(f'{symbol} ({exc})')
    series = {}
    for name in FRED:
        try:
            series[name] = fred_series(name, fetch_fred)
        except LOAD_ERRORS as exc:
            missing.append(f'FRED {name} ({exc})')
    if not charts and not series:
        raise ValueError('No market data could be loaded: ' + '; '.join(missing))
    retrieved = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [f'Market regime, retrieved {retrieved}. Each figure has its own as-of time: Yahoo prices are the latest '
             'trade or settlement (UTC); FRED series are daily and lag a day or more.', '', 'Equities and volatility:']
    used: list[tuple[str, str]] = []  # (symbol, claims) of each chart shown
    for symbol, name in INDICES:
        if symbol in charts:
            lines.append(_index_line(symbol, name, *charts[symbol]))
            used.append((symbol, f'{name} level, year-to-date change and 52-week range'))
    if '^VIX' in charts:
        lines.append(_vix_line(*charts['^VIX']))
        used.append(('^VIX', 'VIX level and 1-year percentile'))
    lines += ['', 'Rates and credit:']
    for symbol, name in YIELDS:
        if symbol in charts:
            lines.append(_yield_line(symbol, name, *charts[symbol]))
            used.append((symbol, f'{name} and its 12-month change'))
    for name in FRED:
        if name in series:
            lines.append(_fred_line(name, series[name]))
            sources.append(fred_source(name, f'{FRED[name]}, latest observation {series[name][-1][0]}'))
    lines += ['', 'Dollar and commodities:']
    for symbol, name, decimals in CROSS_ASSET:
        if symbol in charts:
            lines.append(_cross_asset_line(symbol, name, decimals, *charts[symbol]))
            used.append((symbol, f'{name} level and changes'))
    if SECTOR_BENCHMARK in charts and any(symbol in charts for symbol, _ in SECTORS):
        lines += [''] + _sector_table(charts)
        used.append((SECTOR_BENCHMARK, 'SPY returns, the benchmark for sector relative strength'))
        used += [(symbol, f'{name} sector ETF returns against SPY') for symbol, name in SECTORS if symbol in charts]
    if missing:
        lines += ['', 'Not available: ' + '; '.join(missing) + '.']
    sources = [prices.chart_source(charts[symbol][0], claims) for symbol, claims in used] + sources
    return Retrieved('\n'.join(lines), sources)


def _shares(value: float) -> str:
    return f'{value / 1e6:,.2f}M' if value >= 1e6 else f'{value / 1e3:,.1f}K'


def _money(value: float) -> str:
    return f'{value / 1e9:,.2f}B' if value >= 1e9 else f'{value / 1e6:,.1f}M' if value >= 1e6 else f'{value / 1e3:,.0f}K'


def trading_snapshot(ticker: str, sector_etf: str | None = None,
                     fetch_chart: prices.Fetch = prices.fetch_chart) -> Retrieved:
    """What price_summary gives over a year, and the trading context: 20-day and 3-month average daily volume in
    shares and in the trading currency, the 50- and 200-day moving averages and the price against each, the 1-, 3-,
    6- and 12-month returns against the S&P 500 and, if named, the sector ETF, and where the price sits in its
    52-week range."""
    summary = prices.price_summary(ticker, '1y', fetch_chart)
    meta, rows = prices.daily(ticker, '1y', fetch_chart)
    symbol, currency = meta['symbol'], meta.get('currency', '?')
    price, at = meta['regularMarketPrice'], meta['regularMarketTime']
    points = [(t, close) for t, close, _ in rows]
    closes = [close for _, close in points]
    session = (meta.get('currentTradingPeriod') or {}).get('regular') or {}
    # Today's volume is partial while the session is open, so the averages stop at the last full day.
    open_now = session.get('start', 0) <= at < session.get('end', 0)
    traded = rows[:-1] if open_now else rows
    lines = [summary.text, '', f'Trading context for {symbol} (values in {currency}):']

    liquidity = []
    for label, days in (('20-day', 20), ('3-month (63 trading days)', 63)):
        window = [(close, volume) for _, close, volume in traded[-days:] if volume]
        if window:
            shares = sum(volume for _, volume in window) / len(window)
            value = sum(close * volume for close, volume in window) / len(window)
            liquidity.append(f'{label} {_shares(shares)} shares, {_money(value)} {currency} traded')
    lines.append('Average daily volume: ' + ('; '.join(liquidity) if liquidity else 'n/a (no volume reported)')
                 + (", excluding today's session, still open" if open_now and liquidity else '') + '.')

    averages = []
    for days in (50, 200):
        if len(closes) >= days:
            average = sum(closes[-days:]) / days
            averages.append(f'{days}-day {average:,.2f} (price {(price / average - 1) * 100:+.1f}%)')
        else:
            averages.append(f'{days}-day n/a (only {len(closes)} days of history)')
    lines.append('Moving averages of daily closes: ' + '; '.join(averages) + '.')

    year = closes[-252:]
    high, low = meta.get('fiftyTwoWeekHigh') or max(year), meta.get('fiftyTwoWeekLow') or min(year)
    at_or_above = sum(close <= price for close in year) / len(year) * 100
    position = f'{(price - low) / (high - low) * 100:.0f}% of the way from the low to the high' if high > low else 'n/a'
    lines.append(f'52-week range {low:,.2f} to {high:,.2f}: the price is {position}, and at or above '
                 f"{at_or_above:.0f}% of the past year's {len(year)} daily closes.")

    sources = list(summary.sources)
    benchmarks, notes = [], []
    for benchmark, name in [('^GSPC', 'S&P 500')] + ([(sector_etf.strip().upper(), 'sector ETF')] if sector_etf else []):
        try:
            benchmark_meta, benchmark_points = prices.chart(benchmark, '1y', fetch_chart)
        except LOAD_ERRORS as exc:
            notes.append(f'{name} {benchmark} not available ({exc}).')
            continue
        benchmarks.append((benchmark, name, benchmark_meta, benchmark_points))
        sources.append(prices.chart_source(benchmark_meta, f'{name} returns, for relative performance'))
    header = f'| Period | {symbol} | ' + ' | '.join(f'{name} ({b}) | {symbol} vs {b}' for b, name, _, _ in benchmarks)
    lines += ['', 'Returns to the latest price, and the difference in percentage points:', header + ' |',
              '|---|---|' + '---|---|' * len(benchmarks)]
    for months in prices.RETURN_MONTHS:
        own = prices.change(points, price, at, months)
        cells = [_pct(own)]
        for _, _, benchmark_meta, benchmark_points in benchmarks:
            theirs = prices.change(benchmark_points, benchmark_meta['regularMarketPrice'],
                                   benchmark_meta['regularMarketTime'], months)
            cells += [_pct(theirs), _signed(own - theirs) if own is not None and theirs is not None else 'n/a']
        lines.append(f'| {months} month{"s" if months > 1 else ""} | ' + ' | '.join(cells) + ' |')
    lines += notes
    # The backdrop registers the S&P 500 chart too; one source per location.
    return Retrieved('\n'.join(lines), list({s['location']: s for s in sources}.values()))
