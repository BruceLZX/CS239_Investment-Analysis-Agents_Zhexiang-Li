"""Memo checks drawn from the skill's evidence and QA rules. In Phase 1 they report and never block.

The source-ID pattern comes straight from the skill's scripts/check_citations.py, so the agent
team and the skill judge citations the same way. Rule numbers refer to requirements.md.
"""
import importlib.util
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]


def _load_skill_citation_rules():
    spec = importlib.util.spec_from_file_location('skill_check_citations', REPO / 'scripts' / 'check_citations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE_ID_RE = _load_skill_citation_rules().SOURCE_ID_RE
NUMBER_RE = re.compile(r'(?<![\w.])\$?\d[\d,]*(?:\.\d+)?\s?(?:%|x|bn|billion|million|mn|[MBK]\b)?')
ISO_DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
YEAR_RE = re.compile(r'^(?:19|20)\d{2}$')
URL_RE = re.compile(r'https?://\S+')
FORM_RE = re.compile(r'\b(?:10-K|10-Q|8-K|20-F|S-1|DEF 14A)(?:/A)?\b')
LIST_MARKER_RE = re.compile(r'^(?:[-*+]|\d+[.)])\s+')
SOURCES_HEADING_RE = re.compile(r'^#{1,6}\s*sources?\b', re.I)
DISCLAIMER_RE = re.compile(r'not (?:investment|financial) advice|for research (?:purposes|reference) only', re.I)
AS_OF_RE = re.compile(r'data as of|as of \d{4}-\d{2}-\d{2}', re.I)
RATING_RE = re.compile(r'\b(?:rating|recommendation)\b\W{0,6}'
                       r'(buy|add|hold-off|hold|reduce|sell|watchlist|invest|wait|pass)', re.I)
VERIFICATION_RE = re.compile(r'company-provided|not independently verified|partially verified|unverified|contradicted', re.I)
# Working material the skill keeps out of delivered reports ("mandatory cleanliness").
INTERNAL_PHRASES_RE = re.compile(r'\bmust[- ]fix\b|\bshould[- ]fix\b|\bevidence packet\b|\bcase file\b|\bsource register\b'
                                 r'|\b(?:get|save|list|find|read|register|deliver)_[a-z_]+\b|\bTODO\b'
                                 r'|\bthis run\b|\bnot retrieved\b', re.I)
INTERNAL_IDS_RE = re.compile(r'\b[ER]\d{1,3}\b')
LISTED_DIRECTIONAL = {'buy', 'add', 'sell', 'reduce'}


def _statements(markdown: str):
    """Table rows and sentences, skipping headings, table separators, list markers and the Sources list."""
    in_sources = False
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith('#'):
            in_sources = bool(SOURCES_HEADING_RE.match(line))
            continue
        line = LIST_MARKER_RE.sub('', line)
        if in_sources or not line or set(line) <= set('|-: '):
            continue
        if line.startswith('|'):
            yield line
        else:
            yield from (part for part in re.split(r'(?<=[.!?])\s+', line) if part)


def _material_numbers(statement: str) -> list[str]:
    found = []
    text = FORM_RE.sub('', URL_RE.sub('', ISO_DATE_RE.sub('', SOURCE_ID_RE.sub('', statement))))
    for match in NUMBER_RE.finditer(text):
        token = match.group().strip()
        if not YEAR_RE.match(token.replace(',', '')):
            found.append(token)
    return found


def _is_company_provided(source: dict) -> bool:
    return 'company-provided' in source['source_type'].lower()


def check_memo(markdown: str, sources: list[dict]) -> dict:
    by_id = {source['id']: source for source in sources}
    # Citations are visible tags like [S1]; a URL can contain S-numbers too (e.g. ScienceDirect's pii/S27…).
    markdown = URL_RE.sub('', markdown)
    cited = set(SOURCE_ID_RE.findall(markdown))
    findings = []

    orphans = sorted(cited - set(by_id), key=lambda s: int(s[1:]))
    if orphans:
        findings.append({'rule': 'N1', 'detail': 'cites source IDs not in the register: ' + ', '.join(orphans)})

    statements = list(_statements(markdown))
    unsourced = [s for s in statements if _material_numbers(s) and not SOURCE_ID_RE.search(s)]
    if unsourced:
        findings.append({'rule': 'N2', 'detail': f'{len(unsourced)} statements with numbers but no source ID',
                         'examples': [s[:140] for s in unsourced[:5]]})

    unlabelled = [s for s in statements
                  if (ids := [i for i in SOURCE_ID_RE.findall(s) if i in by_id])
                  and all(_is_company_provided(by_id[i]) for i in ids) and not VERIFICATION_RE.search(s)]
    if unlabelled:
        findings.append({'rule': 'N3', 'detail': f'{len(unlabelled)} claims rest only on company-provided sources '
                                                 'without a verification status',
                         'examples': [s[:140] for s in unlabelled[:5]]})

    rating_match = RATING_RE.search(markdown)
    rating = rating_match.group(1).lower() if rating_match else None
    types = [source['source_type'].lower() for source in sources]
    if rating in LISTED_DIRECTIONAL:
        has_filing = any('primary' in t or 'filing' in t for t in types)
        has_prices = any('market data' in t or 'price' in t for t in types)
        if not (has_filing and has_prices):
            findings.append({'rule': 'N4', 'detail': f'rating "{rating}" without both a primary filing and a market-data source'})
    if rating == 'invest' and not any(i in by_id and not _is_company_provided(by_id[i]) for i in cited):
        findings.append({'rule': 'N4', 'detail': 'rating "invest" cites no independent (non-company) source'})

    internal = sorted({m.group() for m in INTERNAL_PHRASES_RE.finditer(markdown)} |
                      {m.group() for m in INTERNAL_IDS_RE.finditer(markdown)})
    if internal:
        findings.append({'rule': 'N6', 'detail': 'internal working material in the memo: ' + ', '.join(internal[:8])})

    if not DISCLAIMER_RE.search(markdown):
        findings.append({'rule': 'disclosure', 'detail': 'missing the research-only / not-investment-advice disclaimer'})
    if not AS_OF_RE.search(markdown):
        findings.append({'rule': 'disclosure', 'detail': 'missing a data-as-of date'})
    return {
        'rating': rating,
        'cited_registered_ids': sorted(cited & set(by_id), key=lambda s: int(s[1:])),
        'registered_but_uncited': sorted(set(by_id) - cited, key=lambda s: int(s[1:])),
        'findings': findings,
        'note': 'Phase 1 report only: nothing is blocked.',
    }
