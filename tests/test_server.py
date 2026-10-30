from contextlib import contextmanager
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from tools import case_file, report, sections, server
from tools.qa import check_evidence, check_workflow_docs
from tools.retrieved import Retrieved, source

from .helpers import call_tool, list_tools, result_text
from .report_samples import EXECUTIVE_SUMMARY, FINANCIALS, SCORING

SOURCE = {'title': 'Apple 10-K FY2025', 'source_type': 'primary filing', 'location': 'https://sec.example/10k',
          'date': '2025-10-31', 'confidence': 'high', 'claims': 'FY2025 revenue'}
RAKAZO_TEXT_LIMIT = 12_000  # what Rakazo passes on of one tool result's text
COVER = {'tagline': 'Devices and subscriptions', 'business_summary': 'Sells devices with subscriptions.',
         'industry': 'Consumer electronics', 'headquarters': 'Austin, TX', 'stage': 'Listed (NASDAQ: NWD)'}
VERSION = {'rating': 'Watchlist', 'data_as_of': '2026-10-28', **COVER}
LEAD, FUNDAMENTALS, REVIEWER = 'Lead Analyst', 'Fundamentals Analyst', 'IC Reviewer'


@pytest.fixture(autouse=True)
def quick_pdf(monkeypatch):
    """Versions print a PDF; a stand-in keeps these tests fast (test_report prints a real one)."""
    def fake(html_path: Path, pdf_path: Path, timeout: int = 180) -> dict:
        pdf_path.write_bytes(b'%PDF-1.4 stand-in')
        return {'pdf': str(pdf_path), 'bytes': pdf_path.stat().st_size}
    monkeypatch.setattr(report, 'write_pdf', fake)


@contextmanager
def caller(agent: str):
    token = server.CALLER.set(agent)
    try:
        yield
    finally:
        server.CALLER.reset(token)


def call(name: str, arguments: dict | None = None, agent: str | None = None):
    with caller(agent) if agent else contextmanager(lambda: (yield))():
        result = call_tool(server.server, name, arguments)
    assert not result.is_error, result_text(result)
    text = result_text(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def error(name: str, arguments: dict, agent: str | None = None) -> str:
    with caller(agent) if agent else contextmanager(lambda: (yield))():
        result = call_tool(server.server, name, arguments)
    assert result.is_error
    return result_text(result)


def save(section: str, markdown: str, agent: str | None = None) -> dict:
    return call('save_memo_part', {'section': section, 'markdown': markdown},
                agent or sections.BY_KEY[sections.section_key(section)].owner)


def listed_case(**scope) -> None:
    case_file.start_run('demo', request='Prepare an investment report on Northwind Devices (NWD).')
    call('set_case_scope', {'company': 'Northwind Devices', 'ticker': 'NWD', 'company_type': 'listed',
                            'decision': 'Watchlist or not', **scope}, LEAD)


# The tool list and its schemas

def test_every_tool_is_listed_with_text_only_results():
    tools = list_tools(server.server)
    assert {t.name for t in tools} == {
        'find_sec_company', 'get_sec_financials', 'list_sec_filings', 'read_sec_filing', 'get_price_history',
        'get_valuation_snapshot', 'get_trading_snapshot', 'get_market_regime', 'get_insider_activity',
        'search_public_records', 'search_literature', 'read_playbook', 'register_source', 'list_sources',
        'get_case_status', 'set_case_scope', 'read_client_document', 'request_user_data', 'save_evidence_block', 'get_evidence_matrix',
        'get_gate', 'save_research_plan', 'save_profile_requirements', 'save_thesis_table', 'save_scenario_analysis',
        'save_red_team_review', 'get_workflow_doc', 'save_memo_part', 'get_memo_parts', 'run_qa_loop',
        'save_memo_version', 'get_memo_check', 'start_review', 'save_review_pass', 'finish_review',
        'get_latest_review', 'deliver_memo', 'leave_note'}
    assert all(t.output_schema is None for t in tools)


def test_structured_arguments_are_spelled_out_inline():
    # Rakazo reads a schema field without a "type" as a string, and it does not follow $ref: an argument built from a
    # model must reach it as an inline object (jsonField, packages/adapters/src/pi-runtime.ts).
    tools = {t.name: t.input_schema for t in list_tools(server.server)}
    for name in ('save_evidence_block', 'save_review_pass', 'save_scenario_analysis', 'save_research_plan'):
        assert '$ref' not in json.dumps(tools[name]) and '$defs' not in json.dumps(tools[name]), name
    rows = tools['save_evidence_block']['properties']['rows']
    assert rows['type'] == 'array' and rows['items']['type'] == 'object'
    assert set(rows['items']['properties']) == {'source_ids', 'source_type', 'finding', 'mechanism', 'benchmark',
                                                'weakens', 'implication', 'confidence', 'follow_up'}
    items = tools['save_review_pass']['properties']['items']['items']
    assert items['properties']['sections']['type'] == 'array' and 'evidence_request' not in items['required']


def test_calls_are_logged_and_credited_to_the_caller(runs_dir):
    case_file.start_run('demo')
    assert call('register_source', SOURCE, FUNDAMENTALS)['id'] == 'S1'
    entry = json.loads((case_file.active_run_dir() / 'tool_log.jsonl').read_text().splitlines()[0])
    assert entry['tool'] == 'register_source' and entry['agent'] == FUNDAMENTALS
    registered = case_file.read_case()['sources'][0]
    assert (registered['registered_by'], registered['via'], registered['source_type']) == (
        FUNDAMENTALS, 'register_source', 'primary')


def test_each_call_is_credited_to_the_agent_whose_endpoint_it_came_in_on(runs_dir):
    case_file.start_run('demo')
    body = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'register_source', 'arguments': SOURCE}}
    # The base URL keeps the Host header inside the server's DNS-rebinding allowlist.
    with TestClient(server.http_app(), base_url='http://127.0.0.1:8766') as client:
        for key in ('valuation', 'red_team', 'someone-else'):
            response = client.post(f'/mcp?agent={key}', json=body,
                                   headers={'Accept': 'application/json, text/event-stream'})
            assert response.status_code == 200 and '"isError":false' in response.text
    log = [json.loads(line) for line in (case_file.active_run_dir() / 'tool_log.jsonl').read_text().splitlines()]
    assert [entry['agent'] for entry in log] == ['Valuation Analyst', 'Red Team Analyst', None]


# Data tools and sources

FILING = source('Apple 10-K FY2025', 'primary filing', 'https://sec.example/10k', '2025-10-31', 'statements',
                '10-K for FY2025')


def test_data_tools_register_what_they_retrieved_and_give_the_ids_to_cite(runs_dir, monkeypatch):
    case_file.start_run('demo')
    monkeypatch.setattr(server.sec_edgar, 'statements', lambda ticker, years: Retrieved('| Revenue |', [FILING, FILING]))
    text = call('get_sec_financials', {'ticker': 'AAPL'}, FUNDAMENTALS)
    assert text.endswith('- [S1] 10-K for FY2025, https://sec.example/10k')
    assert case_file.read_case()['sources'][0]['via'] == 'get_sec_financials'


def test_data_tools_still_answer_without_an_active_run(runs_dir, monkeypatch):
    monkeypatch.setattr(server.sec_edgar, 'statements', lambda ticker, years: Retrieved('table', [FILING]))
    assert call('get_sec_financials', {'ticker': 'AAPL'}).endswith(
        'Sources (not registered: no active run):\n- 10-K for FY2025: https://sec.example/10k')


def test_source_types_are_fixed_and_a_client_document_points_to_sources(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.pdf').write_text('deck')
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Orrin deck', 'file': 'deck.pdf', 'confidentiality': 'client-confidential'}])
    types = [call('register_source', {**SOURCE, 'source_type': kind, 'location': f'https://x.example/{n}'})['source_type']
             for n, kind in enumerate(('regulator record', 'company website', 'independent media', 'pitch deck from '
                                       'the company', 'market data', 'OCR of a scan'))]
    assert types == ['primary', 'near-primary', 'independent', 'company-provided', 'market data', 'OCR']
    assert 'source_type must be one of' in error('register_source', {**SOURCE, 'source_type': 'blog'})
    deck = call('register_source', {**SOURCE, 'source_type': 'company-provided', 'location': 'Orrin deck p.4'})
    assert case_file.read_case()['sources'][-1]['location'] == 'sources/deck.pdf p.4' and deck['id'] == 'S7'


def test_sources_are_listed_a_page_at_a_time(runs_dir):
    case_file.start_run('demo')
    for n in range(45):
        call('register_source', {**SOURCE, 'location': f'https://sec.example/{n}'})
    first, second = call('list_sources', {}), call('list_sources', {'page': 2})
    assert first.startswith('Page 1 of 2 (45 sources).') and first.count('\n| S') == 40
    assert second.count('\n| S') == 5 and '| S45 |' in second


def test_client_documents_carry_their_confidentiality_label(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.md').write_text('ARR $3.2M')
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Deck', 'file': 'deck.md', 'confidentiality': 'client-confidential'}])
    assert call('read_client_document', {'name': 'deck'}) == ('[CLIENT-CONFIDENTIAL: Deck]\ndeck.md: Markdown, 1 line. '
                                                              'Output page 1 of 1. Cite as "deck.md".\n\nARR $3.2M\n\n'
                                                              '--- End of deck.md. ---')


def test_client_documents_are_read_a_page_at_a_time_with_page_markers(runs_dir, monkeypatch):
    monkeypatch.setattr(case_file, 'ROOT', Path(__file__).resolve().parents[1] / 'src')
    case_file.start_run('demo', [{'name': 'Vantelle deck', 'file': 'fixtures/vantelle_deck.pdf',
                                  'confidentiality': 'client-confidential'}])
    first = call('read_client_document', {'name': 'Vantelle deck'})
    assert first.startswith('[CLIENT-CONFIDENTIAL: Vantelle deck]\nvantelle_deck.pdf: PDF, 15 pages.')
    assert '--- p.1 ---' in first and 'read it with page=2' in first
    assert '--- End of vantelle_deck.pdf. ---' in call('read_client_document', {'name': 'Vantelle deck', 'page': 2})


def test_longer_results_are_cut_where_rakazo_would_cut_them(runs_dir):
    case_file.start_run('demo')
    for n in range(40):
        call('register_source', {**SOURCE, 'title': 'A long title ' * 30, 'location': f'https://sec.example/{n}'})
    text = call('list_sources', {})
    assert len(text) == RAKAZO_TEXT_LIMIT and text.endswith('\n[truncated]')


# Scope, playbooks and workflow records

def test_the_scope_records_the_language_of_the_request(runs_dir):
    case_file.start_run('demo', request='帮我分析一下北风科技是否值得投资')
    scope = call('set_case_scope', {'company': '北风科技', 'ticker': '', 'company_type': 'private',
                                    'decision': '是否投资'}, LEAD)
    assert scope == {'company': '北风科技', 'ticker': None, 'type': 'private', 'decision': '是否投资', 'language': 'zh'}
    assert 'language must be' in error('set_case_scope', {'company': 'A', 'ticker': '', 'company_type': 'private',
                                                          'decision': 'x', 'language': 'fr'})


def test_playbooks_are_read_by_heading_or_listed_when_too_long():
    listing = call('read_playbook', {'name': 'company_deep_dive_playbook.md'})
    assert listing.startswith('company_deep_dive_playbook.md is') and '1.3 Equity & Cap Table' in listing
    text = call('read_playbook', {'name': 'company_deep_dive_playbook', 'heading': '1.3 equity & cap table'})
    assert text.startswith('Playbook: company_deep_dive_playbook.md > 1.3 Equity & Cap Table')
    assert '## Section 2' not in text  # stops at the next heading of the same or a higher level
    whole = call('read_playbook', {'name': 'decision_framework.md'})
    assert whole.startswith('Playbook: decision_framework.md') and '## The One Question' in whole
    assert 'No playbook' in error('read_playbook', {'name': 'README.md'})
    assert 'Headings:' in error('read_playbook', {'name': 'decision_framework.md', 'heading': 'Valuation'})


def test_workflow_records_come_back_with_their_checks(runs_dir):
    listed_case()
    plan = call('save_research_plan', {
        'spines': [{'spine': 'Public equity', 'must_answer': 'Is the market mispricing future cash flow or risk?'}],
        'industry_map': 'Devices sold through distributors; subscriptions are the profit pool.',
        'geo_lens': 'Material: US home market, EU and Japan revenue markets.', 'policy_lens': 'Not material.',
        'regulatory_databases': ['SEC EDGAR', 'FCC equipment authorization'], 'gates_done': [1, 2, 3, 4, 5],
        'hypothesis': 'Watchlist'}, LEAD)
    assert plan['failures'] == ['research plan: 5 of the 13 gates done; needs 8'] and len(plan['gates']) == 13
    profile = call('save_profile_requirements', {'items_done': list(range(1, 14)), 'evidence': 'x' * 240}, LEAD)
    assert profile['failures'] == []
    red = call('save_red_team_review', {'answers': {k: 'An answer naming the receivables trend in the filing. ' * 2
                                                    for k in check_workflow_docs.RED_TEAM_QUESTIONS},
                                        'weakest_section': 's7'}, 'Red Team Analyst')
    assert red['failures'] == [] and case_file.read_case()['workflow']['red_team_review']['weakest_section'] == 'financials'
    assert '"author": "Red Team Analyst"' in call('get_workflow_doc', {'kind': 'red_team_review'})
    assert 'kind must be one of' in error('get_workflow_doc', {'kind': 'notes'})


def test_user_data_requests_are_kept_for_the_report(runs_dir):
    listed_case()
    request = call('request_user_data', {'database': 'FCC equipment authorization', 'query': 'NWD-2 grant date',
                                         'why': 'The launch needs it', 'how': 'Search fccid.io', 'section': 's9'},
                   'Regulatory Analyst')
    assert request == {'id': 'U1', 'section': 'strategy'}
    assert 'U1 (strategy, Regulatory Analyst): FCC equipment authorization' in call('get_workflow_doc',
                                                                                     {'kind': 'user_data_requests'})


# The evidence matrix and the gate

ROW = {'source_ids': 'S1, S2', 'source_type': 'primary', 'finding': 'Gross margin rose to 41.3% in FY2025 from 39.6%.',
       'mechanism': 'Subscriptions carry a 78% margin, so mix shift lifts the blend.',
       'benchmark': 'Peer median gross margin is 36.5%.', 'weakens': 'Hardware margin fell to 28.1%.',
       'implication': 'Supports quality but not a discount valuation.', 'confidence': 'high',
       'follow_up': 'Is the attach rate durable past FY2026?'}
PLAN = {key: f'A specific {key} for this section' for key in check_evidence.PLAN_FIELDS}


def register_sources(count: int = 9) -> None:
    for n in range(1, count + 1):
        call('register_source', {**SOURCE, 'source_type': 'primary filing' if n < 3 else 'independent media',
                                 'location': f'https://x.example/{n}'}, FUNDAMENTALS)


def test_an_evidence_block_reports_its_gate_and_the_gate_covers_your_sections(runs_dir):
    listed_case()
    register_sources()
    saved = call('save_evidence_block', {'section': 'financials', 'queries': ['a', 'b', 'c', 'd'], 'rows': [ROW] * 4,
                                         'gate_done': list(range(1, 10)), 'plan': PLAN}, FUNDAMENTALS)
    assert saved['gate_passed'] and saved['owner'] == FUNDAMENTALS
    thin = call('save_evidence_block', {'section': 's6', 'queries': ['a'], 'rows': [ROW], 'gate_done': [1],
                                        'plan': PLAN}, FUNDAMENTALS)
    assert not thin['gate_passed'] and '1 search queries; needs 4 targeted ones' in thin['gate_failures']
    gate = call('get_gate', {}, FUNDAMENTALS)
    assert set(gate['sections']) == {'business_model', 'financials'}
    assert gate['sections']['financials']['passed'] and not gate['sections']['business_model']['passed']
    assert len(call('get_gate', {}, LEAD)['sections']) == 14
    assert '| 财务分析 Financial Analysis | financials | Fundamentals Analyst | Fundamentals Analyst | 4 | 4 | passed |' in call(
        'get_evidence_matrix', {})
    assert 'error' not in call('get_evidence_matrix', {'sections_wanted': ['s7']})
    assert 'needs no evidence block' in error('save_evidence_block', {'section': 'executive_summary', 'queries': [],
                                                                       'rows': [], 'gate_done': [], 'plan': PLAN})


# Sections

def test_a_saved_section_comes_back_with_its_check_and_whether_its_evidence_came_first(runs_dir):
    listed_case()
    for n in range(1, 9):
        call('register_source', {**SOURCE, 'location': f'https://x.example/{n}',
                                 'source_type': 'market data' if n == 3 else 'independent media' if n > 4 else 'primary'})
    early = save('financials', FINANCIALS)
    assert early['check']['passed'] and early['owner'] == FUNDAMENTALS
    assert early['note'] == 'This section has no passing evidence block yet: draft only from a completed one.'
    assert case_file.read_case()['memo_parts']['financials'][0]['evidence_before_draft'] is False
    summary = save('executive_summary', EXECUTIVE_SUMMARY)
    assert summary['check']['passed'] and 'note' not in summary


def test_unknown_oversized_and_broken_sections_are_explained(runs_dir):
    listed_case()
    assert 'No section' in error('save_memo_part', {'section': 'valuation', 'markdown': 'x'})
    assert 'at most 9,000' in error('save_memo_part', {'section': 's7', 'markdown': 'x' * 9_001})
    broken = save('s7', '::: kpi\nno table\n:::\n\nText [S1].')
    assert broken['check']['depth'][0].startswith('component: "::: kpi" needs a Markdown table')


def test_sections_come_back_whole_or_the_reader_is_asked_for_fewer(runs_dir):
    listed_case()
    save('financials', FINANCIALS)
    save('scoring', SCORING)
    listing = call('get_memo_parts', {})
    assert '| 7 | 财务分析 Financial Analysis | financials | Fundamentals Analyst | revision 1 by Fundamentals Analyst |' in listing
    assert '| 4 | 市场与行业分析 Market & Industry Analysis | market | Market Analyst | not saved | | |' in listing
    assert call('get_memo_parts', {'sections_wanted': ['s7']}).endswith(FINANCIALS.strip())
    save('financials', FINANCIALS + '\n' + 'More analysis. ' * 200)
    save('scoring', SCORING + '\n' + 'More scoring. ' * 300)
    assert 'Ask for fewer' in error('get_memo_parts', {'sections_wanted': ['financials', 'scoring']})


def test_a_section_saved_again_and_again_gets_a_note(runs_dir):
    listed_case()
    first, second = save('risk', 'Too short [S1].'), save('risk', 'Still too short [S1].')
    assert 'This is your save' not in first.get('note', '') + second.get('note', '')
    assert save('risk', 'Short again [S1].')['note'].endswith(
        'Rather than saving again, state what is still open as a limitation in the section.')


# The QA loop, versions and delivery

def test_the_composite_score_is_section_14s_weighted_average():
    assert server.composite_score(SCORING) == ('6.7', [])
    wrong = server.composite_score(SCORING.replace('composite score is 6.7', 'composite score is 7.4'))
    assert wrong[1] == ['the stated composite 7.4 is not the weighted average 6.7']
    assert server.composite_score('No table.')[0] is None


def test_the_qa_loop_writes_a_rewrite_plan_for_each_failing_section(runs_dir):
    listed_case()
    save('financials', 'Too short [S1].')
    loop = call('run_qa_loop', {}, LEAD)
    assert not loop['passed'] and 'financials' in loop['sections']
    assert 'financials' in loop['rewrite_items_by_owner'][FUNDAMENTALS] and loop['required_fixes']
    workflow = case_file.read_case()['workflow']
    assert workflow['iteration_log'][0]['passed'] is False and workflow['rewrite_plan'][0]['owner'] == FUNDAMENTALS
    # A second loop does not make the open plan an item of its own.
    call('run_qa_loop', {}, LEAD)
    assert not any(item['problems'][0].startswith('rewrite plan:')
                   for item in case_file.read_case()['workflow']['rewrite_plan'])


def test_a_version_is_rendered_checked_and_never_changes(runs_dir):
    listed_case()
    save('financials', FINANCIALS)
    save('scoring', SCORING)
    version = call('save_memo_version', VERSION, LEAD)
    assert (version['version'], version['composite_score']) == (1, '6.7')
    html = Path(version['files']['html']).read_text()
    assert 'Northwind Devices' in html and '<meta name="composite-score" content="6.7">' in html
    assert Path(version['files']['pdf']).exists() and Path(version['files']['markdown']).read_text().startswith(
        '# Northwind Devices')
    assert not version['check']['passed'] and 'missing sections' in ' '.join(version['check']['report'])
    save('financials', FINANCIALS.replace('4.8%', '4.9%'))
    second = call('save_memo_version', VERSION, LEAD)
    assert second['changed_parts'] == ['financials']
    assert call('get_memo_parts', {'sections_wanted': ['s7'], 'version': 1}).endswith(FINANCIALS.strip())
    assert call('get_memo_check', {'version': 1})['checked'] == 'version 1'


def test_ratings_follow_the_company_type(runs_dir):
    listed_case()
    assert 'Hold off' in error('save_memo_version', {**VERSION, 'rating': 'Invest now'}, LEAD)
    case_file.start_run('demo')
    call('set_case_scope', {'company': 'Orrin', 'ticker': '', 'company_type': 'private', 'decision': 'Series A'}, LEAD)
    assert call('save_memo_version', {**VERSION, 'rating': 'Wait for milestone'}, LEAD)['version'] == 1


def test_the_review_takes_five_passes_and_routes_items_to_owners(runs_dir):
    listed_case()
    call('save_memo_version', VERSION, LEAD)
    review = call('start_review', {'memo_version': 1}, REVIEWER)
    assert review['review_id'] == 'R1' and review['passes']['5'] == 'Number stress-test'
    # A version saved while a review is under way says so; it is still saved.
    second = call('save_memo_version', VERSION, LEAD)
    assert second['version'] == 2 and second['note'].startswith('Review R1 of version 1 is still under way')
    call('save_review_pass', {'review_id': 'R1', 'pass_number': 1, 'items': [
        {'severity': 'critical', 'sections': ['s7', 'scoring'], 'issue': 'No debt maturity table.',
         'action': 'Read the 10-K debt note.', 'evidence_request': 'Debt maturities by year'}]}, REVIEWER)
    call('save_review_pass', {'review_id': 'R1', 'pass_number': 3, 'items': [
        {'severity': 'Minor', 'sections': ['competition'], 'issue': 'Name Garmin.', 'action': 'Add it.'}]}, REVIEWER)
    assert 'Save every pass first' in error('finish_review', {'review_id': 'R1', 'verdict': 'revise', 'grade': 'C',
                                                               'top_three': [], 'ready': 'No'}, REVIEWER)
    for n in (2, 4, 5):
        call('save_review_pass', {'review_id': 'R1', 'pass_number': n, 'items': [], 'notes': f'pass {n} notes'}, REVIEWER)
    assert '1 Critical items are open' in error('finish_review', {'review_id': 'R1', 'verdict': 'approve', 'grade': 'B',
                                                                   'top_three': [], 'ready': 'Yes'}, REVIEWER)
    finished = call('finish_review', {'review_id': 'R1', 'verdict': 'revise', 'grade': 'c',
                                      'top_three': ['Debt maturities', 'Peer set', 'Attach rate'], 'ready': 'With fixes'},
                    REVIEWER)
    assert finished['revisions_requested_from'] == [FUNDAMENTALS, LEAD]
    assert finished['items'] == {'Critical': 1, 'Important': 0, 'Minor': 1}
    text = call('get_latest_review', {})
    assert text.startswith('Review R1 of report version 1 (round 1 of 3): verdict revise, depth grade C')
    assert '- [Critical, pass 1] financials, scoring: No debt maturity table. Fix: Read the 10-K debt note. Evidence ' \
           'request: Debt maturities by year' in text
    assert 'Pass 5 (Number stress-test): pass 5 notes' in text
    assert 'is finished' in error('save_review_pass', {'review_id': 'R1', 'pass_number': 1, 'items': []}, REVIEWER)


def test_a_review_needs_items_unless_it_approves_and_reopening_keeps_the_round(runs_dir):
    listed_case()
    call('save_memo_version', VERSION, LEAD)
    call('start_review', {'memo_version': 1}, REVIEWER)
    for n in range(1, 6):
        call('save_review_pass', {'review_id': 'R1', 'pass_number': n, 'items': []}, REVIEWER)
    assert 'needs at least one Critical or Important item' in error(
        'finish_review', {'review_id': 'R1', 'verdict': 'revise', 'grade': 'B', 'top_three': [], 'ready': 'No'}, REVIEWER)
    call('finish_review', {'review_id': 'R1', 'verdict': 'approve', 'grade': 'B', 'top_three': [], 'ready': 'Yes'},
         REVIEWER)
    again = call('start_review', {'memo_version': 1}, REVIEWER)
    assert (again['review_id'], again['round']) == ('R1', 1) and len(case_file.read_case()['reviews']) == 1


def test_delivery_writes_the_folder_records_the_gate_and_never_blocks(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.pdf').write_text('deck')
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Deck', 'file': 'deck.pdf', 'confidentiality': 'client-confidential'}])
    call('set_case_scope', {'company': 'Northwind Devices', 'ticker': 'NWD', 'company_type': 'listed',
                            'decision': 'x'}, LEAD)
    save('financials', FINANCIALS)
    call('save_memo_version', VERSION, LEAD)
    delivered = call('deliver_memo', {}, LEAD)
    assert delivered['review_gate'] == {'reviewed': False, 'approved': False, 'review_id': None}
    assert not delivered['final_check']['passed'] and delivered['note'] == 'Report only: delivery is never blocked.'
    folder = Path(delivered['folder'])
    assert folder.name == 'NorthwindDevices_ConsumerElectronics'
    assert sorted(p.name for p in folder.iterdir()) == ['NorthwindDevices_Investment_Report.html',
                                                         'NorthwindDevices_Investment_Report.pdf', 'sources']
    assert (folder / 'sources' / 'deck.pdf').exists() and delivered['final_check']['output'] == []
    record = case_file.read_case()['deliveries'][0]
    assert record['memo_version'] == 1 and (case_file.active_run_dir() / 'memo_v1.md').exists()


def a_case_with_a_source() -> str:
    case_file.start_run('demo')
    return call('register_source', SOURCE, 'Valuation Analyst')['id']


def test_a_note_goes_to_the_sections_owner_and_reaches_it_once_through_its_next_section_tool():
    source = a_case_with_a_source()
    left = call('leave_note', {'note': 'Capex is $12.7B in my table, $9.4B in yours.', 'section': 's7', 'source_ids': [source]},
                'Valuation Analyst')
    assert (left['id'], left['to'], left['section']) == ('N1', FUNDAMENTALS, 'financials')
    assert 'notes_for_you' not in left
    # It wakes nobody and changes nothing; another agent's tools do not carry it.
    assert 'notes_for_you' not in call('register_source', {**SOURCE, 'location': 'https://sec.example/other'}, 'Market Analyst')
    first = call('register_source', {**SOURCE, 'location': 'https://sec.example/mine'}, FUNDAMENTALS)
    assert first['notes_for_you'] == [{'id': 'N1', 'from': 'Valuation Analyst', 'section': 'financials',
                                       'note': 'Capex is $12.7B in my table, $9.4B in yours.', 'source_ids': [source],
                                       'answers': None}]
    assert 'answer it with leave_note' in first['notes_next']
    assert 'notes_for_you' not in call('register_source', {**SOURCE, 'location': 'https://sec.example/again'}, FUNDAMENTALS)


def test_each_section_tool_can_carry_a_note():
    source = a_case_with_a_source()
    for tool, arguments in (('get_gate', {}), ('save_memo_part', {'section': 'financials', 'markdown': 'Short [S1].'}),
                            ('get_memo_check', {'section': 'financials'})):
        call('leave_note', {'note': f'About {tool}.', 'section': 'financials', 'source_ids': [source]}, 'Valuation Analyst')
        assert [note['note'] for note in call(tool, arguments, FUNDAMENTALS)['notes_for_you']] == [f'About {tool}.']


def test_an_answer_closes_the_note_and_reaches_its_author():
    source = a_case_with_a_source()
    call('leave_note', {'note': 'Capex differs.', 'section': 'financials', 'source_ids': [source]}, 'Valuation Analyst')
    assert [(n['id'], n['to'], n['seen']) for n in call('get_case_status', agent=LEAD)['open_notes']] == [('N1', FUNDAMENTALS, False)]
    answer = call('leave_note', {'note': 'You are right; corrected in revision 2.', 'answers': 'N1'}, FUNDAMENTALS)
    assert (answer['id'], answer['to'], answer['section']) == ('N2', 'Valuation Analyst', 'financials')
    assert answer['notes_for_you'][0]['id'] == 'N1'  # A bot answering from the Lead's brief has now seen it too.
    assert call('get_case_status', agent=LEAD)['open_notes'] == []
    back = call('register_source', {**SOURCE, 'location': 'https://sec.example/next'}, 'Valuation Analyst')
    assert [(n['id'], n['answers']) for n in back['notes_for_you']] == [('N2', 'N1')]
    assert 'notes_next' not in back  # An answer needs no answer.


def test_a_note_that_cannot_be_checked_or_has_no_one_to_go_to_is_explained():
    source = a_case_with_a_source()
    note = {'note': 'Capex differs.', 'section': 'financials', 'source_ids': [source]}
    assert 'a note holds at most 600' in error('leave_note', {**note, 'note': 'x' * 601}, 'Valuation Analyst')
    assert 'needs text' in error('leave_note', {**note, 'note': ' '}, 'Valuation Analyst')
    assert 'Name the section' in error('leave_note', {'note': 'Capex differs.'}, 'Valuation Analyst')
    assert 'No section' in error('leave_note', {**note, 'section': 'nothing'}, 'Valuation Analyst')
    assert 'at least one registered source' in error('leave_note', {**note, 'source_ids': []}, 'Valuation Analyst')
    assert 'Not in the source register: S99' in error('leave_note', {**note, 'source_ids': ['S99']}, 'Valuation Analyst')
    assert 'is yours' in error('leave_note', note, FUNDAMENTALS)
    assert "the Lead Analyst's" in error('leave_note', {**note, 'section': 'thesis'}, 'Valuation Analyst')
    assert 'There is no note N7' in error('leave_note', {'note': 'Fixed.', 'answers': 'N7'}, FUNDAMENTALS)
    call('leave_note', note, 'Valuation Analyst')
    assert f'for {FUNDAMENTALS}, not for you' in error('leave_note', {'note': 'Fixed.', 'answers': 'N1'}, 'Market Analyst')


def test_the_qa_loop_lists_the_notes_still_open():
    listed_case()
    source = call('register_source', SOURCE, 'Valuation Analyst')['id']
    call('leave_note', {'note': 'Capex differs.', 'section': 'financials', 'source_ids': [source]}, 'Valuation Analyst')
    assert call('run_qa_loop', agent=LEAD)['open_notes'] == [
        {'id': 'N1', 'from': 'Valuation Analyst', 'to': FUNDAMENTALS, 'section': 'financials'}]
