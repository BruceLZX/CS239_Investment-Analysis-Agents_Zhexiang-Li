"""Memo checks drawn from the skill's evidence and QA rules. They report and never block.

A memo has the parts in PARTS, each written and saved on its own by its owner. check_part checks one part as it is
saved, against the rules (rule numbers refer to requirements.md) and the depth standard ported from the
investment-analysis skill's QA scripts; check_version checks a whole saved version. The source-ID pattern is the
skill's own, so the agent team and the skill judge citations the same way.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from urllib.parse import urlparse

from .agents import AGENTS, ANALYSTS

# SOURCE_ID_RE in the skill's scripts/check_citations.py:
# https://github.com/BruceLZX/investment-analysis-skill/blob/9f1e8656e396a611c9b7137a83e7326e57ff5c70/scripts/check_citations.py#L14
SOURCE_ID_RE = re.compile(r'\bS\d+\b')
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
                                 r'|\b(?:get|save|set|list|find|read|register|deliver)_[a-z_]+\b|\bTODO\b'
                                 r'|\bthis run\b|\bnot retrieved\b', re.I)
INTERNAL_IDS_RE = re.compile(r'\b[ER]\d{1,3}\b')
# The skill's FINAL_REPORT_FORBIDDEN_PATTERNS (scripts/check_depth.py): writing about how the memo is made, or by whom.
META_WRITING_RE = re.compile(r'\bthis (?:part|section|memo) (?:should|must|will|needs to)\b|\bas (?:briefed|instructed)\b'
                             r'|\bevidence gate\b|\bpart check\b', re.I)
TEAM_NAMES_RE = re.compile(r'\b(?:IC Reviewer|Lead Analyst|Fundamentals Analyst|Market Analyst)\b')
LISTED_DIRECTIONAL = {'buy', 'add', 'sell', 'reduce'}
DISCLAIMER = 'For research purposes only; not investment advice.'


@dataclass(frozen=True)
class Part:
    key: str
    heading: str
    owner: str
    chars: tuple[int, int]  # the depth floor, and the length to aim for (a note, not a problem)
    numbers: int            # material numbers, each with its source (N2)
    source_ids: int         # distinct source IDs cited
    tables: int = 0
    analysis: bool = False  # one of the analysis parts, which carry the skill's evidence gate


LEAD, FUNDAMENTALS, MARKET = AGENTS['lead'], AGENTS['fundamentals'], AGENTS['market']
# The memo's parts in order. The Sources part, the header and the disclaimer are generated (assemble).
PARTS = (
    Part('executive_summary', 'Executive summary', LEAD, (1500, 3000), 6, 4, tables=2),
    Part('business', 'Business', MARKET, (2500, 5000), 8, 4, tables=1, analysis=True),
    Part('financials', 'Financials', FUNDAMENTALS, (3000, 6000), 15, 4, tables=1, analysis=True),
    Part('valuation', 'Valuation and price', FUNDAMENTALS, (2500, 5000), 12, 4, tables=2, analysis=True),
    Part('competition', 'Competition and market', MARKET, (2500, 5000), 8, 5, tables=2, analysis=True),
    Part('risks', 'Risks and counter-evidence', LEAD, (2500, 4500), 8, 5, tables=1, analysis=True),
    Part('scenarios', 'Scenarios', LEAD, (2000, 4000), 10, 4, tables=2),
    Part('one_question', 'The one diligence question', LEAD, (300, 900), 1, 1),
    Part('takeaways', 'Three takeaways', LEAD, (400, 1000), 3, 3),
)
PART_BY_KEY = {part.key: part for part in PARTS}
# The most a part may hold, so that several parts fit in one 12,000-character tool result.
MAX_PART_CHARS = 9_000
# A private company has no filings, and its deck gives fewer figures to cite.
PRIVATE_NUMBERS = {'financials': 8, 'valuation': 6}

# The skill's ANALYTICAL_COVERAGE_TERMS (scripts/check_depth.py) in English: every analysis part needs each group.
ANALYSIS_TERMS = {
    'interpretation': ('because', 'driven by', 'reflects', 'means', 'implies', 'as a result', 'due to', 'suggests',
                       'indicates', 'therefore', 'explains', 'shows that', 'the reason', 'thus', 'which leaves'),
    'comparison': ('peer', 'compared', 'versus', ' vs', 'benchmark', 'median', 'historical', 'relative to', 'than'),
    'counter-evidence': ('however', 'counter', 'downside', 'bear', 'weaken', 'contradict', 'offset', 'against'),
    'investor implication': ('investor', 'implication', 'for the rating', 'position', 'decision', 'thesis',
                             'watchlist', 'entry', 'upside', 'risk/reward'),
}
CONFIDENCE_RE = re.compile(r'\b(?:high|medium|low)[- ]confidence\b|\bconfidence\b[^.\n|]{0,20}\b(?:high|medium|low)\b', re.I)
# What each part must cover: the skill's executive-summary and public-equity groups (scripts/check_report.py)
# and its section mandates (references/section_deepening.md), as English terms.
PART_TERMS = {
    'executive_summary': {
        'verdict or action': ('verdict', 'action', 'recommend'),
        'positives': ('positive', 'strength', 'upside', 'bull', 'in favour', 'in favor'),
        'risks': ('risk', 'downside', 'bear'),
        'evidence confidence': ('confidence',),
        'valuation or terms': ('valuation', 'price', 'terms', 'multiple'),
        'follow-up diligence': ('diligence', 'follow-up', 'verify'),
        'consensus view': ('consensus',),
    },
    'business': {
        'what it sells and to whom': ('customer', 'sells', 'product', 'service'),
        'revenue mix': ('segment', 'mix', 'of revenue', 'revenue from'),
        'management': ('management', 'founder', 'ceo', 'chief executive', 'capital allocation', 'leadership'),
        'moat': ('moat', 'advantage', 'switching cost', 'network effect', 'brand', 'scale', 'ecosystem'),
    },
    'financials': {
        'income statement': ('gross margin', 'operating margin', 'operating income', 'net income', 'eps'),
        'cash flow': ('cash flow', 'capex', 'capital expenditure', 'cash conversion'),
        'balance sheet': ('balance sheet', 'debt', 'net cash', 'liquidity', 'leverage'),
        'earnings quality': ('accounting', 'auditor', 'impairment', 'related-party', 'one-off', 'non-recurring',
                             'stock-based compensation', 'working capital'),
        'key variable': ('sensitiv', 'key variable', 'every 1', 'each 1'),
    },
    'valuation': {
        'trading snapshot': ('market cap', 'enterprise value', 'exchange'),
        'multiples': ('p/e', 'ev/sales', 'ev/ebitda', 'fcf yield', 'multiple'),
        'peers': ('peer', 'median', 'comparable'),
        'consensus': ('consensus', 'not disclosed'),
        'catalysts': ('catalyst',),
        'what the price implies': ('implies', 'implied', 'priced in', 'margin of safety'),
    },
    'competition': {
        'market size': ('market size', 'tam', 'addressable', 'market was', 'market is', 'sized'),
        'growth': ('cagr', 'growth', 'growing'),
        'competitors': ('competitor', 'rival'),
        'substitutes': ('substitute', 'alternative', 'do nothing', 'status quo', 'in-house'),
        'share': ('share',),
        'regulation': ('regulat', 'policy', 'antitrust', 'tariff', 'law'),
    },
    'risks': {
        'probability and impact': ('probability', 'likelihood'),
        'signposts': ('signpost', 'indicator', 'trigger', 'monitor', 'watch'),
        'stress test': ('stress', '-30%', '−30%', '30% lower', '30% decline', '30% drop'),
        'fatal versus manageable': ('fatal', 'manageable', 'existential', 'thesis-breaking'),
    },
    'scenarios': {
        'key assumptions': ('assumption',),
        'position sizing': ('position', 'sizing', 'starter', 'check size', 'reserve', 'allocation'),
        'signposts': ('signpost', 'indicator', 'trigger', 'watch'),
    },
}
# A private company: the round's terms instead of a trading snapshot, burn and runway instead of the notes.
PRIVATE_TERMS = {
    'financials': {
        'reported figures': ('reported', 'company-provided', 'deck'),
        'burn and runway': ('burn', 'runway'),
        'key variable': ('sensitiv', 'key variable', 'every 1', 'each 1'),
    },
    'valuation': {
        'round terms': ('round', 'pre-money', 'post-money', 'terms'),
        'comparables': ('comparable', 'peer', 'median'),
        'dilution': ('dilut',),
        'exit': ('exit', 'acquir', 'ipo'),
    },
}
# The skill's SHALLOW_PHRASES and VAGUE_PATTERNS (scripts/check_depth.py) in English: they sound like analysis
# but say nothing a reader can check.
SHALLOW_PHRASES = ('huge market', 'massive opportunity', 'strong team', 'high barriers to entry', 'clear business model',
                   'fierce competition', 'risks are manageable', 'bright future', 'significant potential',
                   'well positioned', 'well-positioned', 'best-in-class', 'world-class')
VAGUE_RE = re.compile(r'\b(?:approximately|roughly|around|about)\s+\$?\d'
                      r'|\b(?:many|numerous|several)\s+(?:patents|customers|partners)\b'
                      r'|\b(?:team|founders|management)\s+(?:is|are)\s+(?:experienced|strong|excellent)\b', re.I)
MAX_VAGUE = 2  # check_depth.py fails a section with more than two
SCORE_DIMENSIONS = {'business quality': 'business', 'financial strength': 'financ', 'valuation': 'valuation',
                    'competitive position': 'competit', 'management and governance': 'management', 'risk': 'risk'}
SCORE_RE = re.compile(r'(?<![\w.])(10|[1-9])(?:\s*/\s*10)?(?![\d.%])')
TABLE_SEPARATOR_RE = re.compile(r'^\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?$')
SENTENCE_RE = re.compile(r'[^.!?\n]{24,}[.!?]')


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


def _ids(text: str) -> set[str]:
    return set(SOURCE_ID_RE.findall(text))


def _by_number(ids) -> list[str]:
    return sorted(ids, key=lambda s: int(s[1:]))


def _sourcing_findings(text: str, by_id: dict) -> list[dict]:
    """N1 to N3 for Markdown whose URLs are already removed."""
    findings = []
    orphans = _by_number(_ids(text) - set(by_id))
    if orphans:
        findings.append({'rule': 'N1', 'detail': 'cites source IDs not in the register: ' + ', '.join(orphans)})

    statements = list(_statements(text))
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
    return findings


def _internal_findings(text: str) -> list[dict]:
    """N6: working material, team names and writing about the writing."""
    internal = sorted({m.group() for regex in (INTERNAL_PHRASES_RE, INTERNAL_IDS_RE, META_WRITING_RE, TEAM_NAMES_RE)
                       for m in regex.finditer(text)})
    if not internal:
        return []
    return [{'rule': 'N6', 'detail': 'internal working material in the memo: ' + ', '.join(internal[:8])}]


def check_memo(markdown: str, sources: list[dict]) -> dict:
    by_id = {source['id']: source for source in sources}
    # Citations are visible tags like [S1]; a URL can contain S-numbers too (e.g. ScienceDirect's pii/S27…).
    markdown = URL_RE.sub('', markdown)
    cited = _ids(markdown)
    findings = _sourcing_findings(markdown, by_id)

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

    findings += _internal_findings(markdown)
    if not DISCLAIMER_RE.search(markdown):
        findings.append({'rule': 'disclosure', 'detail': 'missing the research-only / not-investment-advice disclaimer'})
    if not AS_OF_RE.search(markdown):
        findings.append({'rule': 'disclosure', 'detail': 'missing a data-as-of date'})
    return {
        'rating': rating,
        'cited_registered_ids': _by_number(cited & set(by_id)),
        'registered_but_uncited': _by_number(set(by_id) - cited),
        'findings': findings,
        'note': 'Report only: nothing is blocked.',
    }


# The depth standard, part by part

def normalize_part(key: str, markdown: str) -> str:
    """A part's text without surrounding blank lines or a repeated heading; assemble adds the heading."""
    lines = markdown.strip().splitlines()
    if lines and re.fullmatch(r'#{1,6}\s*' + re.escape(PART_BY_KEY[key].heading) + r'\s*', lines[0].strip(), re.I):
        lines = lines[1:]
    return '\n'.join(lines).strip()


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def _tables(markdown: str) -> list[list[list[str]]]:
    """Each Markdown table as rows of cells, header first."""
    tables, current, previous = [], None, ''
    for line in markdown.splitlines():
        stripped = line.strip()
        if TABLE_SEPARATOR_RE.match(stripped) and previous.startswith('|'):
            current = [_cells(previous)]
            tables.append(current)
        elif current is not None and stripped.startswith('|'):
            current.append(_cells(stripped))
        else:
            current = None
        previous = stripped
    return tables


def _column(header: list[str], word: str) -> int | None:
    return next((i for i, cell in enumerate(header) if word in cell.lower()), None)


def _missing_terms(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = text.lower()
    return [group for group, terms in groups.items() if not any(term in lowered for term in terms)]


def _kind(source: dict) -> str:
    """Where a registered source sits in the skill's source hierarchy."""
    kind = source.get('source_type', '').lower()
    if 'company-provided' in kind:
        return 'company-provided'
    if 'market data' in kind or 'price' in kind:
        return 'market data'
    if re.search(r'primary|filing|regulat|government|official', kind):
        return 'primary'
    if re.search(r'company|investor relations|press release', kind):
        return 'company'
    return 'independent'


def _publisher(source: dict) -> str:
    location = source.get('location', '')
    return urlparse(location).netloc.lower().removeprefix('www.') or location.lower()


def _gate(key: str, cited: list[dict], listed: bool) -> list[str]:
    """What an analysis part's cited sources lack under the skill's evidence gate."""
    kinds = {_kind(s) for s in cited}
    publishers = {_publisher(s) for s in cited}
    independent = {_publisher(s) for s in cited if _kind(s) in ('independent', 'primary', 'market data')}
    missing = []
    if key == 'business':
        if not kinds & {'primary', 'company'}:
            missing.append("a primary source (a filing, a regulator or the company's own site)")
        if len(independent) < 2:
            missing.append('2 independent publishers')
    elif key == 'financials':
        if listed and 'primary' not in kinds:
            missing.append('a primary filing')
        if not listed and not independent:
            missing.append('a source that is not company-provided')
        if len(publishers) < (3 if listed else 2):
            missing.append(f'{3 if listed else 2} publishers')
    elif key == 'valuation':
        if listed and 'market data' not in kinds:
            missing.append('a timestamped market-data source')
        if listed and 'primary' not in kinds:
            missing.append('a primary filing')
        if not listed and not independent:
            missing.append('an independent comparable')
    elif key == 'competition':
        if len({_publisher(s) for s in cited if _kind(s) == 'independent'}) < 3:
            missing.append('3 independent publishers')
        if not any(_kind(s) in ('primary', 'company') or 'industry' in s.get('source_type', '').lower() for s in cited):
            missing.append('a primary or near-primary source (a filing, a regulator, an industry body or a company site)')
    elif key == 'risks':
        if len(publishers) < 3:
            missing.append('3 publishers')
        registrars = {s.get('registered_by') for s in cited} - {None}
        if registrars and not set(ANALYSTS) <= registrars:
            missing.append("sources from both analysts' research")
    return missing


def _scorecard(tables: list[list[list[str]]]) -> list[str]:
    """Problems with the executive summary's scorecard: six dimensions scored 1-10, and their equal-weight average."""
    for table in tables:
        header, rows = table[0], table[1:]
        column = _column(header, 'score')
        scores, composite = {}, None
        for row in rows:
            label = row[0].lower()
            cells = [row[column]] if column is not None and column < len(row) else row[1:]
            if 'composite' in label or 'overall' in label:
                found = next((m for cell in cells if (m := re.search(r'\d+(?:\.\d+)?', cell))), None)
                composite = float(found.group()) if found else None
                continue
            for name, stem in SCORE_DIMENSIONS.items():
                if stem in label and name not in scores:
                    found = next((m for cell in cells if (m := SCORE_RE.search(cell))), None)
                    scores[name] = int(found.group(1)) if found else None
        if len(scores) < 4:
            continue
        problems = [f'the scorecard has no {name} row' for name in SCORE_DIMENSIONS if name not in scores]
        problems += [f'{name} has no 1-10 score' for name, score in scores.items() if score is None]
        if composite is None:
            problems.append('the scorecard has no composite score')
        elif not problems:
            average = sum(scores.values()) / len(scores)
            if abs(composite - average) > 0.1:
                problems.append(f'the composite {composite:g} is not the average of the six scores ({average:.1f})')
        return problems
    return ['no scorecard table scoring the six dimensions 1-10']


def _scenario_table(tables: list[list[list[str]]]) -> list[str]:
    """Problems with the scenario table: bull, base and bear rows whose probabilities add up to 100%."""
    for table in tables:
        header, rows = table[0], table[1:]
        column = _column(header, 'prob')
        probabilities = {}
        for row in rows:
            case = next((c for c in ('bull', 'base', 'bear') if c in row[0].lower()), None)
            if case and case not in probabilities:
                cells = [row[column]] if column is not None and column < len(row) else row[1:]
                found = next((m for cell in cells if (m := re.search(r'(\d{1,3}(?:\.\d+)?)\s?%', cell))), None)
                probabilities[case] = float(found.group(1)) if found else None
        if len(probabilities) < 3:
            continue
        if None in probabilities.values():
            return ['a scenario has no probability']
        total = sum(probabilities.values())
        return [] if abs(total - 100) <= 2 else [f'the scenario probabilities add up to {total:g}%, not 100%']
    return ['no table with bull, base and bear scenarios and their probabilities']


def _depth(key: str, markdown: str, sources: list[dict], listed: bool) -> tuple[list[str], list[str]]:
    """A part's depth problems, and notes that do not count against it (a length past the target)."""
    part = PART_BY_KEY[key]
    by_id = {source['id']: source for source in sources}
    text = URL_RE.sub('', markdown)
    statements = list(_statements(text))
    tables = _tables(markdown)
    floor, ceiling = part.chars
    problems, notes = [], []
    if len(markdown) < floor:
        problems.append(f'{len(markdown):,} characters; the floor is {floor:,}')
    elif len(markdown) > ceiling:
        notes.append(f'{len(markdown):,} characters, past the {ceiling:,} to aim for; tighten it when you next revise')
    numbers = sum(len(_material_numbers(s)) for s in statements)
    needed = PRIVATE_NUMBERS.get(key, part.numbers) if not listed else part.numbers
    if numbers < needed:
        problems.append(f'{numbers} figures; needs {needed}')
    cited = _ids(text)
    if len(cited) < part.source_ids:
        problems.append(f'{len(cited)} distinct source IDs; needs {part.source_ids}')
    if len(tables) < part.tables:
        problems.append(f'{len(tables)} tables; needs {part.tables}')
    for table in tables:
        if any(_material_numbers(' '.join(row)) for row in table[1:]) and _column(table[0], 'source') is None:
            problems.append(f'the table headed "{" | ".join(table[0])[:60]}" has figures but no Source column')

    terms = PRIVATE_TERMS.get(key) if not listed and key in PRIVATE_TERMS else PART_TERMS.get(key, {})
    problems += [f'does not cover {group}' for group in _missing_terms(text, terms)]
    if part.analysis:
        problems += [f'no {group}' for group in _missing_terms(text, ANALYSIS_TERMS)]
        if not CONFIDENCE_RE.search(text):
            problems.append('no confidence statement (high, medium or low)')
        gate = _gate(key, [by_id[i] for i in _by_number(cited & set(by_id))], listed)
        if gate:
            problems.append('evidence gate: needs ' + '; '.join(gate))

    if key == 'executive_summary':
        problems += _scorecard(tables)
    elif key == 'scenarios':
        problems += _scenario_table(tables)
    elif key == 'one_question' and text.count('?') != 1:
        problems.append(f'{text.count("?")} question marks; ask exactly one question')
    elif key == 'takeaways':
        items = [line for line in markdown.splitlines() if re.match(r'\s*\d+[.)]\s+', line)]
        if len(items) != 3:
            problems.append(f'{len(items)} numbered takeaways; needs exactly 3')
        if any(not (_material_numbers(item) and SOURCE_ID_RE.search(item)) for item in items):
            problems.append('every takeaway needs a figure and its source ID')

    lowered = text.lower()
    shallow = [phrase for phrase in SHALLOW_PHRASES if phrase in lowered]
    if shallow:
        problems.append('empty phrases: ' + ', '.join(shallow))
    vague = [m.group() for m in VAGUE_RE.finditer(text)]
    if len(vague) > MAX_VAGUE:
        problems.append(f'{len(vague)} vague phrasings such as "{vague[0]}"; give the exact figure or name')
    return problems, notes


def check_part(key: str, markdown: str, sources: list[dict], listed: bool = True) -> dict:
    """One part against the rules N1-N3 and N6 and its depth standard. Reports only."""
    by_id = {source['id']: source for source in sources}
    text = URL_RE.sub('', markdown)
    findings = _sourcing_findings(text, by_id) + _internal_findings(text)
    depth, notes = _depth(key, markdown, sources, listed)
    return {'part': key, 'chars': len(markdown), 'findings': findings, 'depth': depth, 'notes': notes,
            'passed': not findings and not depth}


# A whole version

def _paragraphs(markdown: str) -> list[str]:
    blocks = re.split(r'\n\s*\n', markdown)
    return [b.strip() for b in blocks if len(b.strip()) >= 80 and not b.lstrip().startswith(('#', '|'))]


def _normalized(paragraph: str) -> str:
    text = re.sub(r'\d[\d,.]*%?', 'N', SOURCE_ID_RE.sub('S', paragraph.lower()))
    return re.sub(r'[^a-z ]+', '', re.sub(r'\s+', ' ', text))


def repeated_sentences(markdown: str) -> list[str]:
    """Sentences of 28 or more characters said three or more times (check_depth.py's repeated_sentences)."""
    counts: dict[str, int] = {}
    shown: dict[str, str] = {}
    for sentence in SENTENCE_RE.findall(URL_RE.sub('', markdown)):
        compact = re.sub(r'\s+', '', sentence)
        if len(compact) >= 28:
            counts[compact] = counts.get(compact, 0) + 1
            shown.setdefault(compact, sentence.strip())
    return [shown[key] for key, count in counts.items() if count > 2]


def near_duplicate_paragraphs(markdown: str) -> list[str]:
    """Paragraphs with three or more near-copies (check_depth.py's near_duplicate_paragraphs, for English)."""
    paragraphs = _paragraphs(markdown)
    normalized = [_normalized(p) for p in paragraphs]
    found, used = [], set()
    for i, base in enumerate(normalized):
        if i in used:
            continue
        similar = [i] + [j for j in range(i + 1, len(normalized)) if j not in used
                         and SequenceMatcher(None, base, normalized[j]).quick_ratio() >= 0.82
                         and SequenceMatcher(None, base, normalized[j]).ratio() >= 0.82]
        if len(similar) >= 3:
            used.update(similar)
            found.append(paragraphs[i][:140])
    return found


def check_version(markdown: str, parts: dict[str, str], rating: str | None, sources: list[dict],
                  listed: bool = True) -> dict:
    """A whole version: the assembled memo against the rules, each part's depth, and what spans parts.
    rating is None for parts not yet saved as a version."""
    report = check_memo(markdown, sources)
    report['parts'] = {}
    for part in PARTS:
        if parts.get(part.key):
            check = check_part(part.key, parts[part.key], sources, listed)
            report['parts'][part.key] = {'passed': check['passed'], 'findings': [f['rule'] for f in check['findings']],
                                         'depth': check['depth']}
    depth = []
    missing = [part.heading for part in PARTS if not parts.get(part.key)]
    if missing:
        depth.append('missing parts: ' + ', '.join(missing))
    summary = parts.get('executive_summary')
    if summary and rating and not re.search(r'\b' + re.escape(rating) + r'\b', summary, re.I):
        depth.append(f'the executive summary does not state the rating "{rating}"')
    depth += [f'said three or more times: "{s[:100]}"' for s in repeated_sentences(markdown)]
    depth += [f'paragraph repeated with small changes: "{p[:100]}"' for p in near_duplicate_paragraphs(markdown)]
    report['depth'] = depth
    report['passed'] = not report['findings'] and not depth and all(p['passed'] for p in report['parts'].values())
    return report


def sources_table(sources: list[dict], cited: set[str]) -> str:
    """The generated Sources part: each cited, registered source with its type, date and link."""
    rows = ['| ID | Source | Type | Date | Link |', '|---|---|---|---|---|']
    for source in sources:
        if source['id'] in cited:
            cells = [source['id'], source['title'], source['source_type'], source.get('date', ''), source['location']]
            rows.append('| ' + ' | '.join(str(cell).replace('|', '/').replace('\n', ' ') for cell in cells) + ' |')
    return '\n'.join(rows) if len(rows) > 2 else 'No sources cited.'


def assemble(parts: dict[str, str], scope: dict, rating: str, data_as_of: str, sources: list[dict]) -> str:
    """The memo as delivered: header, the parts in order (saying when one is missing), the cited sources and the
    disclaimer."""
    company = scope.get('company') or 'Company'
    ticker = scope.get('ticker') or 'private'
    lines = [f'# {company} ({ticker}): investment memo', f'Rating: {rating}', f'Data as of: {data_as_of}', '']
    for part in PARTS:
        lines += [f'## {part.heading}', '', (parts.get(part.key) or '').strip() or '_Not available in this version._', '']
    cited = _ids(URL_RE.sub('', '\n'.join(parts.get(part.key) or '' for part in PARTS)))
    lines += ['## Sources', '', sources_table(sources, cited), '', DISCLAIMER, '']
    return '\n'.join(lines)
