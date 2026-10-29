"""The text of a company's 10-K and 10-Q filings, read and searched on this machine.

Reading a filing through this tool gives the analysts its own words (the business, segments, risk factors,
management's discussion) as a primary source without fetching sec.gov through Rakazo, whose fetch guard holds URLs a
bot did not search for. Keyword searches of a filing run here, so their terms never leave this machine.
"""
from collections.abc import Callable
import html
import re
import time

import httpx

from . import sec_edgar
from .retrieved import Retrieved, source

ITEMS = {
    '10-K': {'1': 'Business', '1A': 'Risk Factors', '7': "Management's Discussion and Analysis",
             '7A': 'Quantitative and Qualitative Disclosures About Market Risk',
             '8': 'Financial Statements and Supplementary Data'},
    '10-Q': {'1': 'Financial Statements', '2': "Management's Discussion and Analysis", '1A': 'Risk Factors'},
}
PAGE_CHARS = 9_000
HEADING_RE = re.compile(r'^item\s*(\d{1,2}[a-c]?)\b\s*[.:\-–—]?', re.I)
END_RE = re.compile(r'^signatures?\s*$', re.I)
BLOCK_RE = re.compile(r'<\s*/?\s*(?:p|div|br|tr|li|h[1-6]|table|section|center)\b[^>]*>', re.I)

FetchText = Callable[[str], str]


def fetch_text(url: str) -> str:
    sec_edgar.CACHE.mkdir(parents=True, exist_ok=True)
    path = sec_edgar.CACHE / url.split('://', 1)[1].replace('/', '_')
    if path.exists() and time.time() - path.stat().st_mtime < sec_edgar.CACHE_SECONDS:
        return path.read_text()
    response = httpx.get(url, headers={'User-Agent': sec_edgar.user_agent()}, timeout=60)
    response.raise_for_status()
    path.write_text(response.text)
    return response.text


def html_to_text(markup: str) -> str:
    """Readable text, one block (paragraph, table row, heading) a line, without the inline XBRL header."""
    markup = re.sub(r'(?is)<(script|style|ix:header)\b.*?</\1\s*>', ' ', markup)
    markup = BLOCK_RE.sub('\n', markup)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', markup)).replace('\xa0', ' ')
    lines = (re.sub(r'\s+', ' ', line).strip() for line in text.splitlines())
    return '\n'.join(line for line in lines if line)


def sections(text: str) -> list[tuple[str, str]]:
    """Each "Item N" heading in the filing with the text up to the next one: (item, text)."""
    found, item, start = [], None, 0
    lines = text.splitlines()
    for index, line in enumerate(lines + ['SIGNATURES']):
        heading = HEADING_RE.match(line)
        if heading or END_RE.match(line):
            if item is not None:
                found.append((item, '\n'.join(lines[start:index])))
            item, start = (heading.group(1).upper(), index) if heading else (None, index)
    return found


def find_item(text: str, item: str) -> str | None:
    """An item's text. The table of contents and Part II's same-numbered items name it too, so take the longest."""
    candidates = [body for name, body in sections(text) if name == item.upper()]
    return max(candidates, key=len) if candidates else None


def _filing(ticker: str, form: str, accession: str | None, fetch: sec_edgar.Fetch) -> dict:
    company = sec_edgar.find_company(ticker, fetch)
    recent = fetch(sec_edgar.SUBMISSIONS_URL.format(cik=company['cik']))['filings']['recent']
    for i, kind in enumerate(recent['form']):
        if (recent['accessionNumber'][i] == accession) if accession else kind == form:
            folder = sec_edgar.filing_url(company['cik'], recent['accessionNumber'][i])
            return {'company': company, 'form': kind, 'accession': recent['accessionNumber'][i],
                    'filed': recent['filingDate'][i], 'period': recent['reportDate'][i], 'folder': folder,
                    'document': folder + recent['primaryDocument'][i]}
    raise ValueError(f"No {accession or form} filing found for {company['ticker']} among its recent filings.")


def _pages(text: str) -> list[str]:
    pages, current = [], []
    for line in text.splitlines():
        if current and sum(len(part) + 1 for part in current) + len(line) > PAGE_CHARS:
            pages.append('\n'.join(current))
            current = []
        current.append(line[:PAGE_CHARS])
    return pages + (['\n'.join(current)] if current else [])


def read_filing(ticker: str, form: str = '10-K', item: str = '7', page: int = 1, keywords: list[str] | None = None,
                accession: str | None = None, fetch: sec_edgar.Fetch = sec_edgar.fetch_json,
                fetch_document: FetchText = fetch_text) -> Retrieved:
    """One item of the company's latest 10-K or 10-Q (or the filing with this accession), a page at a time, or the
    paragraphs mentioning any of the keywords, within the item or, with item empty, the whole filing."""
    form = form.strip().upper()
    if form not in ITEMS:
        raise ValueError('form must be 10-K or 10-Q.')
    filing = _filing(ticker, form, accession, fetch)
    text = html_to_text(fetch_document(filing['document']))
    item = (item or '').strip().upper().removeprefix('ITEM ').strip()
    scope = 'the whole filing'
    if item:
        body = find_item(text, item)
        if body is None:
            if not keywords:
                found = sorted({name for name, _ in sections(text)}, key=lambda n: (int(re.match(r'\d+', n).group()), n))
                raise ValueError(f"Item {item} not found in this {filing['form']}; its items are {', '.join(found)}. "
                                 'Name another item, or search the whole filing with keywords.')
        else:
            text, scope = body, f"Item {item} ({ITEMS[form].get(item, 'as titled in the filing')})"
    if keywords:
        terms = [k.lower() for k in keywords if k.strip()]
        text = '\n'.join(line for line in text.splitlines() if any(term in line.lower() for term in terms))
        if not text:
            raise ValueError(f"No paragraph in {scope} mentions {', '.join(keywords)}.")
        scope += ', paragraphs mentioning ' + ', '.join(keywords)
    pages = _pages(text)
    page = min(max(page, 1), len(pages))
    company = filing['company']
    header = (f"{company['name']} {filing['form']} for the period ending {filing['period']}, filed {filing['filed']} "
              f"(accession {filing['accession']}): {scope}. Page {page} of {len(pages)} ({len(text):,} characters).")
    more = f'\n\nNext: page {page + 1}.' if page < len(pages) else ''
    claims = f"{filing['form']} text: {scope}"
    filed = source(f"{company['name']} {filing['form']} for the period ending {filing['period']}", 'primary filing',
                   filing['folder'], filing['filed'], claims,
                   f"{filing['form']} for the period ending {filing['period']}, accession {filing['accession']}, "
                   f"filed {filing['filed']}, {filing['document']}")
    return Retrieved(f'{header}\n\n{pages[page - 1]}{more}', [filed])
