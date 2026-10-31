"""Per-run case file: the shared state the bots read and write through MCP tools.

One scenario runs at a time. team.run_scenario writes runs/active.json; every tool call
loads the active run's case.json, changes it and saves it back. The case file also lets
the Lead see what has actually arrived, instead of relying on memory across Rakazo runs.
It holds the workflow records too (research plan, evidence matrix, thesis table, scenario
analysis, red-team and investor reviews), which the playbooks call _work/ files.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import threading

from . import sections
from .agents import ANALYSTS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'  # Read at call time, so tests can point it at a temporary folder.
# Review rounds per report: the owners revise after the first and second; the third is final.
MAX_REVIEW_ROUNDS = 3
_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def new_case(run_id: str, scenario: str, client_documents: list[dict], request: str | None = None) -> dict:
    return {
        'run_id': run_id, 'scenario': scenario, 'request': request, 'started_at': now(), 'scope': None,
        'client_documents': client_documents,
        # memo_parts holds each section's revisions; memo_drafts holds the versions, snapshots of the sections.
        'sources': [], 'evidence': {}, 'workflow': {}, 'user_data_requests': [], 'notes': [], 'memo_parts': {},
        'memo_drafts': [], 'reviews': [], 'deliveries': [],
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


def open_notes(case: dict) -> list[dict]:
    """Notes between section owners that their owners have not answered yet."""
    return [note for note in case.get('notes') or [] if not note.get('answers') and not note.get('answered_at')]


def is_listed(case: dict) -> bool:
    return (case.get('scope') or {}).get('type') != 'private'


def add_source(case: dict, title: str, source_type: str, location: str, date: str, confidence: str, claims: str,
               registered_by: str | None = None, via: str = 'register_source', claims_weakened: str = '') -> str:
    """Register a source and return its ID; re-registering the same location reuses the ID. registered_by is the
    agent whose call registered it, and via the tool, since data tools register what they retrieve."""
    for source in case['sources']:
        if source['location'] == location and location:
            return source['id']
    source_id = f"S{len(case['sources']) + 1}"
    case['sources'].append({
        'id': source_id, 'title': title, 'source_type': source_type, 'location': location,
        'date': date, 'confidence': confidence, 'claims': claims, 'claims_weakened': claims_weakened,
        'registered_by': registered_by, 'via': via, 'registered_at': now(),
    })
    return source_id


def save_part(case: dict, key: str, markdown: str, author: str | None, check: dict) -> dict:
    """Append a revision of one section, with its check at the time it was saved."""
    revisions = case['memo_parts'].setdefault(key, [])
    revision = {'revision': len(revisions) + 1, 'author': author, 'markdown': markdown, 'chars': len(markdown),
                'sha256': hashlib.sha256(markdown.encode()).hexdigest(), 'passed': check['passed'],
                'findings': [finding['rule'] for finding in check['findings']], 'depth': check['depth'],
                'saved_at': now()}
    revisions.append(revision)
    return revision


def current_parts(case: dict) -> dict[str, dict]:
    """The latest revision of each saved section, in report order."""
    saved = case.get('memo_parts') or {}
    return {s.key: saved[s.key][-1] for s in sections.ALL_SECTIONS if saved.get(s.key)}


def version_parts(case: dict, version: dict) -> dict[str, str]:
    """The text of each section as a version snapshotted it."""
    saved = case.get('memo_parts') or {}
    return {key: saved[key][ref['revision'] - 1]['markdown'] for key, ref in version.get('parts', {}).items()}


def add_version(case: dict, rating: str, data_as_of: str, cover: dict, composite_score: str, files: dict,
                check: dict) -> dict:
    """Snapshot the latest revision of every section as a new version. A version never changes: an edit to any
    section needs a new version, and a review approves one exact version."""
    parts = {key: {'revision': r['revision'], 'sha256': r['sha256'], 'author': r['author']}
             for key, r in current_parts(case).items()}
    previous = case['memo_drafts'][-1]['parts'] if case['memo_drafts'] else {}
    version = {
        'version': len(case['memo_drafts']) + 1, 'rating': rating, 'data_as_of': data_as_of, 'cover': cover,
        'composite_score': composite_score, 'parts': parts,
        'changed_parts': [key for key, ref in parts.items() if previous.get(key, {}).get('sha256') != ref['sha256']],
        'missing_parts': [s.key for s in sections.ALL_SECTIONS if s.key not in parts],
        'files': files, 'check': check, 'passed': check.get('passed', False), 'saved_at': now(),
    }
    case['memo_drafts'].append(version)
    return version


def finished_reviews(case: dict) -> list[dict]:
    return [review for review in case['reviews'] if review.get('verdict')]


def final_review_failed(case: dict) -> bool:
    """The last review round has ended without approval, so the report will not be delivered (P9)."""
    reviews = finished_reviews(case)
    return len(reviews) >= MAX_REVIEW_ROUNDS and reviews[-1]['verdict'] != 'approve'


def review_gate(case: dict, version: int) -> dict:
    """Whether the IC Reviewer reviewed this exact version and approved it (rule N5)."""
    reviews = [review for review in finished_reviews(case) if review['memo_version'] == version]
    latest = reviews[-1] if reviews else None
    return {'reviewed': latest is not None, 'approved': bool(latest and latest['verdict'] == 'approve'),
            'review_id': latest['id'] if latest else None}


def _revised_since(case: dict, review: dict) -> dict[str, list[str]]:
    """For each owner the review asks for revisions, the sections it named that have a revision saved since."""
    saved = case.get('memo_parts') or {}
    finished = review.get('finished_at') or review.get('saved_at') or ''
    return {owner: [key for key in keys if any(r['saved_at'] >= finished for r in saved.get(key, []))]
            for owner, keys in (review.get('revision_requests') or {}).items()}


def evidence_status(case: dict) -> dict[str, dict]:
    """Each section's latest evidence block: who saved it, how many queries and rows, whether its gate passed."""
    status = {}
    for key, blocks in (case.get('evidence') or {}).items():
        block = blocks[-1]
        status[key] = {'author': block.get('author'), 'queries': len(block.get('queries') or []),
                       'rows': len(block.get('rows') or []), 'gate_passed': block.get('gate_passed'),
                       'saved_at': block.get('saved_at')}
    return status


def status_summary(case: dict) -> dict:
    """What has arrived so far, without the bulky content: the scope, the workflow records, each analyst's
    sections and evidence, each section's latest revision and check, the latest version and review, and what the
    review is still waiting for."""
    latest_version = case['memo_drafts'][-1] if case['memo_drafts'] else None
    latest_review = case['reviews'][-1] if case['reviews'] else None
    current = current_parts(case)
    workflow = case.get('workflow') or {}
    evidence = evidence_status(case)
    analysts = {}
    for analyst in ANALYSTS:
        keys = sections.OWNED.get(analyst, ())
        analysts[analyst] = {'sections_saved': [k for k in keys if k in current],
                             'sections_missing': [k for k in keys if k not in current],
                             'evidence_blocks': [k for k in keys if k in evidence]}
    open_rewrites = [item for item in workflow.get('rewrite_plan') or [] if not item.get('resolved')]
    return {
        'run_id': case['run_id'],
        'scope': case.get('scope') and {k: case['scope'].get(k) for k in ('company', 'ticker', 'type', 'decision')},
        'client_documents': [{'name': d['name'], 'confidentiality': d['confidentiality']}
                             for d in case['client_documents']],
        'sources_registered': len(case['sources']),
        'workflow': {name: bool(workflow.get(name)) for name in ('research_plan', 'profile_requirements',
                                                                 'thesis_table', 'scenario_analysis',
                                                                 'red_team_review')},
        'analysts': analysts,
        'sections': [{'section': key, 'owner': sections.BY_KEY[key].owner, 'revision': r['revision'],
                      'author': r['author'], 'chars': r['chars'], 'check_passed': r['passed']}
                     for key, r in current.items()],
        'missing_sections': {owner: keys for owner, keys in ((o, [k for k in ks if k not in current])
                                                              for o, ks in sections.OWNED.items()) if keys},
        'open_rewrite_items': {owner: [i['section'] or 'report' for i in open_rewrites if i['owner'] == owner]
                               for owner in dict.fromkeys(i['owner'] for i in open_rewrites)},
        'user_data_requests': len(case.get('user_data_requests') or []),
        'open_notes': [{'id': note['id'], 'from': note['from'], 'to': note['to'], 'section': note['section'],
                        'note': note['note'], 'seen': bool(note.get('seen_at'))} for note in open_notes(case)],
        'latest_version': latest_version and {'version': latest_version['version'],
                                              'rating': latest_version['rating'],
                                              'changed_parts': latest_version.get('changed_parts', []),
                                              'missing_parts': latest_version.get('missing_parts', []),
                                              'check_passed': latest_version.get('passed'),
                                              'saved_at': latest_version['saved_at']},
        'latest_review': latest_review and {
            'id': latest_review['id'], 'memo_version': latest_review['memo_version'],
            'round': latest_review.get('round'), 'verdict': latest_review.get('verdict'),
            'finished': bool(latest_review.get('verdict')),
            'items': {severity: sum(i['severity'] == severity for i in latest_review.get('items') or [])
                      for severity in ('Critical', 'Important', 'Minor')},
            'revisions_requested': latest_review.get('revision_requests') or {},
            'revised_since': _revised_since(case, latest_review)},
        'review_rounds_left': max(0, MAX_REVIEW_ROUNDS - len(finished_reviews(case))),
        'delivered_versions': [d['memo_version'] for d in case['deliveries']],
    }
