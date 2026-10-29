import re

import pytest

from tools import report, sections, server
from tools.agents import AGENTS, ANALYSTS


def test_the_sections_fill_the_skills_template_slots_in_order():
    template = report.TEMPLATE.read_text()
    slots = [int(n) for n in re.findall(r'\{\{SECTION_(\d+)\}\}', template)]
    assert slots == list(range(1, 15)) == [s.number for s in sections.SECTIONS]
    for section in sections.SECTIONS:
        assert f'data-title="{section.title_zh} ' in template, section.key


def test_every_section_has_an_owner_on_the_team_and_every_analyst_owns_sections():
    owners = {s.owner for s in sections.ALL_SECTIONS}
    assert owners <= set(AGENTS.values())
    assert all(sections.OWNED[analyst] for analyst in ANALYSTS)
    assert sections.OWNED[AGENTS['lead']] == ('executive_summary', 'thesis', 'scoring')
    assert sections.OWNED[AGENTS['red_team']] == ('risk',)


def test_a_section_is_found_by_key_number_or_title():
    assert sections.section_key('financials') == 'financials'
    assert sections.section_key('s7') == sections.section_key('S7') == sections.section_key('7') == 'financials'
    assert sections.section_key('Financial Analysis') == 'financials'
    with pytest.raises(ValueError, match='Sections: executive_summary'):
        sections.section_key('valuation')


def test_the_mandatory_components_sit_where_skill_md_puts_them():
    by_key = sections.BY_KEY
    assert set(by_key['executive_summary'].components) == {'verdict', 'briefing', 'efficiency', 'one-question',
                                                           'takeaways'}
    assert {'kpi', 'timeline'} <= set(by_key['company_overview'].components)
    assert 'scenarios' in by_key['thesis'].components and 'analogs' in by_key['thesis'].components
    assert 'risk-matrix' in by_key['risk'].components
    assert {'sensitivity', 'takeaways'} <= set(by_key['scoring'].components)
    assert all('evidence' in by_key[k].components for k in ('team', 'technology_product', 'market', 'competition',
                                                            'business_model'))
    every = {kind for s in sections.ALL_SECTIONS for kind in s.components}
    assert every == set(report.COMPONENTS)


def test_score_weights_add_up_to_100_for_each_company_type():
    assert all(sum(weights.values()) == 100 for weights in sections.SCORE_WEIGHTS.values())


def test_ratings_follow_the_company_type():
    assert sections.is_rating('Watchlist', listed=True) and not sections.is_rating('Watchlist', listed=False)
    assert sections.is_rating('Wait for milestone', listed=False) and not sections.is_rating('Buy', listed=False)


def test_every_playbook_heading_a_section_names_exists():
    for section in sections.ALL_SECTIONS:
        for name, heading in section.playbooks:
            text = server.read_playbook(name=name, heading=heading)
            assert text.startswith('Playbook:'), (section.key, name, heading)
