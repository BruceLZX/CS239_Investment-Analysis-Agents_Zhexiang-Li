import json

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
    assert {'evidence', 'workflow', 'user_data_requests'} <= set(case)


def test_reading_without_an_active_run_explains_how_to_start_one(runs_dir):
    with pytest.raises(RuntimeError, match='No active run'):
        case_file.read_case()


def test_registering_the_same_location_reuses_its_id(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        first = case_file.add_source(case, 'A', 'primary', 'https://sec.example/a', '2025', 'high', 'x')
        again = case_file.add_source(case, 'A again', 'primary', 'https://sec.example/a', '2025', 'high', 'x')
        other = case_file.add_source(case, 'B', 'market data', 'https://prices.example/b', '2026', 'medium', 'y',
                                     claims_weakened='z')
    assert (first, again, other) == ('S1', 'S1', 'S2')
    assert case_file.read_case()['sources'][1]['claims_weakened'] == 'z'


def test_status_summary_lists_what_arrived_without_the_content(runs_dir):
    case_file.start_run('demo', [DECK])
    with case_file.open_case() as case:
        case['scope'] = {'company': 'Apple', 'ticker': 'AAPL', 'type': 'listed', 'decision': 'Watchlist or not',
                         'set_by': 'Lead Analyst', 'set_at': 't'}
        case['workflow']['research_plan'] = {'spines': []}
        case['evidence']['financials'] = [{'author': 'Fundamentals Analyst', 'queries': ['a'], 'rows': [],
                                           'gate_passed': False, 'saved_at': 't'}]
        case_file.save_part(case, 'financials', '# Long text', 'Fundamentals Analyst', CHECK)
        case['memo_drafts'].append({'version': 1, 'rating': 'Watchlist', 'saved_at': 't', 'parts': {},
                                    'changed_parts': ['financials'], 'missing_parts': ['team'], 'passed': False})
        case['reviews'].append({'id': 'R1', 'memo_version': 1, 'round': 1, 'verdict': 'revise', 'finished_at': '2000-01-01',
                                'items': [{'severity': 'Critical'}, {'severity': 'Minor'}],
                                'revision_requests': {'Fundamentals Analyst': ['financials']}})
    status = case_file.status_summary(case_file.read_case())
    assert status['scope']['company'] == 'Apple'
    assert status['client_documents'] == [{'name': 'Deck', 'confidentiality': 'client-confidential'}]
    assert status['workflow']['research_plan'] and not status['workflow']['thesis_table']
    assert status['analysts']['Fundamentals Analyst'] == {'sections_saved': ['financials'],
                                                          'sections_missing': ['business_model'],
                                                          'evidence_blocks': ['financials']}
    assert status['sections'] == [{'section': 'financials', 'owner': 'Fundamentals Analyst', 'revision': 1,
                                   'author': 'Fundamentals Analyst', 'chars': 11, 'check_passed': False}]
    assert status['missing_sections']['Lead Analyst'] == ['executive_summary', 'thesis', 'scoring']
    assert status['latest_review']['items'] == {'Critical': 1, 'Important': 0, 'Minor': 1}
    assert status['latest_review']['revised_since'] == {'Fundamentals Analyst': ['financials']}
    assert status['review_rounds_left'] == 2
    assert '# Long text' not in json.dumps(status)


def test_a_version_snapshots_the_latest_revision_of_each_section(runs_dir):
    case_file.start_run('demo')
    with case_file.open_case() as case:
        case_file.save_part(case, 'financials', 'v1 text', 'Fundamentals Analyst', CHECK)
        case_file.save_part(case, 'financials', 'v2 text', 'Fundamentals Analyst', CHECK)
        case_file.save_part(case, 'market', 'market text', 'Market Analyst', CHECK)
        version = case_file.add_version(case, 'Watchlist', '2026-10-28', {'company': 'Apple'}, '6.7',
                                        {'html': 'v1/report.html'}, {'passed': False})
        assert case_file.version_parts(case, version) == {'market': 'market text', 'financials': 'v2 text'}
    assert version['parts']['financials']['revision'] == 2
    assert version['composite_score'] == '6.7' and 'executive_summary' in version['missing_parts']


def test_unfinished_reviews_do_not_count_as_rounds():
    case = {'reviews': [{'verdict': 'revise', 'memo_version': 1}, {'verdict': 'revise', 'memo_version': 2},
                        {'verdict': None, 'memo_version': 3}]}
    assert not case_file.final_review_failed(case)
    case['reviews'][-1]['verdict'] = 'reject'
    assert case_file.final_review_failed(case)


def test_review_gate_needs_an_approving_review_of_that_exact_version():
    case = {'reviews': [{'id': 'R1', 'memo_version': 1, 'verdict': 'approve'},
                        {'id': 'R2', 'memo_version': 2, 'verdict': None}]}
    assert case_file.review_gate(case, 1) == {'reviewed': True, 'approved': True, 'review_id': 'R1'}
    assert case_file.review_gate(case, 2) == {'reviewed': False, 'approved': False, 'review_id': None}


def test_tool_calls_are_logged_only_while_a_run_is_active(runs_dir):
    case_file.log_tool_call({'tool': 'nothing'})
    assert not list(runs_dir.iterdir())
    case_file.start_run('demo')
    case_file.log_tool_call({'tool': 'list_sources'})
    assert json.loads((case_file.active_run_dir() / 'tool_log.jsonl').read_text())['tool'] == 'list_sources'
