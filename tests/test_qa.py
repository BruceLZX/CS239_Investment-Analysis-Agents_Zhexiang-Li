"""The skill's QA scripts as ported to the team, each held to the script's thresholds, with its bugs fixed."""
from pathlib import Path

from tools import report, sections
from tools.qa import (check_citations, check_depth, check_evidence, check_report, check_source_register,
                      check_workflow_docs, clean_output, diagnose_report)

from .report_samples import EXECUTIVE_SUMMARY, FINANCIALS, SCORING, SOURCES

FINANCIALS_SECTION = sections.BY_KEY['financials']


def section_check(markdown: str, section: sections.Section = FINANCIALS_SECTION, listed: bool = True) -> dict:
    return check_depth.check_section(section, markdown, report.render_section(markdown, SOURCES), listed)


# check_depth

def test_a_section_written_to_the_standard_passes_every_depth_rule():
    result = section_check(FINANCIALS)
    assert result['failures'] == []
    assert result['counts']['inline_tags'] == 6 and result['counts']['paragraphs'] == 7


def test_depth_floors_are_the_skills():
    short = FINANCIALS.split('| Measure |')[0]
    failures = section_check(short)['failures']
    assert any('needs 2,500' in f for f in failures) and any('analytical paragraphs; needs 6' in f for f in failures)


def test_more_than_six_inline_tags_fail():
    tagged = FINANCIALS.replace('Neither changes the cash picture', 'Neither changes the cash picture [S6]').replace(
        'For investors,', 'For investors [S8],')
    assert any('inline source tags; at most 6' in f for f in section_check(tagged)['failures'])


def test_a_missing_component_or_table_is_named():
    no_card = FINANCIALS.replace('::: info warning\n', '').replace('[S2].\n:::\n', '[S2].\n')
    assert 'missing the "::: info" component' in section_check(no_card)['failures']
    no_returns = (FINANCIALS.replace('Return on invested capital', 'Capital').replace('Days sales outstanding', 'Receivable days')
                  .replace('Cash conversion cycle', 'Cycle'))
    assert any(f.startswith('no returns and working capital table') for f in section_check(no_returns)['failures'])


def test_shallow_vague_and_writing_about_writing_fail():
    padded = FINANCIALS + '\nThis section should explain why the team is experienced and the market is a huge market.'
    failures = section_check(padded)['failures']
    assert any('writes about how the report is made' in f for f in failures)
    assert any('empty phrases: huge market' in f for f in failures)
    vague = FINANCIALS + '\nRevenue was roughly $4 billion, around 5 segments, about 3 regions.'
    assert any('vague phrasings' in f for f in section_check(vague)['failures'])


def test_granularity_markers_run_and_are_generic():
    # check_depth.py's NameError meant these never ran; and its competition marker named BCI companies only.
    no_year = FINANCIALS.replace('FY20', 'fiscal ').replace('2029', 'later')
    assert 'granularity: no a fiscal year' in section_check(no_year)['failures']


def test_numbers_do_not_count_source_ids_or_urls():
    assert check_depth.numbers('See S12 and https://x.com/2025/report') == []


def test_english_paragraphs_are_not_mistaken_for_copies():
    # check_depth.py folded every English word into one letter, so any three English paragraphs of similar length
    # looked 82% alike.
    paragraphs = ''.join(f'<p>{text}</p>' for text in (
        'Northwind grew subscriptions to 26.6% of revenue because attach rates rose on new devices sold in Europe.',
        'The balance sheet holds 1.34 billion of net cash with no maturities before 2029 and no covenants at all.',
        'Peers cut device prices by 8% in 2025, which shows how quickly hardware margins can fall in a price war.'))
    assert check_depth.near_duplicate_paragraphs(paragraphs) == []
    copies = ''.join(f'<p>The receivables trend in section {n} needs diligence with management because it may '
                     f'signal looser distributor terms in {2020 + n}.</p>' for n in range(3))
    assert len(check_depth.near_duplicate_paragraphs(copies)) == 1


def test_repeated_sentences_ignore_css():
    text = 'Receivables are the one figure that would change the rating. ' * 3
    assert check_depth.repeated_sentences(text)
    assert check_depth.repeated_sentences('<style>.a{}</style>' * 3) == []


def test_the_source_appendix_may_repeat_a_title():
    # Three 8-Ks read for the same item are three sources with one title; the first Apple run failed on it.
    rows = '<tr><td>Apple Inc. 8-K, Item 5.02 (Departure or Election of Directors and Officers).</td></tr>' * 3
    opening = '<section class="section-card" id="sources-appendix">'
    html = full_report().replace(opening, f'{opening}<table>{rows}</table>', 1)
    assert html.count('Item 5.02') == 3
    failures = check_depth.check_report_depth(html, {}, True)['failures']
    assert not any(f.startswith('said three or more times') for f in failures)


# check_report

def full_report(texts: dict | None = None) -> str:
    texts = texts or {'executive_summary': EXECUTIVE_SUMMARY, 'financials': FINANCIALS, 'scoring': SCORING}
    return report.render_report(texts, SOURCES, report.Cover('Northwind Devices'), '2026-10-28', '6.7')


def test_the_executive_summary_written_to_the_standard_passes():
    assert check_report.executive_summary_failures(report.render_section(EXECUTIVE_SUMMARY, SOURCES)) == []


def test_the_report_check_names_each_missing_component():
    failures = check_report.check_report(full_report(), listed=True)['failures']
    assert 'missing the risk matrix component' in failures and 'missing the timeline component' in failures
    assert 'missing the verdict strip component' not in failures
    assert not any('template version' in f or 'placeholders' in f for f in failures)


def test_chinese_scenario_labels_count_and_pe_needs_the_term():
    zh = '<p>牛市情景、基准情景与熊市情景</p>'
    assert 'no bull, base and bear scenarios' not in check_report.check_report(zh, listed=False)['failures']
    # "pe" inside "people" or "operate" is not a valuation multiple.
    failures = check_report.check_report('<p>people operate</p>', listed=True)['failures']
    assert 'public equity: no valuation' in failures


def test_the_composite_score_must_be_in_the_meta_tag_and_agree():
    failures = check_report.check_report(full_report(), composite_score='7.1')['failures']
    assert any('differs from section 14' in f for f in failures)


def test_the_pdf_must_exist(tmp_path: Path):
    failures = check_report.check_report(full_report(), pdf_path=tmp_path / 'missing.pdf')['failures']
    assert 'the PDF is missing or empty' in failures


# check_citations

def test_citations_must_be_registered_and_linked():
    result = check_citations.check_citations(full_report(), SOURCES)
    assert result['passed'] and result['linked_urls'] >= 3
    orphan = check_citations.check_citations(full_report() + '<p>[S42]</p>', SOURCES)
    assert any('register lacks: S42' in f for f in orphan['failures'])


def test_ids_next_to_chinese_text_are_found():
    assert check_citations.check_citations('<p>来源S1、S2</p>', SOURCES[:2])['cited'] == ['S1', 'S2']


# check_evidence

ROW = {'source_ids': 'S1, S4', 'source_type': 'primary', 'finding': 'Gross margin rose to 41.3% in FY2025 from 39.6%.',
       'mechanism': 'Subscriptions carry a 78% margin, so mix shift lifts the blend.',
       'benchmark': 'Peer median gross margin is 36.5%.', 'weakens': 'Hardware margin fell to 28.1%.',
       'implication': 'Supports quality but not a discount valuation.', 'confidence': '高',
       'follow_up': 'Is the attach rate durable past FY2026?'}
PLAN = {'decision_question': 'Is the margin expansion structural?', 'thesis_sentence': 'Mix, not price, drives margins.',
        'why_different': 'Only section that reads the segment note.', 'mechanism': 'Subscription mix lifts margin.',
        'comparison_set': 'Four listed device makers.', 'counter_evidence': 'Hardware price war risk.',
        'visual': 'Statements table and a red-flag card.', 'prohibited': '不能被写成 a list of facts; no scaffolds.'}


def block(**changes) -> dict:
    return {'section': 'financials', 'queries': ['q1', 'q2', 'q3', 'q4'],
            'rows': [dict(ROW, finding=ROW['finding'] + f' Row {n}.') for n in range(4)],
            'gate': list(check_evidence.GATE_ITEMS), 'plan': PLAN, **changes}


def test_a_complete_evidence_block_passes_even_with_a_one_character_confidence():
    assert check_evidence.check_block(block(), SOURCES) == []


def test_the_prohibited_words_field_may_list_the_prohibited_words():
    # check_evidence.py failed a block for naming, in this very field, the phrases it prohibits.
    assert check_evidence.check_block(block(), SOURCES) == []
    rubric = dict(PLAN, mechanism='不能被写成 a list.')
    assert any('internal writing rubric' in f for f in check_evidence.check_block(block(plan=rubric), SOURCES))


def test_thin_or_unsourced_blocks_fail():
    failures = check_evidence.check_block(block(queries=['only one'], rows=[dict(ROW, mechanism='short')]), SOURCES)
    assert any('1 search queries' in f for f in failures) and any('evidence rows' in f for f in failures)
    assert any('row 1: too thin in Mechanism' in f for f in failures)
    company_only = [dict(ROW, source_ids='S7', source_type='company-provided') for _ in range(4)]
    failures = check_evidence.check_block(block(rows=company_only), SOURCES)
    assert any('primary or near-primary' in f for f in failures) and any('1 distinct' in f for f in failures)
    assert check_evidence.check_block(None, SOURCES)[0].startswith('no evidence block')


def test_secondary_is_not_mistaken_for_a_filing():
    secondary = [dict(ROW, source_ids='S5, S6', source_type='secondary research') for _ in range(4)]
    assert any('primary or near-primary' in f for f in check_evidence.check_block(block(rows=secondary), SOURCES))


def test_a_listed_companys_matrix_needs_its_public_equity_rows():
    blocks = {s.key: block(section=s.key) for s in sections.SECTIONS}
    failures = check_evidence.check_evidence(blocks, SOURCES, listed=True)['failures']
    assert 'public equity: no evidence row on consensus and guidance' in failures


# check_source_register

def test_the_register_needs_eight_usable_four_independent_and_one_primary_source():
    assert check_source_register.check_source_register(SOURCES)['passed']
    thin = check_source_register.check_source_register(SOURCES[:5])
    assert thin['failures'] == ['5 usable sources; needs 8 (each with a title, type, link or file, date, the claims it '
                                'supports and a confidence)']
    no_primary = [dict(s, source_type='secondary research') for s in SOURCES]
    assert 'no primary or near-primary source' in check_source_register.check_source_register(no_primary)['failures']


# check_workflow_docs

def workflow(**records) -> dict:
    return {'workflow': records}


def test_the_research_plan_needs_eight_gates_spines_and_a_hypothesis():
    plan = {'gates': list(check_workflow_docs.RESEARCH_GATES[:8]), 'hypothesis': 'Watchlist',
            'spines': [{'spine': 'Public equity', 'must_answer': 'Is the market mispricing cash flow?'}]}
    assert check_workflow_docs.check_research_plan(plan) == []
    assert check_workflow_docs.check_research_plan(dict(plan, gates=plan['gates'][:7]))


def test_the_profile_needs_every_item_and_the_evidence():
    complete = {'items': list(check_workflow_docs.PROFILE_ITEMS), 'evidence': 'x' * 240}
    assert check_workflow_docs.check_profile(complete) == []
    assert check_workflow_docs.check_profile(dict(complete, items=complete['items'][:4]))


def test_a_thesis_row_with_confidence_high_counts():
    rows = [{'component': c, 'belief': 'belief text', 'evidence': 'evidence [S1]', 'counter_evidence': 'counter text',
             'confidence': 'High', 'change': 'what changes'} for c in check_workflow_docs.THESIS_COMPONENTS]
    assert check_workflow_docs.check_thesis_table({'rows': rows}, listed=False) == []
    assert any('no row for' in f and 'Earnings quality' in f
               for f in check_workflow_docs.check_thesis_table({'rows': rows}, True))


def scenario_analysis(**changes) -> dict:
    case = {'driver': 'Attach rate rises', 'evidence': 'IR data [S8]', 'outcome': '$55 a share',
            'implication': 'Add to position'}
    return {'scenarios': [dict(case, case='Bull', probability='25%'), dict(case, case='Base', probability='50%'),
                          dict(case, case='Bear', probability='25%')],
            'assumptions': [{'assumption': f'Assumption {n}', 'confidence': 'medium', 'disproof': 'Attach falls',
                             'impact': '-18% EV', 'early_warning': 'Q1 churn'} for n in range(3)],
            'consensus': {'consensus': 'Software company in the making', 'our_view': 'Hardware base is shrinking',
                          'evidence': 'Device units fell 1.9% [S1]', 'proof_event': 'FY2026 attach disclosure'},
            'one_question': {'question': 'What share of subscriptions comes from old devices?',
                             'why': 'It shows whether growth rests on a shrinking installed base.'}, **changes}


def test_the_scenario_analysis_reads_probabilities_as_numbers_that_add_to_100():
    assert check_workflow_docs.check_scenario_analysis(scenario_analysis()) == []
    skewed = scenario_analysis()
    skewed['scenarios'][0]['probability'] = '45%'
    assert any('add up to 120%' in f for f in check_workflow_docs.check_scenario_analysis(skewed))
    two = scenario_analysis(one_question={'question': 'Why? How?', 'why': 'x' * 40})
    assert any('exactly one question' in f for f in check_workflow_docs.check_scenario_analysis(two))


def test_the_red_team_review_answers_all_seven_questions():
    answers = {key: 'A specific answer naming the receivables trend and the S2 filing note. ' * 2
               for key in check_workflow_docs.RED_TEAM_QUESTIONS}
    assert check_workflow_docs.check_red_team({'answers': answers}) == []
    del answers['ocr_claims']
    assert any('unanswered' in f for f in check_workflow_docs.check_red_team({'answers': answers}))


def test_an_open_rewrite_plan_fails_the_version_stage():
    case = workflow(rewrite_plan=[{'id': 'W1', 'section': 'financials', 'owner': 'Fundamentals Analyst',
                                   'problems': ['x'], 'created_at': '2026-10-29T00:00:00+00:00', 'resolved': False}])
    assert any('rewrite plan: 1 items unresolved' in f
               for f in check_workflow_docs.check_workflow_docs(case, True, 'version')['failures'])
    assert not any('rewrite plan' in f for f in check_workflow_docs.check_workflow_docs(case, True, 'draft')['failures'])


# diagnose_report and clean_output

def test_the_rewrite_plan_resolves_when_the_section_is_saved_again():
    items = diagnose_report.rewrite_plan({'financials': ['too short'], 'market': []}, ['no timeline'], '2026-10-29T01')
    assert [(i['section'], i['owner']) for i in items] == [('financials', 'Fundamentals Analyst'), (None, 'Lead Analyst')]
    diagnose_report.resolve(items, {'financials': {'saved_at': '2026-10-29T02', 'passed': False}}, '2026-10-29T03')
    assert all(i['resolved'] for i in items) and items[0]['still_failing']


def test_an_open_plan_is_never_an_item_and_report_items_resolve_when_checked_again():
    # A failed loop's open item once failed every later loop, which wrote it into the plan again.
    items = diagnose_report.rewrite_plan({}, ['rewrite plan: 1 items unresolved after a failed QA loop', 'no timeline'],
                                         '2026-10-29T01')
    assert [i['problems'] for i in items] == [['no timeline']]
    diagnose_report.resolve(items, {}, '2026-10-29T01')  # a check starting in the same second still counts
    assert items[0]['resolved']


def test_the_delivery_folder_holds_only_sources_one_html_and_one_pdf(tmp_path: Path):
    (tmp_path / 'sources').mkdir()
    (tmp_path / 'Report.html').write_text('x')
    (tmp_path / 'Report.pdf').write_text('x')
    assert clean_output.check_output(tmp_path)['passed']
    (tmp_path / 'notes.md').write_text('x')
    assert clean_output.check_output(tmp_path)['failures'] == ['working files left in the delivery folder: notes.md']
