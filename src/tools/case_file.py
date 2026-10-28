"""Per-run case file: the shared state the bots read and write through MCP tools.

One scenario runs at a time. team.run_scenario writes runs/active.json; every tool call
loads the active run's case.json, changes it and saves it back. The case file also lets
the Lead see what has actually arrived, instead of relying on memory across Rakazo runs.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import threading

from .agents import ANALYSTS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'  # Read at call time, so tests can point it at a temporary folder.
_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def new_case(run_id: str, scenario: str, client_documents: list[dict], request: str | None = None) -> dict:
    return {
        'run_id': run_id, 'scenario': scenario, 'request': request, 'started_at': now(),
        'client_documents': client_documents,
        'sources': [], 'evidence_packets': [], 'memo_drafts': [],
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


def add_source(case: dict, title: str, source_type: str, location: str,
               date: str, confidence: str, claims: str) -> str:
    """Register a source and return its ID; re-registering the same location reuses the ID."""
    for source in case['sources']:
        if source['location'] == location and location:
            return source['id']
    source_id = f"S{len(case['sources']) + 1}"
    case['sources'].append({
        'id': source_id, 'title': title, 'source_type': source_type, 'location': location,
        'date': date, 'confidence': confidence, 'claims': claims, 'registered_at': now(),
    })
    return source_id


def review_gate(case: dict, version: int) -> dict:
    """Whether the IC Reviewer reviewed this exact memo version and approved it (rule N5)."""
    reviews = [review for review in case['reviews'] if review['memo_version'] == version]
    latest = reviews[-1] if reviews else None
    return {'reviewed': latest is not None, 'approved': bool(latest and latest['verdict'] == 'approve'),
            'review_id': latest['id'] if latest else None}


def _packet_ids(case: dict, analyst: str, follow_up_for: str | None) -> list[str]:
    return [p['id'] for p in case['evidence_packets']
            if p.get('analyst') == analyst and p.get('follow_up_for') == follow_up_for]


def status_summary(case: dict) -> dict:
    """What has arrived so far, without the bulky content: which analysts have saved evidence, and for the
    latest review, which analysts it asks for more evidence and whether their follow-up packets are in."""
    latest_draft = case['memo_drafts'][-1] if case['memo_drafts'] else None
    latest_review = case['reviews'][-1] if case['reviews'] else None
    requested = (latest_review or {}).get('evidence_requests') or {}
    return {
        'run_id': case['run_id'],
        'client_documents': [{'name': d['name'], 'confidentiality': d['confidentiality']}
                             for d in case['client_documents']],
        'sources_registered': len(case['sources']),
        'evidence_packets': [{'id': p['id'], 'analyst': p.get('analyst'), 'follow_up_for': p.get('follow_up_for'),
                              'topic': p['topic'], 'source_ids': p['source_ids'], 'saved_at': p['saved_at']}
                             for p in case['evidence_packets']],
        'first_round_packets': {analyst: _packet_ids(case, analyst, None) for analyst in ANALYSTS},
        'latest_memo_draft': latest_draft and {'version': latest_draft['version'],
                                               'rating': latest_draft['rating'],
                                               'saved_at': latest_draft['saved_at']},
        'latest_review': latest_review and {
            'id': latest_review['id'], 'memo_version': latest_review['memo_version'],
            'verdict': latest_review['verdict'], 'must_fix_count': len(latest_review['must_fix']),
            'evidence_requested_from': list(requested),
            'follow_up_packets': {analyst: _packet_ids(case, analyst, latest_review['id']) for analyst in requested}},
        'reviews_so_far': len(case['reviews']),
        'delivered_versions': [d['memo_version'] for d in case['deliveries']],
    }
