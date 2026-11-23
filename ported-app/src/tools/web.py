"""Web search and page fetching for the bots, on this server rather than as Rakazo's built-ins, so that a query can be
checked before it leaves. Search and fetch follow Rakazo's keyless web provider at the pinned build
(packages/adapters/src/keyless-http-web.ts): DuckDuckGo's public HTML form, and a fetch that refuses private addresses
at every redirect.
"""
import html
from html.parser import HTMLParser
import io
import ipaddress
import re
import socket
import threading
import time
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx
from pypdf import PdfReader

from .filings import html_to_text

SEARCH_ENDPOINT = 'https://html.duckduckgo.com/html/'
USER_AGENT = 'Mozilla/5.0 (compatible; investment-research-team/1.0)'
MAX_RESULTS, DEFAULT_RESULTS = 10, 8
MAX_CHARS, DEFAULT_CHARS, MIN_CHARS = 20_000, 8_000, 500
MAX_BYTES = 5_000_000
MAX_REDIRECTS = 5
TIMEOUT = 20
SEARCH_SPACING = 1.0  # Seconds between searches, so a whole team's research does not look like a flood.
BLOCKED_RE = re.compile(r'anomaly-modal|Unfortunately, bots use DuckDuckGo', re.I)
FURNITURE_RE = re.compile(r'<(nav|header|footer|aside|form|script|style|noscript|svg)\b.*?</\1\s*>', re.I | re.S)
ARTICLE_RE = re.compile(r'<article\b[^>]*>(.*)</article\s*>', re.I | re.S)
MAIN_RE = re.compile(r'<main\b[^>]*>(.*)</main\s*>', re.I | re.S)
MIN_MAIN_CONTENT = 500
_search_lock = threading.Lock()
_last_search = 0.0


class _Results(HTMLParser):
    """DuckDuckGo's result blocks: a link of class result__a and a snippet of class result__snippet."""

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._field: str | None = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get('class') or '').split()
        if self._field:
            self._depth += 1
        elif tag == 'a' and 'result__a' in classes:
            self.results.append({'title': '', 'url': unwrap(dict(attrs).get('href') or ''), 'snippet': ''})
            self._field, self._depth = 'title', 1
        elif 'result__snippet' in classes and self.results:
            self._field, self._depth = 'snippet', 1

    def handle_endtag(self, tag):
        if self._field:
            self._depth -= 1
            if self._depth <= 0:
                self._field = None

    def handle_data(self, data):
        if self._field:
            self.results[-1][self._field] += data


def unwrap(href: str) -> str:
    """The target of a DuckDuckGo redirect link."""
    parsed = urlsplit(urljoin(SEARCH_ENDPOINT, href))
    return (parse_qs(parsed.query).get('uddg') or [parsed.geturl()])[0]


def parse_results(page: str, max_results: int = DEFAULT_RESULTS) -> list[dict]:
    parser = _Results()
    parser.feed(page)
    found = []
    for result in parser.results:
        result = {key: ' '.join(value.split()) for key, value in result.items()}
        if result['title'] and result['url'].startswith(('http://', 'https://')):
            found.append(result)
    return found[:max_results]


def _public(url: str) -> None:
    """Refuse anything but http(s) to a public address, so a page cannot steer a fetch into this machine's network."""
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError(f'Only public http(s) URLs can be fetched: {url}')
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 443)}
    except socket.gaierror as exc:
        raise ValueError(f'Could not find {parts.hostname}: {exc}') from exc
    for address in addresses:
        ip = ipaddress.ip_address(address.split('%')[0])
        if not ip.is_global:
            raise ValueError(f'{parts.hostname} is not a public address, so it is not fetched.')


def _get(url: str, params: dict | None = None) -> httpx.Response:
    """A GET that checks every hop of its redirects."""
    with httpx.Client(timeout=TIMEOUT, headers={'User-Agent': USER_AGENT}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _public(url)
            response = client.get(url, params=params)
            if not response.is_redirect:
                return response
            url, params = urljoin(str(response.url), response.headers['location']), None
    raise ValueError(f'Too many redirects from {url}.')


def search(query: str, max_results: int = DEFAULT_RESULTS, get=_get) -> list[dict]:
    global _last_search
    query = query.strip()
    if not query:
        raise ValueError('query is required.')
    with _search_lock:
        wait = SEARCH_SPACING - (time.monotonic() - _last_search)
        if wait > 0 and get is _get:
            time.sleep(wait)
        _last_search = time.monotonic()
    response = get(SEARCH_ENDPOINT, {'q': query})
    if response.status_code != 200 or BLOCKED_RE.search(response.text):
        raise ValueError('The search provider is refusing requests right now. Try again in a minute, or use a data tool.')
    return parse_results(response.text, min(max(max_results, 1), MAX_RESULTS))


def _main_content(markup: str) -> str:
    """The page without its navigation and furniture, which would otherwise use up the characters a fetch returns:
    its <article> or <main> when one holds a real amount of text."""
    cleaned = FURNITURE_RE.sub(' ', markup)
    for pattern in (ARTICLE_RE, MAIN_RE):
        match = pattern.search(cleaned)
        if match and len(match.group(1)) > MIN_MAIN_CONTENT:
            return match.group(1)
    return cleaned


def _page_text(response: httpx.Response) -> tuple[str, str]:
    kind = response.headers.get('content-type', '').lower()
    body = response.content[:MAX_BYTES]
    if 'pdf' in kind or body[:5] == b'%PDF-':
        reader = PdfReader(io.BytesIO(body))
        return 'PDF document', '\n\n'.join(page.extract_text() or '' for page in reader.pages[:40])
    text = body.decode(response.encoding or 'utf-8', errors='replace')
    if 'html' not in kind and not re.search(r'<html|<body|<p[ >]', text[:4000], re.I):
        return 'Untitled', text
    title = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    return ' '.join(html.unescape(title.group(1)).split()) if title else 'Untitled', html_to_text(_main_content(text))


def fetch(url: str, max_chars: int = DEFAULT_CHARS, get=_get) -> dict:
    response = get(url.strip())
    if response.status_code >= 400:
        raise ValueError(f'{url} answered with HTTP {response.status_code}. Try another source.')
    title, text = _page_text(response)
    text = text.strip()
    if not text:
        raise ValueError(f'{url} has no readable text. Try another source.')
    limit = min(max(max_chars, MIN_CHARS), MAX_CHARS)
    truncated = len(text) > limit
    return {'url': str(response.url), 'title': title, 'text': text[:limit] + ('\n\n[Content truncated]' if truncated else ''),
            'truncated': truncated}
