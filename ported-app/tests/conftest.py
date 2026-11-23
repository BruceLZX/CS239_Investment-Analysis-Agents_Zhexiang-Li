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


@pytest.fixture(autouse=True)
def runs_dir(tmp_path_factory, monkeypatch):
    """Point the case file at a temporary runs/ folder, in every test: a tool called with the real folder would
    write its call into the tool log of whatever run is live. It is not inside tmp_path, which tests use as a
    folder of their own."""
    runs = tmp_path_factory.mktemp('runs')
    monkeypatch.setattr(case_file, 'RUNS', runs)
    return runs
