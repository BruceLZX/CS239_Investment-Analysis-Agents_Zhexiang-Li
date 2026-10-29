import copy
from datetime import datetime, timezone

import pytest

from tools import valuation

TICKERS = {'0': {'ticker': 'AAA', 'cik_str': 1, 'title': 'Alpha Inc.'},
           '1': {'ticker': 'BBB', 'cik_str': 2, 'title': 'Beta Corp.'}}


def flow(start: str, end: str, val: float, form: str = '10-K') -> dict:
    return {'start': start, 'end': end, 'val': val, 'form': form, 'fp': 'FY' if form == '10-K' else 'Q2',
            'filed': end, 'accn': f'{form}-{end}'}


def balance(end: str, val: float, form: str = '10-K') -> dict:
    return {'end': end, 'val': val, 'form': form, 'fp': 'FY' if form == '10-K' else 'Q2', 'filed': end,
            'accn': f'{form}-{end}'}


def flows(fy2024: float, fy2025: float, ytd: float, prior_ytd: float) -> list[dict]:
    """Two fiscal years and a six-month 10-Q with its comparison."""
    return [flow('2024-01-01', '2024-12-31', fy2024), flow('2025-01-01', '2025-12-31', fy2025),
            flow('2026-01-01', '2026-06-30', ytd, '10-Q'), flow('2025-01-01', '2025-06-30', prior_ytd, '10-Q')]


def balances(fy2024: float, fy2025: float, latest: float) -> list[dict]:
    return [balance('2024-12-31', fy2024), balance('2025-12-31', fy2025), balance('2026-06-30', latest, '10-Q')]


def gaap(**lines) -> dict:
    return {concept: {'units': {'USD/shares' if concept == 'EarningsPerShareDiluted' else
                                'shares' if concept.startswith('Weighted') else 'USD': entries}}
            for concept, entries in lines.items()}


ALPHA = {'facts': {
    'us-gaap': gaap(
        Revenues=flows(100e9, 120e9, 70e9, 55e9), OperatingIncomeLoss=flows(25e9, 30e9, 18e9, 13e9),
        DepreciationDepletionAndAmortization=flows(4e9, 5e9, 3e9, 2e9), NetIncomeLoss=flows(20e9, 24e9, 14e9, 11e9),
        EarningsPerShareDiluted=flows(2.00, 2.40, 1.40, 1.10),
        WeightedAverageNumberOfDilutedSharesOutstanding=flows(10e9, 10e9, 10e9, 10e9),
        NetCashProvidedByUsedInOperatingActivities=flows(25e9, 30e9, 17e9, 14e9),
        PaymentsToAcquirePropertyPlantAndEquipment=flows(5e9, 6e9, 4e9, 3e9),
        CashAndCashEquivalentsAtCarryingValue=balances(15e9, 18e9, 20e9),
        MarketableSecuritiesCurrent=balances(8e9, 9e9, 10e9),
        LongTermDebtNoncurrent=balances(42e9, 41e9, 40e9), LongTermDebtCurrent=balances(3e9, 4e9, 5e9),
        StockholdersEquity=balances(45e9, 48e9, 50e9)),
    'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
        {'end': '2026-07-20', 'val': 10e9, 'accn': '10-Q-2026-06-30', 'form': '10-Q'}]}}}}}
# Beta has one fiscal year, tags no debt and has no cover-page share count in the company facts.
BETA = {'facts': {'us-gaap': gaap(
    Revenues=[flow('2025-01-01', '2025-12-31', 50e9)], OperatingIncomeLoss=[flow('2025-01-01', '2025-12-31', 10e9)],
    NetIncomeLoss=[flow('2025-01-01', '2025-12-31', 8e9)], EarningsPerShareDiluted=[flow('2025-01-01', '2025-12-31', 1.0)],
    WeightedAverageNumberOfDilutedSharesOutstanding=[flow('2025-01-01', '2025-12-31', 8e9)],
    NetCashProvidedByUsedInOperatingActivities=[flow('2025-01-01', '2025-12-31', 9e9)],
    PaymentsToAcquirePropertyPlantAndEquipment=[flow('2025-01-01', '2025-12-31', 1e9)],
    CashAndCashEquivalentsAtCarryingValue=[balance('2025-12-31', 5e9)],
    StockholdersEquity=[balance('2025-12-31', 20e9)])}}


def epoch(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())


def chart(symbol: str, price: float, closes: dict[str, float]) -> dict:
    return {'chart': {'error': None, 'result': [{
        'meta': {'symbol': symbol, 'regularMarketPrice': price, 'regularMarketTime': epoch('2026-10-28T20:00:00'),
                 'exchangeName': 'NMS', 'fullExchangeName': 'NasdaqGS', 'currency': 'USD'},
        'timestamp': [epoch(day) for day in closes], 'indicators': {'quote': [{'close': list(closes.values())}]}}]}}


CHARTS = {'AAA': chart('AAA', 54.0, {'2024-12-31': 40.0, '2025-12-31': 48.0, '2026-10-27': 53.0}),
          'BBB': chart('BBB', 25.0, {'2026-10-27': 25.0})}


def fetch_json(url: str) -> dict:
    if url.endswith('company_tickers.json'):
        return TICKERS
    return ALPHA if 'CIK0000000001' in url else BETA


def snapshot(peers=('BBB', 'ZZZ')):
    return valuation.snapshot('aaa', list(peers), fetch_json, lambda ticker, period: CHARTS[ticker])


def test_each_multiple_is_worked_out_from_named_figures():
    lines = snapshot().text.splitlines()
    assert lines[3] == ('| AAA | 54.00 (2026-10-28T20:00+00:00) | 540.0B | 555.0B | 20.0x | 4.1x | 13.5x | 4.8% | '
                        '10.8x | 2026-06-30 |')


def test_unknown_debt_leaves_ev_unknown_and_missing_shares_are_approximated():
    text = snapshot().text
    assert '| BBB | 25.00 (2026-10-28T20:00+00:00) | 200.0B | n/a | 25.0x | n/m | n/m | 4.0% | 10.0x | 2025-12-31 |' in text
    assert 'Debt counted in EV: AAA 45.0B (LongTermDebtNoncurrent + LongTermDebtCurrent); BBB n/a (none tagged).' in text
    assert "BBB: market cap uses the latest quarter's diluted share count" in text


def test_peers_give_a_median_and_the_company_a_premium_or_discount():
    text = snapshot().text
    assert '| Peer median | | | | 25.0x | n/m | n/m | 4.0% | 10.0x | |' in text
    assert 'AAA against the peer median (premium + / discount -): P/E -20%.' in text
    assert "ZZZ: n/a (No SEC registrant found for ticker 'ZZZ'.)" in text


def test_the_company_is_valued_at_its_own_fiscal_year_ends():
    text = snapshot().text
    assert '| 2024-12-31 | 40.00 | 2.00 | 20.0x | 4.2x |' in text
    assert '| 2025-12-31 | 48.00 | 2.40 | 20.0x | 4.2x |' in text


def test_every_filing_and_price_used_is_a_source():
    sources = snapshot().sources
    assert {s['source_type'] for s in sources} == {'primary filing', 'market data'}
    assert any(s['label'].startswith('10-Q for the period ending 2026-06-30') for s in sources)
    assert sum(s['location'] == 'https://finance.yahoo.com/quote/BBB' for s in sources) == 1


def test_a_company_that_cannot_be_valued_says_why():
    with pytest.raises(ValueError, match='No valuation for ZZZ'):
        valuation.snapshot('ZZZ', [], fetch_json, lambda ticker, period: CHARTS[ticker])


# Alpha with cash returned: dividends 5B and buybacks 10B in fiscal 2025, and more this year.
PAYING = copy.deepcopy(ALPHA)
PAYING['facts']['us-gaap'].update(gaap(PaymentsOfDividends=flows(4e9, 5e9, 3e9, 2.5e9),
                                       PaymentsForRepurchaseOfCommonStock=flows(8e9, 10e9, 6e9, 4e9)))


def paying_snapshot():
    return valuation.snapshot('aaa', ['BBB'], lambda url: PAYING if 'CIK0000000001' in url else fetch_json(url),
                              lambda ticker, period: CHARTS[ticker])


def test_ev_to_ebit_price_to_fcf_and_shareholder_yields():
    lines = paying_snapshot().text.splitlines()
    start = lines.index('More multiples and cash returned to shareholders (trailing twelve months):')
    assert lines[start + 1] == '| Company | EV/EBIT | P/FCF | Dividend yield | Buyback yield | Total shareholder yield |'
    # TTM: EBIT 30 + 18 - 13 = 35B; FCF (30 + 17 - 14) - (6 + 4 - 3) = 26B; dividends 5.5B; buybacks 12B; cap 540B.
    assert lines[start + 3] == (f'| AAA | {555 / 35:.1f}x | {540 / 26:.1f}x | {5.5 / 540 * 100:.1f}% | '
                                f'{12 / 540 * 100:.1f}% | {17.5 / 540 * 100:.1f}% |')
    # Beta tags no debt (so no EV) and no cash returned.
    assert lines[start + 4] == '| BBB | n/m | 25.0x | n/m | n/m | n/m |'
    assert lines[start + 5] == '| Peer median | n/m | 25.0x | n/m | n/m | n/m |'
    assert lines[start + 6] == f'AAA against the peer median (premium + / discount -): P/FCF {(540 / 26 / 25 - 1) * 100:+.0f}%.'


def test_the_first_table_is_unchanged_and_the_definitions_cover_the_new_measures():
    text = paying_snapshot().text
    assert '| AAA | 54.00 (2026-10-28T20:00+00:00) | 540.0B | 555.0B | 20.0x | 4.1x | 13.5x | 4.8% | 10.8x | 2026-06-30 |' in text
    assert 'buyback yield = share repurchases paid (gross, not net of shares issued) / market cap' in text
