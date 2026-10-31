import json

import pytest
from starlette.testclient import TestClient

from dashboard import server
from team.rakazo_client import RakazoError
from tools import case_file

from .test_export_trace import BOTS, REQUEST, ms, revision, run_dir  # noqa: F401  (run_dir is a fixture: a captured run)


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
        ('request', 'User', 'Lead Analyst'), ('message', 'Lead Analyst', 'Market Analyst'),
        ('reply', 'Lead Analyst', 'User'), ('message', 'Market Analyst', 'Lead Analyst'),
        ('reply', 'Lead Analyst', 'User')]
    assert snap['conversation'][0]['text'] == REQUEST
    assert [(span['bot'], span['end'] - span['start']) for span in snap['turns']] == [
        ('Lead Analyst', 24000), ('Market Analyst', 158000), ('Lead Analyst', 160000)]
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
    assert not early['captured'] and early['observations'] is None and early['timeline'] is None
    assert client.get('/api/state').json()['runs'][0]['captured'] is False
    outcome.write_text(json.dumps({'outcome': 'delivered'}))
    assert server.snapshot(runs / 'r1')['observations']


def test_the_trace_timeline_shows_thoughts_actions_observations_and_messages_in_time_order(runs):
    timeline = server.snapshot(runs / 'r1')['timeline']
    assert [item['ts'] for item in timeline] == sorted(item['ts'] for item in timeline)
    assert {item['kind'] for item in timeline} == {'thought', 'action', 'observation', 'message'}
    # The Market Analyst's reply has only a receiving end, at the Lead; the Lead's own text goes to the user.
    assert [(item['agent'], item['to']) for item in timeline if item['kind'] == 'message'] == [
        ('User', 'Lead Analyst'), ('Lead Analyst', 'Market Analyst'), ('Lead Analyst', 'User'),
        ('Market Analyst', 'Lead Analyst'), ('Lead Analyst', 'User')]
    result = next(item for item in timeline if item['kind'] == 'observation')
    assert result['label'] == 'get_case_status' and result['text'] == '{"evidence_packets": []}'


def test_thoughts_are_shown_whole_and_long_tool_results_are_cut():
    at = '2026-10-26T10:00:00+00:00'
    thought, result = server.timeline([
        {'type': 'thought', 'agent': 'IC Reviewer', 'ts': at, 'seq': 1, 'text': 'x' * 50_000},
        {'type': 'tool_result', 'agent': 'IC Reviewer', 'ts': at, 'seq': 2, 'tool': 'get_memo_draft', 'text': 'y' * 5000}])
    assert thought['text'] == 'x' * 50_000
    assert result['text'] == 'y' * 4000 + '… (1,000 more characters in the trace)'


def test_each_tool_call_is_credited_to_the_bot_that_could_make_it(runs):
    log_tools(runs / 'r1',
              ('00:10', 'get_case_status', {}),                         # only the Lead has it
              ('00:30', 'list_sources', {}),                            # shared; the analyst was briefed at 00:21
              ('00:40', 'register_source', {'title': 'Strawberry robots enter the field',
                                                'source_type': 'independent media'}),
              ('03:10', 'get_latest_review', {}))                       # Lead or Reviewer; the Lead got the result at 03:00
    tools = server.snapshot(runs / 'r1')['tools']
    assert [(call['tool'], call['bot']) for call in tools] == [
        ('get_case_status', 'Lead Analyst'), ('list_sources', 'Market Analyst'),
        ('register_source', 'Market Analyst'), ('get_latest_review', 'Lead Analyst')]
    assert tools[2]['summary'] == 'Strawberry robots enter the field (independent media)'


def test_a_call_the_server_credited_to_its_caller_keeps_that_caller(runs):
    # The analysts work at the same time, so only the server's record says which one registered a source.
    log_tools(runs / 'r1', ('00:40', 'register_source', {'title': 'Q3 deliveries', 'source_type': 'independent media'}))
    log = runs / 'r1' / 'tool_log.jsonl'
    log.write_text(log.read_text().replace('"tool"', '"agent": "Fundamentals Analyst", "tool"'))
    assert [call['bot'] for call in server.snapshot(runs / 'r1')['tools']] == ['Fundamentals Analyst']


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
    assert snap['status'] == {'Lead Analyst': 'working', 'Market Analyst': 'waiting', 'IC Reviewer': 'idle'}
    assert [(e['kind'], e['text']) for e in snap['conversation']] == [('request', 'Buy or Sell on TSLA?')]
    assert snap['usage'] == [{'ts': ms('2026-10-26T11:00:05+00:00'), 'bot': 'Lead Analyst', 'cost': 0.02}]
    assert snap['request'].startswith('Our investment committee meets in an hour.')


def test_live_costs_are_priced_for_the_hour_of_each_call():
    records = [  # 11:00 UTC on a Monday is off-peak: half of Rakazo's peak-rate estimate.
        {'createdAt': '2026-10-26T11:00:05Z', 'botId': 'bot-lead', 'model': 'deepseek-v4-pro',
         'inputTokens': 1000, 'cacheReadTokens': 0, 'outputTokens': 0, 'costUsd': 0.00132},
        {'createdAt': '2026-10-26T11:00:06Z', 'botId': 'bot-lead', 'model': 'unpriced-model', 'costUsd': 0.5}]
    points = server.usage_points(records, {'Lead Analyst': 'bot-lead'}, ms('2026-10-26T11:00:00+00:00'))
    assert [point['cost'] for point in points] == pytest.approx([0.00066, 0.5])


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


class StartedProcess:
    """Stands in for subprocess.Popen: records the command and keeps running."""
    commands = []

    def __init__(self, command, **options):
        self.commands.append(command)

    def poll(self):
        return None


@pytest.fixture
def launched(monkeypatch):
    StartedProcess.commands = []
    monkeypatch.setattr(server.subprocess, 'Popen', StartedProcess)
    return StartedProcess.commands


def test_a_request_typed_on_the_page_starts_a_run_of_its_own(runs, client, launched):
    for body in ('{', '["Memo on NVDA"]'):  # malformed, or not an object
        assert client.post('/api/start', content=body, headers={'content-type': 'application/json'}).status_code == 415
    assert client.post('/api/start', json={'request': '   '}).status_code == 400
    assert client.post('/api/start', json={'request': 'x' * 4001}).status_code == 400
    assert client.post('/api/start', json={'request': ' Prepare a memo on Nvidia (NVDA). '}).json() == {'started': 'custom'}
    assert [command[-3:] for command in launched] == [['team.run_scenario', '--request', 'Prepare a memo on Nvidia (NVDA).']]


def test_a_follow_up_goes_to_the_latest_run_once_it_has_finished(runs, client, launched):
    (runs / 'active.json').write_text(json.dumps({'run_id': 'r1', 'scenario': 'confidential-startup'}))
    assert client.post('/api/follow-up', content='{"text": "Why Wait?"}',
                       headers={'content-type': 'text/plain'}).status_code == 415
    assert client.post('/api/follow-up', json={'text': ''}).status_code == 400
    assert client.post('/api/follow-up', json={'text': 'Why Wait?'}).json() == {'started': 'follow-up', 'run_id': 'r1'}
    assert launched[0][-2:] == ['--follow-up', 'Why Wait?']
    assert client.post('/api/follow-up', json={'text': 'And the risks?'}).status_code == 409  # the first is still going


def test_a_follow_up_waits_for_the_run_to_finish(runs, client, launched):
    live_run(runs)
    (runs / 'active.json').write_text(json.dumps({'run_id': 'r2', 'scenario': 'rushed-call'}))
    assert client.post('/api/follow-up', json={'text': 'Why?'}).status_code == 409
    assert launched == []


def test_a_second_message_from_the_user_is_a_follow_up():
    user = lambda id_, run, when, text: {'id': id_, 'role': 'user', 'runId': run, 'createdAt': when,
                                         'blocks': [{'kind': 'text', 'text': text}]}
    entries = server.conversation({'Lead Analyst': [
        user('m1', 'run-1', '2026-10-26T11:00:01Z', 'A memo on Nvidia, please.'),
        {'id': 'm2', 'role': 'bot', 'runId': 'run-1', 'createdAt': '2026-10-26T11:20:00Z',
         'blocks': [{'kind': 'text', 'text': 'Delivered: Hold.'}]},
        user('m3', 'run-2', '2026-10-26T11:30:00Z', 'Why Hold?')]})
    assert [(entry['kind'], entry.get('intent')) for entry in entries] == [
        ('request', 'request'), ('reply', None), ('request', 'follow-up')]


def test_sections_evidence_and_review_items_reach_the_page(runs, client):
    case = json.loads((runs / 'r1' / 'case.json').read_text())
    case['memo_parts'] = {'competition': [{'revision': 1, 'author': 'Market Analyst', 'markdown': 'x', 'chars': 1,
                                           'sha256': 'h', 'passed': False, 'findings': ['N1'],
                                           'depth': ['too short', 'no table'], 'evidence_before_draft': True,
                                           'saved_at': '2026-10-26T10:02:00+00:00'}]}
    case['evidence'] = {'competition': [{'author': 'Market Analyst', 'queries': ['a', 'b', 'c', 'd'], 'rows': [{}] * 4,
                                         'gate_passed': True, 'saved_at': '2026-10-26T10:01:00+00:00'}]}
    case['reviews'] = [{'id': 'R1', 'memo_version': 1, 'round': 1, 'verdict': 'revise', 'grade': 'C',
                        'items': [{'severity': 'Critical', 'pass': 3, 'sections': ['competition'],
                                   'owners': ['Market Analyst'], 'issue': 'No Chinese rivals.'}],
                        'revision_requests': {'Market Analyst': ['competition']},
                        'finished_at': '2026-10-26T10:04:30+00:00'}]
    version = runs / 'r1' / 'versions' / 'v1'
    version.mkdir(parents=True)
    (version / 'report.html').write_text('<html>report</html>')
    case['memo_drafts'][0]['files'] = {'html': str(version / 'report.html')}
    (runs / 'r1' / 'case.json').write_text(json.dumps(case))
    view = server.snapshot(runs / 'r1')['case']
    assert [part['key'] for part in view['part_list']][:2] == ['executive_summary', 'company_overview']
    assert view['parts'] == [{'part': 'competition', 'revision': 1, 'author': 'Market Analyst', 'chars': 1,
                              'passed': False, 'problems': 3, 'evidence_first': True,
                              'ts': ms('2026-10-26T10:02:00+00:00')}]
    assert view['evidence'][0]['section'] == 'competition' and view['evidence'][0]['passed']
    review = view['reviews'][0]
    assert (review['round'], review['grade'], review['items'][0]['severity']) == (1, 'C', 'Critical')
    assert view['drafts'][0]['report'] is True
    assert client.get('/api/runs/r1/report/v1.html').text == '<html>report</html>'
    assert client.get('/api/runs/r1/report/v2.html').status_code == 404


def test_the_new_tools_get_short_summaries():
    assert server._summary('save_memo_part', {'section': 'financials', 'markdown': 'x' * 3200}) == \
        'financials (3,200 characters)'
    assert server._summary('get_memo_parts', {'sections_wanted': ['market', 'competition'], 'version': 2}) == \
        'market, competition in v2'
    assert server._summary('read_sec_filing', {'ticker': 'AAPL', 'form': '10-K', 'item': '1A', 'keywords': ['China']}) == \
        'AAPL 10-K item 1A · China'
    assert server._summary('save_review_pass', {'review_id': 'R1', 'pass_number': 3, 'items': [{}, {}]}) == \
        'pass 3: 2 items'
    assert server._summary('read_playbook', {'name': 'decision_framework.md', 'heading': 'The One Question'}) == \
        'decision_framework.md > The One Question'
    assert server._summary('set_case_scope', {'company': 'Apple', 'company_type': 'listed'}) == 'Apple'
    assert server._summary('search_public_records', {'source': 'openfda_device', 'query': 'Vantelle'}) == \
        'openfda_device: Vantelle'
    assert server._summary('get_trading_snapshot', {'ticker': 'AAPL', 'sector_etf': 'XLK'}) == 'AAPL'


def test_exchanges_between_agents_show_on_the_page_and_in_the_trace(runs):
    run = runs / 'r1'
    case = json.loads((run / 'case.json').read_text())
    case['sources'][1]['registered_by'] = 'Market Analyst'
    case['memo_parts'] = {'financials': [revision(1, 'Fundamentals Analyst', '2026-10-26T10:03:00+00:00')]}
    case['notes'] = [{'id': 'N1', 'from': 'Market Analyst', 'to': 'Fundamentals Analyst', 'section': 'financials',
                      'note': 'Segment revenue differs.', 'source_ids': ['S2'], 'answers': None,
                      'at': '2026-10-26T10:02:00+00:00'}]
    (run / 'case.json').write_text(json.dumps(case))
    snap = server.snapshot(run)
    assert [(e['kind'], e['from'], e['to'], e['ts']) for e in snap['exchanges']] == [
        ('note', 'Market Analyst', 'Fundamentals Analyst', ms('2026-10-26T10:02:00+00:00')),
        ('cite', 'Fundamentals Analyst', 'Market Analyst', ms('2026-10-26T10:03:00+00:00'))]
    note = next(entry for entry in snap['conversation'] if entry['kind'] == 'note')
    assert (note['from'], note['to'], note['intent']) == ('Market Analyst', 'Fundamentals Analyst', 'note on financials')
    assert note['text'] == 'Segment revenue differs. [S2]'
    assert [entry['ts'] for entry in snap['conversation']] == sorted(entry['ts'] for entry in snap['conversation'])
    items = [item for item in snap['timeline'] if item['kind'] == 'exchange']
    assert [(i['agent'], i['to'], i['label']) for i in items] == [('Market Analyst', 'Fundamentals Analyst', 'note'),
                                                                  ('Fundamentals Analyst', 'Market Analyst', 'cite')]
    assert [item['ts'] for item in snap['timeline']] == sorted(item['ts'] for item in snap['timeline'])


def test_a_note_is_summarized_by_where_it_goes():
    assert server._summary('leave_note', {'section': 'financials', 'note': 'x'}) == 'for financials'
    assert server._summary('leave_note', {'answers': 'N1', 'note': 'x'}) == 'answering N1'


def test_the_user_reads_what_went_through_tell_user(runs):
    run = runs / 'r1'
    case = json.loads((run / 'case.json').read_text())
    case['user_messages'] = [{'text': 'The analysts are working.', 'at': '2026-10-26T10:00:30+00:00'}]
    (run / 'case.json').write_text(json.dumps(case))
    replies = [e for e in server.snapshot(run)['conversation'] if e['kind'] == 'reply']
    assert [(e['from'], e['to'], e['text']) for e in replies] == [('Lead Analyst', 'User', 'The analysts are working.')]
