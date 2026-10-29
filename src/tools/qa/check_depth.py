"""Section depth, ported from the skill's scripts/check_depth.py.

Per section: at least 2,500 characters, 8 numeric facts, 6 source mentions, 4 distinct source IDs and 6 analytical
paragraphs; at most 6 inline source tags; every analytical-coverage group; no shallow, vague, filler or
writing-about-writing phrases; and the section's granularity markers. Across the report: boilerplate limits,
sentences said three or more times and paragraphs copied with small changes.

Fixed here, with the skill's thresholds kept:
- main() used `visible_text` without defining it, so the granularity and vague-phrase stage never ran; it runs here.
- Numbers counted the digits of source IDs ("S12") and of URLs; they no longer do.
- Repeated sentences were counted over the raw page, CSS and JavaScript included; only visible text is now.
- Near-duplicate paragraphs kept whitespace (a raw-string slip, "\\s" inside a character class) and folded every
  English word into the same letter, so English paragraphs looked alike; words now survive normalisation.
- The granularity markers named brain-computer-interface companies; they are generic here (sections.py) and cover
  section 13, which had none.
Also added, from SKILL.md and the playbooks rather than the script: the components and tables each section needs.
"""
from difflib import SequenceMatcher
import re

from .. import report, sections
from .terms import (ANALYTICAL_COVERAGE, BOILERPLATE_LIMITS, FORBIDDEN_PATTERNS, MAX_VAGUE, PARAGRAPH_RE,
                    SECTION_FILLER, SENTENCE_RE, SHALLOW_PHRASES, SOURCE_ID_RE, SOURCE_MENTION_RE, VAGUE_PATTERNS,
                    missing_groups, numbers, source_ids, strip_html)

MIN_CHARS, MIN_NUMBERS, MIN_SOURCE_MENTIONS, MIN_SOURCE_IDS, MIN_PARAGRAPHS = 2500, 8, 6, 4, 6
MAX_INLINE_TAGS = 6
MAX_TITLE_MENTIONS = 4
SOURCE_TAG_RE = re.compile(r'class="[^"]*\bsource-tag\b[^"]*"')
SECTION_RE = re.compile(r'<section[^>]+class="[^"]*section-card[^"]*"[^>]+id="s(?P<num>\d+)"[\s\S]*?>'
                        r'(?P<body>[\s\S]*?)</section>', re.I)


def _paragraphs(body_html: str) -> list[str]:
    return [p for p in PARAGRAPH_RE.findall(body_html) if 'source-note' not in p]


def _table_labels(markdown: str) -> list[str]:
    """What each Markdown table is about, lowercased: its header row and its first column (a statements table
    names "Revenue" in its rows, not its header). Components' tables count too."""
    labels, current = [], None
    for line in markdown.splitlines() + ['']:
        stripped = line.strip()
        if stripped.startswith('|'):
            cells = [cell.strip() for cell in stripped.strip('|').split('|')]
            if re.fullmatch(r':?-{2,}:?', cells[0] or '-'):
                continue
            current = current + [cells[0]] if current is not None else [' '.join(cells)]
        elif current is not None:
            labels.append(' '.join(current).lower())
            current = None
    return labels


def check_section(section: sections.Section, markdown: str, body_html: str, listed: bool = True) -> dict:
    """One numbered section. Returns its counts and failures; an empty failure list is a pass."""
    text = strip_html(body_html)
    lowered = text.lower()
    failures = []
    for title in (section.title_zh, section.title_en):
        if text.count(title) > MAX_TITLE_MENTIONS:
            failures.append(f'repeats its own title "{title}" {text.count(title)} times; write about the company instead')
    failures += [f'writes about how the report is made ("{m.group()}")'
                 for pattern in FORBIDDEN_PATTERNS for m in [re.search(pattern, text, re.I)] if m]

    counts = {
        'chars': len(text),
        'paragraphs': len(_paragraphs(body_html)),
        'numbers': len(numbers(text)),
        'source_mentions': (len(re.findall(r'https?://', body_html)) + len(SOURCE_TAG_RE.findall(body_html))
                            + len(SOURCE_MENTION_RE.findall(text))),
        'source_ids': len(source_ids(text)),
        'inline_tags': len(SOURCE_TAG_RE.findall(body_html)),
    }
    floors = (('chars', MIN_CHARS, 'characters'), ('paragraphs', MIN_PARAGRAPHS, 'analytical paragraphs'),
              ('numbers', MIN_NUMBERS, 'numeric facts'), ('source_mentions', MIN_SOURCE_MENTIONS, 'source mentions'),
              ('source_ids', MIN_SOURCE_IDS, 'distinct source IDs'))
    failures += [f'{counts[key]:,} {label}; needs {floor:,}' for key, floor, label in floors if counts[key] < floor]
    if counts['inline_tags'] > MAX_INLINE_TAGS:
        failures.append(f'{counts["inline_tags"]} inline source tags; at most {MAX_INLINE_TAGS} (cite per paragraph, '
                        'and put row-level sources in a table\'s Source column)')
    failures += [f'no {group}' for group in missing_groups(text, ANALYTICAL_COVERAGE)]
    shallow = [phrase for phrase in SHALLOW_PHRASES if phrase in lowered]
    if shallow:
        failures.append('empty phrases: ' + ', '.join(shallow))
    failures += [f'filler: "{phrase}"' for phrase in SECTION_FILLER if phrase in text]

    failures += [f'granularity: no {name}' for name, pattern in section.markers if not re.search(pattern, text, re.I)]
    vague = [m.group() for pattern in VAGUE_PATTERNS for m in re.finditer(pattern, text, re.I)]
    if len(vague) > MAX_VAGUE:
        failures.append(f'{len(vague)} vague phrasings such as "{vague[0]}"; give the exact figure or name')

    present = report.components_in(markdown)
    failures += [f'missing the "::: {kind}" component' for kind in section.components if kind not in present]
    labels = _table_labels(markdown)
    for table in section.tables:
        if table.listed is not None and table.listed != listed:
            continue
        if not any(any(word in label for word in table.keywords) for label in labels):
            failures.append(f'no {table.name} (a table with a column such as "{table.keywords[0]}")')
    return {'section': section.key, 'counts': counts, 'failures': failures, 'passed': not failures}


def _normalized(paragraph: str) -> str:
    text = SOURCE_ID_RE.sub('s', strip_html(paragraph).lower())
    for section in sections.SECTIONS:
        text = text.replace(section.title_zh, '本节').replace(section.title_en.lower(), '本节')
    text = re.sub(r'\d[\d,.]*%?', 'n', text)
    return re.sub(r'[\s，。；：、,.!?！？;:（）()《》“”"\'\\]+', ' ', text).strip()


def repeated_sentences(visible_text: str) -> list[str]:
    """Sentences of 28 or more non-space characters said three or more times."""
    counts: dict[str, int] = {}
    shown: dict[str, str] = {}
    for sentence in SENTENCE_RE.findall(visible_text):
        compact = re.sub(r'\s+', '', sentence)
        if len(compact) >= 28:
            counts[compact] = counts.get(compact, 0) + 1
            shown.setdefault(compact, sentence.strip())
    return [shown[key] for key, count in counts.items() if count >= 3]


def near_duplicate_paragraphs(report_html: str) -> list[str]:
    """Groups of three or more paragraphs (80+ characters) that are 82% alike once figures and IDs are masked."""
    paragraphs = [p for p in _paragraphs(report_html) if len(strip_html(p)) >= 80]
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
            found.append(strip_html(paragraphs[i])[:140])
    return found


def check_report_depth(report_html: str, section_markdown: dict[str, str], listed: bool = True) -> dict:
    """The whole report, as check_depth.py runs over a finished HTML file."""
    failures = []
    bodies = {int(m.group('num')): m.group('body') for m in SECTION_RE.finditer(report_html)}
    if len(bodies) != 14:
        failures.append(f'expected 14 analysis sections, found {len(bodies)}')
    visible = strip_html(report_html)
    for pattern, most in BOILERPLATE_LIMITS:
        found = len(re.findall(pattern, report_html, re.I))
        if found > most:
            failures.append(f'"{pattern}" appears {found} times; at most {most}')
    failures += [f'said three or more times: "{s[:100]}"' for s in repeated_sentences(visible)]
    failures += [f'paragraph repeated with small changes: "{p[:100]}"' for p in near_duplicate_paragraphs(report_html)]
    per_section = {}
    for section in sections.SECTIONS:
        markdown = section_markdown.get(section.key) or ''
        per_section[section.key] = check_section(section, markdown, bodies.get(section.number, ''), listed)
    passed = not failures and all(result['passed'] for result in per_section.values())
    return {'failures': failures, 'sections': per_section, 'passed': passed}
