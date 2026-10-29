"""SEC EDGAR lookups that give the Fundamentals Analyst primary-source financials.

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

from .retrieved import Retrieved, source

TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
CACHE = Path(__file__).resolve().parents[1] / 'runs' / '.cache' / 'sec'
CACHE_SECONDS = 24 * 3600

# (label, us-gaap concepts in preference order, unit, period kind). Companies name some lines differently.
METRICS = [
    ('Revenue', ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues',
                 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'], 'USD', 'duration'),
    ('Cost of revenue', ['CostOfGoodsAndServicesSold', 'CostOfRevenue', 'CostOfGoodsSold'], 'USD', 'duration'),
    ('Gross profit', ['GrossProfit'], 'USD', 'duration'),
    ('Research and development', ['ResearchAndDevelopmentExpense',
                                  'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost'], 'USD', 'duration'),
    ('Selling, general and administrative', ['SellingGeneralAndAdministrativeExpense'], 'USD', 'duration'),
    ('Operating income', ['OperatingIncomeLoss'], 'USD', 'duration'),
    ('Pretax income', ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                       'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments'],
     'USD', 'duration'),
    ('Income tax', ['IncomeTaxExpenseBenefit'], 'USD', 'duration'),
    ('Net income', ['NetIncomeLoss'], 'USD', 'duration'),
    ('Diluted EPS', ['EarningsPerShareDiluted'], 'USD/shares', 'duration'),
    ('Diluted shares', ['WeightedAverageNumberOfDilutedSharesOutstanding'], 'shares', 'duration'),
    ('Operating cash flow', ['NetCashProvidedByUsedInOperatingActivities'], 'USD', 'duration'),
    ('Capital expenditure', ['PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets'],
     'USD', 'duration'),
    ('Depreciation and amortization', ['DepreciationDepletionAndAmortization', 'DepreciationAmortizationAndAccretionNet',
                                       'DepreciationAndAmortization', 'Depreciation'], 'USD', 'duration'),
    ('Stock-based compensation', ['ShareBasedCompensation', 'AllocatedShareBasedCompensationExpense'], 'USD', 'duration'),
    ('Share buybacks', ['PaymentsForRepurchaseOfCommonStock'], 'USD', 'duration'),
    ('Dividends paid', ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock'], 'USD', 'duration'),
    ('Cash and equivalents', ['CashAndCashEquivalentsAtCarryingValue',
                              'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'], 'USD', 'instant'),
    ('Current marketable securities', ['MarketableSecuritiesCurrent', 'AvailableForSaleSecuritiesDebtSecuritiesCurrent',
                                       'ShortTermInvestments'], 'USD', 'instant'),
    ('Non-current marketable securities', ['MarketableSecuritiesNoncurrent',
                                           'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent'], 'USD', 'instant'),
    ('Receivables', ['AccountsReceivableNetCurrent'], 'USD', 'instant'),
    ('Inventory', ['InventoryNet'], 'USD', 'instant'),
    ('Current assets', ['AssetsCurrent'], 'USD', 'instant'),
    ('Current liabilities', ['LiabilitiesCurrent'], 'USD', 'instant'),
    ('Total assets', ['Assets'], 'USD', 'instant'),
    ('Total liabilities', ['Liabilities'], 'USD', 'instant'),
    ("Stockholders' equity", ['StockholdersEquity',
                              'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'], 'USD', 'instant'),
]
# Cash for net cash and enterprise value: Apple, for one, holds most of its securities as non-current.
CASH_LINES = ('Cash and equivalents', 'Current marketable securities', 'Non-current marketable securities')
# Debt adds noncurrent debt, current debt, commercial paper and short-term borrowings, each from the first concept
# here that a company reports: Apple tags LongTermDebtNoncurrent, Tesla tags its noncurrent debt LongTermDebt.
DEBT_PARTS = (('LongTermDebtNoncurrent', 'LongTermDebt'), ('LongTermDebtCurrent', 'DebtCurrent'), ('CommercialPaper',),
              ('ShortTermBorrowings',))
DEFINITIONS = ('Definitions: free cash flow = operating cash flow - capital expenditure; net cash = cash and '
               'equivalents + current and non-current marketable securities - debt; trailing twelve months (TTM) = '
               'last fiscal year + this year to date - last year to date (for EPS an approximation).')

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


def _units(facts: dict, concept: str, unit: str, taxonomy: str = 'us-gaap') -> list[dict]:
    return facts.get('facts', {}).get(taxonomy, {}).get(concept, {}).get('units', {}).get(unit, [])


def _days(entry: dict) -> int:
    return (date.fromisoformat(entry['end']) - date.fromisoformat(entry['start'])).days


def _year_before(day: str) -> date:
    d = date.fromisoformat(day)
    return date(d.year - 1, d.month, min(d.day, 28) if d.month == 2 else d.day)


def _near(day: str, target: date, slack: int = 10) -> bool:
    return abs((date.fromisoformat(day) - target).days) <= slack


def _annual_entries(units: list[dict], kind: str) -> dict[str, dict]:
    """One 10-K value per fiscal period end, taken from the filing that first reported it."""
    periods: dict[str, dict] = {}
    for entry in units:
        if not entry.get('form', '').startswith('10-K') or entry.get('fp') != 'FY':
            continue
        if kind == 'duration':
            if 'start' not in entry or not 350 <= _days(entry) <= 380:
                continue
        elif 'start' in entry:
            continue
        current = periods.get(entry['end'])
        if current is None or entry['filed'] < current['filed']:
            periods[entry['end']] = entry
    return periods


def _metric_periods(facts: dict, concepts: list[str], unit: str, kind: str) -> tuple[str | None, dict[str, dict]]:
    """The concept with the most recent data, and its annual values; companies switch concepts over time."""
    used, best = None, {}
    for concept in concepts:
        periods = _annual_entries(_units(facts, concept, unit), kind)
        if periods and (not best or max(periods) > max(best)):
            used, best = concept, periods
    return used, best


def _periodic_entries(facts: dict, concepts: list[str], unit: str, kind: str) -> list[dict]:
    """Every 10-K and 10-Q value of the concept with the most recent data, one per period, each from the filing
    that first reported it."""
    best: list[dict] = []
    for concept in concepts:
        periods: dict[tuple, dict] = {}
        for entry in _units(facts, concept, unit):
            if not entry.get('form', '').startswith(('10-K', '10-Q')) or (kind == 'duration') != ('start' in entry):
                continue
            key = (entry.get('start'), entry['end'])
            if key not in periods or entry['filed'] < periods[key]['filed']:
                periods[key] = entry
        entries = list(periods.values())
        if entries and (not best or max(e['end'] for e in entries) > max(e['end'] for e in best)):
            best = entries
    return best


def _latest(entries: list[dict], annual: dict[str, dict], end: str, kind: str) -> dict:
    """The latest-period columns at `end`: the quarter, the same quarter a year earlier, the year to date and the
    same span a year earlier, and the trailing twelve months; for a balance, its value now and a year earlier."""
    prior_end = _year_before(end)
    if kind == 'instant':
        return {'quarter': next((e['val'] for e in entries if e['end'] == end), None),
                'prior_quarter': next((e['val'] for e in entries if _near(e['end'], prior_end)), None)}
    at_end = [e for e in entries if e['end'] == end]
    earlier = [e for e in entries if _near(e['end'], prior_end)]
    quarter = next((e for e in at_end if 80 <= _days(e) <= 100), None)
    prior_quarter = next((e for e in earlier if 80 <= _days(e) <= 100), None)
    ytd = max(at_end, key=_days, default=None)
    prior_ytd = ytd and next((e for e in earlier if abs(_days(e) - _days(ytd)) <= 10), None)
    if ytd and _days(ytd) >= 350:
        ttm = ytd['val']
    else:
        last_year = max((e for k, e in annual.items() if k < end), key=lambda e: e['end'], default=None)
        ttm = last_year['val'] + ytd['val'] - prior_ytd['val'] if ytd and prior_ytd and last_year else None
    return {'quarter': quarter and quarter['val'], 'prior_quarter': prior_quarter and prior_quarter['val'],
            'ytd': ytd and ytd['val'], 'prior_ytd': prior_ytd and prior_ytd['val'], 'ttm': ttm,
            'ytd_months': ytd and round(_days(ytd) / 30.4)}


def _debt(select: Callable[[str], dict]) -> tuple[dict, list[str]]:
    """Debt per period end (DEBT_PARTS), and the concepts it adds up. select gives a concept's values by end."""
    totals: dict = {}
    used = []
    for choices in DEBT_PARTS:
        options = [(concept, values) for concept in choices if (values := select(concept))]
        if options:  # the concept with the most recent data, as for every other line
            concept, values = max(options, key=lambda option: max(option[1]))
            used.append(concept)
            for end, value in values.items():
                totals[end] = totals.get(end, 0) + value
    return totals, used


def _format_value(value: float | None, unit: str) -> str:
    if value is None:
        return 'n/a'
    if unit == 'USD/shares':
        return f'{value:.2f}'
    return f'{value / 1e6:,.0f}M'


def _ratio(numerator, denominator, percent: bool = True) -> str:
    if numerator is None or not denominator:
        return 'n/a'
    return f'{numerator / denominator * 100:.1f}%' if percent else f'{numerator / denominator:.2f}x'


def filing_url(cik: str, accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def filing_source(company: dict, entry: dict) -> dict:
    form, end = entry['form'], entry['end']
    return source(f"{company['name']} {form} for the period ending {end}", 'primary filing',
                  filing_url(company['cik'], entry['accn']), entry['filed'],
                  f'XBRL financial statements for the period ending {end}',
                  f"{form} for the period ending {end}, accession {entry['accn']}, filed {entry['filed']}")


def statements(ticker: str, years: int = 3, fetch: Fetch = fetch_json) -> Retrieved:
    """The income statement, cash flow and balance sheet lines from 10-K XBRL filings for up to five fiscal years,
    with growth, margins, free cash flow, debt and net cash worked out, and the latest quarter, year to date and
    trailing twelve months from 10-Q filings. The 10-Ks and the latest 10-Q are the sources."""
    company = find_company(ticker, fetch)
    facts = fetch(FACTS_URL.format(cik=company['cik']))
    annual, labels = {}, {}
    for label, concepts, unit, kind in METRICS:
        concept, periods = _metric_periods(facts, concepts, unit, kind)
        annual[label] = (unit, periods)
        labels[label] = 'Depreciation (amortization not tagged)' if concept == 'Depreciation' else label
    anchor = annual['Revenue'][1] or next((periods for _, periods in annual.values() if periods), {})
    if not anchor:
        raise ValueError(f"No annual 10-K XBRL figures found for {company['ticker']}.")
    all_ends = sorted(anchor)
    ends = all_ends[-max(1, min(years, 5)):]
    debt, debt_concepts = _debt(lambda concept: {end: e['val'] for end, e in
                                                 _metric_periods(facts, [concept], 'USD', 'instant')[1].items()})

    def value(label: str, end: str):
        entry = annual[label][1].get(end)
        return entry['val'] if entry else None

    def derived(end: str) -> dict:
        index = all_ends.index(end)
        revenue = value('Revenue', end)
        before = value('Revenue', all_ends[index - 1]) if index else None
        gross = value('Gross profit', end)
        if gross is None and revenue is not None and value('Cost of revenue', end) is not None:
            gross = revenue - value('Cost of revenue', end)
        ocf, capex, net = value('Operating cash flow', end), value('Capital expenditure', end), value('Net income', end)
        fcf = ocf - capex if ocf is not None and capex is not None else None
        cash = sum(value(label, end) or 0 for label in CASH_LINES)
        return {
            'Debt': _format_value(debt.get(end), 'USD'),
            'Revenue growth': _ratio(revenue - before, before) if revenue is not None and before else 'n/a',
            'Gross margin': _ratio(gross, revenue),
            'Operating margin': _ratio(value('Operating income', end), revenue),
            'Net margin': _ratio(net, revenue),
            'Free cash flow': _format_value(fcf, 'USD'),
            'Free cash flow / net income': _ratio(fcf, net, percent=False),
            'Net cash (debt)': _format_value(cash - debt[end], 'USD') if end in debt else 'n/a',
        }

    lines = [f"{company['name']} ({company['ticker']}, CIK {company['cik']}): financial statements from 10-K and "
             f"10-Q XBRL filings. USD; M = millions.",
             '| Metric | ' + ' | '.join(f'FY ending {end}' for end in ends) + ' |',
             '|---|' + '---|' * len(ends)]
    for label, (unit, periods) in annual.items():
        lines.append(f'| {labels[label]} | ' + ' | '.join(_format_value(value(label, end), unit) for end in ends) + ' |')
    worked = [derived(end) for end in ends]
    for label in worked[0]:
        lines.append(f'| {label} | ' + ' | '.join(column[label] for column in worked) + ' |')
    sources = [filing_source(company, anchor[end]) for end in ends]

    revenue_entries = _periodic_entries(facts, METRICS[0][1], 'USD', 'duration')
    latest_end = max((e['end'] for e in revenue_entries), default=None)
    if latest_end and latest_end > ends[-1]:
        columns = {label: (unit, _latest(_periodic_entries(facts, concepts, unit, kind), annual[label][1], latest_end, kind))
                   for label, concepts, unit, kind in METRICS}
        months = columns['Revenue'][1].get('ytd_months')
        lines += ['', f'Latest periods, to {latest_end}:',
                  f'| Metric | Quarter ending {latest_end} | Same quarter a year earlier | '
                  f'{months} months to date | Same span a year earlier | TTM |', '|---|---|---|---|---|---|']
        for label, (unit, cells) in columns.items():
            row = [cells.get(k) for k in ('quarter', 'prior_quarter', 'ytd', 'prior_ytd', 'ttm')]
            if label == 'Diluted shares':
                row[4] = None
            lines.append(f'| {labels[label]} | ' + ' | '.join(_format_value(v, unit) for v in row) + ' |')
        quarterly_debt, _ = _debt(lambda concept: {e['end']: e['val'] for e in
                                                   _periodic_entries(facts, [concept], 'USD', 'instant')})
        prior_end = _year_before(latest_end)
        prior_debt = next((v for end, v in quarterly_debt.items() if _near(end, prior_end)), None)
        lines.append(f"| Debt | {_format_value(quarterly_debt.get(latest_end), 'USD')} | "
                     f"{_format_value(prior_debt, 'USD')} | n/a | n/a | n/a |")
        latest = next(e for e in revenue_entries if e['end'] == latest_end)
        sources.append(filing_source(company, latest))
    debt_terms = ' + '.join(debt_concepts) or 'no debt concept reported'
    lines += ['', f'{DEFINITIONS} Debt = {debt_terms} as tagged; finance leases are not included.']
    return Retrieved('\n'.join(lines), sources)


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


VALUATION_LINES = ('Revenue', 'Operating income', 'Depreciation and amortization', 'Net income', 'Diluted EPS',
                   'Diluted shares', 'Operating cash flow', 'Capital expenditure', 'Cash and equivalents',
                   'Current marketable securities', 'Non-current marketable securities', "Stockholders' equity")


def fundamentals(facts: dict) -> dict:
    """What a valuation needs, by line: each fiscal year's values, and the latest ones (trailing twelve months for
    flows, the latest balance sheet), each with the 10-K or 10-Q entry they come from, and the debt concepts used."""
    spec = {label: (concepts, unit, kind) for label, concepts, unit, kind in METRICS}
    annual = {label: _metric_periods(facts, *spec[label])[1] for label in VALUATION_LINES}
    debt, debt_concepts = _debt(lambda concept: {end: e['val'] for end, e in
                                                 _metric_periods(facts, [concept], 'USD', 'instant')[1].items()})
    years = [{'end': end, 'entry': entry, 'Debt': debt.get(end),
              **{label: annual[label][end]['val'] if end in annual[label] else None for label in VALUATION_LINES}}
             for end, entry in sorted(annual['Revenue'].items())]
    revenue_entries = _periodic_entries(facts, spec['Revenue'][0], 'USD', 'duration')
    latest_end = max((e['end'] for e in revenue_entries), default=None)
    if not years or not latest_end or latest_end <= years[-1]['end']:
        return {'years': years, 'latest': years[-1] if years else None, 'debt_concepts': debt_concepts}
    latest = {'end': latest_end, 'entry': next(e for e in revenue_entries if e['end'] == latest_end)}
    for label in VALUATION_LINES:
        concepts, unit, kind = spec[label]
        cells = _latest(_periodic_entries(facts, concepts, unit, kind), annual[label], latest_end, kind)
        # A share count is an average over the period, so it has no trailing-twelve-month sum.
        latest[label] = cells['quarter'] if kind == 'instant' or label == 'Diluted shares' else cells['ttm']
    quarterly_debt, _ = _debt(lambda concept: {e['end']: e['val'] for e in
                                               _periodic_entries(facts, [concept], 'USD', 'instant')})
    latest['Debt'] = quarterly_debt.get(latest_end)
    return {'years': years, 'latest': latest, 'debt_concepts': debt_concepts}


def shares_outstanding(facts: dict) -> tuple[float | None, str | None]:
    """Shares outstanding from the latest filing's cover page, all classes added, and their date."""
    entries = _units(facts, 'EntityCommonStockSharesOutstanding', 'shares', 'dei')
    if not entries:
        return None, None
    latest = max(e['end'] for e in entries)
    filing = max(e['accn'] for e in entries if e['end'] == latest)
    return sum(e['val'] for e in entries if e['end'] == latest and e['accn'] == filing), latest
