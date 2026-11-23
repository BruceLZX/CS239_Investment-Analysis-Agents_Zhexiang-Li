"""SEC EDGAR lookups that give the Fundamentals Analyst primary-source financials and insider activity.

Uses SEC's public JSON APIs and filing archive. Their fair-access policy requires a User-Agent naming a contact,
read from SEC_USER_AGENT ("Your Name you@example.com"); only SEC requests carry it. Responses are cached for a day.
"""
from collections.abc import Callable
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import time
from xml.etree import ElementTree

import httpx

from .retrieved import Retrieved, source

TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'
FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
SUBMISSIONS_URL = 'https://data.sec.gov/submissions/CIK{cik}.json'
# EDGAR's list of the company's Form 4 filings, the insider-activity source.
FORM4_LIST_URL = ('https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include'
                  '&count=40')
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
    # The 2024 taxonomy moved non-operating interest to InterestExpenseNonoperating (Tesla from 2024).
    ('Interest expense', ['InterestExpense', 'InterestExpenseNonoperating', 'InterestExpenseDebt',
                          'InterestAndDebtExpense'], 'USD', 'duration'),
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
    # Alphabet moved its dividends to PaymentsOfOrdinaryDividends in 2026.
    ('Dividends paid', ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock', 'PaymentsOfOrdinaryDividends'],
     'USD', 'duration'),
    ('Cash and equivalents', ['CashAndCashEquivalentsAtCarryingValue',
                              'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'], 'USD', 'instant'),
    ('Current marketable securities', ['MarketableSecuritiesCurrent', 'AvailableForSaleSecuritiesDebtSecuritiesCurrent',
                                       'ShortTermInvestments'], 'USD', 'instant'),
    ('Non-current marketable securities', ['MarketableSecuritiesNoncurrent',
                                           'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent'], 'USD', 'instant'),
    ('Receivables', ['AccountsReceivableNetCurrent'], 'USD', 'instant'),
    ('Inventory', ['InventoryNet'], 'USD', 'instant'),
    ('Accounts payable', ['AccountsPayableCurrent', 'AccountsPayableTradeCurrent'], 'USD', 'instant'),
    ('Current assets', ['AssetsCurrent'], 'USD', 'instant'),
    ('Current liabilities', ['LiabilitiesCurrent'], 'USD', 'instant'),
    ('Goodwill', ['Goodwill'], 'USD', 'instant'),
    ('Intangible assets', ['IntangibleAssetsNetExcludingGoodwill', 'FiniteLivedIntangibleAssetsNet'], 'USD', 'instant'),
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
               'last fiscal year + this year to date - last year to date (for EPS an approximation). '
               "ROE = net income / average stockholders' equity; ROA = net income / average total assets; ROIC "
               '(approximate) = operating income x (1 - effective tax rate) / average invested capital, where the tax '
               'rate is income tax / pretax income (21% when pretax income is not positive) and invested capital = '
               'equity + debt - cash and marketable securities; an average is of the opening and closing balances, or '
               'the closing one alone when the opening one is missing. DSO = receivables / revenue x 365; DIO = '
               'inventory / cost of revenue x 365; DPO = accounts payable / cost of revenue x 365, all from closing '
               'balances; cash conversion cycle = DSO + DIO - DPO. Interest coverage = operating income / interest '
               'expense; goodwill and intangibles count what is tagged; capex / D&A = capital expenditure / '
               'depreciation and amortization. n/m = not meaningful (a base that is not positive).')
TAX_RATE = 0.21  # the US federal rate, for ROIC when pretax income is not positive
MAX_FORM4 = 40
# Form 4 transaction codes (SEC Form 4 General Instructions, item 8).
TRANSACTION_CODES = {'P': 'purchase', 'S': 'sale', 'A': 'grant or award', 'M': 'option exercise or RSU settlement',
                     'F': 'shares withheld for tax or exercise price', 'G': 'gift', 'C': 'derivative conversion',
                     'D': 'disposition to the issuer', 'X': 'in-the-money option exercise', 'J': 'other',
                     'W': 'will or laws of descent', 'I': 'discretionary transaction', 'V': 'voluntarily reported'}

Fetch = Callable[[str], dict]
FetchText = Callable[[str], str]


def user_agent() -> str:
    agent = os.environ.get('SEC_USER_AGENT', '').strip()
    if '@' not in agent:
        raise RuntimeError('Set SEC_USER_AGENT to "Your Name you@example.com" (SEC fair-access policy).')
    return agent


def _get(url: str, timeout: int) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    name = url.split('://', 1)[1].replace('/', '_')
    if '?' in name or len(name) > 200:  # a search: name the file by its hash
        name = name.split('?', 1)[0][:100] + '_' + hashlib.sha256(url.encode()).hexdigest()[:16]
    path = CACHE / name
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        return path.read_text()
    response = httpx.get(url, headers={'User-Agent': user_agent()}, timeout=timeout)
    response.raise_for_status()
    path.write_text(response.text)
    return response.text


def fetch_json(url: str) -> dict:
    return json.loads(_get(url, 30))


def fetch_text(url: str) -> str:
    return _get(url, 60)


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


def _return_on(numerator, base) -> str:
    """A return in percent; n/m when its base (equity, assets, invested capital) is not positive."""
    if numerator is None or base is None:
        return 'n/a'
    return f'{numerator / base * 100:.1f}%' if base > 0 else 'n/m'


def _average(closing, opening):
    """The average of the opening and closing balances, or the closing one alone when the opening one is missing."""
    if closing is None:
        return None
    return (closing + opening) / 2 if opening is not None else closing


def _days_of(balance, flow) -> float | None:
    """A balance in days of a year's flow (DSO, DIO, DPO)."""
    return balance / flow * 365 if balance is not None and flow else None


def _quality(flow: Callable[[str], float | None], closing: Callable[[str], float | None],
             opening: Callable[[str], float | None], debt: float | None, opening_debt: float | None) -> dict:
    """Returns, working-capital days, interest coverage and intensity ratios (see DEFINITIONS) from one period's
    flows and its closing and opening balances, each given as a function of a METRICS label."""
    revenue, cost, operating = flow('Revenue'), flow('Cost of revenue'), flow('Operating income')
    pretax, tax, interest = flow('Pretax income'), flow('Income tax'), flow('Interest expense')
    rate = min(max(tax / pretax, 0.0), 1.0) if tax is not None and pretax and pretax > 0 else TAX_RATE

    def invested(balance: Callable[[str], float | None], owed: float | None):
        equity = balance("Stockholders' equity")
        if equity is None or owed is None:
            return None
        return equity + owed - sum(balance(label) or 0 for label in CASH_LINES)

    dso = _days_of(closing('Receivables'), revenue)
    dio = _days_of(closing('Inventory'), cost)
    dpo = _days_of(closing('Accounts payable'), cost)
    goodwill, intangibles = closing('Goodwill'), closing('Intangible assets')
    tagged = goodwill is not None or intangibles is not None
    return {
        'Return on equity (ROE)': _return_on(flow('Net income'), _average(closing("Stockholders' equity"),
                                                                          opening("Stockholders' equity"))),
        'Return on assets (ROA)': _return_on(flow('Net income'), _average(closing('Total assets'),
                                                                          opening('Total assets'))),
        'ROIC (approximate)': _return_on(operating * (1 - rate) if operating is not None else None,
                                         _average(invested(closing, debt), invested(opening, opening_debt))),
        'Days sales outstanding (DSO)': 'n/a' if dso is None else f'{dso:.1f}',
        'Days inventory outstanding (DIO)': 'n/a' if dio is None else f'{dio:.1f}',
        'Days payables outstanding (DPO)': 'n/a' if dpo is None else f'{dpo:.1f}',
        'Cash conversion cycle (days)': 'n/a' if None in (dso, dio, dpo) else f'{dso + dio - dpo:.1f}',
        'Interest coverage': _ratio(operating, interest, percent=False) if not interest or interest > 0 else 'n/m',
        'Goodwill and intangibles / total assets': (_ratio((goodwill or 0) + (intangibles or 0), closing('Total assets'))
                                                    if tagged else 'n/a'),
        'Stock-based compensation / revenue': _ratio(flow('Stock-based compensation'), revenue),
        'Capex / D&A': _ratio(flow('Capital expenditure'), flow('Depreciation and amortization'), percent=False),
    }


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
    with growth, margins, free cash flow, debt and net cash worked out, returns (ROE, ROA, approximate ROIC),
    working-capital days and the cash conversion cycle, interest coverage, goodwill and intangibles against assets,
    stock-based compensation against revenue and capex against D&A, and the latest quarter, year to date and
    trailing twelve months from 10-Q filings. The 10-Ks and the latest 10-Q are the sources."""
    company = find_company(ticker, fetch)
    facts = fetch(FACTS_URL.format(cik=company['cik']))
    annual, labels, used = {}, {}, {}
    for label, concepts, unit, kind in METRICS:
        concept, periods = _metric_periods(facts, concepts, unit, kind)
        annual[label] = (unit, periods)
        labels[label] = 'Depreciation (amortization not tagged)' if concept == 'Depreciation' else label
        used[label] = concept
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
        opening = all_ends[index - 1] if index else None  # the prior fiscal year end
        return {
            'Debt': _format_value(debt.get(end), 'USD'),
            'Revenue growth': _ratio(revenue - before, before) if revenue is not None and before else 'n/a',
            'Gross margin': _ratio(gross, revenue),
            'Operating margin': _ratio(value('Operating income', end), revenue),
            'Net margin': _ratio(net, revenue),
            'Free cash flow': _format_value(fcf, 'USD'),
            'Free cash flow / net income': _ratio(fcf, net, percent=False),
            'Net cash (debt)': _format_value(cash - debt[end], 'USD') if end in debt else 'n/a',
            **_quality(lambda label: value(label, end), lambda label: value(label, end),
                       lambda label: value(label, opening) if opening else None, debt.get(end), debt.get(opening)),
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
        ttm = _quality(lambda label: columns[label][1].get('ttm'), lambda label: columns[label][1].get('quarter'),
                       lambda label: columns[label][1].get('prior_quarter'), quarterly_debt.get(latest_end), prior_debt)
        lines.append(f'TTM ratios to {latest_end} (trailing-twelve-month flows; balances at {latest_end} and a year '
                     'earlier): ' + '; '.join(f'{label} {shown}' for label, shown in ttm.items()) + '.')
        latest = next(e for e in revenue_entries if e['end'] == latest_end)
        sources.append(filing_source(company, latest))
    debt_terms = ' + '.join(debt_concepts) or 'no debt concept reported'
    interest = f"Interest expense = {used['Interest expense']} as tagged. " if used['Interest expense'] else ''
    lines += ['', f'{DEFINITIONS} {interest}Debt = {debt_terms} as tagged; finance leases are not included.']
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
                   'Diluted shares', 'Operating cash flow', 'Capital expenditure', 'Share buybacks', 'Dividends paid',
                   'Cash and equivalents', 'Current marketable securities', 'Non-current marketable securities',
                   "Stockholders' equity")


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


def _flag(text: str | None) -> bool:
    return (text or '').strip().lower() in ('1', 'true')


def _number(text: str | None) -> float | None:
    try:
        return float((text or '').strip())
    except ValueError:
        return None


def _role(owner: ElementTree.Element) -> str:
    relationship = owner.find('reportingOwnerRelationship')
    if relationship is None:
        return ''
    roles = []
    if _flag(relationship.findtext('isOfficer')):
        roles.append((relationship.findtext('officerTitle') or '').strip() or 'Officer')
    if _flag(relationship.findtext('isDirector')):
        roles.append('Director')
    if _flag(relationship.findtext('isTenPercentOwner')):
        roles.append('10% owner')
    if _flag(relationship.findtext('isOther')):
        roles.append((relationship.findtext('otherText') or '').strip() or 'Other')
    return ', '.join(' '.join(role.split()) for role in roles)


def form4_transactions(xml: str) -> list[dict]:
    """A Form 4's non-derivative transactions: date, insider, title, code, shares, price and value, and whether the
    filing or the row's footnotes put it under a Rule 10b5-1 plan or say the shares were sold to cover tax."""
    root = ElementTree.fromstring(xml)
    owners = root.findall('reportingOwner')
    insider = '; '.join(' '.join((o.findtext('reportingOwnerId/rptOwnerName') or '').split()) for o in owners)
    title = _role(owners[0]) if owners else ''
    plan = _flag(root.findtext('aff10b5One'))
    notes = {note.get('id'): ' '.join((note.text or '').split()) for note in root.findall('footnotes/footnote')}
    found = []
    for row in root.findall('nonDerivativeTable/nonDerivativeTransaction'):
        footnotes = ' '.join(notes.get(ref.get('id'), '') for ref in row.iter('footnoteId')).lower()
        shares = _number(row.findtext('transactionAmounts/transactionShares/value'))
        price = _number(row.findtext('transactionAmounts/transactionPricePerShare/value'))
        found.append({'date': (row.findtext('transactionDate/value') or '').strip()[:10], 'insider': insider,
                      'title': title, 'code': (row.findtext('transactionCoding/transactionCode') or '').strip(),
                      'shares': shares or 0.0, 'price': price,
                      'value': shares * price if shares and price else 0.0,
                      'plan': plan or '10b5-1' in footnotes, 'tax': 'withh' in footnotes and 'tax' in footnotes})
    return found


def _usd(value: float) -> str:
    return f'${value / 1e9:,.2f}B' if value >= 1e9 else f'${value / 1e6:,.2f}M' if value >= 1e6 else f'${value:,.0f}'


def _side(trades: list[dict]) -> str:
    shares, value = sum(t['shares'] for t in trades), sum(t['value'] for t in trades)
    return f"{len(trades)} transaction{'s' if len(trades) != 1 else ''}, {shares:,.0f} shares, {_usd(value)}"


def insider_activity(ticker: str, months: int = 6, fetch: Fetch = fetch_json, fetch_document: FetchText = fetch_text,
                     today: date | None = None) -> Retrieved:
    """Insider transactions from the company's Form 4 filings over the last `months` months (1-24): purchases
    against sales by count, shares and value, the other transaction codes, the insiders with the largest purchases
    and sales, and those trades a filing at a time. Reads at most 40 filings, the most recent, and says so when the
    window holds more. EDGAR's Form 4 list and the filings with the largest trades are the sources."""
    months = max(1, min(months, 24))
    company = find_company(ticker, fetch)
    recent = fetch(SUBMISSIONS_URL.format(cik=company['cik']))['filings']['recent']
    start = ((today or date.today()) - timedelta(days=round(months * 30.44))).isoformat()
    window = [i for i, form in enumerate(recent['form']) if form == '4' and recent['filingDate'][i] >= start]
    amended = sum(form == '4/A' and recent['filingDate'][i] >= start for i, form in enumerate(recent['form']))
    listing = FORM4_LIST_URL.format(cik=company['cik'])
    retrieved = date.today().isoformat()
    header = f"Insider transactions at {company['name']} ({company['ticker']}) from Form 4 filings since {start}"
    span = f"the last {months} month{'s' if months > 1 else ''}"
    reach = recent['filingDate'][-1] if recent['filingDate'] else start
    coverage = (f" EDGAR's recent-filings list reaches back only to {reach}, so earlier filings are not read."
                if reach > start else '')
    if amended:  # an amendment restates its original, so adding both would count trades twice
        coverage += f' {amended} amended Form 4 (4/A) not read.'
    if not window:
        return Retrieved(f'{header}: none filed in {span}.{coverage}', [source(
            f"{company['name']} Form 4 filings (EDGAR)", 'primary', listing, retrieved,
            f'No Form 4 filed since {start}', f"EDGAR Form 4 filings for {company['ticker']}")])
    read, failed, trades = window[:MAX_FORM4], [], []
    for i in read:
        accession = recent['accessionNumber'][i]
        folder = filing_url(company['cik'], accession)
        document = recent['primaryDocument'][i]
        try:  # the primary document is the XML's rendering under xslF345X0n/; the XML sits in the folder
            rows = form4_transactions(fetch_document(folder + document.rsplit('/', 1)[-1]))
        except (ElementTree.ParseError, httpx.HTTPError) as exc:
            failed.append(f'{accession} ({exc})')
            continue
        trades += [dict(row, filed=recent['filingDate'][i], accession=accession, link=folder + document) for row in rows]
    first, last = recent['filingDate'][read[-1]], recent['filingDate'][read[0]]
    lines = [f'{header}: {len(window)} filed in {span}; '
             + (f'the {MAX_FORM4} most recent, filed {first} to {last}, were read (the cap).' if len(window) > MAX_FORM4
                else f'all read, filed {first} to {last}.') + coverage]
    buys = [t for t in trades if t['code'] == 'P']
    sells = [t for t in trades if t['code'] == 'S']
    lines.append(f"Purchases (code P): {_side(buys) if buys else 'none'}.")
    if sells:
        planned, taxed = [t for t in sells if t['plan']], [t for t in sells if t['tax']]
        lines.append(f'Sales (code S): {_side(sells)}; under a Rule 10b5-1 plan: {_side(planned) if planned else "none"}'
                     f'; sold to cover tax, per the footnotes: {_side(taxed) if taxed else "none"}.')
    else:
        lines.append('Sales (code S): none.')
    net = sum(t['value'] for t in buys) - sum(t['value'] for t in sells)
    lines.append(f"Purchases less sales: {'-' if net < 0 else ''}{_usd(abs(net))}.")
    others = sorted({t['code'] for t in trades} - {'P', 'S'})
    if others:
        lines.append('Other transactions: ' + '; '.join(
            f"{code} ({TRANSACTION_CODES.get(code, 'see the Form 4 instructions')}) "
            f"{_side([t for t in trades if t['code'] == code])}" for code in others) + '.')
    people: dict[str, dict] = {}
    for t in buys + sells:
        person = people.setdefault(t['insider'], {'title': t['title'], 'bought': 0.0, 'sold': 0.0})
        person['bought' if t['code'] == 'P' else 'sold'] += t['value']
    if people:
        top = sorted(people.items(), key=lambda item: item[1]['bought'] + item[1]['sold'], reverse=True)[:5]
        lines.append('Largest buyers and sellers: ' + '; '.join(
            f"{name} ({p['title'] or 'role not given'}) sold {_usd(p['sold'])}, bought {_usd(p['bought'])}"
            for name, p in top) + '.')
    # One row per filing and code for purchases and sales: a filing often splits one day's sale into lots.
    groups: dict[tuple, list[dict]] = {}
    for t in buys + sells:
        groups.setdefault((t['accession'], t['code']), []).append(t)
    if groups:
        lines += ['', '| Filed | Trade dates | Insider | Title | Code | Shares | Average price | Value | Notes | Accession |',
                  '|---|---|---|---|---|---|---|---|---|---|']
        for (accession, code), rows in groups.items():
            shares, value = sum(t['shares'] for t in rows), sum(t['value'] for t in rows)
            dates = sorted({t['date'] for t in rows})
            notes = ', '.join(note for note, on in (('10b5-1 plan', any(t['plan'] for t in rows)),
                                                     ('to cover tax', any(t['tax'] for t in rows))) if on)
            price = f'{value / shares:,.2f}' if shares and value else 'n/a'
            lines.append(f"| {rows[0]['filed']} | {dates[0]}{' to ' + dates[-1] if len(dates) > 1 else ''} | "
                         f"{rows[0]['insider']} | {rows[0]['title']} | {code} | {shares:,.0f} | {price} | "
                         f"{_usd(value)} | {notes or '-'} | {accession} |")
    if failed:
        lines += ['', 'Not read: ' + '; '.join(failed) + '.']
    lines += ['', 'Values are shares x the reported price (a weighted average where the filing says so); grants, '
              'exercises and withholdings carry no market price, so they count as $0 unless one is given.']
    sources = [source(f"{company['name']} Form 4 filings (EDGAR)", 'primary', listing, retrieved,
                      f'Insider transactions in Form 4 filings filed {first} to {last}',
                      f"EDGAR Form 4 filings for {company['ticker']}, filed {first} to {last}")]
    largest = sorted(groups.values(), key=lambda rows: sum(t['value'] for t in rows), reverse=True)
    for rows in largest[:5]:
        t = rows[0]
        if t['link'] not in {s['location'] for s in sources}:
            sources.append(source(f"{company['name']} Form 4 filed {t['filed']} by {t['insider']}", 'primary',
                                  t['link'], t['filed'], f"{t['insider']}: code {t['code']}, {_side(rows)}",
                                  f"Form 4 filed {t['filed']} by {t['insider']}, accession {t['accession']}"))
    return Retrieved('\n'.join(lines), sources)


def shares_outstanding(facts: dict) -> tuple[float | None, str | None]:
    """Shares outstanding from the latest filing's cover page, all classes added, and their date."""
    entries = _units(facts, 'EntityCommonStockSharesOutstanding', 'shares', 'dei')
    if not entries:
        return None, None
    latest = max(e['end'] for e in entries)
    filing = max(e['accn'] for e in entries if e['end'] == latest)
    return sum(e['val'] for e in entries if e['end'] == latest and e['accn'] == filing), latest
