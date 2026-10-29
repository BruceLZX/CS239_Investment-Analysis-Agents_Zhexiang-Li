"""Per-run case file: the shared state the bots read and write through MCP tools.

One scenario runs at a time. team.run_scenario writes runs/active.json; every tool call
loads the active run's case.json, changes it and saves it back. The case file also lets
the Lead see what has actually arrived, instead of relying on memory across Rakazo runs.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import threading

from . import memo
from .agents import AGENTS, ANALYSTS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'  # Read at call time, so tests can point it at a temporary folder.
# Review rounds per memo: the analysts revise after the first and second, the Lead alone after the second.
MAX_REVIEW_ROUNDS = 3
_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def new_case(run_id: str, scenario: str, client_documents: list[dict], request: str | None = None) -> dict:
    return {
        'run_id': run_id, 'scenario': scenario, 'request': request, 'started_at': now(), 'scope': None,
        'client_documents': client_documents,
        # memo_parts holds each part's revisions; memo_drafts holds the versions, snapshots of the parts.
        'sources': [], 'evidence_packets': [], 'memo_parts': {}, 'memo_drafts': [],
        'reviews': [], 'deliveries': [],
    }


def start_run(scenario: str, client_documents: list[dict] | None = None, request: str | None = None) -> str:
    """Create a fresh case file and make it the active run."""
    run_id = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(2)
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True)
    case = new_case(run_id, scenario, client_documents or [], request)
    (run_dir / 'case.json').write_text(json.dumps(case, indent=2))
    (RUNS / 'active.json').write_text(json.dumps({'run_id': run_id, 'scenario': scenario}))
    return run_id


def active_run_dir() -> Path:
    marker = RUNS / 'active.json'
    if not marker.exists():
        raise RuntimeError('No active run. Start one with: python -m team.run_scenario <scenario>')
    return RUNS / json.loads(marker.read_text())['run_id']


@contextmanager
def open_case():
    """Load the active case under a lock and save it back when the block exits cleanly."""
    with _lock:
        path = active_run_dir() / 'case.json'
        case = json.loads(path.read_text())
        yield case
        path.write_text(json.dumps(case, indent=2))


def read_case() -> dict:
    with _lock:
        return json.loads((active_run_dir() / 'case.json').read_text())


def log_tool_call(entry: dict) -> None:
    """Append one tool call to the active run's tool log; tools still work without a run."""
    try:
        run_dir = active_run_dir()
    except RuntimeError:
        return
    with _lock, (run_dir / 'tool_log.jsonl').open('a') as log:
        log.write(json.dumps(entry) + '\n')


def add_source(case: dict, title: str, source_type: str, location: str, date: str, confidence: str, claims: str,
               registered_by: str | None = None, via: str = 'register_source') -> str:
    """Register a source and return its ID; re-registering the same location reuses the ID. registered_by is the
    agent whose call registered it, and via the tool, since data tools register what they retrieve."""
    for source in case['sources']:
        if source['location'] == location and location:
            return source['id']
    source_id = f"S{len(case['sources']) + 1}"
    case['sources'].append({
        'id': source_id, 'title': title, 'source_type': source_type, 'location': location,
        'date': date, 'confidence': confidence, 'claims': claims, 'registered_by': registered_by, 'via': via,
        'registered_at': now(),
    })
    return source_id


def save_part(case: dict, key: str, markdown: str, author: str | None, check: dict) -> dict:
    """Append a revision of one memo part, with its check at the time it was saved."""
    revisions = case['memo_parts'].setdefault(key, [])
    revision = {'revision': len(revisions) + 1, 'author': author, 'markdown': markdown, 'chars': len(markdown),
                'sha256': hashlib.sha256(markdown.encode()).hexdigest(), 'passed': check['passed'],
                'findings': [finding['rule'] for finding in check['findings']], 'depth': check['depth'],
                'saved_at': now()}
    revisions.append(revision)
    return revision


def current_parts(case: dict) -> dict[str, dict]:
    """The latest revision of each saved part, in memo order."""
    saved = case.get('memo_parts') or {}
    return {part.key: saved[part.key][-1] for part in memo.PARTS if saved.get(part.key)}


def version_parts(case: dict, version: dict) -> dict[str, str]:
    """The text of each part as a version snapshotted it."""
    saved = case.get('memo_parts') or {}
    return {key: saved[key][ref['revision'] - 1]['markdown'] for key, ref in version.get('parts', {}).items()}


def add_version(case: dict, rating: str, data_as_of: str, markdown: str, check: dict) -> dict:
    """Snapshot the latest revision of every part as a new memo version. A version never changes: an edit to any
    part needs a new version, and a review approves one exact version."""
    parts = {key: {'revision': r['revision'], 'sha256': r['sha256'], 'author': r['author']}
             for key, r in current_parts(case).items()}
    previous = case['memo_drafts'][-1]['parts'] if case['memo_drafts'] else {}
    version = {
        'version': len(case['memo_drafts']) + 1, 'rating': rating, 'data_as_of': data_as_of, 'parts': parts,
        'changed_parts': [key for key, ref in parts.items() if previous.get(key, {}).get('sha256') != ref['sha256']],
        'missing_parts': [part.key for part in memo.PARTS if part.key not in parts],
        'markdown': markdown, 'passed': check['passed'], 'saved_at': now(),
    }
    case['memo_drafts'].append(version)
    return version


def final_review_failed(case: dict) -> bool:
    """The last review round has ended without approval, so the memo will not be delivered (P9)."""
    reviews = case['reviews']
    return len(reviews) >= MAX_REVIEW_ROUNDS and reviews[-1]['verdict'] != 'approve'


def review_gate(case: dict, version: int) -> dict:
    """Whether the IC Reviewer reviewed this exact memo version and approved it (rule N5)."""
    reviews = [review for review in case['reviews'] if review['memo_version'] == version]
    latest = reviews[-1] if reviews else None
    return {'reviewed': latest is not None, 'approved': bool(latest and latest['verdict'] == 'approve'),
            'review_id': latest['id'] if latest else None}


def _packet_ids(case: dict, analyst: str, follow_up_for: str | None) -> list[str]:
    return [p['id'] for p in case['evidence_packets']
            if p.get('analyst') == analyst and p.get('follow_up_for') == follow_up_for]


def _revised_since(case: dict, review: dict) -> dict[str, list[str]]:
    """For each owner the review asks for revisions, the parts it named that have a revision saved since."""
    saved = case.get('memo_parts') or {}
    return {owner: [key for key in keys if any(r['saved_at'] >= review['saved_at'] for r in saved.get(key, []))]
            for owner, keys in (review.get('revision_requests') or {}).items()}


def status_summary(case: dict) -> dict:
    """What has arrived so far, without the bulky content: the case's scope, which analysts have saved evidence,
    each memo part's latest revision and check, and for the latest review, what it asks of whom and what has come in."""
    latest_version = case['memo_drafts'][-1] if case['memo_drafts'] else None
    latest_review = case['reviews'][-1] if case['reviews'] else None
    requested = (latest_review or {}).get('evidence_requests') or {}
    current = current_parts(case)
    return {
        'run_id': case['run_id'],
        'scope': case.get('scope') and {k: case['scope'][k] for k in ('company', 'ticker', 'type', 'decision')},
        'client_documents': [{'name': d['name'], 'confidentiality': d['confidentiality']}
                             for d in case['client_documents']],
        'sources_registered': len(case['sources']),
        'evidence_packets': [{'id': p['id'], 'analyst': p.get('analyst'), 'follow_up_for': p.get('follow_up_for'),
                              'topic': p['topic'], 'parts': p.get('parts') or [], 'saved_at': p['saved_at']}
                             for p in case['evidence_packets']],
        'first_round_packets': {analyst: _packet_ids(case, analyst, None) for analyst in ANALYSTS},
        'memo_parts': [{'part': key, 'owner': memo.PART_BY_KEY[key].owner, 'revision': r['revision'],
                        'author': r['author'], 'chars': r['chars'], 'check_passed': r['passed']}
                       for key, r in current.items()],
        'missing_parts': {owner: keys for owner in AGENTS.values()
                          if (keys := [p.key for p in memo.PARTS if p.owner == owner and p.key not in current])},
        'latest_version': latest_version and {'version': latest_version['version'],
                                              'rating': latest_version['rating'],
                                              'changed_parts': latest_version.get('changed_parts', []),
                                              'check_passed': latest_version.get('passed'),
                                              'saved_at': latest_version['saved_at']},
        'latest_review': latest_review and {
            'id': latest_review['id'], 'memo_version': latest_review['memo_version'],
            'round': latest_review.get('round'), 'verdict': latest_review['verdict'],
            'must_fix_count': len(latest_review['must_fix']),
            'revisions_requested': latest_review.get('revision_requests') or {},
            'revised_since': _revised_since(case, latest_review),
            'evidence_requested_from': list(requested),
            'follow_up_packets': {analyst: _packet_ids(case, analyst, latest_review['id']) for analyst in requested}},
        'review_rounds_left': max(0, MAX_REVIEW_ROUNDS - len(case['reviews'])),
        'delivered_versions': [d['memo_version'] for d in case['deliveries']],
    }
