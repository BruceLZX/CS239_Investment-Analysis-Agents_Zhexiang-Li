"""A valuation snapshot from primary data: prices from Yahoo, financials from SEC XBRL filings.

Every multiple is worked out here from figures the result names, for the company, its peers, and the company at
each of its last five fiscal year ends, so the Valuation part compares like with like instead of quoting a site's
multiples. Companies that do not file US GAAP statements with the SEC (most foreign issuers) are shown as n/a.
"""
from datetime import datetime, timezone
from statistics import median

import httpx

from . import prices, sec_edgar
from .retrieved import Retrieved

MAX_PEERS = 4
HOW = ('How these are built: market cap = latest price x shares outstanding from the latest filing cover page (all '
       'classes); EV = market cap + debt - cash and equivalents - current marketable securities; earnings, sales, '
       'EBITDA (operating income + depreciation and amortization) and free cash flow (operating cash flow - capital '
       'expenditure) are trailing twelve months from 10-K and 10-Q XBRL; P/B uses the latest stockholders\' equity. '
       'Year-end multiples use the closing price on or before the fiscal year end, that year\'s diluted EPS, and '
       'diluted shares as an approximation of shares outstanding. n/m = not meaningful (a negative or zero denominator) or not available (no debt figure, so no EV). '
       'XBRL company facts leave out figures tagged by segment or share class, so a company with a finance arm or '
       'several share classes can show too little debt or no share count; check its balance sheet (read_sec_filing, '
       '10-K item 8) before relying on its EV, and note the "Figures to" date.')


def _multiple(numerator, denominator) -> float | None:
    return numerator / denominator if numerator is not None and denominator and denominator > 0 else None


def _shown(value: float | None, kind: str = 'x') -> str:
    if value is None:
        return 'n/m'
    return f'{value * 100:.1f}%' if kind == '%' else f'{value:.1f}x'


def _money(value: float | None) -> str:
    return 'n/a' if value is None else f'{value / 1e9:,.1f}B'


def _company(ticker: str, fetch_json: sec_edgar.Fetch, fetch_chart: prices.Fetch, history: bool) -> dict:
    company = sec_edgar.find_company(ticker, fetch_json)
    facts = fetch_json(sec_edgar.FACTS_URL.format(cik=company['cik']))
    if not facts.get('facts', {}).get('us-gaap'):
        raise ValueError('it does not file US GAAP XBRL statements with the SEC')
    figures = sec_edgar.fundamentals(facts)
    latest = figures['latest']
    if not latest:
        raise ValueError('no 10-K XBRL figures')
    meta, points = prices.chart(company['ticker'], '5y' if history else '1y', fetch_chart)
    price = meta['regularMarketPrice']
    shares, shares_date = sec_edgar.shares_outstanding(facts)
    approximate = shares is None and latest['Diluted shares'] is not None
    if approximate:  # Multi-class companies tag cover-page shares by class, which the XBRL company facts leave out.
        shares = latest['Diluted shares']
    cap = price * shares if shares else None
    cash = (latest['Cash and equivalents'] or 0) + (latest['Current marketable securities'] or 0)
    # Unknown debt leaves EV unknown rather than understated.
    ev = cap + latest['Debt'] - cash if cap is not None and latest['Debt'] is not None else None
    ebitda = (latest['Operating income'] + (latest['Depreciation and amortization'] or 0)
              if latest['Operating income'] is not None else None)
    fcf = (latest['Operating cash flow'] - latest['Capital expenditure']
           if latest['Operating cash flow'] is not None and latest['Capital expenditure'] is not None else None)
    row = {'company': company, 'meta': meta, 'price': price, 'debt': latest['Debt'],
           'debt_concepts': figures['debt_concepts'], 'time': datetime.fromtimestamp(meta['regularMarketTime'], timezone.utc).isoformat(timespec='minutes'),
           'cap': cap, 'ev': ev, 'shares_date': shares_date, 'approximate_shares': approximate,
           'figures_to': latest['end'],
           'P/E': _multiple(price, latest['Diluted EPS']), 'EV/Sales': _multiple(ev, latest['Revenue']),
           'EV/EBITDA': _multiple(ev, ebitda), 'FCF yield': _multiple(fcf, cap) if fcf is not None else None,
           'P/B': _multiple(cap, latest["Stockholders' equity"]),
           'sources': [sec_edgar.filing_source(company, latest['entry']),
                       prices.chart_source(meta, 'price used for market cap and multiples')]}
    if history:
        row['history'] = []
        for year in figures['years'][-5:]:
            close = prices.close_on_or_before(points, datetime.fromisoformat(year['end']).replace(tzinfo=timezone.utc))
            shares_then = year['Diluted shares']
            ev_then = (close * shares_then + year['Debt'] - (year['Cash and equivalents'] or 0)
                       - (year['Current marketable securities'] or 0)) if close and shares_then and year['Debt'] is not None else None
            row['history'].append({'end': year['end'], 'price': close, 'eps': year['Diluted EPS'],
                                   'P/E': _multiple(close, year['Diluted EPS']), 'EV/Sales': _multiple(ev_then, year['Revenue']),
                                   'source': sec_edgar.filing_source(company, year['entry'])})
    return row


def snapshot(ticker: str, peers: list[str] | None = None, fetch_json: sec_edgar.Fetch = sec_edgar.fetch_json,
             fetch_chart: prices.Fetch = prices.fetch_chart) -> Retrieved:
    """Price, market cap, EV and multiples for the company and up to four peers, the company's multiples at its last
    five fiscal year ends, the peer median, and the company's premium or discount to it."""
    names = [ticker.strip().upper()] + [p.strip().upper() for p in (peers or []) if p.strip()][:MAX_PEERS]
    rows, missing, sources = [], [], []
    for index, name in enumerate(names):
        try:
            row = _company(name, fetch_json, fetch_chart, history=index == 0)
        except (ValueError, KeyError, httpx.HTTPError) as exc:
            if index == 0:
                raise ValueError(f'No valuation for {name}: {exc}') from exc
            missing.append(f'{name}: n/a ({exc})')
            continue
        rows.append(row)
        sources += row['sources'] + [year['source'] for year in row.get('history', [])]
    company = rows[0]
    columns = ('P/E', 'EV/Sales', 'EV/EBITDA', 'FCF yield', 'P/B')
    lines = [f"Valuation snapshot for {company['company']['name']} ({company['company']['ticker']}) and peers, "
             f"in each company's trading currency; B = billions.",
             '| Company | Price (time, UTC) | Market cap | EV | P/E (TTM) | EV/Sales | EV/EBITDA | FCF yield | P/B | '
             'Figures to |', '|---|---|---|---|---|---|---|---|---|---|']
    for row in rows:
        cells = [_shown(row[c], '%' if c == 'FCF yield' else 'x') for c in columns]
        lines.append(f"| {row['company']['ticker']} | {row['price']:.2f} ({row['time']}) | {_money(row['cap'])} | "
                     f"{_money(row['ev'])} | " + ' | '.join(cells) + f" | {row['figures_to']} |")
    peer_rows = rows[1:]
    if peer_rows:
        medians = {c: median(v for r in peer_rows if (v := r[c]) is not None)
                   if any(r[c] is not None for r in peer_rows) else None for c in columns}
        lines.append('| Peer median | | | | ' + ' | '.join(_shown(medians[c], '%' if c == 'FCF yield' else 'x')
                                                       for c in columns) + ' | |')
        gaps = [f'{c} {(company[c] / medians[c] - 1) * 100:+.0f}%' for c in ('P/E', 'EV/Sales', 'EV/EBITDA')
                if company[c] is not None and medians[c]]
        if gaps:
            lines.append(f"{company['company']['ticker']} against the peer median (premium + / discount -): "
                         + ', '.join(gaps) + '.')
    lines.append('Debt counted in EV: ' + '; '.join(
        f"{row['company']['ticker']} {_money(row['debt'])} ({' + '.join(row['debt_concepts']) or 'none tagged'})"
        for row in rows) + '.')
    lines += missing
    lines += [f"{row['company']['ticker']}: market cap uses the latest quarter's diluted share count, since the filing "
              'tags its cover-page shares by class.' for row in rows if row['approximate_shares']]
    lines += ['', f"{company['company']['ticker']} at its fiscal year ends:",
              '| Fiscal year end | Price | Diluted EPS | P/E | EV/Sales (approx.) |', '|---|---|---|---|---|']
    for year in company['history']:
        price = f"{year['price']:.2f}" if year['price'] else 'n/a (before the price history)'
        eps = f"{year['eps']:.2f}" if year['eps'] is not None else 'n/a'
        lines.append(f"| {year['end']} | {price} | {eps} | {_shown(year['P/E'])} | {_shown(year['EV/Sales'])} |")
    lines += ['', HOW]
    return Retrieved('\n'.join(lines), sources)
