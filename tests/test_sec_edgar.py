import pytest

from tools import sec_edgar


def test_find_company_pads_the_cik(sec_fetch):
    assert sec_edgar.find_company('aapl', sec_fetch) == {'ticker': 'AAPL', 'cik': '0000320193', 'name': 'Apple Inc.'}


def test_find_company_rejects_unknown_tickers(sec_fetch):
    with pytest.raises(ValueError, match='No SEC registrant'):
        sec_edgar.find_company('ZZZZ', sec_fetch)


def test_annual_financials_use_10k_values_from_the_current_revenue_concept(sec_fetch):
    table = sec_edgar.annual_financials('AAPL', 3, sec_fetch)
    header = table.splitlines()[1]
    assert header.count('FY ending') == 3
    assert header.endswith('FY ending 2025-09-27 |')
    # Revenues stopped in 2018; the current concept carries FY2025's annual (not quarterly) figure.
    assert '416,161M' in table
    assert '0000320193-25-000079' in table
    assert 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/' in table
    total_assets = next(line for line in table.splitlines() if line.startswith('| Total assets |'))
    assert 'n/a' not in total_assets


def test_annual_financials_cap_the_number_of_years(sec_fetch):
    header = sec_edgar.annual_financials('AAPL', 10, sec_fetch).splitlines()[1]
    assert header.count('FY ending') == 5


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
