"""SEC EDGAR lookups that give the Research Analyst primary-source financials.

Uses SEC's public JSON APIs. Their fair-access policy requires a User-Agent naming a contact,
read from SEC_USER_AGENT ("Your Name you@example.com"). Responses are cached for a day.
"""
from collections.abc import Callable
from datetime import date
import json
import os
from pathlib import Path
import time

import httpx

TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
CACHE = Path(__file__).resolve().parents[1] / 'runs' / '.cache' / 'sec'
CACHE_SECONDS = 24 * 3600

# (label, us-gaap concepts in preference order, unit, period kind)
METRICS = [
    ('Revenue', ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues',
                 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'], 'USD', 'duration'),
    ('Net income', ['NetIncomeLoss'], 'USD', 'duration'),
    ('Diluted EPS', ['EarningsPerShareDiluted'], 'USD/shares', 'duration'),
    ('Operating cash flow', ['NetCashProvidedByUsedInOperatingActivities'], 'USD', 'duration'),
    ('Capital expenditure', ['PaymentsToAcquirePropertyPlantAndEquipment'], 'USD', 'duration'),
    ('Cash and equivalents', ['CashAndCashEquivalentsAtCarryingValue'], 'USD', 'instant'),
    ('Total assets', ['Assets'], 'USD', 'instant'),
    ('Total liabilities', ['Liabilities'], 'USD', 'instant'),
    ("Stockholders' equity", ['StockholdersEquity'], 'USD', 'instant'),
]

Fetch = Callable[[str], dict]


def user_agent() -> str:
    agent = os.environ.get('SEC_USER_AGENT', '').strip()
    if '@' not in agent:
        raise RuntimeError('Set SEC_USER_AGENT to "Your Name you@example.com" (SEC fair-access policy).')
    return agent


def fetch_json(url: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / url.split('://', 1)[1].replace('/', '_')
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        return json.loads(path.read_text())
    response = httpx.get(url, headers={'User-Agent': user_agent()}, timeout=30)
    response.raise_for_status()
    path.write_text(response.text)
    return response.json()


def find_company(ticker: str, fetch: Fetch = fetch_json) -> dict:
    wanted = ticker.strip().upper()
    for row in fetch(TICKERS_URL).values():
        if row['ticker'].upper() == wanted:
            return {'ticker': row['ticker'], 'cik': f"{row['cik_str']:010d}", 'name': row['title']}
    raise ValueError(f'No SEC registrant found for ticker {ticker!r}.')


def _annual_entries(units: list[dict], kind: str) -> dict[str, dict]:
    """One 10-K value per fiscal period end, taken from the filing that first reported it."""
    periods: dict[str, dict] = {}
    for entry in units:
        if not entry.get('form', '').startswith('10-K') or entry.get('fp') != 'FY':
            continue
        if kind == 'duration':
            if 'start' not in entry:
                continue
            days = (date.fromisoformat(entry['end']) - date.fromisoformat(entry['start'])).days
            if not 350 <= days <= 380:
                continue
        elif 'start' in entry:
            continue
        current = periods.get(entry['end'])
        if current is None or entry['filed'] < current['filed']:
            periods[entry['end']] = entry
    return periods


def _metric_periods(facts: dict, concepts: list[str], unit: str, kind: str) -> dict[str, dict]:
    """Use the concept with the most recent data; companies switch concepts over time."""
    best: dict[str, dict] = {}
    for concept in concepts:
        units = facts.get('facts', {}).get('us-gaap', {}).get(concept, {}).get('units', {}).get(unit, [])
        periods = _annual_entries(units, kind)
        if periods and (not best or max(periods) > max(best)):
            best = periods
    return best


def _format_value(value: float, unit: str) -> str:
    if unit == 'USD/shares':
        return f'{value:.2f}'
    return f'{value / 1e6:,.0f}M'


def filing_url(cik: str, accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def annual_financials(ticker: str, years: int = 3, fetch: Fetch = fetch_json) -> str:
    company = find_company(ticker, fetch)
    facts = fetch(FACTS_URL.format(cik=company['cik']))
    metrics = [(label, unit, _metric_periods(facts, concepts, unit, kind))
               for label, concepts, unit, kind in METRICS]
    anchor = next((periods for _, _, periods in metrics if periods), {})
    if not anchor:
        raise ValueError(f"No annual 10-K XBRL figures found for {company['ticker']}.")
    ends = sorted(anchor)[-max(1, min(years, 5)):]
    lines = [f"{company['name']} ({company['ticker']}, CIK {company['cik']}): annual figures from "
             f"10-K XBRL filings. USD; M = millions.",
             '| Metric | ' + ' | '.join(f'FY ending {end}' for end in ends) + ' |',
             '|---|' + '---|' * len(ends)]
    for label, unit, periods in metrics:
        cells = [_format_value(periods[end]['val'], unit) if end in periods else 'n/a' for end in ends]
        lines.append(f'| {label} | ' + ' | '.join(cells) + ' |')
    lines.append('Primary sources (register each 10-K you cite):')
    for end in ends:
        entry = anchor[end]
        lines.append(f"- FY ending {end}: {entry['form']} accession {entry['accn']}, filed {entry['filed']}, "
                     f"{filing_url(company['cik'], entry['accn'])}")
    return '\n'.join(lines)


def recent_filings(ticker: str, forms: list[str] | None = None, limit: int = 8,
                   fetch: Fetch = fetch_json) -> str:
    company = find_company(ticker, fetch)
    wanted = set(forms or ['10-K', '10-Q', '8-K', 'DEF 14A'])
    recent = fetch(SUBMISSIONS_URL.format(cik=company['cik']))['filings']['recent']
    lines = [f"Recent SEC filings for {company['name']} ({company['ticker']}):"]
    for i, form in enumerate(recent['form']):
        if form not in wanted:
            continue
        accession = recent['accessionNumber'][i]
        url = filing_url(company['cik'], accession) + recent['primaryDocument'][i]
        lines.append(f"- {form} filed {recent['filingDate'][i]} (period {recent['reportDate'][i] or 'n/a'}): "
                     f"accession {accession}, {url}")
        if len(lines) > max(1, min(limit, 20)):
            break
    return '\n'.join(lines)
