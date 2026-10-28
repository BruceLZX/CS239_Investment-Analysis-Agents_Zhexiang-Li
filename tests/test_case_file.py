import pytest

from tools import case_file

DECK = {'name': 'Deck', 'file': 'fixtures/deck.md', 'confidentiality': 'client-confidential'}


def test_start_run_creates_the_case_and_marks_it_active(runs_dir):
    run_id = case_file.start_run('demo', [DECK])
    assert case_file.active_run_dir() == runs_dir / run_id
    case = case_file.read_case()
    assert case['scenario'] == 'demo'
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
        case['evidence_packets'].append(packet('E1', 'Fundamentals Analyst'))
        case['memo_drafts'].append({'version': 1, 'rating': 'Watchlist', 'saved_at': 't', 'markdown': '# Memo'})
        case['reviews'].append({'id': 'R1', 'memo_version': 1, 'verdict': 'revise', 'must_fix': ['a', 'b']})
    status = case_file.status_summary(case_file.read_case())
    assert status['client_documents'] == [{'name': 'Deck', 'confidentiality': 'client-confidential'}]
    assert status['evidence_packets'] == [{'id': 'E1', 'analyst': 'Fundamentals Analyst', 'follow_up_for': None,
                                           'topic': 'Apple', 'source_ids': ['S1'], 'saved_at': 't'}]
    assert status['first_round_packets'] == {'Fundamentals Analyst': ['E1'], 'Market Analyst': []}
    assert status['latest_memo_draft'] == {'version': 1, 'rating': 'Watchlist', 'saved_at': 't'}
    assert status['latest_review'] == {'id': 'R1', 'memo_version': 1, 'verdict': 'revise', 'must_fix_count': 2,
                                       'evidence_requested_from': [], 'follow_up_packets': {}}
    assert 'long text' not in str(status) and '# Memo' not in str(status)


def test_status_summary_tracks_the_follow_up_research_a_review_asks_for(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        case['evidence_packets'] += [packet('E1', 'Fundamentals Analyst'), packet('E2', 'Market Analyst')]
        case['reviews'].append({'id': 'R1', 'memo_version': 1, 'verdict': 'revise', 'must_fix': ['a'],
                                'evidence_requests': {'Market Analyst': ["BYD's 2025 BEV-only sales"]}})
    assert case_file.status_summary(case_file.read_case())['latest_review']['follow_up_packets'] == {'Market Analyst': []}
    with case_file.open_case() as case:
        case['evidence_packets'].append(packet('E3', 'Market Analyst', follow_up_for='R1'))
    status = case_file.status_summary(case_file.read_case())
    assert status['first_round_packets'] == {'Fundamentals Analyst': ['E1'], 'Market Analyst': ['E2']}
    assert status['latest_review']['evidence_requested_from'] == ['Market Analyst']
    assert status['latest_review']['follow_up_packets'] == {'Market Analyst': ['E3']}


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
