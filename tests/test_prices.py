import copy

import pytest

from tools import prices

from .helpers import load_fixture

CHART = load_fixture('yahoo_chart_aapl_1mo.json')
DAY = 86_400


def chart_for(symbol: str, price: float, closes: list[float], last: int = 1_792_762_200) -> dict:
    """A chart with one close a day up to `last`, and `price` as the latest price."""
    chart = copy.deepcopy(CHART)
    result = chart['chart']['result'][0]
    result['meta'].update({'symbol': symbol, 'regularMarketPrice': price, 'regularMarketTime': last})
    result['timestamp'] = [last - (len(closes) - 1 - i) * DAY for i in range(len(closes))]
    result['indicators']['quote'][0]['close'] = closes
    return chart


def only(chart: dict):
    return lambda ticker, period: chart


def test_summary_states_exchange_currency_and_timestamp():
    result = prices.price_summary('aapl', '1mo', only(CHART), backdrop=False)
    assert result.text.startswith('AAPL on NasdaqGS, prices in USD.')
    assert 'Latest price: 347.73 at' in result.text and '(UTC)' in result.text
    assert '1mo range of daily closes' in result.text
    assert '52-week range: 243.42 to' in result.text
    [source] = result.sources
    assert (source['source_type'], source['location'], source['confidence']) == (
        'market data', 'https://finance.yahoo.com/quote/AAPL', 'medium')
    assert source['title'] == 'Yahoo Finance chart data for AAPL (NasdaqGS, USD)'


def test_summary_skips_missing_closes():
    chart = copy.deepcopy(CHART)
    chart['chart']['result'][0]['indicators']['quote'][0]['close'][0] = None
    assert 'Latest price:' in prices.price_summary('AAPL', '1mo', only(chart), backdrop=False).text


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError, match='period must be one of'):
        prices.price_summary('AAPL', '10y', only(CHART))


def test_api_errors_are_reported():
    failed = {'chart': {'result': None, 'error': {'code': 'Not Found', 'description': 'No data found'}}}
    with pytest.raises(ValueError, match='No price data'):
        prices.price_summary('NOPE', '1y', only(failed))


def test_price_changes_run_to_the_latest_price():
    closes = [100.0] * 364 + [110.0]  # a year of daily closes, one day short of twelve months
    text = prices.price_summary('AAPL', '1y', only(chart_for('AAPL', 120.0, closes)), backdrop=False).text
    assert 'Change to the latest price: 1 month +20.0%, 3 months +20.0%, 6 months +20.0%, 12 months +20.0%.' in text


def test_the_market_backdrop_is_registered_too():
    charts = {'AAPL': CHART, '^GSPC': chart_for('^GSPC', 7700.0, [7000.0, 7700.0]),
              '^VIX': chart_for('^VIX', 17.0, [16.5, 17.0]), '^TNX': chart_for('^TNX', 5.04, [3.98, 5.04])}
    result = prices.price_summary('AAPL', '1mo', lambda ticker, period: charts[ticker])
    assert result.text.endswith('Market backdrop: S&P 500 (^GSPC) 7,700.00, +10.0% over 12 months; VIX (^VIX) 17.00, '
                                '+0.50 points over 12 months; 10-year Treasury yield (^TNX) 5.04%, '
                                '+1.06 points over 12 months.')
    assert [s['location'] for s in result.sources] == [
        'https://finance.yahoo.com/quote/AAPL', 'https://finance.yahoo.com/quote/%5EGSPC',
        'https://finance.yahoo.com/quote/%5EVIX', 'https://finance.yahoo.com/quote/%5ETNX']


def test_a_benchmark_that_fails_to_load_is_left_out():
    failed = {'chart': {'result': None, 'error': 'down'}}
    charts = {'AAPL': CHART, '^GSPC': failed, '^VIX': failed, '^TNX': chart_for('^TNX', 5.0, [4.0, 5.0])}
    result = prices.price_summary('AAPL', '1mo', lambda ticker, period: charts[ticker])
    assert result.text.endswith('Market backdrop: 10-year Treasury yield (^TNX) 5.00%, +1.00 points over 12 months.')
    assert len(result.sources) == 2
