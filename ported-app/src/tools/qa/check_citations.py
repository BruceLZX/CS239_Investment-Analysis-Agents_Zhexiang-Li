"""Citations against the source register, ported from scripts/check_citations.py.

The report shows registered source IDs (at least five, or all of them when fewer are registered), cites no ID the
register lacks, links at least three of the registered web sources, and names its sources in words.

Fixed here: the script counted the register's own unfilled template row as a source; the register here holds only
real entries.
"""
import re

from .terms import URL_RE, source_ids, strip_html

MIN_CITED_SOURCES = 5
MIN_LINKED_URLS = 3


def check_citations(report_html: str, sources: list[dict]) -> dict:
    registered = {source['id'] for source in sources}
    urls = {source['location'].rstrip('.,;') for source in sources if URL_RE.fullmatch(source.get('location', '') or '')}
    visible = strip_html(report_html)
    shown = source_ids(visible)
    hrefs = set(re.findall(r'<a\s+[^>]*href="([^"]+)"', report_html))
    failures = []
    if not registered:
        failures.append('the source register is empty')
    if len(shown & registered) < min(len(registered), MIN_CITED_SOURCES):
        failures.append(f'{len(shown & registered)} registered source IDs appear in the report; needs '
                        f'{min(len(registered), MIN_CITED_SOURCES)}')
    orphans = sorted(shown - registered, key=lambda s: int(s[1:]))
    if orphans:
        failures.append('cites source IDs the register lacks: ' + ', '.join(orphans))
    linked = len({url for url in urls if url in hrefs})
    if linked < min(len(urls), MIN_LINKED_URLS):
        failures.append(f'{linked} registered web sources are linked; needs {min(len(urls), MIN_LINKED_URLS)}')
    if not re.search(r'source|citation|evidence', visible, re.I):
        failures.append('the report never names its sources')
    return {'failures': failures, 'passed': not failures, 'cited': sorted(shown & registered, key=lambda s: int(s[1:])),
            'linked_urls': linked}
