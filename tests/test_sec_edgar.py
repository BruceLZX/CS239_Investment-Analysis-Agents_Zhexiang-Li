import pytest

from tools import sec_edgar


def test_find_company_pads_the_cik(sec_fetch):
    assert sec_edgar.find_company('aapl', sec_fetch) == {'ticker': 'AAPL', 'cik': '0000320193', 'name': 'Apple Inc.'}


def test_find_company_rejects_unknown_tickers(sec_fetch):
    with pytest.raises(ValueError, match='No SEC registrant'):
        sec_edgar.find_company('ZZZZ', sec_fetch)


def test_statements_use_10k_values_from_the_current_revenue_concept(sec_fetch):
    result = sec_edgar.statements('AAPL', 3, sec_fetch)
    header = result.text.splitlines()[1]
    assert header.count('FY ending') == 3
    assert header.endswith('FY ending 2025-09-27 |')
    # Revenues stopped in 2018; the current concept carries FY2025's annual (not quarterly) figure.
    assert '| Revenue | 383,285M | 391,035M | 416,161M |' in result.text
    total_assets = next(line for line in result.text.splitlines() if line.startswith('| Total assets |'))
    assert 'n/a' not in total_assets
    first = result.sources[0]
    assert first['source_type'] == 'primary filing' and first['date'] == '2023-11-03'
    assert result.sources[2]['location'] == 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/'
    assert '0000320193-25-000079' in result.sources[2]['label']


def test_statements_work_out_margins_free_cash_flow_debt_and_net_cash(sec_fetch):
    lines = sec_edgar.statements('AAPL', 3, sec_fetch).text.splitlines()
    annual = lines[:lines.index('Latest periods, to 2026-06-27:')]
    row = {line.split(' | ')[0][2:]: line for line in annual if line.startswith('| ')}
    assert row['Gross margin'].endswith('| 44.1% | 46.2% | 46.9% |')
    assert row['Revenue growth'].endswith('| -2.8% | 2.0% | 6.4% |')
    assert row['Free cash flow'].endswith('| 99,584M | 108,807M | 98,767M |')
    assert row['Debt'].startswith('| Debt | 111,088M | 106,629M | 98,657M |')
    assert row['Net cash (debt)'].endswith('| -49,533M | -41,458M | -43,960M |')
    assert lines[-1].endswith('Debt = LongTermDebtNoncurrent + LongTermDebtCurrent + CommercialPaper as tagged; '
                              'finance leases are not included.')


def test_statements_add_the_latest_quarter_year_to_date_and_ttm(sec_fetch):
    result = sec_edgar.statements('AAPL', 3, sec_fetch)
    assert 'Latest periods, to 2026-06-27:' in result.text
    assert '| Quarter ending 2026-06-27 | Same quarter a year earlier | 9 months to date |' in result.text
    assert '| Revenue | 109,417M | 94,036M | 364,357M | 313,695M | 466,823M |' in result.text
    assert '| Diluted shares | 14,715M | 14,948M | 14,750M | 15,052M | n/a |' in result.text
    assert '| Debt | 84,344M | 101,698M | n/a | n/a | n/a |' in result.text
    assert result.sources[-1]['label'].startswith('10-Q for the period ending 2026-06-27, accession 0000320193-26-000020')


def test_statements_cap_the_number_of_years(sec_fetch):
    header = sec_edgar.statements('AAPL', 10, sec_fetch).text.splitlines()[1]
    assert header.count('FY ending') == 5


def entry(end: str, val: float, form: str = '10-K', start: str | None = None, fp: str = 'FY') -> dict:
    return {'end': end, 'val': val, 'form': form, 'fp': fp, 'filed': end, 'accn': f'a-{end}',
            **({'start': start} if start else {})}


def test_debt_takes_the_concept_with_the_most_recent_data():
    # Tesla tagged LongTermDebtNoncurrent until 2021, then its noncurrent debt as LongTermDebt.
    facts = {'facts': {'us-gaap': {
        'LongTermDebtNoncurrent': {'units': {'USD': [entry('2021-12-31', 5)]}},
        'LongTermDebt': {'units': {'USD': [entry('2021-12-31', 6), entry('2025-12-31', 7)]}},
        'DebtCurrent': {'units': {'USD': [entry('2025-12-31', 2)]}}}}}
    select = lambda concept: {e: v['val'] for e, v in sec_edgar._metric_periods(facts, [concept], 'USD', 'instant')[1].items()}
    assert sec_edgar._debt(select) == ({'2021-12-31': 6, '2025-12-31': 9}, ['LongTermDebt', 'DebtCurrent'])


def test_depreciation_alone_is_labelled_as_such():
    year = lambda end, val: entry(end, val, start=end[:4] + '-01-01')
    facts = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [year('2025-12-31', 100e6)]}},
                                   'Depreciation': {'units': {'USD': [year('2025-12-31', 5e6)]}}}}}
    text = sec_edgar.statements('TSLA', 1, lambda url: facts if 'companyfacts' in url else
                                {'0': {'ticker': 'TSLA', 'cik_str': 1318605, 'title': 'Tesla, Inc.'}}).text
    assert '| Depreciation (amortization not tagged) | 5M |' in text


def test_valuation_inputs_come_from_the_latest_filings(sec_fetch):
    facts = sec_fetch(sec_edgar.FACTS_URL.format(cik='0000320193'))
    latest = sec_edgar.fundamentals(facts)['latest']
    assert latest['end'] == '2026-06-27' and latest['entry']['form'] == '10-Q'
    assert (latest['Revenue'], latest['Debt'], latest['Diluted shares']) == (466_823e6, 84_344e6, 14_714_676e3)
    assert sec_edgar.shares_outstanding(facts) == (14_594_180_000, '2026-07-17')


def test_recent_filings_keep_only_the_requested_forms(sec_fetch):
    lines = sec_edgar.recent_filings('AAPL', None, 8, sec_fetch).splitlines()[1:]
    assert len(lines) == 8
    assert not any(line.startswith(('- 4 ', '- 144 ')) for line in lines)
    assert all('https://www.sec.gov/Archives/edgar/data/320193/' in line for line in lines)
    annual = sec_edgar.recent_filings('AAPL', ['10-K'], 8, sec_fetch).splitlines()[1:]
    assert annual and all(line.startswith('- 10-K filed') for line in annual)


def test_sec_user_agent_must_name_a_contact(monkeypatch):
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    with pytest.raises(RuntimeError, match='SEC_USER_AGENT'):
        sec_edgar.user_agent()
    monkeypatch.setenv('SEC_USER_AGENT', 'Test Person test@example.com')
    assert sec_edgar.user_agent() == 'Test Person test@example.com'
