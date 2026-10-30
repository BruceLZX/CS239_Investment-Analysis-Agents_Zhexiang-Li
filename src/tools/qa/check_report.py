"""Report completeness, ported from the skill's scripts/check_report.py.

The rendered report keeps the template (its version marker, no old overlay TOC, no unfilled placeholder); its
executive summary is a real briefing (900+ characters, every element, a verdict strip and five briefing cards);
sources are visible but not over-tagged; the report holds at least four tables, scenarios, assumptions, a
consensus view and the geographic frame; a listed company's report covers price, the three statements, the notes,
valuation and position sizing; and the PDF exists.

Fixed or added here:
- The scenario rule counted only English "bull case"-style labels; Chinese labels and scenario-table rows count too.
- The assumption rule matched almost any text (".*" across the whole report); it needs the words themselves.
- The public-equity "valuation" group matched "pe" inside any English word; it needs P/E as a term.
- SKILL.md requires sixteen visual components in every report but the script checked two; all are checked here,
  with the composite score in the meta tag and section 14 (which nothing checked).
- The script allowed 60 inline source tags in a report while check_depth.py allows 6 a section, so fourteen
  sections within their own limit failed the report's. The report's limit is 6 for each of its fifteen sections,
  the executive summary included (90).
- A KPI signal counted only good and warning cards, so a company whose every KPI was critical, as in a Pass,
  had none; the template's critical card counts too.
"""
from pathlib import Path
import re

from .. import report as report_module, sections
from .check_depth import MAX_INLINE_TAGS
from .terms import BOILERPLATE_LIMITS, FORBIDDEN_PATTERNS, missing_groups, strip_html

EXEC_SUMMARY_RE = re.compile(r'<section[^>]+class="[^"]*exec-summary[^"]*"[\s\S]*?>(?P<body>[\s\S]*?)</section>')
MIN_EXEC_CHARS = 900
MIN_BRIEF_CARDS = 5
MIN_SOURCE_MENTIONS = 30
MAX_SOURCE_TAGS = MAX_INLINE_TAGS * len(sections.ALL_SECTIONS)
MIN_TABLES = 4
MAX_KPI_DASHBOARDS = 6
REQUIRED_TEXT = ('5分钟速读', '重要声明', '数据截至', '风险', '投资')
EXEC_GROUPS = {
    'verdict/action': ('结论', '建议', '行动', 'verdict', 'action', 'recommend'),
    'score/rating': ('评分', '评级', 'score', 'rating'),
    'core positives': ('核心理由', '正面', '优势', 'bull', 'positive', 'strength', 'in favour', 'in favor'),
    'key risks': ('风险', '下行', 'bear', 'risk'),
    'evidence confidence': ('置信', 'confidence', '证据质量', 'source confidence'),
    'valuation/terms': ('估值', '价格', '条款', 'valuation', 'price', 'terms'),
    'follow-up diligence': ('尽调', '待验证', '待核实', 'follow-up', 'diligence'),
    'one question': ('最重要的问题', '一个问题', 'one question', '关键问题'),
    'three takeaways': ('三件事', '三个要点', 'three takeaways', 'three things'),
}
PUBLIC_EQUITY_GROUPS = {
    'stock price context': ('股价', 'share price', '价格截至', '交易日', '市值', 'market cap', 'ticker', '证券代码'),
    'income statement quality': ('利润表', '收入', '毛利率', '营业利润', '净利润', 'eps', 'margin', 'earnings quality', '盈利质量'),
    'cash flow': ('现金流', '经营现金流', '自由现金流', 'capex', '资本开支', 'fcf', 'cash conversion', '现金转化', 'cash flow'),
    'balance sheet': ('资产负债表', '资产', '负债', '现金', '债务', '流动性', '杠杆', 'balance sheet', 'debt', 'liquidity'),
    'notes/accounting quality': ('附注', '会计', '审计', '减值', '关联方', '表外', 'accounting', 'auditor', 'impairment',
                                 'related-party', 'related party'),
    'valuation': ('估值', 'p/e', 'ev/ebitda', 'ev/sales', 'p/b', 'fcf yield', '市盈率', '市净率'),
    'position sizing': ('仓位', 'position sizing', '配置', 'starter position', 'full position', 'watchlist', 'buy',
                        'hold', 'reduce', 'sell'),
}
SCENARIO_RE = re.compile(r'(?:bull|bear|base)\s*(?:case|情景|场景)|牛市情景|基准情景|熊市情景|乐观情景|悲观情景', re.I)
ASSUMPTION_RE = re.compile(r'关键假设|敏感性分析|sensitivity|key assumption', re.I)
CONSENSUS_RE = re.compile(r'非共识|non.consensus|variant perception|市场共识|共识|consensus', re.I)
GEOGRAPHY_RE = re.compile(r'地理|市场体系|国内|国际|海外|本土|全球|区域|跨境|客户市场|供应链|资本市场|退出市场|home market|'
                          r'customer market|supplier market|capital market|exit market|geographic|domestic|international|'
                          r'overseas|region|cross-border', re.I)
SOURCE_WORDS_RE = re.compile(r'来源|Source|source|公告|年报|招股书|专利|监管|filing|10-K|10-Q|annual report|disclosed')
# The sixteen components SKILL.md requires in every report, by the class (or classes) that show each is there.
REQUIRED_COMPONENTS = {
    'verdict strip': ('verdict-strip',), 'briefing grid': ('briefing-grid', 'brief-card'),
    'KPI dashboard': ('kpi-dashboard', 'kpi-card'), 'KPI signal': ('kpi-good', 'kpi-warn', 'kpi-critical'),
    'efficiency strip': ('efficiency-strip', 'eff-card'), 'one question': ('one-question',),
    'three takeaways': ('takeaway-strip', 'takeaway-item'), 'scenario table': ('scenario-table',),
    'scenario rows': ('bull', 'base', 'bear'), 'sensitivity table': ('sensitivity-table',),
    'high-impact assumption': ('high-impact',), 'risk matrix': ('risk-matrix',),
    'critical or high risk level': ('level-critical', 'level-high'), 'timeline': ('timeline', 'timeline-item'),
    'source tags': ('source-tag',), 'source confidence': ('source-confidence',),
    'data tables': ('table-wrap', 'data-table'), 'info cards': ('info-card',), 'evidence cards': ('evidence-card',),
    'quad grid': ('quad-grid',), 'analog grid': ('analog-grid', 'analog-card'),
}
ANY_OF = {'KPI signal', 'critical or high risk level'}  # one of the classes is enough; otherwise all are needed


def _class_count(markup: str, name: str) -> int:
    return len(re.findall(r'class="[^"]*\b' + re.escape(name) + r'\b[^"]*"', markup))


def executive_summary_failures(summary_html: str) -> list[str]:
    """The executive summary's own rules, which also run when the Lead saves it."""
    text = strip_html(summary_html)
    failures = []
    if len(text) < MIN_EXEC_CHARS:
        failures.append(f'executive summary has {len(text):,} characters; needs {MIN_EXEC_CHARS:,}')
    failures += [f'executive summary has no {group}' for group in missing_groups(text, EXEC_GROUPS)]
    if _class_count(summary_html, 'verdict-strip') < 1:
        failures.append('executive summary has no verdict strip')
    cards = _class_count(summary_html, 'brief-card')
    if cards < MIN_BRIEF_CARDS:
        failures.append(f'executive summary has {cards} briefing cards; needs {MIN_BRIEF_CARDS}')
    tags = _class_count(summary_html, 'source-tag')
    if tags > MAX_INLINE_TAGS:
        failures.append(f'executive summary has {tags} inline source tags; at most {MAX_INLINE_TAGS} (cite per '
                        "paragraph, and put row-level sources in a table's Source column)")
    return failures


def check_report(report_html: str, pdf_path: str | Path | None = None, listed: bool = True,
                 composite_score: str | None = None) -> dict:
    failures = []
    if f'data-template-version="{report_module.TEMPLATE_VERSION}"' not in report_html:
        failures.append('the template version marker is missing')
    if re.search(r'id="openToc"|id="tocBackdrop"|id="closeToc"|setTocOpen\(', report_html):
        failures.append('old overlay TOC code is present')
    placeholders = sorted(set(re.findall(r'\{\{[A-Z0-9_]+\}\}', report_html)))
    if placeholders:
        failures.append('unfilled placeholders: ' + ', '.join(placeholders))
    failures += [f'missing the text "{text}"' for text in REQUIRED_TEXT if text not in report_html]

    summary = EXEC_SUMMARY_RE.search(report_html)
    failures += executive_summary_failures(summary.group('body') if summary else '')

    visible = strip_html(report_html)
    mentions = len(re.findall(r'class="[^"]*source-(?:tag|confidence)[^"]*"', report_html)) + len(SOURCE_WORDS_RE.findall(visible))
    if mentions < MIN_SOURCE_MENTIONS:
        failures.append(f'{mentions} source mentions; needs {MIN_SOURCE_MENTIONS}')
    tags = _class_count(report_html, 'source-tag')
    if tags > MAX_SOURCE_TAGS:
        failures.append(f'{tags} inline source tags; at most {MAX_SOURCE_TAGS}')
    if len(re.findall(r'class="[^"]*citation-line[^"]*"|引用锚点', report_html)) > 1:
        failures.append('repeated citation-anchor blocks')
    if not re.search(r'数据来源与引用|引用附录|Source Appendix', visible, re.I):
        failures.append('no source appendix')
    if len(re.findall(r'<a\s+[^>]*href=', report_html)) < 5:
        failures.append('fewer than five links')
    for pattern, most in BOILERPLATE_LIMITS:
        found = len(re.findall(pattern, visible, re.I))
        if found > most:
            failures.append(f'"{pattern}" appears {found} times; at most {most}')
    failures += [f'writes about how the report is made ("{m.group()}")'
                 for pattern in FORBIDDEN_PATTERNS for m in [re.search(pattern, visible, re.I)] if m]
    tables = len(re.findall(r'<table\b', report_html))
    if tables < MIN_TABLES:
        failures.append(f'{tables} tables; needs {MIN_TABLES}')
    dashboards = _class_count(report_html, 'kpi-dashboard')
    if dashboards > MAX_KPI_DASHBOARDS:
        failures.append(f'{dashboards} KPI dashboards; at most {MAX_KPI_DASHBOARDS} (a KPI strip in every section is a layout failure)')
    scenarios = len(SCENARIO_RE.findall(visible)) + sum(_class_count(report_html, c) for c in ('bull', 'base', 'bear'))
    if scenarios < 3:
        failures.append('no bull, base and bear scenarios')
    if not ASSUMPTION_RE.search(visible):
        failures.append('no key assumptions or sensitivity analysis')
    if not CONSENSUS_RE.search(visible):
        failures.append('no consensus or non-consensus view')
    if not GEOGRAPHY_RE.search(visible):
        failures.append('no geographic or market-system frame')
    if listed:
        lowered = visible.lower()
        for group, words in PUBLIC_EQUITY_GROUPS.items():
            if not any(re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', lowered) if w.isascii() else w in lowered
                       for w in words):
                failures.append(f'public equity: no {group}')
    for name, classes in REQUIRED_COMPONENTS.items():
        present = [_class_count(report_html, c) > 0 for c in classes]
        if not (any(present) if name in ANY_OF else all(present)):
            failures.append(f'missing the {name} component')
    meta = re.search(r'<meta name="composite-score" content="([^"]*)"', report_html)
    if not meta or not re.fullmatch(r'\d{1,2}(?:\.\d)?', meta.group(1)):
        failures.append('the composite-score meta tag has no score')
    elif composite_score is not None and meta.group(1) != composite_score:
        failures.append(f'the meta composite score {meta.group(1)} differs from section 14\'s {composite_score}')
    if pdf_path is not None:
        pdf = Path(pdf_path)
        if not pdf.exists() or pdf.stat().st_size == 0:
            failures.append('the PDF is missing or empty')
    return {'failures': failures, 'passed': not failures, 'source_tags': tags, 'tables': tables}
