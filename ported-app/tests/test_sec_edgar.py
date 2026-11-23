import copy
from datetime import date

import httpx
import pytest

from tools import sec_edgar

from .helpers import FIXTURES, load_fixture


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
    assert row['Net cash (debt)'].endswith('| 51,011M | 50,021M | 33,763M |')  # non-current securities count
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


def with_ratio_lines(sec_fetch):
    """The AAPL fixture with the lines the ratios add (payables, interest, intangibles), recorded from the same API."""
    facts = copy.deepcopy(sec_fetch(sec_edgar.FACTS_URL.format(cik='0000320193')))
    facts['facts']['us-gaap'].update(load_fixture('sec_companyfacts_aapl_ratios.json')['facts']['us-gaap'])
    return lambda url: facts if 'companyfacts' in url else sec_fetch(url)


def test_statements_add_returns_working_capital_days_and_intensity_ratios(sec_fetch):
    lines = sec_edgar.statements('AAPL', 3, with_ratio_lines(sec_fetch)).text.splitlines()
    row = {line.split(' | ')[0][2:]: line for line in lines if line.startswith('| ')}
    # FY2025: net income 112,010M over average equity (73,733M + 56,950M) / 2.
    assert f'{112_010 / ((73_733 + 56_950) / 2) * 100:.1f}%' == '171.4%'
    assert row['Return on equity (ROE)'] == '| Return on equity (ROE) | 171.9% | 157.4% | 171.4% |'
    assert row['Return on assets (ROA)'] == '| Return on assets (ROA) | 27.5% | 26.1% | 30.9% |'
    assert row['ROIC (approximate)'] == '| ROIC (approximate) | 1527.0% | 1035.6% | 478.8% |'
    assert row['Days sales outstanding (DSO)'] == '| Days sales outstanding (DSO) | 28.1 | 31.2 | 34.9 |'
    assert row['Cash conversion cycle (days)'] == '| Cash conversion cycle (days) | -67.8 | -75.8 | -71.1 |'
    # Apple stopped tagging interest expense after FY2023, and tags no goodwill.
    assert row['Interest coverage'] == '| Interest coverage | 29.06x | n/a | n/a |'
    assert row['Goodwill and intangibles / total assets'].endswith('| n/a | n/a | n/a |')
    assert row['Stock-based compensation / revenue'] == '| Stock-based compensation / revenue | 2.8% | 3.0% | 3.1% |'
    assert row['Capex / D&A'] == '| Capex / D&A | 0.95x | 0.83x | 1.09x |'
    assert lines[-1].startswith('Definitions:') and 'Interest expense = InterestExpense as tagged.' in lines[-1]
    assert 'DSO = receivables / revenue x 365' in lines[-1]


def test_ratios_are_worked_out_for_the_trailing_twelve_months_too(sec_fetch):
    text = sec_edgar.statements('AAPL', 3, with_ratio_lines(sec_fetch)).text
    ttm = next(line for line in text.splitlines() if line.startswith('TTM ratios to 2026-06-27'))
    assert 'Return on equity (ROE) 148.8%; Return on assets (ROA) 36.1%; ROIC (approximate) 320.6%;' in ttm
    assert 'Cash conversion cycle (days) -56.8; Interest coverage n/a; Goodwill and intangibles / total assets 6.6%' in ttm


def test_interest_falls_back_to_the_2024_concept_and_a_negative_base_is_not_meaningful():
    year = lambda end, val: entry(end, val, start=end[:4] + '-01-01')
    facts = {'facts': {'us-gaap': {
        'Revenues': {'units': {'USD': [year('2024-12-31', 100e6), year('2025-12-31', 120e6)]}},
        'OperatingIncomeLoss': {'units': {'USD': [year('2024-12-31', 10e6), year('2025-12-31', 12e6)]}},
        'NetIncomeLoss': {'units': {'USD': [year('2024-12-31', 5e6), year('2025-12-31', 6e6)]}},
        'InterestExpense': {'units': {'USD': [year('2024-12-31', 2e6)]}},
        'InterestExpenseNonoperating': {'units': {'USD': [year('2024-12-31', 2e6), year('2025-12-31', 3e6)]}},
        'StockholdersEquity': {'units': {'USD': [entry('2024-12-31', -8e6), entry('2025-12-31', -4e6)]}}}}}
    text = sec_edgar.statements('TSLA', 1, lambda url: facts if 'companyfacts' in url else
                                {'0': {'ticker': 'TSLA', 'cik_str': 1318605, 'title': 'Tesla, Inc.'}}).text
    assert '| Interest expense | 3M |' in text and '| Interest coverage | 4.00x |' in text
    assert '| Return on equity (ROE) | n/m |' in text
    assert 'Interest expense = InterestExpenseNonoperating as tagged.' in text


SALE = (FIXTURES / 'sec_form4_aapl_sale.xml').read_text()
VESTING = (FIXTURES / 'sec_form4_aapl_vesting.xml').read_text()
TAX_SALE = (FIXTURES / 'sec_form4_tsla_tax_sale.xml').read_text()


def test_form4_rows_carry_the_insider_code_shares_price_and_plan():
    [sale] = sec_edgar.form4_transactions(SALE)
    assert sale == {'date': '2026-10-20', 'insider': 'Newstead Jennifer', 'title': 'SVP, GC and Government Affairs',
                    'code': 'S', 'shares': 2399.0, 'price': 339.62, 'value': 2399 * 339.62, 'plan': True, 'tax': False}
    rows = sec_edgar.form4_transactions(VESTING)
    assert [r['code'] for r in rows] == ['M', 'F', 'S', 'S', 'S', 'S', 'S']
    assert rows[0]['value'] == 0 and rows[1]['value'] == 5361 * 342.00 and rows[1]['tax']
    assert rows[0]['title'] == 'Senior Vice President, CFO'  # the filing's double space is tidied
    # Tesla marks booleans 0/1 and sells shares to cover tax without a 10b5-1 plan.
    exercise, sale = sec_edgar.form4_transactions(TAX_SALE)
    assert (exercise['code'], exercise['price'], exercise['value']) == ('M', 0.0, 0.0)
    assert (sale['shares'], sale['plan'], sale['tax'], sale['title']) == (2605.75, False, True, 'Chief Financial Officer')


def insider_fetch(sec_fetch, keep: tuple[str, ...], since: str = ''):
    """The AAPL submissions with only the Form 4s whose accessions are kept (and only filings since a date), and the
    Form 4 XML by accession."""
    submissions = copy.deepcopy(sec_fetch(sec_edgar.SUBMISSIONS_URL.format(cik='0000320193')))
    recent = submissions['filings']['recent']
    rows = [i for i, accession in enumerate(recent['accessionNumber'])
            if (recent['form'][i] != '4' or accession in keep) and recent['filingDate'][i] >= since]
    submissions['filings']['recent'] = {key: [values[i] for i in rows] for key, values in recent.items()}
    documents = {'000114036126040540': SALE, '000114036126040126': VESTING}
    requested = []

    def fetch_document(url: str) -> str:
        requested.append(url)
        folder = url.split('/')[-2]
        if folder not in documents:
            raise httpx.ConnectError('offline')
        return documents[folder]
    return (lambda url: submissions if 'submissions' in url else sec_fetch(url)), fetch_document, requested


def test_insider_activity_sums_purchases_and_sales_and_names_the_largest_sellers(sec_fetch):
    fetch, fetch_document, requested = insider_fetch(sec_fetch, ('0001140361-26-040540', '0001140361-26-040126'))
    result = sec_edgar.insider_activity('AAPL', 1, fetch, fetch_document, today=date(2026, 10, 29))
    lines = result.text.splitlines()
    assert lines[0] == ('Insider transactions at Apple Inc. (AAPL) from Form 4 filings since 2026-09-29: 2 filed in the '
                        'last 1 month; all read, filed 2026-10-19 to 2026-10-22.')
    assert requested[0] == 'https://www.sec.gov/Archives/edgar/data/320193/000114036126040540/form4.xml'  # not xsl
    sold = 2399 * 339.62 + 200 * 342.66 + 192 * 343.68 + 880 * 345.66 + 80 * 346.47 + 40 * 347.46
    assert lines[1] == 'Purchases (code P): none.'
    assert lines[2] == (f'Sales (code S): 6 transactions, 3,791 shares, ${sold / 1e6:,.2f}M; under a Rule 10b5-1 plan: '
                        f'6 transactions, 3,791 shares, ${sold / 1e6:,.2f}M; sold to cover tax, per the footnotes: none.')
    assert lines[3] == f'Purchases less sales: -${sold / 1e6:,.2f}M.'
    assert lines[4].startswith('Other transactions: F (shares withheld for tax or exercise price) 1 transaction, 5,361 '
                               'shares, $1.83M; M (option exercise or RSU settlement) 1 transaction, 10,926 shares, $0.')
    assert lines[5].startswith('Largest buyers and sellers: Newstead Jennifer (SVP, GC and Government Affairs) sold '
                               '$814,748, bought $0; Parekh Kevan')
    table = [line for line in lines if line.startswith('| 2026-')]
    assert table == ['| 2026-10-22 | 2026-10-20 | Newstead Jennifer | SVP, GC and Government Affairs | S | 2,399 | '
                     '339.62 | $814,748 | 10b5-1 plan | 0001140361-26-040540 |',
                     '| 2026-10-19 | 2026-10-16 | Parekh Kevan | Senior Vice President, CFO | S | 1,392 | 345.05 | '
                     '$480,315 | 10b5-1 plan | 0001140361-26-040126 |']
    listing, *filings = result.sources
    assert {s['source_type'] for s in result.sources} == {'primary'}
    assert listing['location'] == ('https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=4'
                                   '&dateb=&owner=include&count=40')
    assert [s['location'] for s in filings] == [
        'https://www.sec.gov/Archives/edgar/data/320193/000114036126040540/xslF345X06/form4.xml',
        'https://www.sec.gov/Archives/edgar/data/320193/000114036126040126/xslF345X06/form4.xml']


def test_insider_activity_reads_at_most_the_cap_and_says_so(sec_fetch, monkeypatch):
    monkeypatch.setattr(sec_edgar, 'MAX_FORM4', 1)
    fetch, fetch_document, requested = insider_fetch(sec_fetch, ('0001140361-26-040540', '0001140361-26-040126'))
    text = sec_edgar.insider_activity('AAPL', 1, fetch, fetch_document, today=date(2026, 10, 29)).text
    assert '2 filed in the last 1 month; the 1 most recent, filed 2026-10-22 to 2026-10-22, were read (the cap).' in text
    assert len(requested) == 1


def test_insider_activity_with_no_filings_or_unreadable_ones(sec_fetch):
    fetch, fetch_document, _ = insider_fetch(sec_fetch, ('0001140361-26-040540', '0001140361-26-039785'))
    quiet = sec_edgar.insider_activity('AAPL', 6, fetch, fetch_document, today=date(2030, 1, 1))
    assert quiet.text == ('Insider transactions at Apple Inc. (AAPL) from Form 4 filings since 2029-07-02: none filed '
                          'in the last 6 months.')
    assert len(quiet.sources) == 1 and quiet.sources[0]['claims'] == 'No Form 4 filed since 2029-07-02'
    partial = sec_edgar.insider_activity('AAPL', 1, fetch, fetch_document, today=date(2026, 10, 29)).text
    assert 'Not read: 0001140361-26-039785 (offline).' in partial and 'Newstead Jennifer' in partial
    with pytest.raises(ValueError, match='No SEC registrant'):
        sec_edgar.insider_activity('ZZZZ', 6, fetch, fetch_document)


def test_insider_activity_says_when_the_filing_list_stops_short(sec_fetch):
    fetch, fetch_document, _ = insider_fetch(sec_fetch, ('0001140361-26-040540',), since='2025-01-01')
    text = sec_edgar.insider_activity('AAPL', 24, fetch, fetch_document, today=date(2026, 10, 29)).text
    assert "EDGAR's recent-filings list reaches back only to 2025-01-03, so earlier filings are not read." in text


def test_sec_responses_are_cached_by_name_or_by_hash(tmp_path, monkeypatch):
    calls = []

    def get(url, headers, timeout):
        calls.append(headers)
        return httpx.Response(200, text='{"ok": true}', request=httpx.Request('GET', url))
    monkeypatch.setattr(sec_edgar, 'CACHE', tmp_path)
    monkeypatch.setattr(sec_edgar.httpx, 'get', get)
    monkeypatch.setenv('SEC_USER_AGENT', 'Test Person test@example.com')
    assert sec_edgar.fetch_json('https://data.sec.gov/submissions/CIK0000320193.json') == {'ok': True}
    assert sec_edgar.fetch_text('https://efts.sec.gov/LATEST/search-index?q=%22a%22') == '{"ok": true}'
    assert sec_edgar.fetch_json('https://data.sec.gov/submissions/CIK0000320193.json') == {'ok': True}
    assert calls == [{'User-Agent': 'Test Person test@example.com'}] * 2
    names = sorted(path.name for path in tmp_path.iterdir())
    assert names[0] == 'data.sec.gov_submissions_CIK0000320193.json' and names[1].startswith('efts.sec.gov_LATEST_search-index_')
