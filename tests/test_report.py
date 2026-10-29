from pathlib import Path
import re

import pytest

from tools import report, sections
from tools.qa import check_report

from .report_samples import EXECUTIVE_SUMMARY, FINANCIALS, SCORING, SOURCES


def render(markdown: str) -> str:
    return report.render_section(markdown, SOURCES)


def test_prose_citations_become_tags_with_their_sources_confidence():
    html = render('Revenue rose 4.8% [S1]. Price context [S3, S5].')
    assert '<a href="#src-S1" class="source-tag">[S1]</a><span class="source-confidence conf-high">high</span>' in html
    # A group is one tag, and takes the lowest confidence of its sources.
    assert html.count('class="source-tag"') == 2
    assert 'conf-medium' in html and '<a href="#src-S5">S5</a>' in html


def test_table_citations_are_plain_links_that_do_not_count_as_tags():
    html = render('| Year | Revenue | Source |\n|---|---|---|\n| 2025 | $4.21B | S1, [S2] |')
    assert '<div class="table-wrap"><table class="data-table">' in html
    assert html.count('class="src-ref"') == 2 and 'source-tag' not in html


def test_an_id_missing_from_the_register_is_shown_but_not_linked():
    html = render('A claim [S99].')
    assert 'href="#src-S99"' not in html and '[S99]' in html


def test_each_component_renders_to_the_templates_classes():
    html = render(FINANCIALS) + render(EXECUTIVE_SUMMARY) + render(SCORING)
    for name in ('verdict-strip', 'briefing-grid', 'brief-card', 'efficiency-strip', 'eff-card', 'one-question',
                 'takeaway-strip', 'takeaway-item', 'info-card warning'):
        assert name in html, name
    timeline = render('::: timeline\n| Date | Event | Significance | Source |\n|---|---|---|---|\n'
                      '| 2007-01-09 | Launch | Created the category | S5 |\n:::')
    assert 'class="timeline"' in timeline and '<div class="date">2007-01-09</div>' in timeline
    risks = render('::: risk-matrix\n| Risk | Probability | Impact | Level | Source |\n|---|---|---|---|---|\n'
                   '| Price war | 30% | -20% EV | Critical | S5 |\n| Receivables | 20% | -8% EV | medium | S2 |\n:::')
    assert 'risk-matrix' in risks and 'class="level-critical"' in risks and 'class="level-medium"' in risks
    scenarios = render('::: scenarios\n| Scenario | Probability | Outcome | Source |\n|---|---|---|---|\n'
                       '| Bull | 25% | $55 | S3 |\n| Base case | 50% | $42 | S3 |\n| 熊市 | 25% | $30 | S3 |\n:::')
    assert all(f'<tr class="{case}">' in scenarios for case in ('bull', 'base', 'bear'))
    quad = render('::: quad\n| Quadrant | Points | Source |\n|---|---|---|\n| Strengths | Margin; Cash | S1 |\n'
                  '| Weaknesses | Receivables | S2 |\n| Opportunities | Attach | S8 |\n| Threats | Price war | S5 |\n:::')
    assert all(f'quad-{q}' in quad for q in ('strength', 'weakness', 'opportunity', 'threat'))
    analogs = render('::: analogs\n| Analog | Kind | Period | Lesson | Source |\n|---|---|---|---|---|\n'
                     '| Garmin | best | 2008-2012 | Services cushioned a hardware slump | S6 |\n'
                     '| BlackBerry | cautionary | 2010-2013 | Installed base fell faster than services grew | S6 |\n:::')
    assert 'analog-card best' in analogs and 'analog-card cautionary' in analogs
    evidence = render('::: evidence\n**Subscriptions carry the margin**\n\nThe segment note shows 78% margin [S1].\n:::')
    assert '<div class="evidence-card"><strong>Subscriptions carry the margin</strong>' in evidence
    sensitivity = render('::: sensitivity\n| Rank | Assumption | Impact on value | Impact level | Source |\n'
                         '|---|---|---|---|---|\n| 1 | Attach rate | -18% EV | High | S8 |\n:::')
    assert 'sensitivity-table' in sensitivity and 'class="high-impact"' in sensitivity


def test_component_text_is_not_counted_as_prose_paragraphs():
    html = render('::: info highlight\nFirst point [S1].\n\nSecond point.\n:::')
    assert '<p>' not in html and html.count('class="card-text"') == 2


def test_a_component_the_renderer_cannot_read_says_how_to_write_it():
    with pytest.raises(report.ComponentError, match='unknown component'):
        render('::: chart\n| a |\n:::')
    with pytest.raises(report.ComponentError, match='no closing'):
        render('::: kpi\n| Metric | Value |\n|---|---|\n| a | 1 |')
    with pytest.raises(report.ComponentError, match='needs a Markdown table'):
        render('::: kpi\nNo table here.\n:::')
    with pytest.raises(report.ComponentError, match='Strengths, Weaknesses'):
        render('::: quad\n| Quadrant | Points |\n|---|---|\n| Moat | Brand |\n:::')


def test_plain_markdown_keeps_component_content_without_the_fences():
    plain = report.plain_markdown(EXECUTIVE_SUMMARY)
    assert ':::' not in plain and '| Watchlist |' in plain
    assert report.components_in(EXECUTIVE_SUMMARY) == ['verdict', 'briefing', 'efficiency', 'one-question', 'takeaways']


def full_report(language: str = 'en', **extra) -> str:
    texts = {'executive_summary': EXECUTIVE_SUMMARY, 'financials': FINANCIALS, 'scoring': SCORING}
    cover = report.Cover('Northwind Devices', 'Devices and subscriptions', 'Sells devices with subscriptions.',
                         'Consumer electronics', 'Austin, TX', 'Listed (NASDAQ: NWD)')
    return report.render_report(texts, SOURCES, cover, '2026-10-28', '6.7', language, report_date='2026-10-29',
                                **extra)


def test_the_report_fills_every_template_placeholder():
    html = full_report()
    assert not re.findall(r'\{\{[A-Z0-9_]+\}\}', html)
    assert 'data-template-version="codex-compact-toc-v3"' in html and '<html lang="en">' in html
    assert '<meta name="composite-score" content="6.7">' in html
    assert '© 2026 Investment Analysis Skill' in html
    # A section missing from the version says so in its place.
    assert html.count(report.LABELS['en']['missing']) == 12
    assert '<html lang="zh-CN">' in full_report('zh') and report.LABELS['zh']['missing'] in full_report('zh')


def test_the_appendix_lists_each_cited_source_with_its_link_and_confidence():
    html = full_report(requests=[{'database': 'FDA 510(k)', 'query': 'K123456 status', 'why': 'Clearance gates sales',
                                  'how': 'Search accessdata.fda.gov'}], further=['financials: verify distributor terms'])
    assert '<tr id="src-S1"><td class="src-id">S1</td>' in html
    assert 'href="https://www.sec.gov/Archives/edgar/data/1/nwd-10k-2025.htm"' in html
    assert 'id="src-S7"' not in html  # registered but never cited
    assert 'User data requests' in html and 'K123456 status' in html
    assert 'Areas for further diligence' in html and 'verify distributor terms' in html


def test_a_client_document_links_to_the_delivery_folders_sources():
    deck = [*SOURCES, report_source := {**SOURCES[6], 'id': 'S9'}]
    html = report.source_appendix(deck, {'S9'}, 'en')
    assert report_source['location'].startswith('sources/') and 'href="sources/northwind_deck.pdf"' in html


def test_the_pdf_prints_from_the_html(tmp_path: Path):
    html_path = tmp_path / 'report.html'
    html_path.write_text(full_report())
    result = report.write_pdf(html_path, tmp_path / 'report.pdf')
    if 'error' in result and 'library' in result['error']:
        pytest.skip('WeasyPrint cannot find Pango on this machine')
    assert result['bytes'] > 10_000 and (tmp_path / 'report.pdf').read_bytes()[:4] == b'%PDF'


def test_names_follow_the_skills_output_contract():
    assert report.folder_name('Northwind Devices', 'consumer electronics') == 'NorthwindDevices_ConsumerElectronics'
    assert report.report_file_name('Northwind Devices', 'en') == 'NorthwindDevices_Investment_Report'
    assert report.report_file_name('北风科技', 'zh') == '北风科技_投资分析报告'


def test_the_report_language_follows_the_request():
    assert report.language_of('Prepare an investment memo on Apple (AAPL).') == 'en'
    assert report.language_of('帮我分析一下苹果公司（AAPL）是否值得买入') == 'zh'


def test_a_report_in_english_has_its_labels_and_disclaimers_in_english_too():
    template = report.TEMPLATE.read_text()
    assert all(chinese in template for chinese, _ in report.ENGLISH_CHROME)
    english, chinese = full_report(), full_report('zh')
    assert 'Report date' in english and 'it is not investment advice' in english
    assert all(text in english for text in check_report.REQUIRED_TEXT)  # the Chinese the skill's check needs
    assert 'Report date' not in chinese and 'not investment advice' not in chinese


def test_every_section_has_a_template_title():
    html = full_report()
    for section in sections.SECTIONS:
        assert f'<strong>{section.title_zh}</strong>' in html
