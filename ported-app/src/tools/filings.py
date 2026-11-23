"""The text of a company's 10-K, 10-Q, 8-K and proxy (DEF 14A) filings, read and searched on this machine.

Reading a filing through this tool gives the analysts its own words (the business, segments, risk factors,
management's discussion, an earnings release, the board and its pay) as a primary source without fetching sec.gov
through Rakazo, whose fetch guard holds URLs a bot did not search for. Keyword searches of a filing run here, so their
terms never leave this machine.
"""
from collections import Counter
from collections.abc import Callable
import html
import re
from urllib.parse import urljoin

import httpx

from . import sec_edgar
from .retrieved import Retrieved, source

ITEMS = {
    '10-K': {'1': 'Business', '1A': 'Risk Factors', '1B': 'Unresolved Staff Comments', '1C': 'Cybersecurity',
             '2': 'Properties', '3': 'Legal Proceedings', '4': 'Mine Safety Disclosures',
             '5': "Market for the Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of "
                  'Equity Securities',
             '7': "Management's Discussion and Analysis",
             '7A': 'Quantitative and Qualitative Disclosures About Market Risk',
             '8': 'Financial Statements and Supplementary Data', '9A': 'Controls and Procedures',
             '10': 'Directors, Executive Officers and Corporate Governance', '11': 'Executive Compensation',
             '12': 'Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters',
             '13': 'Certain Relationships and Related Transactions, and Director Independence',
             '14': 'Principal Accountant Fees and Services', 'EX-21': 'Exhibit 21, subsidiaries of the registrant'},
    '10-Q': {'1': 'Financial Statements', '2': "Management's Discussion and Analysis", '1A': 'Risk Factors'},
    '8-K': {'2.02': 'Results of Operations and Financial Condition',
            '5.02': 'Departure or Election of Directors and Officers; Compensatory Arrangements',
            '7.01': 'Regulation FD Disclosure', '8.01': 'Other Events', '9.01': 'Financial Statements and Exhibits',
            '99.1': 'Exhibit 99.1, the press release'},
}
PAGE_CHARS = 9_000
HEADING_RE = re.compile(r'^item\s*(\d{1,2}[a-c]?)\b\s*[.:\-–—]?', re.I)
CURRENT_REPORT_HEADING_RE = re.compile(r'^item\s*(\d{1,2}\.\d{2})\b\s*[.:\-–—]?', re.I)  # 8-K items: 2.02
END_RE = re.compile(r'^signatures?\s*$', re.I)
BLOCK_RE = re.compile(r'<\s*/?\s*(?:p|div|br|tr|li|h[1-6]|table|section|center)\b[^>]*>', re.I)
INVISIBLE_RE = re.compile('[​-‍﻿]')
INCORPORATED_RE = re.compile(r'incorporated\s+(herein\s+)?by\s+reference', re.I)
# The proxy section that answers a 10-K Part III item incorporated by reference.
PROXY_FOR_ITEM = {'10': 'directors', '11': 'compensation', '12': 'ownership', '13': 'related', '14': 'auditor'}

# Proxy sections: (title, heading patterns, keywords to fall back on when no heading matches). A heading is a short
# line, or two short lines read together, that matches a pattern whole (case and a trailing page number ignored).
PROXY_SECTIONS = {
    'directors': ('Directors and director nominees', (
        r'(proposal (no\.?|number|one|1)\W*)?election of (class \w+ )?directors',
        r'(the |our )?(director )?nominees( for (election|re-?election)( as directors?| to the board( of directors)?)?'
        r'| for (class \w+ )?directors?)?',
        r'(information (regarding|about) )?(the |our )?board( of directors)? and (the )?director nominees',
        r'(our )?(board of directors|directors) and executive officers'), ('director nominee', 'nominees for')),
    'compensation': ('Compensation discussion and analysis', (r'compensation discussion (and|&) analysis( \(cd&a\))?',),
                     ('compensation discussion',)),
    'ownership': ('Security ownership of certain beneficial owners and management', (
        r'(security |stock |share )?ownership of (certain beneficial owners( and management)?|securities'
        r'|(our )?(common )?(stock|shares)|management and (certain )?(principal|major) (stockholders|shareholders))',
        r'beneficial ownership( of (securities|(our )?(common )?(stock|shares)))?',
        r'principal (stockholders|shareholders)'), ('beneficial own',)),
    'related': ('Related-party transactions', (
        r'(certain )?(relationships and )?related[- ]p(erson|arty)( policy and)? transactions( policy)?',
        r'(review of |policies and procedures (for|regarding) )?(related[- ]p(erson|arty)|interested[- ]party) '
        r'transactions',
        r'(certain )?transactions with related (persons|parties)'), ('related person', 'related party',
                                                                     'related-person', 'related-party')),
    'committees': ('Board committees', (
        r'(the )?committees of (the|our) board( of directors)?', r'(our )?board committees',
        r'board meetings and committees', r'board and committee (structure|meetings|composition)'), ('committee',)),
    'auditor': ('Principal accountant fees and services', (
        r'(principal )?account(ant|ing) fees and services',
        r'fees (paid|billed) (to|by) (the |our )?(independent )?(registered public accounting firm|auditors?)',
        r'(independent )?(registered public accounting firm|auditor) fees'), ('audit fees',)),
}
# Executive officers have their own heading in most proxies; their table gives ages (Regulation S-K item 401).
OFFICERS_RE = re.compile(r'(our |information (regarding|about) (our )?)?executive officers( of the (company|registrant))?')
AGES_RE = re.compile(r'\bages?\b', re.I)
# Top-level proxy headings that end a section besides the sections themselves.
PROXY_BOUNDARIES = (
    r'proposal (no\.?|number)? ?\d*\b.*', r'proposal (one|two|three|four|five|six|seven|eight|nine|ten)\b.*',
    r'executive compensation( tables| for fiscal year \d{4})?', r'summary compensation table.*',
    r'(people and )?compensation committee report', r'(the )?audit( and finance)? committee report',
    r'director compensation.*', r'compensation of (non-employee )?directors', r'pay versus performance.*',
    r'ceo pay ratio', r'equity compensation plan information', r'other (matters|information)',
    r'questions and answers.*', r'(general|additional) information.*', r'(shareholder|stockholder) proposals.*',
    r'delinquent section 16\(a\) reports', r'audit[- ]related matters', r'board role in risk oversight',
    r'board leadership structure', r'householding.*')
PROXY_ALIASES = {'officers': 'directors', 'executive officers': 'directors', 'board': 'directors',
                 'nominees': 'directors', 'cd&a': 'compensation', 'pay': 'compensation',
                 'beneficial ownership': 'ownership', 'security ownership': 'ownership', 'related party': 'related',
                 'related-party': 'related', 'related person': 'related', 'committee': 'committees',
                 'board committees': 'committees', 'fees': 'auditor', 'audit fees': 'auditor', 'auditors': 'auditor'}
MAX_HEADING = 100
# A line a heading may follow: a sentence's end, a page number, or a page's link back to the contents.
FINISHED_RE = re.compile(r'[.!?:;)\]”"’]$|^[\d\W]*$|^table of contents\b', re.I)

FetchText = Callable[[str], str]
fetch_text = sec_edgar.fetch_text


def html_to_text(markup: str) -> str:
    """Readable text, one block (paragraph, table row, heading) a line, without the inline XBRL header."""
    markup = re.sub(r'(?is)<(script|style|ix:header)\b.*?</\1\s*>', ' ', markup)
    markup = BLOCK_RE.sub('\n', markup)
    text = INVISIBLE_RE.sub('', html.unescape(re.sub(r'<[^>]+>', ' ', markup)).replace('\xa0', ' '))
    lines = (re.sub(r'\s+', ' ', line).strip() for line in text.splitlines())
    return '\n'.join(line for line in lines if line)


def sections(text: str, heading_re: re.Pattern = HEADING_RE) -> list[tuple[str, str]]:
    """Each "Item N" heading in the filing with the text up to the next one: (item, text)."""
    found, item, start = [], None, 0
    lines = text.splitlines()
    for index, line in enumerate(lines + ['SIGNATURES']):
        heading = heading_re.match(line)
        if heading or END_RE.match(line):
            if item is not None:
                found.append((item, '\n'.join(lines[start:index])))
            item, start = (heading.group(1).upper(), index) if heading else (None, index)
    return found


def find_item(text: str, item: str, heading_re: re.Pattern = HEADING_RE) -> str | None:
    """An item's text. The table of contents and Part II's same-numbered items name it too, so take the longest."""
    candidates = [body for name, body in sections(text, heading_re) if name == item.upper()]
    return max(candidates, key=len) if candidates else None


def _heading(line: str) -> str | None:
    """A line as a heading to match: lower case, without a trailing page number or punctuation; None if too long."""
    line = re.sub(r'\s+\d{1,3}$', '', line.strip(' •')).rstrip(' .:;,').lower()
    return line if line and len(line) <= MAX_HEADING else None


def _any(patterns) -> re.Pattern:
    return re.compile('|'.join(f'(?:{pattern})' for pattern in patterns))


def _proxy_body(lines: list[str], heading: re.Pattern, boundary: re.Pattern, noise: set[str],
                check: Callable[[str], bool] = lambda start: True) -> str | None:
    """The longest stretch from a heading to the next boundary heading. A heading split over two short lines counts
    too; one followed by a page number is a contents entry, and a stretch under 400 characters is not a section.
    Noise lines (a page's running header) are never headings, and neither is a line that carries on from an
    unfinished one before it (a sentence broken over lines, a table's next label)."""
    def matches(pattern: re.Pattern, index: int, joined: bool = False) -> bool:
        parts = lines[index:index + 2] if joined else lines[index:index + 1]
        if len(parts) < (2 if joined else 1) or any(part in noise for part in parts):
            return False
        line = _heading(' '.join(parts))
        return line is not None and pattern.fullmatch(line) is not None

    def standalone(index: int) -> bool:
        before = lines[index - 1] if index else ''
        return (not index or before in noise or bool(FINISHED_RE.search(before)) or matches(heading, index - 1)
                or matches(boundary, index - 1))

    ends = [i for i in range(len(lines))
            if (matches(boundary, i) or matches(boundary, i, joined=True)) and standalone(i)]
    bodies = []
    for index in range(len(lines)):
        if not standalone(index):
            continue
        if matches(heading, index):
            start = index + 1
        elif matches(heading, index, joined=True) and not matches(heading, index + 1):
            start = index + 2
        else:
            continue
        if start < len(lines) and re.fullmatch(r'\d{1,3}', lines[start]):
            continue
        end = next((i for i in ends if i >= start), len(lines))
        body = '\n'.join(lines[index:end])
        if len(body) >= 400 and check(body[:600]):
            bodies.append(body)
    return max(bodies, key=len) if bodies else None


def proxy_section(text: str, key: str) -> str | None:
    """A proxy statement's section by its heading, running to the next heading of another section or another top-level
    heading; for directors, the executive officers' section follows when the proxy has one (its opening gives their
    ages, which a passing mention of executive officers does not)."""
    lines = text.splitlines()
    every_heading = _any([p for _, patterns, _ in PROXY_SECTIONS.values() for p in patterns] + [OFFICERS_RE.pattern])
    # A short line repeated on many pages is a running header, unless it is a section's own title.
    noise = {line for line, count in Counter(lines).items()
             if count >= 5 and len(line) <= 30 and not every_heading.fullmatch(_heading(line) or '')}
    others = [pattern for name, (_, patterns, _) in PROXY_SECTIONS.items() if name != key for pattern in patterns]
    boundary = _any(others + list(PROXY_BOUNDARIES) + [OFFICERS_RE.pattern])
    body = _proxy_body(lines, _any(PROXY_SECTIONS[key][1]), boundary, noise)
    if key == 'directors':
        every = _any(others + list(PROXY_SECTIONS[key][1]) + list(PROXY_BOUNDARIES))
        officers = _proxy_body(lines, OFFICERS_RE, every, noise, check=lambda start: bool(AGES_RE.search(start)))
        body = '\n\n'.join(part for part in (body, officers) if part) or None
    return body


def _filings(ticker: str, form: str, accession: str | None, fetch: sec_edgar.Fetch,
             wanted_item: str | None = None) -> list[dict]:
    """The company's recent filings of the form, newest first (or the one with this accession); for an 8-K item,
    only those reporting it."""
    company = sec_edgar.find_company(ticker, fetch)
    recent = fetch(sec_edgar.SUBMISSIONS_URL.format(cik=company['cik']))['filings']['recent']
    found = []
    for i, kind in enumerate(recent['form']):
        if accession:
            if recent['accessionNumber'][i] != accession:
                continue
        elif kind != form or (wanted_item and wanted_item not in recent['items'][i].split(',')):
            continue
        folder = sec_edgar.filing_url(company['cik'], recent['accessionNumber'][i])
        found.append({'company': company, 'form': kind, 'accession': recent['accessionNumber'][i],
                      'filed': recent['filingDate'][i], 'period': recent['reportDate'][i], 'folder': folder,
                      'items': recent['items'][i], 'document': folder + recent['primaryDocument'][i]})
    if not found:
        reporting = f' reporting Item {wanted_item}' if wanted_item and not accession else ''
        raise ValueError(f"No {accession or form} filing{reporting} found for {company['ticker']} among its recent "
                         'filings.')
    return found


def documents(filing: dict, fetch_document: FetchText) -> list[tuple[str, str, str]]:
    """The documents of a filing, from its EDGAR index page: (type, description, URL)."""
    page = fetch_document(f"{filing['folder']}{filing['accession']}-index.htm")
    table = re.search(r'(?is)<table[^>]*class="tableFile"[^>]*>(.*?)</table>', page)
    found = []
    for row in re.findall(r'(?is)<tr[^>]*>(.*?)</tr>', table.group(1) if table else ''):
        cells = [' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', cell)).split())
                 for cell in re.findall(r'(?is)<td[^>]*>(.*?)</td>', row)]
        link = re.search(r'href="([^"]+)"', row)
        if len(cells) >= 4 and link:
            found.append((cells[3].upper(), cells[1], urljoin('https://www.sec.gov', link.group(1).replace('/ix?doc=', ''))))
    return found


def _exhibit(filing: dict, prefix: str, fetch_document: FetchText) -> tuple[str, str] | None:
    """The first exhibit whose type starts with the prefix (EX-21, EX-99), preferring the .1: (URL, text)."""
    exhibits = [(kind, url) for kind, _, url in documents(filing, fetch_document) if kind.startswith(prefix)]
    if not exhibits:
        return None
    _, url = min(exhibits, key=lambda exhibit: exhibit[0] != f'{prefix}.1')
    return url, html_to_text(fetch_document(url))


def _pages(text: str) -> list[str]:
    pages, current = [], []
    for line in text.splitlines():
        if current and sum(len(part) + 1 for part in current) + len(line) > PAGE_CHARS:
            pages.append('\n'.join(current))
            current = []
        current.append(line[:PAGE_CHARS])
    return pages + (['\n'.join(current)] if current else [])


def _normal_item(form: str, item: str) -> str:
    item = (item or '').strip().upper().removeprefix('ITEM ').strip()
    if form == 'DEF 14A':
        item = item.lower()
        return PROXY_ALIASES.get(item, item)
    if form == '8-K' and (item.startswith('EX-99') or item in ('99', '99.1')):
        return '99.1'
    if form == '10-K' and item.startswith(('EX-21', '21')):
        return 'EX-21'
    return item


def _current_report(ticker: str, item: str, accession: str | None, fetch: sec_edgar.Fetch,
                    fetch_document: FetchText) -> tuple[dict, str, str, str]:
    """An 8-K's item (the latest 8-K reporting it, unless an accession is given), with the exhibit 99.1 press
    release after it when the filing has one; item 99.1 is the release alone. (filing, text, scope, document)"""
    if item and item not in ITEMS['8-K']:
        raise ValueError(f"8-K items are {', '.join(ITEMS['8-K'])} (99.1 is the press release); or leave item empty "
                         'for the whole filing.')
    candidates = _filings(ticker, '8-K', accession, fetch, None if item in ('', '99.1') else item)
    if item == '99.1':  # the latest 8-K that has exhibits and a press release among them
        for filing in [f for f in candidates if accession or '9.01' in f['items'].split(',')][:5]:
            if release := _exhibit(filing, 'EX-99', fetch_document):
                return filing, release[1], 'Exhibit 99.1 (press release)', release[0]
        raise ValueError(f'No exhibit 99 press release found in the latest 8-Ks of {ticker.upper()}.')
    filing = candidates[0]
    text = html_to_text(fetch_document(filing['document']))
    scope, document = 'the whole filing', filing['document']
    if item:
        body = find_item(text, item, CURRENT_REPORT_HEADING_RE)
        if body is None:
            found = ', '.join(name for name, _ in sections(text, CURRENT_REPORT_HEADING_RE)) or 'none'
            raise ValueError(f'Item {item} not found in this 8-K; its items are {found}.')
        text, scope = body, f"Item {item} ({ITEMS['8-K'][item]})"
        if item != '9.01':
            try:
                release = _exhibit(filing, 'EX-99', fetch_document)
            except httpx.HTTPError:  # the item still reads without its release
                release, scope = None, scope + '; its exhibit index could not be read'
            if release:
                text += f'\n\nExhibit 99.1 (press release, {release[0]}):\n{release[1]}'
                scope += ', then exhibit 99.1 (the press release)'
    return filing, text, scope, document


def read_filing(ticker: str, form: str = '10-K', item: str = '7', page: int = 1, keywords: list[str] | None = None,
                accession: str | None = None, fetch: sec_edgar.Fetch = sec_edgar.fetch_json,
                fetch_document: FetchText = fetch_text) -> Retrieved:
    """One item of the company's latest 10-K, 10-Q or 8-K, or one section of its latest proxy (DEF 14A), or the
    filing with this accession, a page at a time, or the paragraphs mentioning any of the keywords, within the item or,
    with item empty, the whole filing. 10-K item EX-21 is the subsidiary list; an 8-K item is read from the latest
    8-K that reports it, followed by its exhibit 99.1 press release, and 8-K item 99.1 is the release alone. Proxy
    sections: directors, compensation, ownership, related, committees, auditor."""
    form = form.strip().upper()
    if form not in ITEMS and form != 'DEF 14A':
        raise ValueError('form must be 10-K, 10-Q, 8-K or DEF 14A.')
    item = _normal_item(form, item)
    scope, notes = 'the whole filing', ''
    if form == '8-K':
        filing, text, scope, document = _current_report(ticker, item, accession, fetch, fetch_document)
    elif form == 'DEF 14A':
        if item and item not in PROXY_SECTIONS:
            raise ValueError(f"DEF 14A sections are {', '.join(PROXY_SECTIONS)}; or leave item empty for the whole "
                             'filing.')
        filing = _filings(ticker, form, accession, fetch)[0]
        document = filing['document']
        text = html_to_text(fetch_document(document))
        if item:
            title, _, fallback = PROXY_SECTIONS[item]
            body = proxy_section(text, item)
            if body is not None:
                text, scope = body, f'{title} (found by its heading)'
            elif not keywords:  # no heading: the paragraphs that name the section's subject instead
                keywords, scope = list(fallback), f'{title} (no heading found)'
    elif form == '10-K' and item == 'EX-21':
        filing = _filings(ticker, form, accession, fetch)[0]
        exhibit = _exhibit(filing, 'EX-21', fetch_document)
        if exhibit is None:
            raise ValueError('This 10-K has no exhibit 21 in its filing index.')
        document, text = exhibit
        scope = f"{ITEMS['10-K']['EX-21']}"
    else:
        filing = _filings(ticker, form, accession, fetch)[0]
        document = filing['document']
        text = html_to_text(fetch_document(document))
        if item:
            body = find_item(text, item)
            if body is None:
                if not keywords:
                    found = sorted({name for name, _ in sections(text)},
                                   key=lambda n: (int(re.match(r'\d+', n).group()), n))
                    raise ValueError(f"Item {item} not found in this {filing['form']}; its items are "
                                     f"{', '.join(found)}. Name another item, or search the whole filing with keywords.")
            else:
                text, scope = body, f"Item {item} ({ITEMS.get(form, {}).get(item, 'as titled in the filing')})"
                if form == '10-K' and len(body) < 3_000 and INCORPORATED_RE.search(body) and 'proxy' in body.lower():
                    section = PROXY_FOR_ITEM.get(item)
                    notes = (' This item is incorporated by reference to the proxy statement'
                             + (f'; read form DEF 14A, section {section}.' if section else '.'))
    if keywords:
        terms = [k.lower() for k in keywords if k.strip()]
        text = '\n'.join(line for line in text.splitlines() if any(term in line.lower() for term in terms))
        if not text:
            raise ValueError(f"No paragraph in {scope} mentions {', '.join(keywords)}.")
        scope += ', paragraphs mentioning ' + ', '.join(keywords)
    pages = _pages(text)
    page = min(max(page, 1), len(pages))
    company = filing['company']
    described = {'8-K': f"reporting {filing['period'] or 'an event'}",
                 'DEF 14A': f"for the meeting of {filing['period']}" if filing['period'] else 'for the annual meeting'
                 }.get(filing['form'], f"for the period ending {filing['period']}")
    header = (f"{company['name']} {filing['form']} {described}, filed {filing['filed']} (accession "
              f"{filing['accession']}): {scope}. Page {page} of {len(pages)} ({len(text):,} characters).{notes}")
    more = f'\n\nNext: page {page + 1}.' if page < len(pages) else ''
    claims = f"{filing['form']} text: {scope}"
    filed = source(f"{company['name']} {filing['form']} {described}", 'primary filing', filing['folder'],
                   filing['filed'], claims, f"{filing['form']} {described}, accession {filing['accession']}, "
                                            f"filed {filing['filed']}, {document}")
    return Retrieved(f'{header}\n\n{pages[page - 1]}{more}', [filed])
