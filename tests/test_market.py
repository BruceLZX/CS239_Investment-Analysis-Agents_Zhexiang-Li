import copy
from datetime import datetime, timezone

import httpx
import pytest

from tools import market

from .helpers import FIXTURES, load_fixture

SPX = load_fixture('yahoo_chart_gspc_1y.json')  # recorded 2026-10-29 19:57 UTC, during the session
AAPL = load_fixture('yahoo_chart_aapl_1y.json')
DGS2 = (FIXTURES / 'fred_dgs2.csv').read_text()
HIGH_YIELD = (FIXTURES / 'fred_bamlh0a0hym2.csv').read_text()


def relabelled(chart: dict, symbol: str, scale: float = 1.0, last: float | None = None) -> dict:
    """The recorded chart as another symbol: its closes scaled, and optionally its latest close and price set."""
    chart = copy.deepcopy(chart)
    result = chart['chart']['result'][0]
    closes = result['indicators']['quote'][0]['close']
    result['indicators']['quote'][0]['close'] = [c * scale if c is not None else None for c in closes]
    if last is not None:
        result['indicators']['quote'][0]['close'][-1] = last
    meta = result['meta']
    meta.update(symbol=symbol, regularMarketPrice=last if last is not None else meta['regularMarketPrice'] * scale)
    for key in ('fiftyTwoWeekHigh', 'fiftyTwoWeekLow'):
        meta[key] *= scale
    return chart


def closes(chart: dict) -> list[tuple[int, float]]:
    result = chart['chart']['result'][0]
    return [(t, c) for t, c in zip(result['timestamp'], result['indicators']['quote'][0]['close']) if c is not None]


def close_before(chart: dict, day: str) -> float:
    cut = datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()
    return [c for t, c in closes(chart) if t <= cut][-1]


SYMBOLS = ['^GSPC', '^IXIC', '^VIX', '^IRX', '^TNX', 'DX-Y.NYB', 'CNY=X', 'CL=F', 'GC=F', 'HG=F', 'SPY'] + \
          [symbol for symbol, _ in market.SECTORS]


def charts(**overrides) -> dict:
    found = {symbol: relabelled(SPX, symbol, 0.01 if symbol in ('^VIX', '^IRX', '^TNX') else 1.0) for symbol in SYMBOLS}
    found['^GSPC'] = SPX
    found.update(overrides)
    return found


def fetch_chart(found: dict):
    def fetch(symbol: str, period: str) -> dict:
        assert period == '1y'
        if symbol not in found:
            raise httpx.ConnectError('offline')
        return found[symbol]
    return fetch


def fred(series: str) -> str:
    return HIGH_YIELD if series.startswith('BAML') else DGS2


def regime(**overrides):
    return market.market_regime(fetch_chart(charts(**overrides)), fred)


def line(text: str, start: str) -> str:
    return next(row for row in text.splitlines() if row.startswith(start))


def test_indices_give_level_year_to_date_and_distance_from_the_52_week_range():
    text = regime().text
    base = close_before(SPX, '2025-12-31T23:59')
    assert line(text, '- S&P 500 (^GSPC)') == (
        f'- S&P 500 (^GSPC): 7,717.59 at 2026-10-29 19:57 UTC; YTD {(7717.59 / base - 1) * 100:+.1f}% '
        f'(from {base:,.2f}, the 2025-12-31 close); 1.6% below its 52-week high of 7,844.52 and 22.2% above its '
        '52-week low of 6,316.91.')


def test_the_vix_is_placed_in_its_one_year_distribution():
    vix = relabelled(SPX, '^VIX', 0.01, last=20.0)
    text = regime(**{'^VIX': vix}).text
    below = sum(c < 20.0 for _, c in closes(vix)) / len(closes(vix)) * 100
    assert line(text, '- VIX').startswith(f'- VIX (^VIX): 20.00 at 2026-10-29 19:57 UTC; 1-year percentile {below:.0f} '
                                          f"(above {below:.0f}% of the past year's 252 daily closes")


def test_fred_series_skip_holidays_and_carry_their_own_dates():
    points = market.fred_series('DGS2', fred)
    assert points[-1] == ('2026-10-27', 4.70)
    assert '2025-10-13' not in dict(points)  # Columbus Day, left blank by FRED
    text = regime().text
    assert line(text, '- 2-year Treasury yield (FRED DGS2)') == (
        '- 2-year Treasury yield (FRED DGS2): 4.70% on 2026-10-27; +1.22 points over 12 months.')
    assert line(text, '- ICE BofA US High Yield') == (
        '- ICE BofA US High Yield Index option-adjusted spread (FRED BAMLH0A0HYM2): 314 bp on 2026-10-28; '
        '12 months earlier 282 bp; 1-year range 260 to 346 bp.')


def test_an_inverted_curve_says_so():
    inverted = 'observation_date,T10Y2Y\n2025-10-28,0.52\n2026-10-28,-0.15\n'
    text = market.market_regime(fetch_chart(charts()), lambda s: inverted if s == 'T10Y2Y' else fred(s)).text
    assert line(text, '- 2s10s curve') == ('- 2s10s curve, 10-year minus 2-year Treasury yield (FRED T10Y2Y): -15 bp on '
                                           '2026-10-28 (inverted: the 2-year yields more); 12 months earlier +52 bp.')


def test_sectors_are_ranked_by_three_month_strength_against_spy():
    spy_points = closes(SPX)
    then = market.prices.close_months_before(spy_points, SPX['chart']['result'][0]['meta']['regularMarketTime'], 3)
    leader = relabelled(SPX, 'XLE', 1.0, last=None)
    leader['chart']['result'][0]['meta']['regularMarketPrice'] = then * 1.30  # 30% over three months
    laggard = relabelled(SPX, 'XLU', 1.0)
    laggard['chart']['result'][0]['meta']['regularMarketPrice'] = then * 0.90
    text = regime(XLE=leader, XLU=laggard).text
    table = text[text.index('Sector leadership'):].splitlines()
    spy_3m = (7717.59 / then - 1) * 100
    top, bottom = table[3].strip('| ').split(' | '), table[-1].strip('| ').split(' | ')
    assert top[:2] == ['XLE', 'Energy'] and top[3] == '+30.0%' and top[5] == f'{30 - spy_3m:+.1f}'
    assert bottom[:2] == ['XLU', 'Utilities'] and bottom[3] == '-10.0%' and bottom[5] == f'{-10 - spy_3m:+.1f}'
    assert len(table) == 3 + len(market.SECTORS)


def test_figures_that_fail_to_load_are_named_and_the_rest_come_back():
    found = charts()
    del found['^IXIC']
    text = market.market_regime(fetch_chart(found), lambda s: '<html>error</html>' if s == 'DFEDTARU' else fred(s)).text
    assert 'Nasdaq' not in text.split('Not available')[0]
    assert text.endswith("Not available: ^IXIC (offline); FRED DFEDTARU (FRED returned no CSV for DFEDTARU.).")
    assert '- S&P 500 (^GSPC)' in text


def test_nothing_loading_is_an_error():
    def down(*args):
        raise httpx.ConnectError('offline')
    with pytest.raises(ValueError, match='No market data could be loaded'):
        market.market_regime(down, down)


def test_every_figure_is_registered_as_market_data():
    sources = regime().sources
    assert len(sources) == len(SYMBOLS) + len(market.FRED)
    assert {s['source_type'] for s in sources} == {'market data'}
    fred_source = next(s for s in sources if s['location'] == 'https://fred.stlouisfed.org/series/DGS2')
    assert fred_source['claims'] == '2-year Treasury yield, latest observation 2026-10-27'
    assert any(s['location'] == 'https://finance.yahoo.com/quote/XLK' for s in sources)


def test_fred_requests_name_no_one_and_are_cached(tmp_path, monkeypatch):
    calls = []

    def get(url, params, headers, timeout):
        calls.append((url, params, headers))
        return httpx.Response(200, text=DGS2, request=httpx.Request('GET', url))
    monkeypatch.setattr(market, 'CACHE', tmp_path)
    monkeypatch.setattr(market.httpx, 'get', get)
    assert market.fetch_fred('DGS2') == DGS2 and market.fetch_fred('DGS2') == DGS2
    [(url, params, headers)] = calls
    assert url == 'https://fred.stlouisfed.org/graph/fredgraph.csv' and params['id'] == 'DGS2'
    assert headers == {'User-Agent': 'investment-research-agents/1.0'}


def snapshot(sector: str | None = 'XLK', **overrides):
    found = {'AAPL': AAPL, '^GSPC': SPX, '^VIX': relabelled(SPX, '^VIX', 0.01), '^TNX': relabelled(SPX, '^TNX', 0.01),
             'XLK': relabelled(SPX, 'XLK', 0.025), **overrides}
    return market.trading_snapshot('aapl', sector, fetch_chart(found))


def test_the_snapshot_extends_the_price_summary():
    text = snapshot().text
    assert text.startswith('AAPL on NasdaqGS, prices in USD.\nLatest price: 348.74 at 2026-10-29T19:57+00:00 (UTC).')
    assert 'Market backdrop: S&P 500 (^GSPC) 7,717.59' in text


def test_volume_averages_stop_at_the_last_full_day_while_the_session_is_open():
    result = AAPL['chart']['result'][0]
    rows = [(c, v) for c, v in zip(result['indicators']['quote'][0]['close'], result['indicators']['quote'][0]['volume'])
            if c is not None][:-1]  # the recording was taken during the session
    shares = sum(v for _, v in rows[-20:]) / 20
    value = sum(c * v for c, v in rows[-20:]) / 20
    assert line(snapshot().text, 'Average daily volume:').startswith(
        f'Average daily volume: 20-day {shares / 1e6:,.2f}M shares, {value / 1e9:,.2f}B USD traded; 3-month (63 trading days)')
    assert line(snapshot().text, 'Average daily volume:').endswith(", excluding today's session, still open.")


def test_moving_averages_and_the_52_week_position():
    prices = [c for _, c in closes(AAPL)]
    fifty, two_hundred = sum(prices[-50:]) / 50, sum(prices[-200:]) / 200
    text = snapshot().text
    assert line(text, 'Moving averages') == (
        f'Moving averages of daily closes: 50-day {fifty:,.2f} (price {(348.74 / fifty - 1) * 100:+.1f}%); '
        f'200-day {two_hundred:,.2f} (price {(348.74 / two_hundred - 1) * 100:+.1f}%).')
    position = (348.74 - 243.42) / (351.73 - 243.42) * 100
    assert line(text, '52-week range 243.42') == (
        f'52-week range 243.42 to 351.73: the price is {position:.0f}% of the way from the low to the high, and at or '
        f"above 100% of the past year's 252 daily closes.")


def test_returns_are_set_against_the_index_and_the_sector():
    text = snapshot().text
    table = text[text.index('| Period |'):].splitlines()
    assert table[0] == '| Period | AAPL | S&P 500 (^GSPC) | AAPL vs ^GSPC | sector ETF (XLK) | AAPL vs XLK |'
    assert [row.split(' | ')[0] for row in table[2:6]] == ['| 1 month', '| 3 months', '| 6 months', '| 12 months']
    twelve = table[5].strip('| ').split(' | ')
    assert twelve[1] == f'{(348.74 / 269.7 - 1) * 100:+.1f}%' and twelve[2] == f'{(7717.59 / 6890.5898 - 1) * 100:+.1f}%'
    # XLK is the S&P 500 at 2.5% of its level, so its returns match the index's.
    assert twelve[2] == twelve[4] and twelve[3] == twelve[5]


def test_a_sector_etf_that_fails_to_load_is_noted_and_sources_are_not_repeated():
    result = snapshot('ZZZZ')
    assert result.text.endswith('sector ETF ZZZZ not available (offline).')
    locations = [s['location'] for s in result.sources]
    assert len(locations) == len(set(locations)) == 4  # AAPL, ^GSPC, ^VIX, ^TNX


def test_no_sector_etf_compares_with_the_index_alone():
    assert '| Period | AAPL | S&P 500 (^GSPC) | AAPL vs ^GSPC |\n' in snapshot(None).text
