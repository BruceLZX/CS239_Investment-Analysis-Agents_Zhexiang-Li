import json

from starlette.testclient import TestClient

from tools import case_file, server

from .helpers import call_tool, list_tools, result_text

MEMO = 'Rating: Watchlist\nRevenue grew 6% [S1].\nData as of 2026-10-23. For research purposes only; not investment advice.'
DRAFT = {'markdown': MEMO, 'rating': 'Watchlist', 'data_as_of': '2026-10-23'}
SOURCE = {'title': 'Apple 10-K FY2025', 'source_type': 'primary filing', 'location': 'https://sec.example/10k',
          'date': '2025-10-31', 'confidence': 'high', 'claims': 'FY2025 revenue'}
RAKAZO_TEXT_LIMIT = 12_000  # what Rakazo passes on of one tool result's text


def memo_of(length: int) -> str:
    return (MEMO + '\n' + 'More analysis. ' * length)[:length]


def memo_room() -> int:
    """How much memo fits in one get_memo_draft result after its header line."""
    return server.MAX_RESULT - len(server._memo_text({'version': 1, **DRAFT, 'markdown': ''}))


def test_every_tool_is_listed_with_text_only_results():
    tools = list_tools(server.server)
    names = {t.name for t in tools}
    assert len(tools) == 16
    assert {'register_source', 'get_case_status', 'get_memo_check', 'deliver_memo'} <= names
    assert 'share_memo' not in names
    assert all(t.output_schema is None for t in tools)


def test_calls_are_logged_to_the_active_run(runs_dir):
    case_file.start_run('demo')
    result = call_tool(server.server, 'register_source', SOURCE)
    assert json.loads(result_text(result)) == {'id': 'S1', 'cite_as': '[S1]'}
    entry = json.loads((case_file.active_run_dir() / 'tool_log.jsonl').read_text().splitlines()[0])
    assert entry['tool'] == 'register_source' and entry['arguments']['title'] == 'Apple 10-K FY2025'


def test_error_messages_reach_the_model(runs_dir):
    case_file.start_run('demo')
    result = call_tool(server.server, 'save_memo_draft', {**DRAFT, 'rating': 'Strong buy'})
    assert result.is_error
    assert 'rating must be one of' in result_text(result)


def test_private_company_ratings_are_accepted(runs_dir):
    case_file.start_run('demo')
    assert not call_tool(server.server, 'save_memo_draft', {**DRAFT, 'rating': 'Invest'}).is_error


def test_reviews_need_a_known_verdict(runs_dir):
    case_file.start_run('demo')
    call_tool(server.server, 'save_memo_draft', DRAFT)
    result = call_tool(server.server, 'save_review', {'memo_version': 1, 'verdict': 'looks fine',
                                                       'must_fix': [], 'should_fix': []})
    assert result.is_error and 'verdict must be' in result_text(result)


def test_client_documents_carry_their_confidentiality_label(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.md').write_text('ARR $3.2M')
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Deck', 'file': 'deck.md', 'confidentiality': 'client-confidential'}])
    assert result_text(call_tool(server.server, 'read_client_document', {'name': 'deck'})) == \
        '[CLIENT-CONFIDENTIAL: Deck]\nARR $3.2M'


def test_memo_check_reports_rule_findings(runs_dir):
    case_file.start_run('demo')
    call_tool(server.server, 'save_memo_draft', {**DRAFT, 'markdown': MEMO + ' [S7]'})
    report = json.loads(result_text(call_tool(server.server, 'get_memo_check', {})))
    assert [f['rule'] for f in report['findings']] == ['N1']


def test_delivery_records_the_review_gate_but_never_blocks(runs_dir):
    case_file.start_run('demo')
    call_tool(server.server, 'save_memo_draft', DRAFT)
    unreviewed = json.loads(result_text(call_tool(server.server, 'deliver_memo', {})))
    assert unreviewed['delivered_version'] == 1
    assert unreviewed['review_gate'] == {'reviewed': False, 'approved': False, 'review_id': None}
    call_tool(server.server, 'save_review', {'memo_version': 1, 'verdict': 'approve', 'must_fix': [], 'should_fix': []})
    approved = json.loads(result_text(call_tool(server.server, 'deliver_memo', {'version': 1})))
    assert approved['review_gate'] == {'reviewed': True, 'approved': True, 'review_id': 'R1'}
    assert (case_file.active_run_dir() / 'memo_v1.md').exists()
    assert len(case_file.read_case()['deliveries']) == 2


def test_a_memo_that_fits_one_tool_result_comes_back_whole(runs_dir):
    # Phase 1 cut every result at 6,000 characters, so the IC Reviewer read each 6,000-10,000-character memo cut off.
    case_file.start_run('demo')
    markdown = memo_of(memo_room())
    assert len(markdown) > 10_064  # the longest memo in the Phase 1 traces
    assert not call_tool(server.server, 'save_memo_draft', {**DRAFT, 'markdown': markdown}).is_error
    text = result_text(call_tool(server.server, 'get_memo_draft', {}))
    assert text.endswith(markdown) and len(text) <= RAKAZO_TEXT_LIMIT


def test_a_memo_too_long_to_read_whole_is_refused(runs_dir):
    case_file.start_run('demo')
    result = call_tool(server.server, 'save_memo_draft', {**DRAFT, 'markdown': memo_of(memo_room() + 1)})
    assert result.is_error and 'could not read it whole' in result_text(result)
    assert case_file.read_case()['memo_drafts'] == []


PACKET = {'topic': 'BYD vs Tesla', 'summary': 'BEV volumes', 'findings': ['BYD sold 2.26M BEVs in 2025 [S1]'],
          'source_ids': ['S1'], 'counter_evidence': 'Tesla margins are higher', 'gaps': []}


def test_each_call_is_credited_to_the_agent_whose_endpoint_it_came_in_on(runs_dir):
    case_file.start_run('demo')
    body = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'save_evidence_packet', 'arguments': PACKET}}
    # The base URL keeps the Host header inside the server's DNS-rebinding allowlist.
    with TestClient(server.http_app(), base_url='http://127.0.0.1:8766') as client:
        for key in ('market', 'fundamentals', 'someone-else'):
            response = client.post(f'/mcp?agent={key}', json=body,
                                   headers={'Accept': 'application/json, text/event-stream'})
            assert response.status_code == 200 and '"isError":false' in response.text
    log = [json.loads(line) for line in (case_file.active_run_dir() / 'tool_log.jsonl').read_text().splitlines()]
    assert [entry['agent'] for entry in log] == ['Market Analyst', 'Fundamentals Analyst', None]
    assert [p['analyst'] for p in case_file.read_case()['evidence_packets']] == [
        'Market Analyst', 'Fundamentals Analyst', None]


def test_a_packet_saved_after_a_review_answers_its_evidence_requests(runs_dir):
    case_file.start_run('demo')
    token = server.CALLER.set('Market Analyst')
    try:
        call_tool(server.server, 'save_evidence_packet', PACKET)
        call_tool(server.server, 'save_memo_draft', DRAFT)
        review = call_tool(server.server, 'save_review', {
            'memo_version': 1, 'verdict': 'revise', 'must_fix': ['Compare BEVs with BEVs'], 'should_fix': [],
            'market_requests': ["BYD's 2025 BEV-only sales"]})
        follow_up = call_tool(server.server, 'save_evidence_packet', PACKET)
    finally:
        server.CALLER.reset(token)
    assert json.loads(result_text(review)) == {'id': 'R1', 'evidence_requested_from': ['Market Analyst']}
    assert json.loads(result_text(follow_up))['follow_up_for'] == 'R1'
    assert result_text(call_tool(server.server, 'get_latest_review', {})).endswith(
        "Evidence requests:\n- Market Analyst: BYD's 2025 BEV-only sales")
    packets = result_text(call_tool(server.server, 'get_evidence_packets', {}))
    assert '## E1 (Market Analyst): BYD vs Tesla' in packets
    assert '## E2 (Market Analyst, follow-up for review R1): BYD vs Tesla' in packets


def test_a_review_without_evidence_requests_says_so(runs_dir):
    case_file.start_run('demo')
    call_tool(server.server, 'save_memo_draft', DRAFT)
    call_tool(server.server, 'save_review', {'memo_version': 1, 'verdict': 'approve', 'must_fix': [], 'should_fix': []})
    assert result_text(call_tool(server.server, 'get_latest_review', {})).endswith('Evidence requests: none')


def test_longer_results_are_cut_where_rakazo_would_cut_them(runs_dir):
    case_file.start_run('demo')
    call_tool(server.server, 'save_evidence_packet', {'topic': 'Long', 'summary': 'x' * 20_000, 'findings': [],
                                                       'source_ids': [], 'counter_evidence': '', 'gaps': []})
    text = result_text(call_tool(server.server, 'get_evidence_packets', {}))
    assert len(text) == RAKAZO_TEXT_LIMIT and text.endswith('\n[truncated]')
