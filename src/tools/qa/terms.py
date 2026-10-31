"""Word lists and patterns shared by the QA checks: the original scripts' lists, in English."""
import html
import re

# A source ID: S and digits, not inside another word or number.
SOURCE_ID_RE = re.compile(r'(?<![A-Za-z0-9])S\d+(?!\d)')
URL_RE = re.compile(r'https?://[^\s|)>"\]]+')
STYLE_SCRIPT_RE = re.compile(r'<(style|script)[^>]*>[\s\S]*?</\1>', re.I)
TAG_RE = re.compile(r'<[^>]+>')
PARAGRAPH_RE = re.compile(r'<p(?:\s+[^>]*)?>[\s\S]*?</p>', re.I)
SENTENCE_RE = re.compile(r'[^.!?]{24,}[.!?]')
# check_depth.py's NUMBER_PATTERN.
NUMBER_RE = re.compile(r'(?<![A-Za-z])(?:\d+(?:\.\d+)?%?|\d+(?:\.\d+)?\s*(?:billion|million|m|bn))', re.I)
# "placeholder" alone is an ordinary word; only a bracketed one is left over from a template.
PLACEHOLDER_TERMS = ('todo', 'tbd', 'xxx', '[placeholder]')

# check_depth.py ANALYTICAL_COVERAGE_TERMS.
ANALYTICAL_COVERAGE = {
    'evidence/source grounding': ('source', 'filing', 'disclosed', 'reported', 'according to', 'verified', 'evidence'),
    'economic/strategic interpretation': ('because', 'driven by', 'economics', 'unit economics', 'means', 'implies',
                                          'reflects', 'as a result', 'due to'),
    'comparison/context': ('benchmark', 'peer', 'comparable', 'compared', 'versus', ' vs', 'median', 'relative to', 'than'),
    'counter-evidence/risk': ('counter', 'bear case', 'downside', 'however', 'risk', 'weaken', 'contradict'),
    'investor implication': ('watchlist', 'implication', 'investor', 'valuation', 'position', 'thesis', 'recommend'),
    'open diligence': ('diligence', 'follow-up', 'open question', 'to verify', 'unverified', 'to confirm', 'not disclosed'),
    'confidence/calibration': ('confidence', 'high', 'medium', 'low'),
}
# check_depth.py counts these words as source mentions, with URLs and source tags.
SOURCE_MENTION_RE = re.compile(r'Source|source|filing|10-K|10-Q|8-K|annual report|disclosed|according to|reported')

# check_depth.py SHALLOW_PHRASES, and the ones this app has used since Phase 1.
SHALLOW_PHRASES = ('huge market', 'massive opportunity', 'strong team', 'high barriers to entry', 'clear business model',
                   'fierce competition', 'risks are manageable', 'bright future', 'significant potential',
                   'well positioned', 'well-positioned', 'best-in-class', 'world-class')
# check_depth.py VAGUE_PATTERNS (more than two fail a section).
VAGUE_PATTERNS = (
    r'approximately\s*\d+',
    r'\b(?:roughly|around|about)\s+\$?\d',
    r'\b(?:many|numerous|several)\s+(?:patents|customers|partners)\b',
    r'\b(?:graduated from|worked at) (?:a )?(?:top|leading|prestigious|well-known) (?:university|company|firm)',
    r'\b(?:team|founders|management)\s+(?:is|are)\s+(?:experienced|strong|excellent)\b',
    r'\b(?:valuation|revenue|profit)\s+(?:is|looks)\s+(?:reasonable|decent|good|solid)\b',
)
MAX_VAGUE = 2
# check_depth.py FINAL_REPORT_FORBIDDEN_PATTERNS (writing about how the report is made).
FORBIDDEN_PATTERNS = (
    r'\bcannot be written as\b', r'\bmust put the evidence grade\b', r'\brather than splitting the material into isolated facts\b',
    r'\bhandles evidence, counter-evidence, mechanism and investment implication\b',
    r'\bmust be judged in its own context\b', r'\bkey originals cannot be provided within 18-24 months\b',
    r'\bfirst verify what the target actually controls\b',
    r'\bthis (?:part|section|report|memo) (?:should|must|will|needs to)\b', r'\bas (?:briefed|instructed)\b',
    r'\bevidence gate\b', r'\bpart check\b', r'\bsection check\b', r'\bthe brief asked\b', r'\bsource IDs? (?:are|is) only\b',
)
# check_depth.py PER_SECTION_FILLER_TERMS.
SECTION_FILLER = ('original documents should be prioritized in three tiers',
                  'these ids only show where the evidence came from and do not replace diligence on the originals',
                  'cross-checked public sources against company materials', 'do not price unverified milestones in one go')
# check_depth.py BOILERPLATE_LIMITS: (pattern, most allowed in the whole report).
BOILERPLATE_LIMITS = (
    ('class="source-note"', 2), ('Citation anchor', 1), ('original documents should be prioritized in three tiers', 1),
    ('the first tier is whether the target can prove it really owns the assets, people and contracts', 1),
    ('these IDs only show where the evidence came from and do not replace diligence on the originals', 1),
    ('the 2026 budget and 2027 milestones also need a separate check', 1),
    ('cross-checked public sources against company materials', 4), ('do not price unverified milestones in one go', 3),
    ('compared with looking only at how hot the sector is', 2), ('the implication for deal structure is also direct', 2),
    ('so the investment implication of this section', 3),
    (r'Judgement:[^.]{0,80}must put the evidence grade, economic mechanism, alternatives, counter-evidence and investment '
     'action in one logical chain', 1),
    ('economic mechanism must be explained through registration, physician adoption, patient adherence, payment path, '
     'channel reorders and real collections', 1), ('Original-document priority:', 1),
    ('How investors should read this', 2), ('Economic mechanism:', 4), ('Comparison and benchmark:', 4),
    ('Counter-evidence and risk:', 4), ('Investor implication:', 4), ('Decision threshold:', 1), ('Decision checklist:', 1),
)
INTERNAL_WRITING_TERMS = ('cannot be written as', 'must put the evidence grade',
                          'rather than splitting the material into isolated facts',
                          'handles evidence, counter-evidence, mechanism and investment implication',
                          'source IDs are only used to lock down')


def strip_html(markup: str) -> str:
    """Visible text: style and script removed (check_depth.py skipped this, so CSS counted as text), tags dropped,
    entities decoded and whitespace collapsed."""
    text = TAG_RE.sub(' ', STYLE_SCRIPT_RE.sub(' ', markup))
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def source_ids(text: str) -> set[str]:
    return set(SOURCE_ID_RE.findall(URL_RE.sub('', text)))


def numbers(text: str) -> list[str]:
    """Numeric facts as check_depth.py counts them, without the digits of source IDs and URLs."""
    return NUMBER_RE.findall(SOURCE_ID_RE.sub(' ', URL_RE.sub(' ', text)))


def missing_groups(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = text.lower()
    return [name for name, words in groups.items() if not any(word.lower() in lowered for word in words)]


def has_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(r'(?<![a-z\[])' + re.escape(term) + r'(?![a-z\]])', lowered) for term in PLACEHOLDER_TERMS)
