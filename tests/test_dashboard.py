import json

import pytest
from starlette.testclient import TestClient

from dashboard import server
from team.rakazo_client import RakazoError
from tools import case_file

from .test_export_trace import BOTS, REQUEST, ms, run_dir  # noqa: F401  (run_dir is a fixture: a captured run)


@pytest.fixture
def runs(run_dir, monkeypatch):  # noqa: F811
    """Serve the captured run from a temporary runs/ folder, with a fresh server state."""
    monkeypatch.setattr(case_file, 'RUNS', run_dir.parent)
    monkeypatch.setattr(server, '_runner', {})
    monkeypatch.setattr(server, '_traces', {})
    return run_dir.parent


@pytest.fixture
def client():
    return TestClient(server.app, base_url='http://127.0.0.1')


def log_tools(run_dir, *calls):
    lines = [json.dumps({'ts': f'2026-10-26T10:{clock}+00:00', 'tool': tool, 'arguments': arguments, 'result': '',
                         'duration_ms': 1}) for clock, tool, arguments in calls]
    (run_dir / 'tool_log.jsonl').write_text('\n'.join(lines) + '\n')


def test_a_captured_run_shows_each_delivery_once_with_its_rule_observations(runs):
    snap = server.snapshot(runs / 'r1')
    assert [(e['kind'], e['from'], e['to']) for e in snap['conversation']] == [
        ('request', 'User', 'Lead Analyst'), ('message', 'Lead Analyst', 'Research Analyst'),
        ('reply', 'Lead Analyst', 'User'), ('message', 'Research Analyst', 'Lead Analyst'),
        ('reply', 'Lead Analyst', 'User')]
    assert snap['conversation'][0]['text'] == REQUEST
    assert [(span['bot'], span['end'] - span['start']) for span in snap['turns']] == [
        ('Lead Analyst', 24000), ('Research Analyst', 158000), ('Lead Analyst', 160000)]
    assert snap['captured'] and snap['outcome'] == 'delivered'
    assert {o['rule'] for o in snap['observations']} >= {'N1', 'N5', 'N7', 'N9'}
    assert snap['cost']['total']['model_calls'] > 0
    delivery = snap['case']['deliveries'][0]
    assert delivery['gate'] == {'reviewed': False, 'approved': False, 'review_id': None}
    assert delivery['findings'][0]['rule'] == 'N3'


def test_a_run_counts_as_finished_only_once_its_outcome_is_written(runs, client):
    # Found in a live test: the page read the run while its transcripts were still being copied,
    # and kept the cost and rule observations of the half-copied run.
    outcome = runs / 'r1' / 'outcome.json'
    outcome.unlink()
    early = server.snapshot(runs / 'r1')
    assert not early['captured'] and early['observations'] is None
    assert client.get('/api/state').json()['runs'][0]['captured'] is False
    outcome.write_text(json.dumps({'outcome': 'delivered'}))
    assert server.snapshot(runs / 'r1')['observations']


def test_each_tool_call_is_credited_to_the_bot_that_could_make_it(runs):
    log_tools(runs / 'r1',
              ('00:10', 'get_case_status', {}),                         # only the Lead has it
              ('00:30', 'list_sources', {}),                            # shared; the analyst was briefed at 00:21
              ('00:40', 'register_source', {'title': 'Strawberry robots enter the field',
                                                'source_type': 'independent media'}),
              ('03:10', 'get_evidence_packets', {}))                    # Lead or Reviewer; the Lead got the result at 03:00
    tools = server.snapshot(runs / 'r1')['tools']
    assert [(call['tool'], call['bot']) for call in tools] == [
        ('get_case_status', 'Lead Analyst'), ('list_sources', 'Research Analyst'),
        ('register_source', 'Research Analyst'), ('get_evidence_packets', 'Lead Analyst')]
    assert tools[2]['summary'] == 'Strawberry robots enter the field (independent media)'


class FakeRakazo:
    def __init__(self, threads, statuses, usage, fail=False):
        self.threads, self.statuses, self.records, self.fail = threads, statuses, usage, fail

    def bots(self):
        if self.fail:
            raise RakazoError('Not signed in to Rakazo. Run: .venv/bin/python -m team.login')
        return {name: {'id': bot_id} for name, bot_id in {**BOTS, 'Someone else': 'bot-other'}.items()}

    def messages(self, bot_id):
        return self.threads.get(bot_id, [])

    def runs_in_flight(self, bot_id):
        return [{'status': status} for status in self.statuses.get(bot_id, [])]

    def usage(self):
        return self.records


def live_run(runs):
    """A run still going: its case file exists, but nothing has been captured yet."""
    run = runs / 'r2'
    run.mkdir()
    case = case_file.new_case('r2', 'rushed-call', [])
    case['started_at'] = '2026-10-26T11:00:00+00:00'
    (run / 'case.json').write_text(json.dumps(case))
    return run


def test_a_live_run_reads_the_conversation_status_and_cost_from_rakazo(runs):
    request = {'id': 'm1', 'role': 'user', 'runId': 'run-1', 'createdAt': '2026-10-26T11:00:01Z',
               'blocks': [{'kind': 'text', 'text': 'Buy or Sell on TSLA?'}]}
    rakazo = FakeRakazo(
        threads={'bot-lead': [request]},
        statuses={'bot-lead': ['running'], 'bot-res': ['waiting_input']},
        usage=[{'createdAt': '2026-10-26T11:00:05Z', 'botId': 'bot-lead', 'costUsd': 0.02},
               {'createdAt': '2026-10-26T10:59:00Z', 'botId': 'bot-lead', 'costUsd': 5},     # an earlier run
               {'createdAt': '2026-10-26T11:00:06Z', 'botId': 'bot-other', 'costUsd': 5}])  # not on this team
    snap = server.snapshot(live_run(runs), rakazo)
    assert not snap['captured'] and snap['live_error'] is None
    assert snap['status'] == {'Lead Analyst': 'working', 'Research Analyst': 'waiting', 'IC Reviewer': 'idle'}
    assert [(e['kind'], e['text']) for e in snap['conversation']] == [('request', 'Buy or Sell on TSLA?')]
    assert snap['usage'] == [{'ts': ms('2026-10-26T11:00:05+00:00'), 'bot': 'Lead Analyst', 'cost': 0.02}]
    assert snap['request'].startswith('Our investment committee meets in an hour.')


def test_a_live_run_says_when_rakazo_cannot_be_read(runs):
    snap = server.snapshot(live_run(runs), FakeRakazo({}, {}, [], fail=True))
    assert 'Not signed in to Rakazo' in snap['live_error']
    assert snap['conversation'] == [] and snap['status'] == {}


def test_the_page_lists_runs_and_scenarios(runs, client):
    assert 'Investment research team' in client.get('/').text
    state = client.get('/api/state').json()
    assert [(run['run_id'], run['captured']) for run in state['runs']] == [('r1', True)]
    assert 'rushed-call' in {scenario['name'] for scenario in state['scenarios']}
    assert client.get('/api/runs/r1').json()['run_id'] == 'r1'
    assert client.get('/api/runs/nope').status_code == 404


def test_only_this_machine_can_reach_the_server(runs):
    assert TestClient(server.app, base_url='http://evil.example').get('/api/state').status_code == 400


def test_a_run_starts_once_and_only_from_a_json_request(runs, client, monkeypatch):
    started = []

    class FakeProcess:
        def __init__(self, command, **options):
            started.append(command)

        def poll(self):
            return None  # still running

    monkeypatch.setattr(server.subprocess, 'Popen', FakeProcess)
    assert client.post('/api/start', content='{"scenario": "rushed-call"}',
                       headers={'content-type': 'text/plain'}).status_code == 415
    assert client.post('/api/start', json={'scenario': 'no-such-scenario'}).status_code == 400
    assert client.post('/api/start', json={'scenario': 'rushed-call'}).json() == {'started': 'rushed-call'}
    assert client.post('/api/start', json={'scenario': 'public-equity-memo'}).status_code == 409
    assert len(started) == 1 and started[0][-2:] == ['team.run_scenario', 'rushed-call']
    assert client.get('/api/state').json()['runner']['alive'] is True
