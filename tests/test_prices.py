import copy

import pytest

from tools import prices

from .helpers import load_fixture

CHART = load_fixture('yahoo_chart_aapl_1mo.json')


def test_summary_states_exchange_currency_and_timestamp():
    text = prices.price_summary('aapl', '1mo', lambda ticker, period: CHART)
    assert text.startswith('AAPL on NasdaqGS, prices in USD.')
    assert 'Latest price:' in text and '(UTC)' in text
    assert '1mo range of daily closes' in text
    assert 'Source to register: Yahoo Finance chart data for AAPL (NasdaqGS, USD)' in text


def test_summary_skips_missing_closes():
    chart = copy.deepcopy(CHART)
    chart['chart']['result'][0]['indicators']['quote'][0]['close'][0] = None
    assert 'Latest price:' in prices.price_summary('AAPL', '1mo', lambda ticker, period: chart)


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError, match='period must be one of'):
        prices.price_summary('AAPL', '10y', lambda ticker, period: CHART)


def test_api_errors_are_reported():
    failed = {'chart': {'result': None, 'error': {'code': 'Not Found', 'description': 'No data found'}}}
    with pytest.raises(ValueError, match='No price data'):
        prices.price_summary('NOPE', '1y', lambda ticker, period: failed)
