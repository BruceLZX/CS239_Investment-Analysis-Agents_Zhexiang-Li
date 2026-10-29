import json
from pathlib import Path
import re

import pytest

from tools import memo

TRACES = Path(__file__).resolve().parents[1] / 'traces' / 'phase1'


def source(source_id: str, source_type: str, location: str, registered_by: str | None = None) -> dict:
    return {'id': source_id, 'title': f'Title {source_id}', 'source_type': source_type, 'location': location,
            'date': '2026-10-28', 'registered_by': registered_by}


SOURCES = [
    source('S1', 'primary filing', 'https://www.sec.gov/Archives/edgar/data/320193/a10-k.htm', 'Fundamentals Analyst'),
    source('S2', 'market data', 'https://finance.yahoo.com/quote/AAPL', 'Fundamentals Analyst'),
    source('S3', 'company-provided', 'Series A deck'),
    source('S5', 'industry data', 'https://www.idc.com/smartphones', 'Market Analyst'),
    source('S6', 'industry data', 'https://www.counterpointresearch.com/asp', 'Market Analyst'),
    source('S7', 'independent media', 'https://www.reuters.com/apple-profit', 'Market Analyst'),
    source('S8', 'independent media', 'https://www.cirpinc.com/upgrades', 'Market Analyst'),
    source('S9', 'independent media', 'https://www.scmp.com/huawei', 'Market Analyst'),
    source('S10', 'regulator', 'https://ec.europa.eu/dma', 'Market Analyst'),
    source('S11', 'regulator', 'https://www.justice.gov/apple', 'Market Analyst'),
]

# A Competition and market part written to the standard: the floor, two tables with a Source column, every
# coverage group, the evidence gate and a confidence statement.
COMPETITION = """\
The global smartphone market is sized at 1.25 billion units and $485 billion of revenue in 2025 [S5][S6], growing \
at a CAGR of 2.1% from 2020 to 2025 [S6]. Growth now comes from price rather than units, because premium devices \
above $600 rose to 63% of industry revenue [S6]. That favors Apple, which sells almost only premium devices, and it \
means investors should judge the thesis on pricing power rather than on shipments.

| Measure | 2024 | 2025 | Source |
|---|---|---|---|
| Global smartphone shipments | 1.22B | 1.25B | S5 |
| Apple share of shipments | 18.7% | 19.4% | S5 |
| Samsung share of shipments | 19.4% | 18.9% | S5 |
| Premium segment share of revenue | 61% | 63% | S6 |

Apple held 19.4% of 2025 shipments against Samsung's 18.9% and Xiaomi's 13.8% [S5], but its share of industry \
profit is far higher than its unit share: Counterpoint puts it at 79% of handset operating profit [S7]. Compared \
with Samsung, whose premium Galaxy S line is its closest rival, Apple's average selling price of $988 is 2.4 times \
the industry average of $412 [S6][S7].

| Competitor | Segment | 2025 share | Average price | Source |
|---|---|---|---|---|
| Samsung | Premium and mid-range Android | 18.9% | $310 | S5, S7 |
| Xiaomi | Mid-range Android | 13.8% | $160 | S5 |
| Huawei | Premium Android in China | 16% of China | not disclosed | S9 |

The main substitute is not another brand but a longer replacement cycle: the average upgrade interval in the US \
lengthened to 40 months in 2025 [S8], and doing nothing is the most common alternative for an existing iPhone \
owner. Huawei's return in China, with 16% share of the domestic market in 2025 [S9], is the most dangerous \
competitor because it competes in the same premium tier and benefits from local preference.

Regulation is the second front. The EU Digital Markets Act forces app-store changes that could cut services take \
rates [S10], and the US Department of Justice antitrust case challenges the ecosystem lock-in itself [S11]. \
However, neither has yet reduced reported services revenue, which grew 13% in fiscal 2025 according to the 10-K \
[S1]; the counter-evidence to the moat thesis is therefore regulatory risk rather than lost customers.

For the rating, the competitive position supports a premium multiple only while switching costs hold; a share loss \
below 17% in China [S9] or a cut to services take rates would weaken the thesis. Confidence: medium, because share \
data come from industry trackers that revise their estimates every quarter."""

SCORECARD = """\
| Dimension | Score | Reason | Source |
|---|---|---|---|
| Business quality | 8/10 | Services grew 13% in FY2025 | S1 |
| Financial strength | 9 | Net cash and 26% operating margin | S1 |
| Valuation | 4 | P/E of 33x against a peer median of 22x | S2 |
| Competitive position | 8 | 19.4% of shipments and 79% of profit | S5, S7 |
| Management and governance | 7 | Buybacks of $95B in FY2025 | S1 |
| Risk | 5 | China share fell to 16% | S9 |
| Composite | 6.8 | Equal-weight average of the six | S1 |"""

SCENARIOS = """\
| Scenario | Probability | Driver | Outcome | Source |
|---|---|---|---|---|
| Bull | 25% | Services grow 15% a year | $260 | S2 |
| Base | 50% | Services grow 10% a year | $220 | S2 |
| Bear | 25% | China share falls below 12% | $160 | S2 |"""


def depth(key: str, markdown: str, sources=SOURCES, listed: bool = True) -> list[str]:
    return memo.check_part(key, markdown, sources, listed)['depth']


def test_the_parts_are_the_ten_memo_parts_with_their_owners():
    assert [part.heading for part in memo.PARTS] + ['Sources'] == [
        'Executive summary', 'Business', 'Financials', 'Valuation and price', 'Competition and market',
        'Risks and counter-evidence', 'Scenarios', 'The one diligence question', 'Three takeaways', 'Sources']
    owners = {part.key: part.owner for part in memo.PARTS}
    assert owners['business'] == owners['competition'] == 'Market Analyst'
    assert owners['financials'] == owners['valuation'] == 'Fundamentals Analyst'
    assert {owners[k] for k in ('executive_summary', 'risks', 'scenarios', 'one_question', 'takeaways')} == {'Lead Analyst'}
    assert all(part.chars[1] <= memo.MAX_PART_CHARS for part in memo.PARTS)


def test_a_repeated_heading_is_dropped_because_assembly_adds_it():
    assert memo.normalize_part('business', '\n## Business\n\nApple sells phones.\n') == 'Apple sells phones.'
    assert memo.normalize_part('business', '### Revenue mix\nApple sells phones.') == '### Revenue mix\nApple sells phones.'


def test_a_part_written_to_the_standard_passes():
    report = memo.check_part('competition', COMPETITION, SOURCES)
    assert report['chars'] >= 2500
    assert (report['findings'], report['depth']) == ([], [])
    assert report['passed']


def test_phase_1_memo_parts_fall_short_of_the_depth_standard():
    trace = json.loads((TRACES / 'confidential-startup.json').read_text())
    chunks = re.split(r'^## ', trace['final_memo'], flags=re.M)[1:]
    bodies = {chunk.split('\n', 1)[0].strip(): chunk.split('\n', 1)[1] for chunk in chunks}
    for part in memo.PARTS:
        if part.analysis:
            problems = depth(part.key, bodies[part.heading], trace['case_file']['sources'], listed=False)
            assert any('the floor is' in p for p in problems), part.key


def test_figures_need_a_source_column_in_tables():
    table = '| Metric | FY2025 |\n|---|---|\n| Revenue | $416.2B [S1] |'
    assert any('no Source column' in p for p in depth('financials', table))
    sourced = '| Metric | FY2025 | Source |\n|---|---|---|\n| Revenue | $416.2B | S1 |'
    assert not any('no Source column' in p for p in depth('financials', sourced))


def test_the_evidence_gate_reads_the_cited_sources():
    media_only = 'Revenue grew 6% [S7]. Margins rose 2 points [S8].'
    assert any('a primary filing' in p and '3 publishers' in p for p in depth('financials', media_only))
    filed = 'Revenue grew 6% [S1]. The stock trades at 33x [S2]. Peers trade at 22x [S7].'
    assert not any('evidence gate' in p for p in depth('financials', filed))
    one_side = 'Antitrust risk [S7]. China risk [S8]. Price risk [S9].'
    assert any("both analysts' research" in p for p in depth('risks', one_side))
    both_sides = one_side + ' Debt risk [S1].'
    assert not any('evidence gate' in p for p in depth('risks', both_sides))


def test_private_companies_are_held_to_the_private_standard():
    listed = depth('valuation', 'The round values the company at $40M post-money [S3].')
    private = depth('valuation', 'The round values the company at $40M post-money [S3].', listed=False)
    assert 'does not cover trading snapshot' in listed and 'does not cover trading snapshot' not in private
    assert 'does not cover dilution' in private
    assert any('needs 6' in p for p in private) and any('needs 12' in p for p in listed)


def test_the_scorecard_needs_six_scores_and_their_average():
    assert memo._scorecard(memo._tables(SCORECARD)) == []
    wrong = SCORECARD.replace('| Composite | 6.8 |', '| Composite | 7.5 |')
    assert memo._scorecard(memo._tables(wrong)) == ['the composite 7.5 is not the average of the six scores (6.8)']
    no_risk = '\n'.join(line for line in SCORECARD.splitlines() if not line.startswith('| Risk'))
    assert 'the scorecard has no risk row' in memo._scorecard(memo._tables(no_risk))
    assert memo._scorecard([]) == ['no scorecard table scoring the six dimensions 1-10']


def test_scenario_probabilities_add_up_to_100():
    assert memo._scenario_table(memo._tables(SCENARIOS)) == []
    assert memo._scenario_table(memo._tables(SCENARIOS.replace('| Bear | 25%', '| Bear | 35%'))) == [
        'the scenario probabilities add up to 110%, not 100%']


def test_one_question_and_three_takeaways():
    assert '2 question marks; ask exactly one question' in depth('one_question', 'Will China recover? And when?')
    two = '1. Services grew 13% [S1].\n2. The stock trades at 33x [S2].'
    assert '2 numbered takeaways; needs exactly 3' in depth('takeaways', two)
    unsourced = two + '\n3. China is the swing factor.'
    assert 'every takeaway needs a figure and its source ID' in depth('takeaways', unsourced)


def test_empty_and_vague_phrases_are_flagged():
    problems = depth('business', 'Apple has a strong team and a huge market. It sold about 230M phones, '
                                 'around 50M Macs and roughly 20M iPads [S1].')
    assert 'empty phrases: huge market, strong team' in problems
    assert any(p.startswith('3 vague phrasings') for p in problems)


def test_valuation_language_is_an_investor_implication():
    # How the delivered Tesla business part drew its implication; the check missed it before.
    tesla = 'The mix is moving away from cars: that supports the multiple only if autonomy monetises.'
    assert 'investor implication' not in memo._missing_terms(tesla, memo.ANALYSIS_TERMS)
    assert 'investor implication' in memo._missing_terms('Tesla sells cars to shareholders.', memo.ANALYSIS_TERMS)


def test_team_names_and_writing_about_the_writing_are_internal_material():
    findings = memo.check_part('risks', 'As briefed by the Lead Analyst, this part should list risks.', SOURCES)['findings']
    assert [f['rule'] for f in findings] == ['N6']
    for word in ('As briefed', 'Lead Analyst', 'this part should'):
        assert word in findings[0]['detail']


def test_assembly_adds_the_header_cited_sources_and_disclaimer():
    parts = {'competition': COMPETITION, 'takeaways': '1. Services grew 13% [S1].'}
    text = memo.assemble(parts, {'company': 'Apple', 'ticker': 'AAPL'}, 'Watchlist', '2026-10-28', SOURCES)
    assert text.startswith('# Apple (AAPL): investment memo\nRating: Watchlist\nData as of: 2026-10-28\n')
    headings = re.findall(r'^## (.+)$', text, flags=re.M)
    assert headings == [part.heading for part in memo.PARTS] + ['Sources']
    assert text.count('_Not available in this version._') == 7
    sources_part = text.split('## Sources', 1)[1]
    assert '| S1 |' in sources_part and '| S5 |' in sources_part and '| S2 |' not in sources_part
    assert text.rstrip().endswith(memo.DISCLAIMER)
    private = memo.assemble({}, {'company': 'Orrin Fieldworks', 'ticker': None}, 'Wait', '2026-10-28', [])
    assert private.startswith('# Orrin Fieldworks (private): investment memo')


def test_a_version_check_covers_the_rules_missing_parts_and_repetition():
    repeated = 'Services revenue is the single most important driver of the thesis here.'
    parts = {'competition': COMPETITION, 'executive_summary': f'Our rating is Hold. {repeated}',
             'risks': f'{repeated} {repeated}'}
    text = memo.assemble(parts, {'company': 'Apple', 'ticker': 'AAPL'}, 'Watchlist', '2026-10-28', SOURCES)
    report = memo.check_version(text, parts, 'Watchlist', SOURCES)
    assert [f['rule'] for f in report['findings']] == []  # the header supplies the disclaimer and the date
    assert report['parts']['competition']['passed']
    assert not report['parts']['risks']['passed']
    assert any(d.startswith('missing parts: Business, Financials') for d in report['depth'])
    assert 'the executive summary does not state the rating "Watchlist"' in report['depth']
    assert any(d.startswith('said three or more times') for d in report['depth'])
    assert not report['passed']


@pytest.mark.parametrize('rating', ['Hold', 'Hold-off'])
def test_the_summary_must_state_the_version_rating(rating):
    parts = {'executive_summary': f'We rate the stock {rating}.'}
    text = memo.assemble(parts, {'company': 'Apple', 'ticker': 'AAPL'}, rating, '2026-10-28', SOURCES)
    assert not any('does not state the rating' in d for d in memo.check_version(text, parts, rating, SOURCES)['depth'])


def test_a_part_past_its_length_target_gets_a_note_not_a_problem():
    longer = COMPETITION + '\n\n' + 'Regulators in the EU and the US keep the case open against the moat thesis [S10]. ' * 32
    report = memo.check_part('competition', longer, SOURCES)
    assert report['passed'] and report['depth'] == []
    assert report['notes'] == [f'{len(longer):,} characters, past the 5,000 to aim for; tighten it when you next revise']
