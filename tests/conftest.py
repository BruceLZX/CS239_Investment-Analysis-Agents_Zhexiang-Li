import pytest

from tools import case_file

from .helpers import load_fixture

SEC_ROUTES = {
    'https://www.sec.gov/files/company_tickers.json': 'sec_company_tickers.json',
    'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json': 'sec_companyfacts_aapl.json',
    'https://data.sec.gov/submissions/CIK0000320193.json': 'sec_submissions_aapl.json',
}


@pytest.fixture
def sec_fetch():
    """Serve recorded SEC responses instead of calling sec.gov."""
    return lambda url: load_fixture(SEC_ROUTES[url])


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    """Point the case file at a temporary runs/ folder."""
    runs = tmp_path / 'runs'
    runs.mkdir()
    monkeypatch.setattr(case_file, 'RUNS', runs)
    return runs
