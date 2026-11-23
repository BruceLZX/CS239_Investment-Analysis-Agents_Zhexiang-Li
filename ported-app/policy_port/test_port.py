"""Offline development tests; no live model or student-agent execution."""
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from policyweave.enforcement.telemetry import record_execution
from policyweave.core.artifacts import save

LEAD, COMPANY, MARKET = 'Lead Analyst', 'Company Analyst', 'Market Analyst'
REVIEWER, RED = 'IC Reviewer', 'Red Team Analyst'
VERSION = dict(rating='Watchlist', data_as_of='2026-11-21', tagline='Research',
               business_summary='A public business', industry='Industrial', headquarters='US', stage='Listed')


class PortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recording = record_execution('Offline model fixture: development tests; no live agent execution')
        cls.trace = cls.recording.__enter__()
        global server, case_file, sections, workflow, adapter
        from tools import server, case_file, sections, workflow
        from policy_port import adapter
        from mcp.server.mcpserver.exceptions import ToolError
        cls.ToolError = ToolError
        cls.effects = []

    @classmethod
    def tearDownClass(cls):
        save(ROOT / 'policy_port' / 'trajectories.json', cls.trace.export())
        save(ROOT / 'policy_port' / 'effect-comparison.json', cls.effects)
        cls.recording.__exit__(None, None, None)

    def setUp(self):
        # Keep test outputs inside the checkout, including host-relocated copies.
        self.temp = tempfile.TemporaryDirectory(prefix='port-test-', dir=ROOT / 'policy_port')
        self.addCleanup(self.temp.cleanup)
        self.runs = patch.object(case_file, 'RUNS', Path(self.temp.name))
        self.runs.start()
        self.addCleanup(self.runs.stop)
        self.network = patch('httpx.Client.send', side_effect=AssertionError('No network in offline tests'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.native_subprocess = subprocess.run
        def external_process(command, *args, **kwargs):
            if isinstance(command, list) and command[1:3] == ['-m', 'tools.pdf']:
                Path(command[4]).write_bytes(b'%PDF-1.4\nOffline development print fixture\n%%EOF\n')
                return subprocess.CompletedProcess(command, 0, '', '')
            return self.native_subprocess(command, *args, **kwargs)
        self.process = patch('subprocess.run', side_effect=external_process)
        self.process.start()
        self.addCleanup(self.process.stop)
        self.new_case()

    def new_case(self, mode=None):
        return case_file.start_run('offline-development', request='Research a public company', policy_mode=mode)

    def call(self, name, actor=LEAD, **arguments):
        token = server.CALLER.set(actor)
        try:
            text = getattr(server, name)(**arguments)
        finally:
            server.CALLER.reset(token)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def blocked(self, name, actor=LEAD, **arguments):
        with self.assertRaises(self.ToolError) as caught:
            self.call(name, actor, **arguments)
        return str(caught.exception)

    def scoped(self):
        return self.call('set_case_scope', company='Example', ticker='EX', company_type='listed', decision='Research')

    def prepare_report(self):
        self.scoped()
        for section in sections.ALL_SECTIONS:
            self.call('save_memo_part', section.owner, section=section.key,
                      markdown='The evidence remains incomplete and the conclusion is provisional.')
        self.call('save_thesis_table', rows=[])
        self.call('save_scenario_analysis', scenarios=[], assumptions=[],
                  consensus=workflow.Consensus(consensus='Unclear', our_view='Unclear', evidence='Unavailable',
                                               proof_event='Disclosure'),
                  one_question=workflow.OneQuestion(question='What changes the decision?', why='Evidence matters'))
        self.call('save_red_team_review', RED,
                  answers=workflow.RedTeamAnswers(**{k: 'Evidence is limited.' for k in workflow.RedTeamAnswers.model_fields}),
                  weakest_section='risk')
        self.call('save_research_plan', spines=[workflow.Spine(spine='Public equity', must_answer='Business durability')],
                  industry_map='Industrial', geo_lens='US', policy_lens='Unclear', regulatory_databases=[],
                  gates_done=[], hypothesis='Wait for evidence')
        self.call('save_profile_requirements', items_done=[], evidence='The profile remains incomplete.')
        qa = self.call('run_qa_loop')
        self.assertFalse(qa['passed'])
        result = self.call('save_memo_version', **VERSION)
        self.assertEqual(result['version'], 1)
        self.assertEqual(result['check']['rule_findings'], [])
        return result

    def test_01_scope_freezes_and_session_recovers(self):
        self.scoped()
        error = self.blocked('set_case_scope', company='Other', ticker=None, company_type='private', decision='Change')
        self.assertIn('"reasonType": "explicit_deny"', error)
        self.assertIn('"P5"', error)
        self.assertIn('"requestId"', error)
        self.assertEqual(case_file.read_case()['scope']['company'], 'Example')
        self.assertTrue(self.call('tell_user', message='Research is under way.')['sent'])

    def test_02_section_ownership_and_unknown_section(self):
        self.assertIn('POLICY_BLOCKED', self.blocked('save_memo_part', MARKET,
                      section='company_overview', markdown='Untrusted replacement'))
        self.assertEqual(case_file.read_case()['memo_parts'], {})
        saved = self.call('save_memo_part', COMPANY, section='1', markdown='A public business.')
        self.assertEqual(saved['saved_by'], COMPANY)
        self.assertEqual(saved['revision'], 1)
        self.assertIn('A public business.', self.call('get_memo_parts', COMPANY, sections_wanted=['1']))
        self.assertIn('POLICY_BLOCKED', self.blocked('save_memo_part', COMPANY, section='missing', markdown='Text'))
        self.assertEqual(len(case_file.read_case()['memo_parts']['company_overview']), 1)

    def test_03_original_evidence_refusal_once_exception(self):
        self.new_case('enforce')
        self.assertIn('P34', self.blocked('save_memo_part', COMPANY, section='1', markdown='Evidence is unavailable.'))
        result = self.call('save_memo_part', COMPANY, section='1', markdown='Evidence is unavailable.')
        self.assertEqual(result['revision'], 1)
        revision = case_file.read_case()['memo_parts']['company_overview'][-1]
        self.assertFalse(revision['evidence_before_draft'])
        self.assertEqual(revision['author'], COMPANY)

    def test_04_message_bounds_unrelated_input_and_case_isolation(self):
        self.scoped()
        with case_file.open_case() as case:
            case['request'] = 'x' * 1000  # Unrelated input is not the proposed message.
        self.assertTrue(self.call('tell_user', message='x' * 300)['sent'])
        self.assertIn('P8', self.blocked('tell_user', message='x' * 301))
        self.assertIn('POLICY_BLOCKED', self.blocked('tell_user', COMPANY, message='Hello'))
        old_run = case_file.read_case()['run_id']
        self.new_case()
        self.assertNotEqual(case_file.read_case()['run_id'], old_run)
        self.scoped()
        self.assertIsNone(case_file.read_case().get('user_messages'))
        self.assertIn('N5', self.blocked('deliver_memo', version=0))

    def test_05_notes_retain_sources_routing_answers_and_errors(self):
        self.call('register_source', COMPANY, title='Public record', source_type='independent',
                  location='Public record page', date='2026-11-20', confidence='medium', claims='A public claim')
        result = self.call('leave_note', COMPANY, note='Check the comparison.', section='market', source_ids=['S1'])
        self.assertEqual(result['id'], 'N1')
        self.assertEqual(case_file.read_case()['notes'][-1]['to'], MARKET)
        self.assertIn('P42', self.blocked('leave_note', COMPANY, note='x' * 601, section='market', source_ids=['S1']))
        answer = self.call('leave_note', MARKET, note='Checked; uncertainty remains.', answers='N1')
        self.assertEqual(answer['id'], 'N2')
        self.assertTrue(case_file.read_case()['notes'][0]['answered_at'])
        self.assertEqual(case_file.read_case()['memo_parts'], {})
        self.new_case()
        self.assertIn('Not in the source register', self.blocked('leave_note', COMPANY,
                      note='Check this.', section='market', source_ids=['S999']))

    def test_06_missing_prerequisites_and_roles(self):
        self.assertIn('P6', self.blocked('save_memo_version', **VERSION))
        self.assertEqual(case_file.read_case()['memo_drafts'], [])
        self.assertIn('POLICY_BLOCKED', self.blocked('save_review_pass', LEAD,
                      review_id='R1', pass_number=1, items=[]))
        self.assertIn('P35', self.blocked('start_review', REVIEWER, memo_version=0))
        self.assertIn('P37', self.blocked('finish_review', REVIEWER, review_id='R1',
                      verdict='approve', grade='B', top_three=[], ready='Yes'))

    def test_07_actual_report_review_reads_delivery(self):
        self.prepare_report()
        review = self.call('start_review', REVIEWER, memo_version=0)
        self.assertIn('P37', self.blocked('finish_review', REVIEWER, review_id=review['review_id'],
                      verdict='approve', grade='B', top_three=[], ready='Yes'))
        for number in range(1, 6):
            self.call('save_review_pass', REVIEWER, review_id=review['review_id'], pass_number=number,
                      items=[], notes='Offline development review fixture.')
        text = self.call('get_memo_parts', REVIEWER, sections_wanted=['company_overview'], version=0)
        self.assertIn('The evidence remains incomplete', text)
        self.call('get_memo_check', REVIEWER, version=0)
        self.call('get_evidence_matrix', REVIEWER)
        self.assertIn('in progress', self.call('get_latest_review', REVIEWER))
        self.assertIn('N5', self.blocked('deliver_memo', version=0))
        verdict = self.call('finish_review', REVIEWER, review_id=review['review_id'],
                            verdict='approve', grade='B', top_three=[], ready='With fixes')
        self.assertEqual(verdict['verdict'], 'approve')
        self.assertIn('P9', self.blocked('start_review', REVIEWER, memo_version=1))
        self.assertIn('P9', self.blocked('finish_review', REVIEWER, review_id=review['review_id'],
                      verdict='revise', grade='C', top_three=[], ready='No'))
        delivery = self.call('deliver_memo', version=0)
        self.assertEqual(delivery['delivered_version'], 1)
        self.assertTrue(Path(delivery['folder']).is_dir())
        self.assertFalse(delivery['final_check']['passed'])
        self.assertTrue(self.call('tell_user', message='x' * 301)['sent'])
        self.assertIn('verdict approve', self.call('get_latest_review', REVIEWER))
        self.assertIn('P6', self.blocked('save_memo_version', **VERSION))
        self.assertEqual(len(case_file.read_case()['memo_drafts']), 1)

    def test_08_compare_original_effects_and_offline_visible_model(self):
        original_scope = inspect.unwrap(server.set_case_scope)
        token = server.CALLER.set(LEAD)
        try:
            first = original_scope(company='Example', ticker='EX', company_type='listed', decision='Research')
            original_scope(company='Other', ticker=None, company_type='private', decision='Change')
            original_company = case_file.read_case()['scope']['company']
        finally:
            server.CALLER.reset(token)
        self.new_case()
        self.assertEqual(first, self.scoped())
        self.blocked('set_case_scope', company='Other', ticker=None, company_type='private', decision='Change')
        self.effects.append({'scenario': 'scope replacement', 'baseline_company': original_company,
                             'protected_company': case_file.read_case()['scope']['company'],
                             'fixture': 'offline development; baseline uses unchanged unwrapped candidate body'})
        self.assertEqual(original_company, 'Other')
        self.assertEqual(case_file.read_case()['scope']['company'], 'Example')
        from team.rakazo_client import Rakazo
        fixture = [
            {'id': 'fixture-output', 'role': 'bot', 'blocks': [
                {'kind': 'text', 'text': 'Offline model fixture: I will wait for review.'},
                {'kind': 'thinking', 'text': 'DO NOT CAPTURE'}]},
            {'id': 'fixture-message', 'role': 'bot', 'blocks': [
                {'kind': 'bot_message_sent', 'toBotName': MARKET, 'intent': 'request', 'text': 'Research public demand.'}]},
            {'id': 'fixture-receipt', 'role': 'user', 'blocks': [
                {'kind': 'bot_message_received', 'fromBotName': LEAD, 'text': 'Research public demand.'}]}]
        def offline_rpc(route, data=None):
            if route == 'threads/messages':
                return {'messages': fixture}
            if route == 'threads/get':
                return {'activeRuns': []}
            if route == 'threads/send':
                return {'id': 'fixture-accepted-request'}
            raise AssertionError(route)
        client = Rakazo('http://offline.invalid', session_file=Path(self.temp.name) / 'absent.json')
        self.addCleanup(client.http.close)
        with patch.object(client, 'rpc', side_effect=offline_rpc):
            self.assertEqual(client.send('offline-agent', 'Research a public company.'), {'id': 'fixture-accepted-request'})
            self.assertEqual(client.messages('offline-agent'), fixture)
            client.messages('offline-agent')
        self.call('tell_user', message='Research is under way.')
        events = self.trace.export()['events']
        self.assertTrue(any(e['kind'] == 'tool_call' and e['tool'] == 'tell_user'
                            and e['arguments']['message'] == 'Research is under way.' for e in events))
        self.assertTrue(any(e['kind'] == 'tool_result' and '"sent": true' in str(e.get('result')) for e in events))
        self.assertTrue(any(e['kind'] == 'message' and e['recipients'] == [MARKET]
                            and e['content'] == 'Research public demand.' for e in events))
        outputs = [e for e in events if e['kind'] == 'llm_output']
        self.assertEqual(sum(e['result'] == 'Offline model fixture: I will wait for review.' for e in outputs), 1)
        self.assertNotIn('DO NOT CAPTURE', json.dumps(events))

    def test_09_final_failure_length_exception(self):
        # Stored-state boundary fixture, not source-produced review evidence.
        with case_file.open_case() as case:
            case['reviews'] = [dict(id='R3', memo_version=1, round=3, verdict='reject', passes={}, items=[])]
        self.assertTrue(self.call('tell_user', message='The report failed final review. ' * 15)['sent'])
        self.assertIn('P9', self.blocked('deliver_memo', version=0))

    def test_10_delegated_confidentiality_and_public_search(self):
        self.new_case('enforce')
        with case_file.open_case() as case:
            case['client_documents'] = [{'name': 'Deck', 'file': 'not-present.md',
                                         'confidentiality': 'client-confidential',
                                         'confidential_terms': ['HiddenCustomerName']}]
        self.assertIn('N7', self.blocked('web_search', MARKET, query='HiddenCustomerName'))
        def public_search(query, max_results=8):
            return [{'title': 'Public demand', 'url': 'https://public.invalid/demand', 'snippet': query}]
        with patch.object(server.web, 'search', side_effect=public_search):
            result = self.call('web_search', MARKET, query='public industrial demand')
        self.assertEqual(result['results'][0]['snippet'], 'public industrial demand')
        self.assertEqual(case_file.read_case()['memo_parts'], {})

    def test_11_frozen_item_limit_gap_and_original_critical_guard(self):
        self.prepare_report()
        review = self.call('start_review', REVIEWER, memo_version=0)
        items = [workflow.ReviewItem(severity='Important', sections=['company_overview'],
                                    issue='Evidence is incomplete.', action='Obtain a public record.')
                 for _ in range(11)]
        result = self.call('save_review_pass', REVIEWER, review_id=review['review_id'], pass_number=1, items=items)
        self.assertEqual(result['items_saved'], 11)
        self.effects.append({'scenario': 'P26 frozen binding mismatch', 'actual_first_round_important_items': 11,
                             'coverage': 'unimplemented; original callback and frozen rules allow this'})
        self.call('save_review_pass', REVIEWER, review_id=review['review_id'], pass_number=1,
                  items=[workflow.ReviewItem(severity='Critical', sections=['company_overview'],
                                            issue='Evidence is incomplete.', action='Obtain evidence.')])
        for number in range(2, 6):
            self.call('save_review_pass', REVIEWER, review_id=review['review_id'], pass_number=number, items=[])
        error = self.blocked('finish_review', REVIEWER, review_id=review['review_id'],
                             verdict='approve', grade='B', top_three=[], ready='Yes')
        self.assertIn('1 Critical items are open', error)
        self.assertIsNone(case_file.read_case()['reviews'][-1]['verdict'])
        # No forced retry or fresh runtime conceals the conservative stop after a
        # callback exception. This is a recorded original-workflow recovery gap.
        self.assertIn('session is stopped', self.blocked('save_review_pass', REVIEWER,
                      review_id=review['review_id'], pass_number=1, items=[]))

    def test_12_mcp_client_success_and_refusal_shapes(self):
        import asyncio
        from mcp.client.client import Client
        async def invoke():
            async with Client(server.server) as client:
                good = await client.call_tool('tell_user', {'message': 'Research is under way.'})
                bad = await client.call_tool('tell_user', {'message': 'x' * 301})
                return good, bad
        token = server.CALLER.set(LEAD)
        try:
            good, bad = asyncio.run(invoke())
        finally:
            server.CALLER.reset(token)
        self.assertFalse(good.is_error)
        self.assertTrue(bad.is_error)
        self.assertTrue(json.loads(good.content[0].text)['sent'])
        self.assertIn('"decision": "blocked"', bad.content[0].text)
        self.assertEqual(len(case_file.read_case()['user_messages']), 1)


if __name__ == '__main__':
    unittest.main()
