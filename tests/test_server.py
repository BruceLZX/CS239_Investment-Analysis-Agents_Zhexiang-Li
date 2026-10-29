from contextlib import contextmanager
import json

from starlette.testclient import TestClient

from tools import case_file, memo, server
from tools.retrieved import Retrieved, source

from .helpers import call_tool, list_tools, result_text

SOURCE = {'title': 'Apple 10-K FY2025', 'source_type': 'primary filing', 'location': 'https://sec.example/10k',
          'date': '2025-10-31', 'confidence': 'high', 'claims': 'FY2025 revenue'}
RAKAZO_TEXT_LIMIT = 12_000  # what Rakazo passes on of one tool result's text
VERSION = {'rating': 'Watchlist', 'data_as_of': '2026-10-28'}


@contextmanager
def caller(agent: str):
    token = server.CALLER.set(agent)
    try:
        yield
    finally:
        server.CALLER.reset(token)


def call(name: str, arguments: dict | None = None):
    result = call_tool(server.server, name, arguments)
    assert not result.is_error, result_text(result)
    text = result_text(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def save_part(part: str, markdown: str, agent: str | None = None) -> dict:
    with caller(agent or memo.PART_BY_KEY[part].owner):
        return call('save_memo_part', {'part': part, 'markdown': markdown})


def test_every_tool_is_listed_with_text_only_results():
    tools = list_tools(server.server)
    assert {t.name for t in tools} == {
        'find_sec_company', 'get_sec_financials', 'list_sec_filings', 'read_sec_filing', 'get_price_history',
        'get_valuation_snapshot', 'register_source',
        'list_sources', 'get_case_status', 'set_case_scope', 'read_client_document', 'save_evidence_packet',
        'get_evidence_packets', 'save_memo_part', 'get_memo_parts', 'save_memo_version', 'get_memo_check',
        'save_review', 'get_latest_review', 'deliver_memo'}
    assert all(t.output_schema is None for t in tools)
    # Rakazo passes only plain types through to the model: review items are strings, not objects.
    review = next(t for t in tools if t.name == 'save_review').input_schema
    assert '$defs' not in review and review['properties']['must_fix']['items'] == {'type': 'string'}


def test_calls_are_logged_to_the_active_run(runs_dir):
    case_file.start_run('demo')
    with caller('Fundamentals Analyst'):
        assert call('register_source', SOURCE) == {'id': 'S1', 'cite_as': '[S1]'}
    entry = json.loads((case_file.active_run_dir() / 'tool_log.jsonl').read_text().splitlines()[0])
    assert entry['tool'] == 'register_source' and entry['arguments']['title'] == 'Apple 10-K FY2025'
    registered = case_file.read_case()['sources'][0]
    assert (registered['registered_by'], registered['via']) == ('Fundamentals Analyst', 'register_source')


FILING = source('Apple 10-K FY2025', 'primary filing', 'https://sec.example/10k', '2025-10-31', 'statements',
                '10-K for FY2025')
PRICES = source('Yahoo AAPL', 'market data', 'https://finance.yahoo.com/quote/AAPL', '2026-10-28', 'price',
                'Yahoo chart for AAPL', confidence='medium')


def test_data_tools_register_what_they_retrieved_and_give_the_ids_to_cite(runs_dir, monkeypatch):
    case_file.start_run('demo')
    monkeypatch.setattr(server.sec_edgar, 'statements',
                        lambda ticker, years: Retrieved('| Revenue | 416,161M |', [FILING, FILING]))
    with caller('Fundamentals Analyst'):
        text = call('get_sec_financials', {'ticker': 'AAPL'})
    assert text == ('| Revenue | 416,161M |\n\nSources registered for you (cite these IDs; do not register them again):\n'
                    '- [S1] 10-K for FY2025, https://sec.example/10k')
    [registered] = case_file.read_case()['sources']
    assert (registered['registered_by'], registered['via'], registered['confidence']) == (
        'Fundamentals Analyst', 'get_sec_financials', 'high')
    monkeypatch.setattr(server.prices, 'price_summary', lambda ticker, period: Retrieved('AAPL 347.73', [PRICES]))
    assert call('get_price_history', {'ticker': 'AAPL'}).endswith(
        '- [S2] Yahoo chart for AAPL, https://finance.yahoo.com/quote/AAPL')


def test_data_tools_still_answer_without_an_active_run(runs_dir, monkeypatch):
    monkeypatch.setattr(server.sec_edgar, 'statements', lambda ticker, years: Retrieved('table', [FILING]))
    assert call('get_sec_financials', {'ticker': 'AAPL'}).endswith(
        'Sources (not registered: no active run):\n- 10-K for FY2025: https://sec.example/10k')


def test_error_messages_reach_the_model(runs_dir):
    case_file.start_run('demo')
    result = call_tool(server.server, 'save_memo_version', {**VERSION, 'rating': 'Strong buy'})
    assert result.is_error
    assert 'rating must be one of' in result_text(result)


def test_private_company_ratings_are_accepted(runs_dir):
    case_file.start_run('demo')
    assert call('save_memo_version', {**VERSION, 'rating': 'Invest'})['version'] == 1


def test_reviews_need_a_known_verdict(runs_dir):
    case_file.start_run('demo')
    call('save_memo_version', VERSION)
    result = call_tool(server.server, 'save_review', {'memo_version': 1, 'verdict': 'looks fine',
                                                       'must_fix': [], 'should_fix': []})
    assert result.is_error and 'verdict must be' in result_text(result)


def test_client_documents_carry_their_confidentiality_label(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.md').write_text('ARR $3.2M')
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Deck', 'file': 'deck.md', 'confidentiality': 'client-confidential'}])
    assert call('read_client_document', {'name': 'deck'}) == '[CLIENT-CONFIDENTIAL: Deck]\nARR $3.2M'


def test_the_scope_sets_the_header_and_each_parts_standard(runs_dir):
    case_file.start_run('demo')
    with caller('Lead Analyst'):
        scope = call('set_case_scope', {'company': 'Orrin Fieldworks', 'ticker': 'private',
                                        'company_type': 'private', 'decision': 'Series A: invest or pass'})
    assert scope == {'company': 'Orrin Fieldworks', 'ticker': None, 'type': 'private',
                     'decision': 'Series A: invest or pass'}
    check = save_part('valuation', 'The round values the company at $40M post-money [S1].')['check']
    assert 'does not cover dilution' in check['depth'] and 'does not cover trading snapshot' not in check['depth']
    version = call('save_memo_version', {**VERSION, 'rating': 'Wait'})
    assert case_file.read_case()['memo_drafts'][0]['markdown'].startswith('# Orrin Fieldworks (private): investment memo')
    assert version['missing_parts'] == [p.key for p in memo.PARTS if p.key != 'valuation']
    call('set_case_scope', {'company': 'Orrin', 'ticker': '', 'company_type': 'listed', 'decision': 'x'})
    assert case_file.read_case()['scope_changes'][0]['company'] == 'Orrin Fieldworks'


def test_a_saved_part_comes_back_with_its_check_and_author(runs_dir):
    case_file.start_run('demo')
    first = save_part('competition', '## Competition and market\nApple held 19.4% of shipments [S9].')
    assert (first['part'], first['revision'], first['owner'], first['saved_by']) == (
        'competition', 1, 'Market Analyst', 'Market Analyst')
    assert first['check']['findings'][0]['rule'] == 'N1' and not first['check']['passed']
    assert any('the floor is 2,500' in problem for problem in first['check']['depth'])
    assert 'no scope yet' in first['note']
    second = save_part('competition', 'Revised.', agent='Lead Analyst')
    assert (second['revision'], second['saved_by']) == (2, 'Lead Analyst')
    revisions = case_file.read_case()['memo_parts']['competition']
    assert [r['markdown'] for r in revisions] == ['Apple held 19.4% of shipments [S9].', 'Revised.']


def test_unknown_and_oversized_parts_are_refused(runs_dir):
    case_file.start_run('demo')
    unknown = call_tool(server.server, 'save_memo_part', {'part': 'summary', 'markdown': 'x'})
    assert unknown.is_error and 'executive_summary, business' in result_text(unknown)
    too_long = call_tool(server.server, 'save_memo_part', {'part': 'business', 'markdown': 'x' * 9_001})
    assert too_long.is_error and 'at most 9,000' in result_text(too_long)
    assert case_file.read_case()['memo_parts'] == {}


def test_parts_come_back_whole_or_the_reader_is_asked_for_fewer(runs_dir):
    case_file.start_run('demo')
    for part in ('business', 'financials', 'valuation'):
        save_part(part, f'{part} ' + 'analysis ' * 600)
    two = call('get_memo_parts', {'parts': ['business', 'financials']})
    assert two.count('## ') == 2 and two.endswith('financials ' + ('analysis ' * 600).strip())
    assert len(two) <= server.MAX_READ
    three = call_tool(server.server, 'get_memo_parts', {'parts': ['business', 'financials', 'valuation']})
    assert three.is_error and 'Ask for fewer parts' in result_text(three)
    index = call('get_memo_parts', {})
    assert '| Business | business | Market Analyst | revision 1 by Market Analyst | 5,408 | problems |' in index
    assert '| Scenarios | scenarios | Lead Analyst | not saved | | |' in index


def test_a_version_is_a_snapshot_that_never_changes(runs_dir):
    case_file.start_run('demo')
    save_part('business', 'Apple sells phones.')
    save_part('takeaways', '1. Services grew 13% [S1].')
    first = call('save_memo_version', VERSION)
    assert (first['version'], first['changed_parts']) == (1, ['business', 'takeaways'])
    save_part('business', 'Apple sells phones and services.')
    assert call('get_memo_parts', {'parts': ['business'], 'version': 1}).endswith('\nApple sells phones.')
    assert call('get_memo_parts', {'parts': ['business']}).endswith('\nApple sells phones and services.')
    second = call('save_memo_version', VERSION)
    assert (second['version'], second['changed_parts']) == (2, ['business'])
    versions = case_file.read_case()['memo_drafts']
    assert 'Apple sells phones.\n' in versions[0]['markdown'] and 'and services' in versions[1]['markdown']
    assert versions[0]['parts']['business']['revision'] == 1 and versions[1]['parts']['business']['revision'] == 2


def test_the_memo_check_covers_one_part_or_the_whole_memo(runs_dir):
    case_file.start_run('demo')
    save_part('business', 'Apple sells phones to 1.5 billion users [S7].')
    part = call('get_memo_check', {'part': 'business'})
    assert part['checked'] == 'business, parts as saved now' and part['findings'][0]['rule'] == 'N1'
    now = call('get_memo_check', {})
    assert now['part_rule_findings'] == {'business': ['N1']}
    assert now['memo_depth'][0].startswith('missing parts: Executive summary, Financials')
    call('save_memo_version', VERSION)
    assert call('get_memo_check', {'version': 1})['checked'] == 'version 1'


def test_delivery_records_the_review_gate_but_never_blocks(runs_dir):
    case_file.start_run('demo')
    call('save_memo_version', VERSION)
    unreviewed = call('deliver_memo', {})
    assert unreviewed['delivered_version'] == 1
    assert unreviewed['review_gate'] == {'reviewed': False, 'approved': False, 'review_id': None}
    call('save_review', {'memo_version': 1, 'verdict': 'approve', 'must_fix': [], 'should_fix': []})
    approved = call('deliver_memo', {'version': 1})
    assert approved['review_gate'] == {'reviewed': True, 'approved': True, 'review_id': 'R1'}
    delivered = (case_file.active_run_dir() / 'memo_v1.md').read_text()
    assert delivered == case_file.read_case()['memo_drafts'][0]['markdown']
    assert delivered.rstrip().endswith(memo.DISCLAIMER)
    assert len(case_file.read_case()['deliveries']) == 2


def test_review_items_go_to_each_parts_owner(runs_dir):
    case_file.start_run('demo')
    call('save_memo_version', VERSION)
    review = call('save_review', {'memo_version': 1, 'verdict': 'revise', 'should_fix': ['Shorter summary'], 'must_fix': [
        'business: no segment split. Fix: add the 10-K segment table.',
        'Valuation and price: no peer multiples. Fix: compare with three peers.',
        'risks, scenarios: China risk is unranked. Fix: rank it.'],
        'fundamentals_requests': ['Peer EV/EBITDA for MSFT, GOOGL and DELL']})
    assert review == {'id': 'R1', 'round': 1,
                      'revisions_requested_from': ['Market Analyst', 'Fundamentals Analyst', 'Lead Analyst'],
                      'evidence_requested_from': ['Fundamentals Analyst']}
    text = call('get_latest_review', {})
    assert text.startswith('Review R1 of memo version 1 (round 1 of 3): verdict revise\n'
                           'Must fix, for the Lead Analyst:\n- risks, scenarios: China risk is unranked. Fix: rank it.\n'
                           'Must fix, for the Fundamentals Analyst:\n- Valuation and price: no peer multiples.')
    assert 'Should fix:\n- Shorter summary' in text
    assert text.endswith('Evidence requests:\n- Fundamentals Analyst: Peer EV/EBITDA for MSFT, GOOGL and DELL')
    saved = case_file.read_case()['reviews'][0]
    assert saved['revision_requests'] == {'Market Analyst': ['business'], 'Fundamentals Analyst': ['valuation'],
                                          'Lead Analyst': ['risks', 'scenarios']}
    status = call('get_case_status', {})['latest_review']
    assert status['revisions_requested']['Market Analyst'] == ['business'] and status['revised_since']['Market Analyst'] == []
    save_part('business', 'Apple sells phones.')
    assert call('get_case_status', {})['latest_review']['revised_since']['Market Analyst'] == ['business']


def test_a_review_must_agree_with_its_items(runs_dir):
    case_file.start_run('demo')
    call('save_memo_version', VERSION)
    for arguments, message in (
            ({'verdict': 'revise', 'must_fix': []}, 'needs at least one must-fix item'),
            ({'verdict': 'approve', 'must_fix': ['business: add segments.']}, 'An approving review has no must-fix items'),
            ({'verdict': 'revise', 'must_fix': ['The outlook is thin.']}, 'starts with the part it concerns')):
        result = call_tool(server.server, 'save_review', {'memo_version': 1, 'should_fix': [], **arguments})
        assert result.is_error and message in result_text(result), arguments
    assert case_file.read_case()['reviews'] == []
    memo_wide = call('save_review', {'memo_version': 1, 'verdict': 'revise', 'should_fix': [],
                                     'must_fix': ['memo: the parts disagree on net cash. Fix: use one figure.']})
    assert memo_wide['revisions_requested_from'] == ['Lead Analyst']


def test_a_part_saved_again_and_again_gets_a_note(runs_dir):
    case_file.start_run('demo')
    with caller('Lead Analyst'):
        call('set_case_scope', {'company': 'Apple', 'ticker': 'AAPL', 'company_type': 'listed', 'decision': 'x'})
    first, second = save_part('risks', 'Too short [S1].'), save_part('risks', 'Still too short [S1].')
    assert 'note' not in first and 'note' not in second
    third = save_part('risks', 'Short again [S1].')
    assert third['note'].startswith('This is your save 3 of this part since the last review.')
    assert third['check']['notes'] == []


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
    with caller('Market Analyst'):
        call('save_evidence_packet', {**PACKET, 'parts': ['competition'], 'risks': ['Price war in China [S1]']})
        call('save_memo_version', VERSION)
        call('save_review', {'memo_version': 1, 'verdict': 'revise', 'should_fix': [],
                             'must_fix': ['competition: compare BEVs with BEVs.'],
                             'market_requests': ["BYD's 2025 BEV-only sales"]})
        follow_up = call('save_evidence_packet', PACKET)
    assert follow_up['follow_up_for'] == 'R1'
    assert call('get_latest_review', {}).endswith("Evidence requests:\n- Market Analyst: BYD's 2025 BEV-only sales")
    packets = call('get_evidence_packets', {})
    assert '## E1 (Market Analyst): BYD vs Tesla\nBEV volumes\nParts: competition' in packets
    assert 'Risks:\n- Price war in China [S1]' in packets
    assert '## E2 (Market Analyst, follow-up for review R1): BYD vs Tesla' in packets


def test_a_review_without_items_says_so(runs_dir):
    case_file.start_run('demo')
    call('save_memo_version', VERSION)
    call('save_review', {'memo_version': 1, 'verdict': 'approve', 'must_fix': [], 'should_fix': []})
    text = call('get_latest_review', {})
    assert 'Must fix: none' in text and text.endswith('Should fix: none\nEvidence requests: none')


def test_packets_too_long_for_one_result_come_back_as_a_list(runs_dir):
    case_file.start_run('demo')
    for topic in ('Margins', 'Debt', 'Peers'):
        call('save_evidence_packet', {**PACKET, 'topic': topic, 'summary': 'x' * 5_000})
    listing = call('get_evidence_packets', {})
    assert listing.startswith('These packets add up to') and '| E3 | None |  | Peers |' in listing
    one = call('get_evidence_packets', {'packet_ids': ['e2']})
    assert one.startswith('## E2 (unknown analyst): Debt') and 'x' * 5_000 in one


def test_sources_are_listed_a_page_at_a_time(runs_dir):
    case_file.start_run('demo')
    for n in range(45):
        call('register_source', {**SOURCE, 'location': f'https://sec.example/{n}'})
    first, second = call('list_sources', {}), call('list_sources', {'page': 2})
    assert first.startswith('Page 1 of 2 (45 sources).') and first.count('\n| S') == 40
    assert second.count('\n| S') == 5 and '| S45 |' in second


def test_longer_results_are_cut_where_rakazo_would_cut_them(runs_dir, tmp_path, monkeypatch):
    (tmp_path / 'deck.md').write_text('x' * 20_000)
    monkeypatch.setattr(case_file, 'ROOT', tmp_path)
    case_file.start_run('demo', [{'name': 'Deck', 'file': 'deck.md', 'confidentiality': 'client-confidential'}])
    text = call('read_client_document', {'name': 'Deck'})
    assert len(text) == RAKAZO_TEXT_LIMIT and text.endswith('\n[truncated]')
