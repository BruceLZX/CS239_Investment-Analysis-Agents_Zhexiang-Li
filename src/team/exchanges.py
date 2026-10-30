"""What the agents did with each other's work, besides messages: the sections and evidence they read, the sources they
cited that another agent registered, the notes they left each other, the section the Red Team called weakest and the
review items the IC Reviewer routed to their owners.

Every message goes through the Lead (P2), so this is where the rest of the team's work with each other shows. It is
worked out from the case file and the server's tool log, which every run has, so a recorded run shows it too. The
Lead is left out: what passes through it is already a message.
"""
import json
from pathlib import Path

from tools import sections
from tools.qa.terms import SOURCE_ID_RE

from .profiles import LEAD, RED_TEAM, REVIEWER

READS = {'get_memo_parts': 'read', 'get_evidence_matrix': 'read the evidence for'}


def read_tool_log(run_dir: Path) -> list[dict]:
    """The MCP server's log for a run, each call's arguments as JSON."""
    path = run_dir / 'tool_log.jsonl'
    if not path.exists():
        return []
    calls = []
    for line in path.read_text().splitlines():
        call = json.loads(line)
        if isinstance(call.get('arguments'), str):
            call['arguments'] = json.loads(call['arguments'])
        calls.append(call)
    return calls


def _name(key: str) -> str:
    """A section as the page and the trace name it: "S7 financials"."""
    section = sections.BY_KEY.get(key)
    return (f'S{section.number} ' if section and section.number else '') + key.replace('_', ' ')


def _between(sender: str | None, recipient: str | None) -> bool:
    return bool(sender and recipient) and sender != recipient and LEAD not in (sender, recipient)


def _reads(log: list[dict]) -> list[dict]:
    found = []
    for call in log:
        verb = READS.get(call.get('tool'))
        if not verb or call.get('error'):
            continue
        wanted = (call.get('arguments') or {}).get('sections_wanted') or []
        by_owner: dict[str, list[str]] = {}
        for name in [wanted] if isinstance(wanted, str) else wanted:
            try:
                key = sections.section_key(str(name))
            except ValueError:
                continue
            by_owner.setdefault(sections.BY_KEY[key].owner, []).append(key)
        for owner, keys in by_owner.items():
            if _between(call.get('agent'), owner):
                what = f'{len(keys)} sections' if len(keys) > 1 else _name(keys[0]).split()[0]
                found.append({'ts': call['ts'], 'kind': 'read', 'from': call['agent'], 'to': owner,
                              'label': f"{'read evidence' if verb != 'read' else 'read'} {what}",
                              'text': f"{verb} {', '.join(_name(key) for key in keys)}"})
    return found


def _citations(case: dict) -> list[dict]:
    """Each source an agent first cited that another agent had registered, by the section revision that cited it."""
    registered = {source['id']: source.get('registered_by') for source in case.get('sources') or []}
    revisions = [(key, revision) for key, saved in (case.get('memo_parts') or {}).items() for revision in saved]
    seen, found = set(), []
    for key, revision in sorted(revisions, key=lambda pair: pair[1]['saved_at']):
        author, by_owner = revision.get('author'), {}
        for source_id in dict.fromkeys(SOURCE_ID_RE.findall(revision.get('markdown') or '')):
            owner = registered.get(source_id)
            if _between(author, owner) and (author, source_id) not in seen:
                seen.add((author, source_id))
                by_owner.setdefault(owner, []).append(source_id)
        for owner, ids in by_owner.items():
            found.append({'ts': revision['saved_at'], 'kind': 'cite', 'from': author, 'to': owner,
                          'label': f'cited {ids[0]}' if len(ids) == 1 else f'cited {len(ids)} sources',
                          'text': f"cited {', '.join(ids)} in {_name(key)}"})
    return found


def _review_items(case: dict) -> list[dict]:
    return [{'ts': review['finished_at'], 'kind': 'review', 'from': REVIEWER, 'to': owner, 'label': 'review items',
             'text': f"{review['id']}: items on {', '.join(_name(key) for key in keys)}"}
            for review in case.get('reviews') or [] if review.get('finished_at')
            for owner, keys in (review.get('revision_requests') or {}).items() if _between(REVIEWER, owner)]


def _red_team(case: dict) -> list[dict]:
    review = (case.get('workflow') or {}).get('red_team_review') or {}
    key = review.get('weakest_section')
    owner = sections.BY_KEY[key].owner if key in sections.BY_KEY else None
    if not review.get('saved_at') or not _between(RED_TEAM, owner):
        return []
    return [{'ts': review['saved_at'], 'kind': 'attack', 'from': RED_TEAM, 'to': owner, 'label': 'weakest section',
             'text': f'named {_name(key)} the weakest section'}]


def _notes(case: dict) -> list[dict]:
    found = []
    for note in case.get('notes') or []:
        if _between(note.get('from'), note.get('to')):
            answering = note.get('answers')
            cited = f" [{', '.join(note['source_ids'])}]" if note.get('source_ids') else ''
            found.append({'ts': note['at'], 'kind': 'answer' if answering else 'note', 'from': note['from'],
                          'to': note['to'], 'label': f'answered {answering}' if answering else f"note {note['id']}",
                          'text': note['note'] + cited})
    return found


def exchanges(case: dict, log: list[dict]) -> list[dict]:
    """Every exchange between two agents other than the Lead, oldest first: when, what kind (read, cite, note, answer,
    attack or review), from and to whom, a short label and what happened."""
    found = _reads(log) + _citations(case) + _review_items(case) + _red_team(case) + _notes(case)
    return sorted(found, key=lambda exchange: exchange['ts'])
