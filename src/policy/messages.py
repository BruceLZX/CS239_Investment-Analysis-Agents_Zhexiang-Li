"""What the Lead may tell the user: N5 (no rating before delivery), N6 (no internal material) and P8 (status only)."""
import re

from tools import case_file, memo

STATUS_LIMIT = 300
# Two ratings side by side ("a Buy or Sell call", "Invest/Pass") name the question, not an answer.
RATING_WORDS = r'(?:buy|add|hold off|hold-off|hold|reduce|sell|avoid|watchlist|invest now|invest with conditions|' \
               r'invest|wait for milestone|wait|pass)'
RATING_PAIR_RE = re.compile(rf'\b{RATING_WORDS}\s*(?:/|\bor\b)\s*{RATING_WORDS}\b', re.I)
# What a message to the user must not mention (rule N6); a status note may still describe the work.
INTERNAL_RE = re.compile(r'\bmust[- ]fix\b|\bshould[- ]fix\b|\bevidence (?:packets?|blocks?|matrix)\b'
                         r'|\brewrite plan\b|\bred[- ]team review\b|\bCritical items?\b'
                         r'|\b(?:get|save|set|list|find|read|register|deliver|start|finish|run|request|search)'
                         r'_[a-z_]+\b', re.I)


def named_ratings(text: str, ratings: set[str]) -> list[str]:
    """The ratings a message states as an answer, leaving aside a pair that only names the question."""
    answer = RATING_PAIR_RE.sub(' ', text)
    return sorted(r for r in ratings if re.search(rf'\b{re.escape(r)}\b', answer))


def internal_material(text: str) -> list[str]:
    return sorted({m.group() for m in INTERNAL_RE.finditer(text)} | set(memo.internal_ids(text)))


def problems(text: str, case: dict) -> list[tuple[str, str]]:
    """Each rule a message to the user would break, with what to do instead. Until a version is delivered it is a
    status note; the message that the final review failed may run longer, since it lists the open issues (P9)."""
    found = []
    delivered = bool(case['deliveries'])
    if not delivered and not case_file.final_review_failed(case) and len(text) > STATUS_LIMIT:
        found.append(('P8', f'this status note is {len(text):,} characters, and until a version is delivered a note is '
                            f'at most {STATUS_LIMIT}. Say only what the team is doing and waiting for.'))
    if not delivered:
        named = named_ratings(text, {draft['rating'] for draft in case['memo_drafts']})
        if named:
            found.append(('N5', f"this tells the user the draft's rating ({', '.join(named)}) before any version is "
                                'delivered. Say what the team is doing instead.'))
    internal = internal_material(text)
    if internal:
        found.append(('N6', f"this names internal working material ({', '.join(internal[:6])}). Say it in the user's "
                            'terms.'))
    return found
