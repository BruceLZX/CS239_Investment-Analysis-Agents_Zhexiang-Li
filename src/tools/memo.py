"""The team's must-never rules as checks on the report's text. policy/rules.py refuses an approval or a delivery on
these findings.

N1 (cited sources are registered), N2 (material numbers carry a source), N3 (company-only claims say how far they are
verified) and N6 (no internal working material) apply to every section as it is saved and to the whole report; N4
(the rating's evidence gate) applies to a version. Rule numbers refer to requirements.md. The depth and completeness
standard is in tools/qa/.

N2 is judged per paragraph, list item or table row rather than per sentence: a section is limited to six
inline source tags (tools/qa/check_depth.py), so a paragraph is cited once and a table carries a Source column.
"""
import re

from . import sections
from .agents import AGENTS

# A source ID: S and digits, not inside another word or number.
SOURCE_ID_RE = re.compile(r'(?<![A-Za-z0-9])S\d+(?!\d)')
NUMBER_RE = re.compile(r'(?<![\w.])[$¥€]?\d[\d,]*(?:\.\d+)?\s?(?:%|x|×|bn|billion|million|mn|[MBK]\b)?')
ISO_DATE_RE = re.compile(r'\b\d{4}-\d{2}(?:-\d{2})?\b')
YEAR_RE = re.compile(r'^(?:FY)?(?:19|20)\d{2}$')
URL_RE = re.compile(r'https?://\S+')
FORM_RE = re.compile(r'\b(?:10-K|10-Q|8-K|20-F|S-1|DEF 14A|EX-\d+(?:\.\d+)?)(?:/A)?\b|\bItem\s+\d+[A-C]?\b', re.I)
SMALL_ORDINAL_RE = re.compile(r'^\d$')  # "3 risks", "step 2": too small to be a material figure
LIST_MARKER_RE = re.compile(r'^(?:[-*+]|\d+[.)])\s+')
FENCE_RE = re.compile(r'^:::')
# The cover lines report.plain_report writes from the version's own record, which are not claims to source.
COVER_LINE_RE = re.compile(r'^(?:Rating|Composite score|Data as of):')
TABLE_SEPARATOR_RE = re.compile(r'^\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?$')
VERIFICATION_RE = re.compile(r'company-provided|company-reported|not independently verified|partially verified|unverified|'
                             r'contradicted|not publicly disclosed|not disclosed', re.I)
# Working material kept out of delivered reports ("mandatory cleanliness").
INTERNAL_PHRASES_RE = re.compile(
    r'\bmust[- ]fix\b|\bshould[- ]fix\b|\bevidence (?:block|matrix|packet)\b|\bcase file\b|\bsource register\b'
    r'|\brewrite plan\b|\bred[- ]team review\b|\bsection gate\b|\bCritical item\b'
    r'|\b(?:get|save|set|list|find|read|register|deliver|start|finish|request|search)_[a-z_]+\b|\bTODO\b'
    r'|\bthis run\b|\bnot retrieved\b', re.I)
# Review (R1), rewrite-plan (W1) and user-data-request (U1) IDs. Only beside the team's own vocabulary: a report on Tesla
# may well name Rivian's R1 and R2.
INTERNAL_ID_RE = re.compile(r'(?<![A-Za-z0-9])[RWU]\d{1,3}(?![0-9A-Za-z])')
INTERNAL_ID_CONTEXT_RE = re.compile(r'\b(?:review|round|critical|important|items?|verdict|approv\w*|revis\w*|brief|rewrite|'
                                    r'request|must[- ]fix|fix\w*|gate)\b', re.I)
TEAM_NAMES_RE = re.compile('|'.join(re.escape(name) for name in AGENTS.values()))
DISCLAIMER_RE = re.compile(r'not (?:investment|financial) advice|for research (?:purposes|reference) only', re.I)
COMPANY_PROVIDED_RE = re.compile(r'company-provided|company provided', re.I)
PRIMARY_RE = re.compile(r'\bprimary\b|near-primary|filing|regulat|official|registry', re.I)
MARKET_DATA_RE = re.compile(r'market data|price', re.I)


def internal_ids(text: str) -> list[str]:
    """The review, rewrite-plan and request IDs a text uses as such."""
    return sorted({m.group() for m in INTERNAL_ID_RE.finditer(text)
                   if INTERNAL_ID_CONTEXT_RE.search(text[max(0, m.start() - 60):m.end() + 60])})


def _statements(markdown: str):
    """Paragraphs, list items and table rows, skipping headings, table separators, component fences and the cover."""
    paragraph: list[str] = []
    for line in markdown.splitlines() + ['']:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or FENCE_RE.match(stripped) or COVER_LINE_RE.match(stripped):
            if paragraph:
                yield ' '.join(paragraph)
                paragraph = []
            continue
        if TABLE_SEPARATOR_RE.match(stripped):
            continue
        if stripped.startswith('|'):
            if paragraph:
                yield ' '.join(paragraph)
                paragraph = []
            yield stripped
        elif LIST_MARKER_RE.match(stripped):
            if paragraph:
                yield ' '.join(paragraph)
            paragraph = [LIST_MARKER_RE.sub('', stripped)]
        else:
            paragraph.append(stripped)


def _header_rows(markdown: str) -> set[str]:
    """Table header rows, which name columns rather than state figures."""
    rows, previous = set(), ''
    for line in markdown.splitlines():
        stripped = line.strip()
        if TABLE_SEPARATOR_RE.match(stripped) and previous.startswith('|'):
            rows.add(previous)
        previous = stripped
    return rows


def material_numbers(statement: str) -> list[str]:
    text = FORM_RE.sub('', URL_RE.sub('', ISO_DATE_RE.sub('', SOURCE_ID_RE.sub('', statement))))
    found = []
    for match in NUMBER_RE.finditer(text):
        token = match.group().strip()
        if not YEAR_RE.match(token.replace(',', '')) and not SMALL_ORDINAL_RE.match(token):
            found.append(token)
    return found


def cited_ids(text: str) -> set[str]:
    return set(SOURCE_ID_RE.findall(URL_RE.sub('', text)))


def _by_number(ids) -> list[str]:
    return sorted(ids, key=lambda s: int(s[1:]))


def check_rules(markdown: str, sources: list[dict]) -> list[dict]:
    """N1, N2, N3 and N6 for a section or a whole report."""
    by_id = {source['id']: source for source in sources}
    text = URL_RE.sub('', markdown)
    findings = []
    orphans = _by_number(cited_ids(text) - set(by_id))
    if orphans:
        findings.append({'rule': 'N1', 'detail': 'cites source IDs not in the register: ' + ', '.join(orphans)})

    headers = _header_rows(text)
    statements = [s for s in _statements(text) if s not in headers]
    unsourced = [s for s in statements if material_numbers(s) and not SOURCE_ID_RE.search(s)]
    if unsourced:
        findings.append({'rule': 'N2', 'detail': f'{len(unsourced)} paragraphs, list items or table rows have figures '
                                                 'but no source ID', 'examples': [s[:140] for s in unsourced[:4]]})
    unlabelled = [s for s in statements
                  if (ids := [i for i in SOURCE_ID_RE.findall(s) if i in by_id])
                  and all(COMPANY_PROVIDED_RE.search(by_id[i].get('source_type', '')) for i in ids)
                  and not VERIFICATION_RE.search(s)]
    if unlabelled:
        findings.append({'rule': 'N3', 'detail': f'{len(unlabelled)} claims rest only on company-provided sources '
                                                 'without a verification status',
                         'examples': [s[:140] for s in unlabelled[:4]]})

    internal = sorted({m.group() for regex in (INTERNAL_PHRASES_RE, TEAM_NAMES_RE) for m in regex.finditer(text)}
                      | set(internal_ids(text)))
    if internal:
        findings.append({'rule': 'N6', 'detail': 'internal working material in the report: ' + ', '.join(internal[:8])})
    return findings


def check_rating(rating: str, listed: bool, sources: list[dict], cited: set[str]) -> list[dict]:
    """N4: the rating's evidence gate, against what the register holds and the report cites."""
    by_id = {source['id']: source for source in sources}
    if listed and rating in sections.LISTED_DIRECTIONAL:
        types = [s.get('source_type', '') for s in sources]
        if not (any(PRIMARY_RE.search(t) for t in types) and any(MARKET_DATA_RE.search(t) for t in types)):
            return [{'rule': 'N4', 'detail': f'rating "{rating}" without both a primary filing and a timestamped '
                                             'market-data source'}]
    if not listed and rating in sections.PRIVATE_COMMITTING:
        if not any(i in by_id and not COMPANY_PROVIDED_RE.search(by_id[i].get('source_type', '')) for i in cited):
            return [{'rule': 'N4', 'detail': f'rating "{rating}" cites no independent (non-company) source'}]
    return []


def check_memo(markdown: str, sources: list[dict], rating: str | None = None, listed: bool = True) -> dict:
    """A whole report's text against the rules; the trace export runs it on the delivered report."""
    cited = cited_ids(markdown)
    by_id = {source['id']: source for source in sources}
    findings = check_rules(markdown, sources)
    if rating:
        findings += check_rating(rating, listed, sources, cited)
    if not DISCLAIMER_RE.search(markdown):
        findings.append({'rule': 'disclosure', 'detail': 'missing the research-only / not-investment-advice disclaimer'})
    return {
        'rating': rating,
        'cited_registered_ids': _by_number(cited & set(by_id)),
        'registered_but_uncited': _by_number(set(by_id) - cited),
        'findings': findings,
    }
