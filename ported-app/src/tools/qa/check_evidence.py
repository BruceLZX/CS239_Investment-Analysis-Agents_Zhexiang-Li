"""The evidence matrix, ported from scripts/check_evidence.py: the pre-draft gate for each section.

Every numbered section needs an evidence block before it is drafted:
- at least 4 targeted search queries;
- at least 4 rows of the Deep Evidence Table, each with every cell argued (facts, mechanism and investor
  implication 24+ characters; benchmark, counter-evidence and follow-up 18+), at least one row resting on a primary
  or near-primary source, and at least 2 distinct registered source IDs;
- at least 8 of the 9 section-gate items checked;
- all 8 fields of the internal section plan, 12+ characters each;
- no internal writing rubric, and no cell that repeats another section's.

For a listed company the matrix also needs rows on market data, the income statement, cash flow, the balance sheet
and debt, valuation, consensus and guidance, and capital allocation.

Fixed here:
- The script counted every bullet in a block as a search query, the section plan's own lines included; only the
  queries count now.
- It failed a block whose "prohibited words" field listed the prohibited words; that field is exempt.
- A confidence failed a 3-character minimum; it needs a level, not a length.
- Normalisation folded every English word into one letter, so English cells looked like copies of each other.
- Primary sources are recognised from the register's source type, not by keywords where "sec" matched "secondary".
"""
from difflib import SequenceMatcher
import re

from .. import sections
from .terms import INTERNAL_WRITING_TERMS, SOURCE_ID_RE, has_placeholder

MIN_QUERIES, MIN_ROWS, MIN_CHECKED, MIN_SOURCE_IDS = 4, 4, 8, 2
GATE_ITEMS = (
    '2+ independent sources opened',
    '1+ primary or near-primary source checked where available',
    '2+ numeric facts/proxies or explicit missing-data note',
    'source IDs mapped to source register',
    'mechanism/economic logic explained from evidence',
    '1+ competitor/benchmark/base-rate comparison',
    '1+ counter-evidence or failure mode',
    'investor implication stated',
    '2-5 diligence questions listed',
)
PLAN_FIELDS = {
    'decision_question': 'Decision question',
    'thesis_sentence': 'Final-report thesis sentence',
    'why_different': 'Why this section is different from the other sections',
    'mechanism': 'Evidence mechanism to explain',
    'comparison_set': 'Comparison set / base rate',
    'counter_evidence': 'Counter-evidence or failure mode to price',
    'visual': 'Best visual artifact, if any',
    'prohibited': 'Words/patterns prohibited in final report',
}
ROW_FIELDS = {  # cell: (label, minimum characters)
    'source_ids': ('Source IDs', 2), 'source_type': ('Source type', 3), 'finding': ('Finding / fact', 24),
    'mechanism': ('Mechanism', 24), 'benchmark': ('Benchmark / peer context', 18),
    'weakens': ('Weakens / contradicts', 18), 'implication': ('Investor implication', 24),
    'confidence': ('Confidence', 1), 'follow_up': ('Follow-up', 18),
}
CONFIDENCE_RE = re.compile(r'high|medium|low', re.I)
PRIMARY_TYPES_RE = re.compile(r'\bprimary\b|near-primary|filing|regulat|official|registry|patent|company page|'
                              r'press release', re.I)
# Dedicated evidence rows for a listed company.
PUBLIC_EQUITY_ROWS = {
    'market data': ('market data', 'share price', 'market cap'),
    'income statement': ('income statement', 'revenue', 'margin'),
    'cash flow': ('cash flow', 'free cash flow', 'capex'),
    'balance sheet and debt': ('balance sheet', 'debt', 'liquidity'),
    'valuation': ('valuation', 'p/e', 'ev/', 'multiple'),
    'consensus and guidance': ('consensus', 'guidance'),
    'capital allocation': ('buyback', 'dividend', 'capital allocation', 'repurchase'),
}
DUPLICATE_FIELDS = ('mechanism', 'benchmark', 'weakens', 'implication', 'follow_up')


def _normalized(cell: str) -> str:
    text = SOURCE_ID_RE.sub('s', cell.lower())
    for section in sections.SECTIONS:
        text = text.replace(section.title.lower(), 'this section')
    text = re.sub(r'\d[\d,.]*%?', 'n', text)
    return re.sub(r'[\s,.!?;:()“”"\'\[\]]+', ' ', text).strip()


def _is_primary(row: dict, by_id: dict) -> bool:
    if PRIMARY_TYPES_RE.search(row.get('source_type', '')):
        return True
    return any(PRIMARY_TYPES_RE.search(by_id[i].get('source_type', ''))
               for i in SOURCE_ID_RE.findall(row.get('source_ids', '')) if i in by_id)


def check_block(block: dict | None, sources: list[dict]) -> list[str]:
    """One section's evidence block; an empty list is a pass."""
    if not block:
        return ['no evidence block: research the section and save its evidence before drafting it']
    by_id = {source['id']: source for source in sources}
    failures = []
    queries = [q for q in block.get('queries') or [] if q.strip()]
    if len(queries) < MIN_QUERIES:
        failures.append(f'{len(queries)} search queries; needs {MIN_QUERIES} targeted ones')
    rows = block.get('rows') or []
    if len(rows) < MIN_ROWS:
        failures.append(f'{len(rows)} evidence rows; needs {MIN_ROWS}')
    checked = [item for item in block.get('gate') or [] if item in GATE_ITEMS]
    if len(checked) < MIN_CHECKED:
        failures.append(f'{len(checked)} of the 9 section-gate items checked; needs {MIN_CHECKED}')
    plan = block.get('plan') or {}
    for key, label in PLAN_FIELDS.items():
        if len((plan.get(key) or '').strip()) < 12:
            failures.append(f'section plan: "{label}" is missing or under 12 characters')
    text = ' '.join([*queries, *(str(v) for k, v in plan.items() if k != 'prohibited'),
                     *(str(cell) for row in rows for cell in row.values())])
    failures += [f'internal writing rubric in the block: "{term}"' for term in INTERNAL_WRITING_TERMS if term in text]
    if any(has_placeholder(' '.join(str(cell) for cell in row.values())) for row in rows):
        failures.append('placeholder text (TODO, TBD, xxx) in the evidence rows')
    if rows and not any(_is_primary(row, by_id) for row in rows):
        failures.append('no row rests on a primary or near-primary source (a filing, a regulator, a registry, a patent '
                        'or the company\'s own disclosure)')
    ids = {i for row in rows for i in SOURCE_ID_RE.findall(row.get('source_ids', ''))}
    unknown = sorted(ids - set(by_id), key=lambda s: int(s[1:]))
    if unknown:
        failures.append('source IDs not in the register: ' + ', '.join(unknown))
    if len(ids & set(by_id)) < MIN_SOURCE_IDS:
        failures.append(f'{len(ids & set(by_id))} distinct registered source IDs; needs {MIN_SOURCE_IDS}')
    for n, row in enumerate(rows, 1):
        short = [label for key, (label, least) in ROW_FIELDS.items() if len(str(row.get(key, '')).strip()) < least]
        if short:
            failures.append(f'row {n}: too thin in ' + ', '.join(short))
        elif not CONFIDENCE_RE.search(str(row.get('confidence', ''))):
            failures.append(f'row {n}: confidence must say high, medium or low')
    return failures


def check_evidence(blocks: dict[str, dict], sources: list[dict], listed: bool = True,
                   keys: list[str] | None = None) -> dict:
    """The evidence matrix for the given sections (default: all fourteen)."""
    wanted = keys or [section.key for section in sections.SECTIONS]
    per_section = {key: check_block(blocks.get(key), sources) for key in wanted}
    failures = []
    cells = [(key, field, str(row.get(field, ''))) for key in wanted for row in (blocks.get(key) or {}).get('rows') or []
             for field in DUPLICATE_FIELDS if len(str(row.get(field, ''))) >= 32]
    normalized = [(key, field, _normalized(cell)) for key, field, cell in cells]
    for field in DUPLICATE_FIELDS:
        group = [(key, text) for key, f, text in normalized if f == field and len(text) >= 32]
        for i, (key, text) in enumerate(group):
            alike = [k for j, (k, other) in enumerate(group) if j != i and k != key
                     and SequenceMatcher(None, text, other).quick_ratio() >= 0.86
                     and SequenceMatcher(None, text, other).ratio() >= 0.86]
            if len(alike) >= 3:
                failures.append(f'the "{ROW_FIELDS[field][0]}" cells repeat one pattern across sections '
                                f'({", ".join(sorted({key, *alike}))}); write each from that section\'s evidence')
                break
    if listed and set(wanted) == {section.key for section in sections.SECTIONS}:
        everything = ' '.join(str(cell) for block in blocks.values() for row in block.get('rows') or []
                              for cell in row.values()).lower()
        failures += [f'public equity: no evidence row on {name}' for name, words in PUBLIC_EQUITY_ROWS.items()
                     if not any(word in everything for word in words)]
    passed = not failures and not any(per_section.values())
    return {'failures': failures, 'sections': per_section, 'passed': passed}
