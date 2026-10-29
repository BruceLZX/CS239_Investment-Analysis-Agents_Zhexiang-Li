import pytest

from tools import case_file

DECK = {'name': 'Deck', 'file': 'fixtures/deck.md', 'confidentiality': 'client-confidential'}
CHECK = {'passed': False, 'findings': [], 'depth': ['too short']}


def test_start_run_creates_the_case_and_marks_it_active(runs_dir):
    run_id = case_file.start_run('demo', [DECK], 'Is the deck credible?')
    assert case_file.active_run_dir() == runs_dir / run_id
    case = case_file.read_case()
    assert (case['scenario'], case['request']) == ('demo', 'Is the deck credible?')
    assert case['client_documents'] == [DECK]


def test_reading_without_an_active_run_explains_how_to_start_one(runs_dir):
    with pytest.raises(RuntimeError, match='No active run'):
        case_file.read_case()


def test_registering_the_same_location_reuses_its_id(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        first = case_file.add_source(case, 'A', 'primary filing', 'https://sec.example/a', '2025', 'high', 'x')
        again = case_file.add_source(case, 'A again', 'primary filing', 'https://sec.example/a', '2025', 'high', 'x')
        other = case_file.add_source(case, 'B', 'market data', 'https://prices.example/b', '2026', 'medium', 'y')
    assert (first, again, other) == ('S1', 'S1', 'S2')
    assert [s['id'] for s in case_file.read_case()['sources']] == ['S1', 'S2']


def packet(packet_id: str, analyst: str, follow_up_for: str | None = None) -> dict:
    return {'id': packet_id, 'analyst': analyst, 'follow_up_for': follow_up_for, 'topic': 'Apple',
            'source_ids': ['S1'], 'saved_at': 't', 'summary': 'long text', 'findings': []}


def test_status_summary_lists_what_arrived_without_the_content(runs_dir):
    case_file.start_run('demo', [DECK])
    with case_file.open_case() as case:
        case['scope'] = {'company': 'Apple', 'ticker': 'AAPL', 'type': 'listed', 'decision': 'Watchlist or not',
                         'set_by': 'Lead Analyst', 'set_at': 't'}
        case['evidence_packets'].append(packet('E1', 'Fundamentals Analyst'))
        case_file.save_part(case, 'financials', '# Long text', 'Fundamentals Analyst', CHECK)
        case['memo_drafts'].append({'version': 1, 'rating': 'Watchlist', 'saved_at': 't', 'markdown': '# Memo',
                                    'changed_parts': ['financials'], 'passed': False})
        case['reviews'].append({'id': 'R1', 'memo_version': 1, 'round': 1, 'verdict': 'revise', 'must_fix': ['a', 'b'],
                                'revision_requests': {'Fundamentals Analyst': ['financials']}, 'saved_at': 't'})
    status = case_file.status_summary(case_file.read_case())
    assert status['scope'] == {'company': 'Apple', 'ticker': 'AAPL', 'type': 'listed', 'decision': 'Watchlist or not'}
    assert status['client_documents'] == [{'name': 'Deck', 'confidentiality': 'client-confidential'}]
    assert status['evidence_packets'] == [{'id': 'E1', 'analyst': 'Fundamentals Analyst', 'follow_up_for': None,
                                           'topic': 'Apple', 'parts': [], 'saved_at': 't'}]
    assert status['first_round_packets'] == {'Fundamentals Analyst': ['E1'], 'Market Analyst': []}
    assert status['memo_parts'] == [{'part': 'financials', 'owner': 'Fundamentals Analyst', 'revision': 1,
                                     'author': 'Fundamentals Analyst', 'chars': 11, 'check_passed': False}]
    assert status['missing_parts'] == {
        'Lead Analyst': ['executive_summary', 'risks', 'scenarios', 'one_question', 'takeaways'],
        'Fundamentals Analyst': ['valuation'], 'Market Analyst': ['business', 'competition']}
    assert status['latest_version'] == {'version': 1, 'rating': 'Watchlist', 'changed_parts': ['financials'],
                                        'check_passed': False, 'saved_at': 't'}
    assert status['latest_review'] == {'id': 'R1', 'memo_version': 1, 'round': 1, 'verdict': 'revise',
                                       'must_fix_count': 2,
                                       'revisions_requested': {'Fundamentals Analyst': ['financials']},
                                       'revised_since': {'Fundamentals Analyst': []},
                                       'evidence_requested_from': [], 'follow_up_packets': {}}
    assert status['review_rounds_left'] == 2
    assert 'long text' not in str(status) and '# Memo' not in str(status) and '# Long text' not in str(status)


def test_status_summary_tracks_the_follow_up_research_a_review_asks_for(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        case['evidence_packets'] += [packet('E1', 'Fundamentals Analyst'), packet('E2', 'Market Analyst')]
        case['reviews'].append({'id': 'R1', 'memo_version': 1, 'verdict': 'revise', 'must_fix': ['a'], 'saved_at': 't',
                                'evidence_requests': {'Market Analyst': ["BYD's 2025 BEV-only sales"]}})
    assert case_file.status_summary(case_file.read_case())['latest_review']['follow_up_packets'] == {'Market Analyst': []}
    with case_file.open_case() as case:
        case['evidence_packets'].append(packet('E3', 'Market Analyst', follow_up_for='R1'))
    status = case_file.status_summary(case_file.read_case())
    assert status['first_round_packets'] == {'Fundamentals Analyst': ['E1'], 'Market Analyst': ['E2']}
    assert status['latest_review']['evidence_requested_from'] == ['Market Analyst']
    assert status['latest_review']['follow_up_packets'] == {'Market Analyst': ['E3']}


def test_a_version_snapshots_the_latest_revision_of_each_part(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        case_file.save_part(case, 'business', 'v1 text', 'Market Analyst', CHECK)
        first = case_file.add_version(case, 'Hold', '2026-10-28', '# Memo v1', CHECK)
        case_file.save_part(case, 'business', 'v2 text', 'Market Analyst', CHECK)
        case_file.save_part(case, 'risks', 'risks', 'Lead Analyst', CHECK)
        second = case_file.add_version(case, 'Hold', '2026-10-28', '# Memo v2', CHECK)
    assert first['changed_parts'] == ['business'] and second['changed_parts'] == ['business', 'risks']
    assert first['missing_parts'][:2] == ['executive_summary', 'financials']
    case = case_file.read_case()
    assert case_file.version_parts(case, case['memo_drafts'][0]) == {'business': 'v1 text'}
    assert case_file.version_parts(case, case['memo_drafts'][1]) == {'business': 'v2 text', 'risks': 'risks'}
    assert case['memo_parts']['business'][1]['sha256'] != case['memo_parts']['business'][0]['sha256']


def test_the_memo_fails_review_only_after_the_last_round():
    revise = {'verdict': 'revise'}
    assert not case_file.final_review_failed({'reviews': [revise, revise]})
    assert case_file.final_review_failed({'reviews': [revise, revise, revise]})
    assert not case_file.final_review_failed({'reviews': [revise, revise, {'verdict': 'approve'}]})


def test_sources_record_who_registered_them_and_with_which_tool(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        case_file.add_source(case, '10-K', 'primary filing', 'https://sec.example/10k', '2025', 'high', 'x',
                             registered_by='Fundamentals Analyst', via='get_sec_financials')
    source = case_file.read_case()['sources'][0]
    assert (source['registered_by'], source['via']) == ('Fundamentals Analyst', 'get_sec_financials')


def test_review_gate_needs_an_approving_review_of_that_exact_version():
    case = {'reviews': [{'id': 'R1', 'memo_version': 1, 'verdict': 'revise'},
                        {'id': 'R2', 'memo_version': 2, 'verdict': 'approve'}]}
    assert case_file.review_gate(case, 1) == {'reviewed': True, 'approved': False, 'review_id': 'R1'}
    assert case_file.review_gate(case, 2) == {'reviewed': True, 'approved': True, 'review_id': 'R2'}
    assert case_file.review_gate(case, 3) == {'reviewed': False, 'approved': False, 'review_id': None}


def test_tool_calls_are_logged_only_while_a_run_is_active(runs_dir):
    case_file.log_tool_call({'tool': 'ignored'})
    assert not list(runs_dir.iterdir())
    case_file.start_run('demo')
    case_file.log_tool_call({'tool': 'kept'})
    assert '"kept"' in (case_file.active_run_dir() / 'tool_log.jsonl').read_text()
