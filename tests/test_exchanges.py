"""What the agents did with each other's work, worked out from the case file and the tool log."""
import json

from team.exchanges import exchanges, read_tool_log

LEAD, MARKET, FUNDAMENTALS = 'Lead Analyst', 'Market Analyst', 'Fundamentals Analyst'
VALUATION, RED_TEAM, REVIEWER = 'Valuation Analyst', 'Red Team Analyst', 'IC Reviewer'


def stamp(minute: int) -> str:
    return f'2026-10-29T10:{minute:02}:00+00:00'


def a_case(**extra) -> dict:
    return {'sources': [{'id': 'S1', 'registered_by': FUNDAMENTALS}, {'id': 'S2', 'registered_by': VALUATION},
                        {'id': 'S3', 'registered_by': LEAD}], **extra}


def read(agent: str | None, wanted, minute: int = 1, tool: str = 'get_memo_parts', **extra) -> dict:
    return {'ts': stamp(minute), 'agent': agent, 'tool': tool, 'arguments': {'sections_wanted': wanted}, **extra}


def summary(found: list[dict]) -> list[tuple]:
    return [(e['kind'], e['from'], e['to'], e['text']) for e in found]


def test_reading_another_owners_section_counts_by_its_owner():
    log = [read(VALUATION, ['financials', 's6', 'market']), read(VALUATION, ['funding_valuation']), read(LEAD, ['market']),
           read(VALUATION, ['thesis']), read(VALUATION, ['not a section']), read(None, ['market']),
           read(VALUATION, ['market'], error='ValueError: too long'), read(VALUATION, []),
           read(RED_TEAM, ['financials'], tool='get_evidence_matrix')]
    assert summary(exchanges(a_case(), log)) == [
        ('read', VALUATION, FUNDAMENTALS, 'read S7 financials, S6 business model'),
        ('read', VALUATION, MARKET, 'read S4 market'),
        ('read', RED_TEAM, FUNDAMENTALS, 'read the evidence for S7 financials')]


def test_a_source_counts_the_first_time_an_agent_cites_it():
    parts = {
        'market': [{'author': MARKET, 'saved_at': stamp(1), 'markdown': 'Revenue [S1], again [S1]; a multiple [S2].'},
                   {'author': MARKET, 'saved_at': stamp(3), 'markdown': 'Revenue [S1] | S2 |'}],
        'competition': [{'author': MARKET, 'saved_at': stamp(2), 'markdown': 'The Lead found S3; a table cites S2.'}],
        'financials': [{'author': FUNDAMENTALS, 'saved_at': stamp(4), 'markdown': 'Its own [S1], not in the register [S9].'}],
        'thesis': [{'author': LEAD, 'saved_at': stamp(5), 'markdown': 'The Lead cites [S1].'}]}
    assert summary(exchanges(a_case(memo_parts=parts), [])) == [
        ('cite', MARKET, FUNDAMENTALS, 'cited S1 in S4 market'), ('cite', MARKET, VALUATION, 'cited S2 in S4 market')]


def test_review_items_and_the_weakest_section_go_to_their_owners():
    case = a_case(reviews=[{'id': 'R1', 'finished_at': stamp(9), 'revision_requests': {
                      MARKET: ['market', 'competition'], LEAD: ['thesis']}},
                  {'id': 'R2', 'revision_requests': {MARKET: ['market']}}],
                  workflow={'red_team_review': {'weakest_section': 'financials', 'saved_at': stamp(7)}})
    assert summary(exchanges(case, [])) == [
        ('attack', RED_TEAM, FUNDAMENTALS, 'named S7 financials the weakest section'),
        ('review', REVIEWER, MARKET, 'R1: items on S4 market, S5 competition')]


def test_notes_and_their_answers_are_exchanges_with_their_sources():
    notes = [{'id': 'N1', 'from': VALUATION, 'to': FUNDAMENTALS, 'section': 'financials', 'note': 'Capex differs.',
              'source_ids': ['S1', 'S2'], 'answers': None, 'at': stamp(1)},
             {'id': 'N2', 'from': FUNDAMENTALS, 'to': VALUATION, 'section': 'financials', 'note': 'Corrected.',
              'source_ids': [], 'answers': 'N1', 'at': stamp(2)}]
    found = exchanges(a_case(notes=notes), [])
    assert summary(found) == [('note', VALUATION, FUNDAMENTALS, 'Capex differs. [S1, S2]'),
                              ('answer', FUNDAMENTALS, VALUATION, 'Corrected.')]
    assert [e['label'] for e in found] == ['note N1', 'answered N1']


def test_exchanges_come_oldest_first():
    notes = [{'id': 'N1', 'from': VALUATION, 'to': MARKET, 'section': 'market', 'note': 'x', 'at': stamp(5)}]
    found = exchanges(a_case(notes=notes), [read(RED_TEAM, ['market'], minute=9), read(VALUATION, ['market'], minute=2)])
    assert [e['ts'] for e in found] == [stamp(2), stamp(5), stamp(9)]


def test_a_tool_log_is_read_with_its_arguments_as_json(tmp_path):
    assert read_tool_log(tmp_path) == []
    (tmp_path / 'tool_log.jsonl').write_text(json.dumps({'tool': 'a', 'arguments': '{"x": 1}'}) + '\n'
                                             + json.dumps({'tool': 'b', 'arguments': {'y': 2}}) + '\n')
    assert [call['arguments'] for call in read_tool_log(tmp_path)] == [{'x': 1}, {'y': 2}]
