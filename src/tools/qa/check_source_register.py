"""The source register, ported from scripts/check_source_register.py: at least 8 usable sources, 4 of
them independent and 1 primary or near-primary.

A usable source has a title, a type, a link or file reference, a date, the claims it supports and a confidence of
high, medium or low. Independent means not company-provided (and not unchecked OCR); primary means a filing, a
regulator, an official registry, a patent or the company's own disclosure.

Fixed here: the script matched types by substring, so "sec" counted "secondary" as a filing and "sse" counted
"assessment" as an exchange; types are matched as words.
"""
import re

from .check_evidence import PRIMARY_TYPES_RE
from .terms import has_placeholder

MIN_SOURCES, MIN_INDEPENDENT, MIN_PRIMARY = 8, 4, 1
CONFIDENCE_RE = re.compile(r'high|medium|low|高|中|低', re.I)
NOT_INDEPENDENT_RE = re.compile(r'company-provided|company provided|\bocr\b|公司提供', re.I)


def usable(source: dict) -> bool:
    fields = ('title', 'source_type', 'location', 'date', 'claims')
    return (all(str(source.get(field) or '').strip() for field in fields)
            and bool(CONFIDENCE_RE.search(str(source.get('confidence') or '')))
            and not has_placeholder(' '.join(str(source.get(field) or '') for field in fields)))


def check_source_register(sources: list[dict]) -> dict:
    rows = [source for source in sources if usable(source)]
    independent = [s for s in rows if not NOT_INDEPENDENT_RE.search(s['source_type'])]
    primary = [s for s in rows if PRIMARY_TYPES_RE.search(s['source_type'])]
    failures = []
    if len(rows) < MIN_SOURCES:
        failures.append(f'{len(rows)} usable sources; needs {MIN_SOURCES} (each with a title, type, link or file, date, '
                        'the claims it supports and a confidence)')
    if len(independent) < MIN_INDEPENDENT:
        failures.append(f'{len(independent)} independent sources; needs {MIN_INDEPENDENT}')
    if len(primary) < MIN_PRIMARY:
        failures.append('no primary or near-primary source')
    unusable = [s['id'] for s in sources if not usable(s)]
    return {'failures': failures, 'passed': not failures, 'usable': len(rows), 'independent': len(independent),
            'primary': len(primary), 'incomplete': unusable}
