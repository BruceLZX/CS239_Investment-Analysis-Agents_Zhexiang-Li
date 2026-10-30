"""The exporter on a captured run that follows Rakazo's real formats (Pi format-4 JSONL + API threads).

The run is a confidential-startup diligence with planted rule breaks: a web search containing a figure
from the confidential deck (N7), nineteen searches for one first brief (N9), a registered URL no tool ever
returned (N1), a report delivered without review (N5), a brief sent before the research plan (P33) and a version
saved without a QA loop (P36).
"""
from datetime import datetime
import json

import pytest

from team import check_trace, export_trace
from team.export_trace import build_trace, observe_notes, render_markdown

BOTS = {'Lead Analyst': 'bot-lead', 'Market Analyst': 'bot-res', 'IC Reviewer': 'bot-rev'}
DECK = 'Orrin Fieldworks Series A deck'
REQUEST = "Check whether Orrin Fieldworks' numbers hold up against competitors. Questions to deals.lead@realfund.com."
BRIEF = f'Private company Orrin Fieldworks. Read "{DECK}" with read_client_document and verify its pick-rate claims.'
RESULT = 'Packet E1 saved: two competitors found [S2]; the 94% pick rate is unverified [S1].'
FINAL = ('Rating: Wait\nData as of 2026-10-26.\nThe robot picks 94% of ripe fruit [S1].\n'
         'For research purposes only; not investment advice.')
SYSTEM_PROMPT = 'Rakazo system prompt for the account owner'
SEARCHES = ['strawberry picking robot companies', 'autonomous strawberry harvester pick rate',
            'strawberry harvest labor shortage California', 'Orrin Fieldworks robot', 'soft fruit robotics funding 2026',
            'strawberry robot unit cost $48,000', 'Plant City strawberry robot pilot', 'berry harvest automation',
            'agricultural robotics market size', 'strawberry growers adoption survey', 'harvest robot reliability study',
            'farm labor cost per acre strawberries', 'robotic harvesting startups 2026', 'harvest robot vision systems',
            'berry farm automation grants', 'strawberry yield per acre 2025', 'agtech venture rounds 2026',
            'soft robotic gripper fruit', 'harvest robot service contracts']


def ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def transcript(run_id: str, bot_id: str, created: str, messages: list[tuple[str, dict]]) -> str:
    """A Pi format-4 session file, written the way Rakazo's PiJsonlSessionRecorder writes it."""
    lines = [json.dumps({'v': 4, 'kind': 'header', 'id': run_id, 'storageVersion': 1, 'createdAt': ms(created), 'cwd': '/app'}),
             json.dumps({'kind': 'value', 'op': 'set', 'seq': 1, 'namespace': 'pi.branch.tip', 'key': 'main', 'value': None})]
    entries = [('custom', created, {'customType': 'rakazo_context', 'data': {
        'rakazoUserId': 'user-secret', 'rakazoBotId': bot_id, 'rakazoRunId': run_id, 'rakazoThreadId': 'thread',
        'model': 'deepseek-v4-pro', 'provider': 'deepseek', 'thinkingLevel': 'high', 'systemPrompt': SYSTEM_PROMPT}})]
    entries += [('message', when, {'message': message}) for when, message in messages]
    for seq, (kind, when, body) in enumerate(entries, 1):
        lines.append(json.dumps([{'kind': 'entry', 'type': kind, **body, 'id': f'{run_id}-{seq}', 'parentId': None,
                                  'seq': 2 * seq, 'timestamp': ms(when)},
                                 {'kind': 'value', 'op': 'set', 'seq': 2 * seq + 1, 'namespace': 'pi.branch.tip',
                                  'key': 'main', 'value': f'{run_id}-{seq}'}]))
    return '\n'.join(lines) + '\n'


def assistant(*content, cost=0.01):
    return {'role': 'assistant', 'content': list(content), 'provider': 'deepseek', 'model': 'deepseek-v4-pro',
            'usage': {'input': 1000, 'output': 200, 'cacheRead': 500, 'cacheWrite': 0, 'totalTokens': 1700,
                      'cost': {'total': cost}}, 'stopReason': 'stop', 'timestamp': 0}


def call(call_id: str, name: str, arguments: dict) -> dict:
    return {'type': 'toolCall', 'id': call_id, 'name': name, 'arguments': arguments}


def tool_result(call_id: str, name: str, text: str):
    return {'role': 'toolResult', 'toolCallId': call_id, 'toolName': name,
            'content': [{'type': 'text', 'text': text}], 'isError': False, 'timestamp': 0}


def message(id_, role, run_id, when, block, **extra):
    return {'id': id_, 'threadId': 'thread', 'seq': 1, 'role': role, 'blocks': [block], 'runId': run_id,
            'createdAt': when.replace('+00:00', 'Z'), **extra}


@pytest.fixture
def run_dir(tmp_path):
    run = tmp_path / 'runs' / 'r1'
    sessions = run / 'rakazo' / 'pi-sessions' / 'dXNlcg'
    (sessions / 'lead').mkdir(parents=True)
    (sessions / 'res').mkdir(parents=True)
    t = lambda clock: f'2026-10-26T10:{clock}+00:00'
    (run / 'case.json').write_text(json.dumps({
        'run_id': 'r1', 'scenario': 'confidential-startup', 'started_at': t('00:00'),
        'client_documents': [{'name': DECK, 'file': 'fixtures/orrin_fieldworks_deck.md', 'confidentiality': 'client-confidential'}],
        'sources': [
            {'id': 'S1', 'title': DECK, 'source_type': 'company-provided', 'location': DECK, 'date': '2026-10',
             'confidence': 'low', 'claims': 'pick rate, ARR'},
            {'id': 'S2', 'title': 'Strawberry robots enter the field', 'source_type': 'independent media',
             'location': 'https://agnews.example/strawberry-robots', 'date': '2026-09-01', 'confidence': 'medium',
             'claims': 'competitors'},
            {'id': 'S3', 'title': 'Soft-fruit robotics market report', 'source_type': 'industry data',
             'location': 'https://made-up.example/market-report', 'date': '2026', 'confidence': 'medium',
             'claims': 'market size'}],
        'evidence': {}, 'workflow': {}, 'user_data_requests': [],
        'memo_drafts': [{'version': 1, 'rating': 'Wait for milestone', 'saved_at': t('04:00'), 'files': {}}],
        'reviews': [],
        'deliveries': [{'memo_version': 1, 'file': 'memo_v1.md', 'delivered_at': t('05:00'),
                        'review_gate': {'reviewed': False, 'approved': False, 'review_id': None},
                        'memo_check': {'findings': [{'rule': 'N3', 'detail': '1 claims rest only on company-provided '
                                                                              'sources without a verification status'}]}}]}))
    (run / 'memo_v1.md').write_text('# Orrin Fieldworks (private): investment memo\n' + FINAL)
    (run / 'outcome.json').write_text(json.dumps({'outcome': 'delivered'}))
    (run / 'rakazo' / 'usage.json').write_text('[]')
    (run / 'rakazo' / 'messages.json').write_text(json.dumps({'bots': BOTS, 'messages': {
        'Lead Analyst': [
            message('m1', 'user', 'run-L1', t('00:01'), {'kind': 'text', 'text': REQUEST}),
            message('m2', 'bot', 'run-L1', t('00:20'), {'kind': 'bot_message_sent', 'toBotId': 'bot-res',
                                                         'toBotName': 'Market Analyst', 'text': BRIEF, 'intent': 'request'}),
            message('m3', 'bot', 'run-L1', t('00:25'), {'kind': 'text', 'text': 'Research is underway.'}),
            message('m4', 'user', 'run-L2', t('03:00'), {'kind': 'bot_message_received', 'fromBotId': 'bot-res',
                                                          'fromBotName': 'Market Analyst', 'text': RESULT,
                                                          'intent': 'result', 'returnToMessageId': 'm2', 'hop': 2},
                    replyToMessageId='m2'),
            message('m5', 'bot', 'run-L2', t('05:40'), {'kind': 'text', 'text': FINAL})],
        'Market Analyst': [
            message('a1', 'user', 'run-A1', t('00:21'), {'kind': 'bot_message_received', 'fromBotId': 'bot-lead',
                                                          'fromBotName': 'Lead Analyst', 'text': BRIEF,
                                                          'intent': 'request', 'hop': 1}),
            message('a2', 'bot', 'run-A1', t('02:59'), {'kind': 'text', 'text': RESULT})],
        'IC Reviewer': []}}))
    (sessions / 'lead' / '1_old.jsonl').write_text(transcript('run-intro', 'bot-lead', '2026-10-25T09:00:00+00:00', [
        ('2026-10-25T09:00:01+00:00', assistant({'type': 'text', 'text': 'Hello, I am the Lead Analyst.'}))]))
    (sessions / 'lead' / '2_l1.jsonl').write_text(transcript('run-L1', 'bot-lead', t('00:01'), [
        (t('00:02'), {'role': 'user', 'content': 'Assistant: an earlier memo', 'rakazoHistory': True, 'timestamp': 0}),
        (t('00:03'), {'role': 'user', 'content': REQUEST, 'timestamp': 0}),
        (t('00:10'), assistant({'type': 'thinking', 'thinking': 'A confidential deck is attached; brief the analyst to verify it.'},
                               call('c1', 'mcp__investment-research__get_case_status', {}))),
        (t('00:11'), tool_result('c1', 'mcp__investment-research__get_case_status', '{"evidence_packets": []}')),
        (t('00:12'), assistant(call('c2', 'mcp__investment-research__read_client_document', {'name': DECK}))),
        (t('00:13'), tool_result('c2', 'mcp__investment-research__read_client_document', f'[CLIENT-CONFIDENTIAL: {DECK}]')),
        (t('00:19'), assistant(call('c3', 'message_bot', {'confirm_name': 'Market Analyst', 'intent': 'request', 'message': BRIEF}))),
        (t('00:20'), tool_result('c3', 'message_bot', '{"ok": true}')),
        (t('00:24'), assistant({'type': 'text', 'text': 'Research is underway.'}))]))
    searches = [call(f's{i}', 'web_search', {'query': query}) for i, query in enumerate(SEARCHES)]
    results = [(t('00:41'), tool_result(f's{i}', 'web_search',
                                        'Strawberry robots enter the field https://agnews.example/strawberry-robots' if i == 0
                                        else 'No relevant results.')) for i in range(len(SEARCHES))]
    (sessions / 'res' / '3_a1.jsonl').write_text(transcript('run-A1', 'bot-res', t('00:21'), [
        (t('00:22'), {'role': 'user', 'content': f'Lead Analyst asks: {BRIEF}', 'timestamp': 0}),
        (t('00:40'), assistant({'type': 'thinking', 'thinking': 'Search for competitors and check the unit cost.'}, *searches)),
        *results,
        (t('02:58'), assistant({'type': 'text', 'text': RESULT}))]))
    (sessions / 'lead' / '4_l2.jsonl').write_text(transcript('run-L2', 'bot-lead', t('03:00'), [
        (t('03:01'), {'role': 'user', 'content': f'Market Analyst replied: {RESULT}', 'timestamp': 0}),
        (t('03:10'), assistant({'type': 'thinking', 'thinking': 'Evidence arrived; draft and deliver.'},
                               call('c4', 'mcp__investment-research__get_evidence_packets', {}))),
        (t('03:11'), tool_result('c4', 'mcp__investment-research__get_evidence_packets', '## E1: Orrin Fieldworks')),
        (t('04:59'), assistant(call('c5', 'mcp__investment-research__deliver_memo', {}))),
        (t('05:00'), tool_result('c5', 'mcp__investment-research__deliver_memo', '{"delivered_version": 1}')),
        (t('05:39'), assistant({'type': 'text', 'text': FINAL}))]))
    return run


def test_a_captured_run_becomes_a_complete_trace(run_dir):
    trace = build_trace(run_dir)
    assert check_trace.problems(trace) == []
    runs = {run['rakazo_run_id']: run for run in trace['rakazo_runs']}
    assert list(runs) == ['run-L1', 'run-A1', 'run-L2']  # The intro run from the day before is not part of it.
    assert runs['run-L1']['trigger'] == "the user's request"
    assert runs['run-A1']['trigger'] == 'a request from Lead Analyst, hop 1'
    assert runs['run-L2']['trigger'] == 'a result from Market Analyst, hop 2'
    assert [e['seq'] for e in trace['events']] == list(range(1, len(trace['events']) + 1))
    assert trace['run']['model'] == {'provider': 'deepseek', 'model': 'deepseek-v4-pro', 'thinking_level': 'high'}


def test_rule_observations_catch_the_planted_breaks(run_dir):
    observations = build_trace(run_dir)['observations']
    by_rule = {}
    for observation in observations:
        by_rule.setdefault(observation['rule'], []).append(observation['detail'])
    assert sorted(by_rule) == ['N1', 'N3', 'N5', 'N7', 'N9', 'P33', 'P36']
    assert by_rule['N1'] == ['S3 (https://made-up.example/market-report) never appeared in a tool result in this run']
    assert by_rule['N5'] == ['report v1 was delivered, but that version was never reviewed']
    assert by_rule['N7'] == ['Market Analyst put confidential content in web_search: $48,000']
    assert by_rule['N9'] == ['Market Analyst made 19 web_search calls for one first brief (limit 18)']
    assert by_rule['P33'] == ['the Lead briefed the team before saving the research plan']
    assert by_rule['P36'] == ['version 1 was saved without a QA loop since the previous version']
    numbered = [o['rule'] for o in observations if o['rule'].startswith('N')]
    assert numbered == sorted(numbered, key=lambda r: int(r[1:]))


def test_a_run_resumed_after_an_approval_card_is_merged(run_dir):
    # Found in the first live run: a resumed run gets a second transcript file that replays the first one.
    first = next(run_dir.rglob('3_a1.jsonl'))
    resumed_at = ms('2026-10-26T10:02:57+00:00')
    extra = [{'kind': 'entry', 'type': 'message', 'id': 'resumed', 'parentId': None, 'seq': 99, 'timestamp': resumed_at,
              'message': assistant({'type': 'text', 'text': 'Resumed after the denied fetch.'})},
             {'kind': 'value', 'op': 'set', 'seq': 100, 'namespace': 'pi.branch.tip', 'key': 'main', 'value': 'resumed'}]
    first.with_name('5_a1_resumed.jsonl').write_text(first.read_text() + json.dumps(extra) + '\n')
    trace = build_trace(run_dir)
    assert [r['rakazo_run_id'] for r in trace['rakazo_runs']].count('run-A1') == 1
    analyst_calls = [e for e in trace['events'] if e['type'] == 'tool_call' and e['rakazo_run_id'] == 'run-A1']
    assert len(analyst_calls) == len(SEARCHES)
    assert [e['text'] for e in trace['events'] if e.get('text') == 'Resumed after the denied fetch.'] == \
        ['Resumed after the denied fetch.']


def test_approval_cards_show_as_platform_guard_events(run_dir):
    path = run_dir / 'rakazo' / 'messages.json'
    captured = json.loads(path.read_text())
    captured['messages']['Market Analyst'].append(message(
        'a3', 'bot', 'run-A1', '2026-10-26T10:00:45+00:00',
        {'kind': 'ask', 'text': 'Review before web_fetch → analystlens.com', 'status': 'denied',
         'detail': 'url: https://www.analystlens.com/stocks/aapl'}))
    path.write_text(json.dumps(captured))
    trace = build_trace(run_dir)
    guards = [e for e in trace['events'] if e['type'] == 'platform_guard']
    assert [g['text'] for g in guards] == ['Review before web_fetch → analystlens.com']
    assert any(o['rule'] == 'platform guard' and 'analystlens.com' in o['detail'] for o in trace['observations'])
    assert '**Rakazo approval card:** Review before web_fetch → analystlens.com' in render_markdown(trace)


def test_replayed_history_and_duplicate_replies_are_dropped(run_dir):
    trace = build_trace(run_dir)
    assert not any('an earlier memo' in e.get('text', '') for e in trace['events'])
    assert not any(e['type'] == 'reply' for e in trace['events'])  # Every run has a transcript.
    next(run_dir.rglob('4_l2.jsonl')).unlink()
    replies = [e for e in build_trace(run_dir)['events'] if e['type'] == 'reply']
    assert [e['text'] for e in replies] == [FINAL]


def test_mcp_tool_names_are_shown_without_the_server_prefix(run_dir):
    calls = {e['tool']: e for e in build_trace(run_dir)['events'] if e['type'] == 'tool_call'}
    assert calls['read_client_document']['arguments'] == {'name': DECK}
    assert calls['read_client_document']['tool_full_name'] == 'mcp__investment-research__read_client_document'
    assert calls['message_bot']['arguments']['confirm_name'] == 'Market Analyst'


def test_private_details_stay_out_of_the_trace(run_dir):
    dumped = json.dumps(build_trace(run_dir))
    assert 'deals.lead@realfund.com' not in dumped and '[redacted email]' in dumped
    assert 'user-secret' not in dumped and SYSTEM_PROMPT not in dumped
    # The server names the files it writes by absolute path, which holds this machine's user name.
    local = str(export_trace.ROOT / 'runs' / 'r1' / 'versions' / 'v1' / 'report.html')
    assert export_trace.redact({'files': {'html': local}}) == {'files': {'html': 'src/runs/r1/versions/v1/report.html'}}


def test_usage_is_summed_per_agent(run_dir):
    usage = build_trace(run_dir)['usage']
    assert usage['by_agent']['Lead Analyst']['model_calls'] == 7  # Four calls in its first run, three in its second.
    assert usage['by_agent']['Market Analyst']['model_calls'] == 2
    # Nine deepseek-v4-pro calls of 500 cache-hit, 1,000 cache-miss and 200 output tokens, all after 10:00 UTC on a
    # Monday: DeepSeek's off-peak rate, half its peak price, not the $0.01 a call that Rakazo estimated.
    assert usage['total']['cost_usd'] == pytest.approx(9 * (500 * 0.044 + 1000 * 1.32 + 200 * 3.96) / 1e6 / 2)


def test_markdown_reads_as_a_timeline(run_dir):
    markdown = render_markdown(build_trace(run_dir))
    assert markdown.startswith('# Trace: confidential-startup')
    assert '### User → Lead Analyst' in markdown
    assert '### 2. Market Analyst, woken by a request from Lead Analyst, hop 1' in markdown
    assert '**Action:** `web_search` {"query": "strawberry robot unit cost $48,000"}' in markdown
    assert '**Message to Market Analyst** (request)' in markdown
    assert '- Delivered report v1 (never reviewed; final check failed)' in markdown
    assert '## Rule observations' in markdown and '| N7 | Market Analyst put confidential content' in markdown
    assert '## Final report' in markdown


def test_the_checker_names_what_is_missing(run_dir):
    trace = build_trace(run_dir)
    trace['events'] = [e for e in trace['events'] if not (e['type'] == 'thought' and e['agent'] == 'Market Analyst')]
    assert check_trace.problems(trace) == ['Market Analyst: no thoughts']


def test_messages_to_the_user_carry_no_early_rating_and_no_internal_material():
    case = {'memo_drafts': [{'version': 1, 'rating': 'Sell', 'saved_at': '2026-10-27T21:45:00+00:00'}],
            'deliveries': [{'delivered_at': '2026-10-27T21:48:35+00:00'}]}
    replies = [{'ts_ms': ms(f'2026-10-27T21:{clock}+00:00'), 'text': text} for clock, text in (
        ('42:48', "I can't skip the review: a Buy/Sell call needs it."),        # no draft yet
        ('43:00', 'Status: both analysts are building the case file.'),          # describing the work is fine
        ('44:00', 'Status: waiting on their evidence packets.'),                 # N6
        ('45:22', 'The draft call under review is **Sell**.'),                   # N5
        ('46:00', 'Waiting for market research; the Buy/Sell call is in review.'),  # names the question only
        ('46:30', "I still can't give you a Buy or Sell until the review passes."),  # so does this
        ('47:00', 'Status: ' + 'the team is still working. ' * 12),                # P8: longer than a status line
        ('48:38', 'Delivered: Sell. Version 3 cleared review R2 with no must-fix items.'))]  # after delivery; N6
    observations = export_trace.observe_user_messages(replies, case)
    assert [(o['rule'], o['detail'].split(':')[0]) for o in observations] == [
        ('N6', "the Lead's message to the user names internal material (evidence packets)"),
        ('N5', "before delivery, the Lead told the user the draft's rating (Sell)"),
        ('P8', 'before delivery, the Lead sent the user 332 characters; a status note is at most 300'),
        ('N6', "the Lead's message to the user names internal material (R2, must-fix)")]


def test_a_follow_up_question_appears_in_the_timeline(run_dir):
    t = lambda clock: f'2026-10-26T10:{clock}+00:00'
    captured = json.loads((run_dir / 'rakazo' / 'messages.json').read_text())
    captured['messages']['Lead Analyst'] += [
        message('m6', 'user', 'run-L3', t('07:00'), {'kind': 'text', 'text': 'Why Wait and not Pass?'}),
        message('m7', 'bot', 'run-L3', t('07:30'), {'kind': 'text', 'text': 'Because the market is real.'})]
    (run_dir / 'rakazo' / 'messages.json').write_text(json.dumps(captured))
    (run_dir / 'rakazo' / 'pi-sessions' / 'dXNlcg' / 'lead' / '5_l3.jsonl').write_text(transcript('run-L3', 'bot-lead', t('07:00'), [
        (t('07:01'), {'role': 'user', 'content': 'Why Wait and not Pass?', 'timestamp': 0}),
        (t('07:10'), assistant({'type': 'thinking', 'thinking': 'Answer from the case file.'},
                               call('c6', 'mcp__investment-research__get_case_status', {}))),
        (t('07:11'), tool_result('c6', 'mcp__investment-research__get_case_status', '{"delivered_versions": [1]}')),
        (t('07:29'), assistant({'type': 'text', 'text': 'Because the market is real.'}))]))
    markdown = render_markdown(build_trace(run_dir))
    section = markdown.split("Lead Analyst, woken by the user's request (2026-10-26T10:07:00")[1]
    assert section.split(')', 1)[1].lstrip().startswith('**Follow-up from the user**')
    assert 'Why Wait and not Pass?' in section
    assert markdown.count('**Follow-up from the user**') == 1  # the first request keeps its own heading


def revision(number: int, author: str, saved_at: str, markdown: str = 'A short part [S2].') -> dict:
    return {'revision': number, 'author': author, 'markdown': markdown, 'chars': len(markdown), 'sha256': 'h',
            'passed': False, 'findings': [], 'depth': ['too short'], 'saved_at': saved_at}


def test_sections_versions_reviews_and_the_final_check_join_the_trace(run_dir):
    case = json.loads((run_dir / 'case.json').read_text())
    case['scope'] = {'company': 'Orrin Fieldworks', 'ticker': None, 'type': 'private', 'decision': 'Series A',
                     'language': 'en', 'set_by': 'Lead Analyst', 'set_at': '2026-10-26T10:00:05+00:00'}
    case['memo_parts'] = {'competition': [dict(revision(1, 'Market Analyst', '2026-10-26T10:02:00+00:00'),
                                               evidence_before_draft=True)],
                          'scoring': [revision(1, 'Lead Analyst', '2026-10-26T10:03:30+00:00', '1. Picks 94% [S1].')]}
    case['evidence'] = {'competition': [{'author': 'Market Analyst', 'queries': SEARCHES[:4], 'rows': [], 'gate': [],
                                         'plan': {}, 'gate_passed': True, 'saved_at': '2026-10-26T10:01:30+00:00'}]}
    report = run_dir / 'versions' / 'v1' / 'report.md'
    report.parent.mkdir(parents=True)
    report.write_text(FINAL)
    case['memo_drafts'][0].update(parts={'competition': {'revision': 1, 'sha256': 'h', 'author': 'Market Analyst'},
                                         'scoring': {'revision': 1, 'sha256': 'h', 'author': 'Lead Analyst'}},
                                  changed_parts=['competition', 'scoring'], passed=False, composite_score='5.1',
                                  files={'markdown': str(report)})
    case['deliveries'][0]['final_check'] = {'passed': False, 'report': ['missing the timeline component'],
                                            'depth': [], 'citations': [], 'output': []}
    (run_dir / 'case.json').write_text(json.dumps(case))
    trace = build_trace(run_dir)
    saved = trace['case_file']
    assert saved['scope']['type'] == 'private' and saved['evidence']['competition'][0]['gate_passed']
    assert saved['memo_parts']['competition'][0]['evidence_before_draft'] is True
    assert saved['memo_versions'][0]['parts'] == {'competition': 1, 'scoring': 1}
    assert trace['delivered_check'] == {'version': 1, 'passed': False, 'report': ['missing the timeline component'],
                                        'depth': [], 'citations': [], 'output': []}
    assert any(o['rule'] == 'P40' and 'final check failing: 1 report' in o['detail'] for o in trace['observations'])
    # The delivered report is re-checked from the file the server wrote for that version.
    assert any(o['rule'] == 'N3' and o['detail'].startswith('delivered report v1') for o in trace['observations'])
    markdown = render_markdown(trace)
    assert '| 5 | 竞争格局 Competitive Landscape | Market Analyst | 1 (Market Analyst) | 18 | yes | problems |' in markdown
    assert '| 4 | 市场与行业分析 Market & Industry Analysis | Market Analyst | none |' in markdown
    assert '## Final check at delivery' in markdown and '| report | missing the timeline component |' in markdown


def test_sections_saved_by_someone_else_drafted_too_early_or_answered_without_evidence_are_observed():
    review = lambda n, at, items=(): {'id': f'R{n}', 'round': n, 'verdict': 'revise', 'finished_at': at,
                                      'items': list(items)}
    critical = {'severity': 'Critical', 'sections': ['financials'], 'owners': ['Fundamentals Analyst'],
                'issue': 'No debt maturities.'}
    case = {'memo_parts': {'financials': [dict(revision(1, 'Fundamentals Analyst', '2026-10-26T10:01:00+00:00'),
                                               evidence_before_draft=False),
                                          revision(2, 'Market Analyst', '2026-10-26T10:02:00+00:00')]},
            'sources': [], 'reviews': [review(1, '2026-10-26T10:03:00+00:00', [critical]),
                                       review(2, '2026-10-26T10:04:00+00:00')]}
    observations = export_trace.observe_sections(case)
    assert [o['rule'] for o in observations] == ['P32', 'P34', 'N11']
    assert observations[0]['detail'] == ('Market Analyst saved revision 2 of the financials section, which the '
                                         'Fundamentals Analyst owns')
    case['sources'] = [{'id': 'S9', 'registered_by': 'Fundamentals Analyst', 'registered_at': '2026-10-26T10:03:30+00:00'}]
    assert 'N11' not in [o['rule'] for o in export_trace.observe_sections(case)]
    case['reviews'] += [review(3, '2026-10-26T10:06:00+00:00'), review(4, '2026-10-26T10:07:00+00:00')]
    assert {'rule': 'P9', 'detail': '4 review rounds; the limit is 3'} in export_trace.observe_sections(case)


def test_the_order_of_work_is_observed():
    at = lambda clock: f'2026-10-26T10:{clock}.000+00:00'
    tool = lambda clock, name, agent: {'type': 'tool_call', 'tool': name, 'agent': agent, 'ts': at(clock)}
    events = [tool('01:00', 'message_bot', 'Lead Analyst'), tool('02:00', 'save_research_plan', 'Lead Analyst'),
              tool('05:00', 'start_review', 'IC Reviewer'), tool('06:00', 'save_red_team_review', 'Red Team Analyst'),
              tool('03:00', 'run_qa_loop', 'Lead Analyst')]
    case = {'memo_drafts': [{'version': 1, 'saved_at': '2026-10-26T10:04:00+00:00'},
                            {'version': 2, 'saved_at': '2026-10-26T10:08:00+00:00'}]}
    assert [(o['rule'], o['detail'].split(' was')[0]) for o in export_trace.observe_workflow(events, case)] == [
        ('P33', 'the Lead briefed the team before saving the research plan'),
        ('P35', 'the first review started before the red-team review'), ('P36', 'version 2')]


def test_long_replies_and_overstated_queries_are_observed():
    run = {'rakazo_run_id': 'r1', 'agent': 'Market Analyst', 'started_at': '2026-10-26T10:00:00+00:00',
           'ended_at': '2026-10-26T10:10:00+00:00'}
    events = [{'type': 'tool_call', 'tool': 'web_search', 'agent': 'Market Analyst', 'rakazo_run_id': 'r1',
               'arguments': {'query': 'robots'}, 'seq': 1, 'ts': '2026-10-26T10:01:00.000+00:00'},
              {'type': 'assistant_text', 'agent': 'Market Analyst', 'rakazo_run_id': 'r1', 'text': 'x' * 1600}]
    case = {'deliveries': [], 'memo_drafts': [], 'sources': [], 'client_documents': [], 'reviews': [],
            'evidence': {'market': [{'author': 'Market Analyst', 'saved_at': '2026-10-26T10:05:00+00:00',
                                     'queries': ['robots', 'harvest market', 'labor costs', 'yields']}]}}
    details = {o['rule']: o['detail'] for o in export_trace.observe_rules(events, [run], case)}
    assert details['P21'] == 'Market Analyst replied with 1,600 characters (limit 1,500)'
    assert details['N1'] == 'the market evidence block lists 4 queries, but Market Analyst had run 1'


def test_a_next_line_character_inside_a_transcript_record_keeps_it_whole(tmp_path):
    # Found in a live run: a fetched page put U+0085 into a JSON string, unescaped, and splitlines() broke there.
    text = transcript('run-x', 'bot-res', '2026-10-26T10:00:00+00:00', [
        ('2026-10-26T10:00:01+00:00', tool_result('c1', 'web_fetch', 'Line one\x85line two'))])
    path = tmp_path / 'run-x.jsonl'
    path.write_text(text.replace('\\u0085', '\x85'))
    [(_, message)] = export_trace.read_transcript(path)['messages']
    assert message['content'][0]['text'] == 'Line one\x85line two'


def test_calls_through_rakazos_tool_catalog_count_as_the_tool_they_ran():
    # A bot past Rakazo's direct-tool limit calls each tool through connectors_execute_tool {id, arguments}.
    run = {'run_id': 'run-x', 'model': 'deepseek-flash', 'messages': [
        (ms('2026-10-29T20:00:01+00:00'), assistant(call('c1', 'connectors_load_tool', {'id': 'run_qa_loop'}))),
        (ms('2026-10-29T20:00:02+00:00'), assistant(call('c2', 'connectors_execute_tool',
                                                          {'id': 'run_qa_loop', 'arguments': {}}))),
        (ms('2026-10-29T20:00:03+00:00'), tool_result('c2', 'connectors_execute_tool', '{"passed": true}'))]}
    events, _ = export_trace.transcript_events(run, 'Lead Analyst')
    assert [(e['type'], e['tool']) for e in events] == [('tool_call', 'connectors_load_tool'),
                                                        ('tool_call', 'run_qa_loop'), ('tool_result', 'run_qa_loop')]
    assert events[1]['arguments'] == {} and events[1]['tool_full_name'] == 'connectors_execute_tool'


def test_round_percentages_do_not_mark_a_decks_content(tmp_path, monkeypatch):
    # "10%" from a deck's option-pool term matched an analyst's search about test accuracy.
    (tmp_path / 'deck.md').write_text('Option pool of 10% post-money. Accuracy **98.7%** across **K261734** sites, 51% margin.')
    monkeypatch.setattr(export_trace, 'ROOT', tmp_path)
    tokens = export_trace.confidential_tokens({'client_documents': [
        {'name': 'Deck', 'file': 'deck.md', 'confidentiality': 'client-confidential'}]})
    assert {'98.7%', 'K261734', '51%'} <= set(tokens) and '10%' not in tokens


def test_exchanges_between_agents_join_the_trace_and_its_markdown(run_dir):
    case = json.loads((run_dir / 'case.json').read_text())
    case['sources'][1]['registered_by'] = 'Market Analyst'
    case['memo_parts'] = {'financials': [revision(1, 'Fundamentals Analyst', '2026-10-26T10:03:00+00:00')]}
    case['notes'] = [{'id': 'N1', 'from': 'Market Analyst', 'to': 'Fundamentals Analyst', 'section': 'financials',
                      'note': 'Segment revenue differs.', 'source_ids': ['S2'], 'answers': None,
                      'at': '2026-10-26T10:02:00+00:00'}]
    (run_dir / 'case.json').write_text(json.dumps(case))
    (run_dir / 'tool_log.jsonl').write_text(json.dumps({
        'ts': '2026-10-26T10:04:00+00:00', 'agent': 'Market Analyst', 'tool': 'get_memo_parts',
        'arguments': {'sections_wanted': ['financials']}}) + '\n')
    trace = build_trace(run_dir)
    assert [(e['kind'], e['from'], e['to']) for e in trace['exchanges']] == [
        ('note', 'Market Analyst', 'Fundamentals Analyst'), ('cite', 'Fundamentals Analyst', 'Market Analyst'),
        ('read', 'Market Analyst', 'Fundamentals Analyst')]
    assert trace['case_file']['notes'][0]['id'] == 'N1'
    markdown = render_markdown(trace)
    assert '## Exchanges between agents' in markdown
    assert '| Market Analyst | Fundamentals Analyst | 1 |  | 1 |  |  |  |' in markdown
    assert any(o['rule'] == 'P42' and 'N1' in o['detail'] for o in trace['observations'])  # Open at delivery.


def test_too_many_new_notes_in_a_turn_are_observed():
    note = {'type': 'tool_call', 'tool': 'leave_note', 'agent': 'Market Analyst', 'rakazo_run_id': 'r1',
            'arguments': {'section': 'financials'}}
    answer = {**note, 'arguments': {'answers': 'N1'}}
    case = {'deliveries': [], 'notes': []}
    assert observe_notes([note] * 3 + [answer] * 2 + [{**note, 'rakazo_run_id': 'r2'}], case) == []
    assert observe_notes([note] * 4, case) == [{'rule': 'P42', 'detail': 'Market Analyst left 4 new notes in one turn'}]
