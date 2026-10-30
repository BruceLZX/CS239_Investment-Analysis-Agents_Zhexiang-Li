"""A local web page for demos: start a scenario or type a request of your own and watch the team work,
ask follow-up questions once it has finished, or replay a captured run.

From src/ (a live run also needs Rakazo and the MCP server; a replay needs neither):

    .venv/bin/python -m dashboard.server

Then open http://127.0.0.1:8770.
"""
import argparse
from datetime import datetime
from functools import cache
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import httpx
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route
import uvicorn
import yaml

from team.export_trace import api_events, build_trace
from team.model_costs import call_cost
from team.profiles import LEAD, team_profiles
from team.rakazo_client import WAITING_STATUSES, Rakazo, RakazoError
from team.run_scenario import CUSTOM, SCENARIOS
from tools import case_file, sections
from tools.env import load_env

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name('index.html')
RUN_ID_RE = re.compile(r'^[\w-]+$')
_runner: dict = {}  # The scenario run started from the page: its process, scenario and log file.
_traces: dict = {}  # Rule observations, cost and trace timeline of captured runs, keyed by run id.


def _ms(iso: str | None) -> int | None:
    return int(datetime.fromisoformat(iso.replace('Z', '+00:00')).timestamp() * 1000) if iso else None


def _read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _finished(run_dir: Path) -> bool:
    # team.run_scenario writes outcome.json last, after copying the conversation and transcripts out of Rakazo.
    return (run_dir / 'outcome.json').exists() and (run_dir / 'rakazo' / 'messages.json').exists()


@cache
def tool_owners() -> dict[str, tuple[str, ...]]:
    """Which bots may call each MCP tool, from the team's allowlists."""
    owners = {}
    for profile in team_profiles():
        for tool in profile.mcp_tools:
            owners[tool] = owners.get(tool, ()) + (profile.name,)
    return owners


def conversation(messages: dict[str, list[dict]]) -> list[dict]:
    """One entry per delivery: the user's request and any follow-up questions, each message between bots,
    the Lead's replies and Rakazo's approval cards. A message is shown once, from the thread of the bot that
    received it."""
    entries = []
    for event in sorted(api_events(messages), key=lambda e: e['ts_ms']):
        base = {'ts': int(event['ts_ms']), 'id': event['message_id'], 'text': event.get('text', '')}
        if event['type'] == 'user_message':
            asked = any(entry['kind'] == 'request' for entry in entries)
            entries.append({**base, 'kind': 'request', 'from': 'User', 'to': event['agent'],
                            'intent': 'follow-up' if asked else 'request'})
        elif event['type'] == 'peer_message_received':
            entries.append({**base, 'kind': 'message', 'from': event['from'], 'to': event['agent'],
                            'intent': event.get('intent') or 'message'})
        elif event['type'] == 'reply' and event['agent'] == LEAD:
            if entries and entries[-1]['kind'] == 'reply' and entries[-1]['id'] == base['id']:
                entries[-1]['text'] += event['text']  # One message with several text blocks.
            else:
                entries.append({**base, 'kind': 'reply', 'from': LEAD, 'to': 'User'})
        elif event['type'] == 'platform_guard':
            entries.append({**base, 'kind': 'guard', 'from': event['agent'], 'to': None,
                            'detail': event.get('detail'), 'status': event.get('status')})
    return entries


def turns(messages: dict[str, list[dict]]) -> list[dict]:
    """When each bot was working: one span per Rakazo run, from its first message to its last."""
    spans = {}
    for event in api_events(messages):
        ts = int(event['ts_ms'])
        span = spans.setdefault((event['agent'], event.get('rakazo_run_id')),
                                {'bot': event['agent'], 'start': ts, 'end': ts})
        span['start'], span['end'] = min(span['start'], ts), max(span['end'], ts)
    return sorted(spans.values(), key=lambda span: span['start'])


# The trace timeline: what each agent thought, did (tool calls), observed (tool results and Rakazo's guard) and
# said, in time order. A message between bots is taken from its receiving end, which every delivery has: a reply
# that Rakazo returns to the Lead has no sending end. A turn's prompt repeats a message, and an analyst's or the
# reviewer's own text is narration or that reply.
TRACE_KINDS = {'thought': 'thought', 'tool_call': 'action', 'tool_result': 'observation',
               'platform_guard': 'observation', 'user_message': 'message', 'peer_message_received': 'message'}
# Thoughts and messages are shown whole. A tool call or result can hold a whole memo or filing, so it is cut.
TRACE_TEXT = 4_000


def _result_text(text: str) -> str:
    """An MCP tool result's text, taken out of its content envelope."""
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        return text
    if isinstance(body, dict) and isinstance(body.get('content'), list):
        return '\n'.join(str(item.get('text', '')) for item in body['content'] if isinstance(item, dict))
    return text


def timeline(events: list[dict]) -> list[dict]:
    items = []
    for event in sorted(events, key=lambda e: (_ms(e['ts']), e.get('seq', 0))):
        lead_text = event['type'] == 'assistant_text' and event['agent'] == LEAD  # what the user reads
        kind = 'message' if lead_text else TRACE_KINDS.get(event['type'])
        if not kind:
            continue
        item = {'ts': _ms(event['ts']), 'kind': kind, 'agent': event['agent'], 'label': kind}
        text = event.get('text', '')
        if event['type'] == 'tool_call':
            item['label'] = event.get('tool', '')
            text = json.dumps(event.get('arguments') or {}, ensure_ascii=False)
        elif event['type'] == 'tool_result':
            item.update(label=event.get('tool', ''), error=bool(event.get('is_error')))
            text = _result_text(text)
        elif event['type'] == 'platform_guard':
            item.update(label='platform guard', error=True)
            text = f"{text}. {event.get('detail') or ''}".strip()
        elif event['type'] == 'user_message':
            item.update(agent='User', to=event['agent'])
        elif event['type'] == 'peer_message_received':
            item.update(agent=event.get('from') or 'User', to=event['agent'])
        elif lead_text:
            item['to'] = 'User'
        if kind in ('action', 'observation') and len(text) > TRACE_TEXT:
            text = text[:TRACE_TEXT] + f'… ({len(text) - TRACE_TEXT:,} more characters in the trace)'
        items.append({**item, 'text': text})
    return items


def _summary(tool: str, arguments: dict) -> str:
    if tool == 'register_source':
        return f"{arguments.get('title', '')} ({arguments.get('source_type', '')})"
    if tool in ('start_review', 'finish_review'):
        return f"v{arguments.get('memo_version')}" if 'memo_version' in arguments else str(arguments.get('verdict', ''))
    if tool == 'save_review_pass':
        return f"pass {arguments.get('pass_number')}: {len(arguments.get('items') or [])} items"
    if tool in ('save_memo_part', 'save_evidence_block'):
        size = f" ({len(arguments.get('markdown') or ''):,} characters)" if tool == 'save_memo_part' else ''
        return f"{arguments.get('section', '')}{size}"
    if tool == 'read_playbook':
        return ' > '.join(filter(None, (arguments.get('name', ''), arguments.get('heading', ''))))
    if tool == 'get_memo_parts':
        wanted = ', '.join(arguments.get('sections_wanted') or []) or 'list of sections'
        return wanted + (f" in v{arguments['version']}" if arguments.get('version') else '')
    if tool == 'read_sec_filing':
        searched = f" · {', '.join(arguments['keywords'])}" if arguments.get('keywords') else ''
        return f"{arguments.get('ticker', '')} {arguments.get('form', '10-K')} item {arguments.get('item') or 'any'}{searched}"
    if tool == 'get_valuation_snapshot':
        peers = ', '.join(arguments.get('peers') or [])
        return arguments.get('ticker', '') + (f' vs {peers}' if peers else '')
    if tool in ('search_public_records', 'search_literature'):
        return f"{arguments.get('source', '')}: {arguments.get('query', '')}"
    if tool == 'get_memo_check' and arguments.get('section'):
        return arguments['section'] + (f" in v{arguments['version']}" if arguments.get('version') else '')
    if arguments.get('version'):
        return f"v{arguments['version']}"
    return next((str(arguments[key]) for key in ('ticker', 'section', 'company', 'name', 'rating', 'kind', 'database')
                 if arguments.get(key)), '')


def tool_calls(run_dir: Path, entries: list[dict]) -> list[dict]:
    """The MCP server's log for this run, each call credited to the bot that made it. The server logs the
    caller; for older logs without one, a tool only one bot may call goes to that bot, and a shared one to the
    allowed bot that was most recently given work."""
    path = run_dir / 'tool_log.jsonl'
    if not path.exists():
        return []
    woken = [(entry['ts'], entry['to']) for entry in entries if entry['kind'] in ('request', 'message')]
    calls = []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        arguments = record.get('arguments') or {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        ts = _ms(record['ts'])
        allowed = tool_owners().get(record['tool'], ())
        # The log keeps whole seconds, so a call can look up to a second older than the message that started it.
        bot = record.get('agent') or (allowed[0] if len(allowed) == 1 else next(
            (name for when, name in reversed(woken) if when <= ts + 999 and name in allowed), None))
        calls.append({'ts': ts, 'tool': record['tool'], 'bot': bot, 'summary': _summary(record['tool'], arguments)})
    return calls


def _version_report(version: dict) -> str:
    path = Path((version.get('files') or {}).get('markdown') or '')
    return path.read_text() if path.is_file() else version.get('markdown', '')


def case_view(case: dict, started: int) -> dict:
    """The case file with a timestamp on every item, so a replay can show each one when it arrived."""
    when = lambda item, key: _ms(item.get(key)) or started
    workflow = case.get('workflow') or {}
    return {
        'documents': [{'name': d['name'], 'confidentiality': d['confidentiality']} for d in case['client_documents']],
        'sources': [{'id': s['id'], 'title': s.get('title'), 'type': s.get('source_type'),
                     'location': s.get('location'), 'ts': when(s, 'registered_at')} for s in case['sources']],
        'workflow': [{'kind': kind, 'author': record.get('author'), 'ts': when(record, 'saved_at')}
                     for kind, record in workflow.items() if isinstance(record, dict) and record.get('saved_at')],
        'evidence': [{'section': key, 'author': b.get('author'), 'queries': len(b.get('queries') or []),
                      'rows': len(b.get('rows') or []), 'passed': b.get('gate_passed'), 'ts': when(b, 'saved_at')}
                     for key, blocks in (case.get('evidence') or {}).items() for b in blocks],
        'requests': [{'id': r['id'], 'section': r['section'], 'database': r['database'], 'query': r['query'],
                      'by': r.get('requested_by'), 'ts': when(r, 'requested_at')}
                     for r in case.get('user_data_requests') or []],
        'part_list': [{'key': s.key, 'number': s.number, 'heading': s.title, 'owner': s.owner}
                      for s in sections.ALL_SECTIONS],
        'parts': [{'part': key, 'revision': r['revision'], 'author': r.get('author'), 'chars': r.get('chars'),
                   'passed': r.get('passed'), 'problems': len(r.get('depth') or []) + len(r.get('findings') or []),
                   'evidence_first': r.get('evidence_before_draft'), 'ts': when(r, 'saved_at')}
                  for key, revisions in (case.get('memo_parts') or {}).items() for r in revisions],
        'drafts': [{'version': d['version'], 'rating': d.get('rating'), 'markdown': _version_report(d),
                    'composite': d.get('composite_score'), 'changed_parts': d.get('changed_parts'),
                    'passed': d.get('passed'), 'report': bool((d.get('files') or {}).get('html')),
                    'pdf': bool((d.get('files') or {}).get('pdf')), 'ts': when(d, 'saved_at')}
                   for d in case['memo_drafts']],
        'reviews': [{'id': r['id'], 'version': r.get('memo_version'), 'round': r.get('round'),
                     'verdict': r.get('verdict'), 'grade': r.get('grade'),
                     'items': [{k: i.get(k) for k in ('severity', 'pass', 'sections', 'owners', 'issue')}
                               for i in r.get('items') or []],
                     'owners': r.get('revision_requests') or {}, 'requests': r.get('evidence_requests') or {},
                     'ts': when(r, 'finished_at') if r.get('finished_at') else when(r, 'started_at')}
                    for r in case['reviews']],
        'deliveries': [{'version': d['memo_version'], 'gate': d.get('review_gate') or {},
                        'findings': (d.get('memo_check') or {}).get('findings', []),
                        'final_passed': (d.get('final_check') or {}).get('passed'),
                        'folder': Path(d.get('folder') or '').name, 'ts': when(d, 'delivered_at')}
                       for d in case['deliveries']],
    }


def record_cost(record: dict) -> float:
    """One usage record's cost at DeepSeek's rate for its hour, or Rakazo's estimate for an unpriced model."""
    cost = call_cost(record.get('model'), record.get('cacheReadTokens') or 0, record.get('inputTokens') or 0,
                     record.get('outputTokens') or 0, _ms(record['createdAt']))
    return float(record.get('costUsd') or 0) if cost is None else cost


def usage_points(records: list[dict], bot_ids: dict[str, str], started: int) -> list[dict]:
    """Model-call costs of this run's bots since the run started, oldest first."""
    names = {bot_id: name for name, bot_id in bot_ids.items()}
    points = [{'ts': _ms(r['createdAt']), 'bot': names[r['botId']], 'cost': record_cost(r)}
              for r in records if r.get('botId') in names and _ms(r['createdAt']) >= started]
    return sorted(points, key=lambda point: point['ts'])


def _status(runs: list[dict]) -> str:
    if any(run['status'] in WAITING_STATUSES for run in runs):
        return 'waiting'
    return 'working' if runs else 'idle'


def snapshot(run_dir: Path, rakazo: Rakazo | None = None) -> dict:
    """Everything the page shows for one run. A captured run is read from disk; for a run still going,
    pass a Rakazo client and the conversation, bot status and cost come from Rakazo."""
    case = json.loads((run_dir / 'case.json').read_text())
    started = _ms(case['started_at'])
    captured = _read_json(run_dir / 'rakazo' / 'messages.json') if _finished(run_dir) else None
    bot_ids, messages, records, status, live_error = {}, {}, [], {}, None
    if captured:
        bot_ids, messages = captured['bots'], captured['messages']
        records = _read_json(run_dir / 'rakazo' / 'usage.json') or []
    elif rakazo is not None:
        try:
            team = {profile.name for profile in team_profiles()}
            bot_ids = {name: bot['id'] for name, bot in rakazo.bots().items() if name in team}
            messages = {name: rakazo.messages(bot_id) for name, bot_id in bot_ids.items()}
            status = {name: _status(rakazo.runs_in_flight(bot_id)) for name, bot_id in bot_ids.items()}
            records = rakazo.usage()
        except (RakazoError, httpx.HTTPError) as exc:
            live_error = f"Can't read the run from Rakazo: {exc}"
    try:
        scenario = yaml.safe_load((SCENARIOS / f"{case['scenario']}.yaml").read_text())
    except FileNotFoundError:
        scenario = {}
    entries = conversation(messages)
    view = {
        'run_id': case['run_id'], 'scenario': case['scenario'],
        'request': (case.get('request') or scenario.get('request') or '').strip(),
        'started': started, 'captured': bool(captured),
        'outcome': (_read_json(run_dir / 'outcome.json') or {}).get('outcome'),
        'status': status, 'live_error': live_error,
        'conversation': entries, 'turns': turns(messages), 'tools': tool_calls(run_dir, entries),
        'case': case_view(case, started), 'usage': usage_points(records, bot_ids, started),
        'observations': None, 'cost': None, 'timeline': None,
    }
    if captured:
        key = (run_dir / 'outcome.json').stat().st_mtime
        if _traces.get(case['run_id'], {}).get('key') != key:
            trace = build_trace(run_dir)
            _traces[case['run_id']] = {'key': key, 'observations': trace['observations'], 'cost': trace['usage'],
                                       'timeline': timeline(trace['events'])}
        for name in ('observations', 'cost', 'timeline'):
            view[name] = _traces[case['run_id']][name]
    return view


def _active_run_id() -> str | None:
    marker = case_file.RUNS / 'active.json'
    return json.loads(marker.read_text())['run_id'] if marker.exists() else None


def _runner_state() -> dict | None:
    if not _runner:
        return None
    exit_code = _runner['process'].poll()
    return {'scenario': _runner['scenario'], 'alive': exit_code is None, 'exit_code': exit_code,
            'log_tail': _runner['log'].read_text()[-1500:] if _runner['log'].exists() else ''}


def page(request):
    return FileResponse(PAGE)


def version_report(request):
    """A saved version's HTML report or PDF, as the server rendered it."""
    run_id, version, kind = (request.path_params['run_id'], request.path_params['version'],
                             request.path_params['kind'])
    path = case_file.RUNS / run_id / 'versions' / f'v{version}' / f'report.{kind}'
    if not RUN_ID_RE.match(run_id) or kind not in ('html', 'pdf') or not path.is_file():
        return JSONResponse({'error': f'No {kind} report for version {version} of run {run_id}.'}, status_code=404)
    return FileResponse(path)


def state(request):
    runs = []
    for path in sorted(case_file.RUNS.glob('*/case.json'), reverse=True):
        case = json.loads(path.read_text())
        runs.append({'run_id': case['run_id'], 'scenario': case['scenario'], 'started': _ms(case['started_at']),
                     'captured': _finished(path.parent),
                     'outcome': (_read_json(path.parent / 'outcome.json') or {}).get('outcome')})
    scenarios = [{'name': path.stem, 'summary': yaml.safe_load(path.read_text()).get('summary', '')}
                 for path in sorted(SCENARIOS.glob('*.yaml'))]
    return JSONResponse({'active_run': _active_run_id(), 'runner': _runner_state(), 'runs': runs,
                         'scenarios': scenarios})


def run(request):
    run_id = request.path_params['run_id']
    run_dir = case_file.RUNS / run_id
    if not RUN_ID_RE.match(run_id) or not (run_dir / 'case.json').exists():
        return JSONResponse({'error': f'No run {run_id}.'}, status_code=404)
    if run_id != _active_run_id() or _finished(run_dir):
        return JSONResponse(snapshot(run_dir))
    with Rakazo(os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')) as rakazo:
        return JSONResponse(snapshot(run_dir, rakazo))


MAX_MESSAGE = 4000  # Characters in a request or follow-up typed on the page.


async def _json_body(request) -> dict | None:
    # A JSON body makes browsers ask before sending it from another site, so no other page can start a paid run.
    if not request.headers.get('content-type', '').startswith('application/json'):
        return None
    try:
        body = await request.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _busy() -> JSONResponse | None:
    if _runner and _runner['process'].poll() is None:
        return JSONResponse({'error': f"The {_runner['scenario']} run started from this page is still going."},
                            status_code=409)
    return None


def _message(body: dict, key: str) -> str | None:
    text = str(body.get(key) or '').strip()
    return text if 0 < len(text) <= MAX_MESSAGE else None


def _launch(arguments: list[str], label: str) -> None:
    """Start team.run_scenario in the background; the page follows the run through /api/state."""
    log = case_file.RUNS / 'dashboard-runner.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as output:
        process = subprocess.Popen([sys.executable, '-m', 'team.run_scenario', *arguments], cwd=ROOT,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    _runner.update(process=process, scenario=label, log=log)


async def start(request):
    """Start a scenario ({"scenario": name}), or a request typed on the page ({"request": text})."""
    body = await _json_body(request)
    if body is None:
        return JSONResponse({'error': 'Send a JSON object.'}, status_code=415)
    if 'request' in body:
        text = _message(body, 'request')
        if text is None:
            return JSONResponse({'error': f'Write a request of 1 to {MAX_MESSAGE:,} characters.'}, status_code=400)
        arguments, label = ['--request', text], CUSTOM
    else:
        scenario = body.get('scenario')
        if scenario not in {path.stem for path in SCENARIOS.glob('*.yaml')}:
            return JSONResponse({'error': f'No scenario {scenario!r}.'}, status_code=400)
        arguments, label = [scenario], scenario
    if busy := _busy():
        return busy
    _launch(arguments, label)
    return JSONResponse({'started': label})


async def follow_up(request):
    """Ask the Lead Analyst a follow-up question ({"text": question}) about the latest run, once it has finished."""
    body = await _json_body(request)
    if body is None:
        return JSONResponse({'error': 'Send a JSON object.'}, status_code=415)
    text = _message(body, 'text')
    if text is None:
        return JSONResponse({'error': f'Write a question of 1 to {MAX_MESSAGE:,} characters.'}, status_code=400)
    if busy := _busy():
        return busy
    run_id = _active_run_id()
    if not run_id or not _finished(case_file.RUNS / run_id):
        return JSONResponse({'error': 'Ask a follow-up once the latest run has finished.'}, status_code=409)
    _launch(['--follow-up', text], 'follow-up')
    return JSONResponse({'started': 'follow-up', 'run_id': run_id})


app = Starlette(
    routes=[Route('/', page), Route('/api/state', state), Route('/api/runs/{run_id}', run),
            Route('/api/runs/{run_id}/report/v{version:int}.{kind}', version_report),
            Route('/api/start', start, methods=['POST']), Route('/api/follow-up', follow_up, methods=['POST'])],
    # Only this machine's own addresses, so a web page can't reach the server through DNS rebinding.
    middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=8770)
    args = parser.parse_args()
    load_env()
    print(f'Dashboard: http://127.0.0.1:{args.port}', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
