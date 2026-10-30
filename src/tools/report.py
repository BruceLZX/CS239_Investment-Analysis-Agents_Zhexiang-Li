"""The report: its HTML template filled in, a PDF printed from it, and a
delivery folder holding only sources/, the HTML and the PDF.

Bots write each section in Markdown. A visual component is a fenced block holding a Markdown table or list:

    ::: kpi
    | Metric | Value | Benchmark | Signal | Source |
    |---|---|---|---|---|
    | FY2025 revenue | $416.2B | +6.4% YoY | good | S3 |
    :::

render_section turns a section into the template's markup: components into the template's classes, every
other table into .table-wrap > .data-table, and citations into links to the source appendix. In prose a citation
is a .source-tag pill with its source's confidence; inside a table it is a plain link, so tables with a Source
column on every row stay within the limit on inline tags (six per section).
"""
from dataclasses import dataclass
from datetime import date
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from markdown_it import MarkdownIt

from . import sections

TEMPLATE = Path(__file__).resolve().parent / 'templates' / 'report_template.html'
TEMPLATE_VERSION = 'codex-compact-toc-v3'
MD = MarkdownIt('commonmark', {'html': False}).enable(['table', 'strikethrough'])

FENCE_OPEN_RE = re.compile(r'^:::\s*([a-z][a-z-]*)(?:\s+([a-z-]+))?\s*$')
FENCE_CLOSE_RE = re.compile(r'^:::\s*$')
# A citation group in prose: [S1], [S1, S3] or [S1][S3]. Python's \b treats Chinese characters as word characters,
# so lookarounds stand in for it (a plain \bS\d+\b misses "来源S1").
CITE_GROUP_RE = re.compile(r'(?:\[\s*S\d+(?:\s*[,;，、]\s*S\d+)*\s*\])+')
SOURCE_ID_RE = re.compile(r'(?<![A-Za-z0-9])S\d+(?!\d)')
TABLE_RE = re.compile(r'<table\b.*?</table>', re.S)
TAG_RE = re.compile(r'(<[^>]+>)')

# The component kinds a section may hold, and the class each renders to.
# Source tags and data tables are rendered automatically.
COMPONENTS = {
    'verdict': 'verdict-strip', 'briefing': 'briefing-grid', 'kpi': 'kpi-dashboard', 'efficiency': 'efficiency-strip',
    'one-question': 'one-question', 'takeaways': 'takeaway-strip', 'scenarios': 'scenario-table',
    'sensitivity': 'sensitivity-table', 'risk-matrix': 'risk-matrix', 'timeline': 'timeline', 'info': 'info-card',
    'evidence': 'evidence-card', 'quad': 'quad-grid', 'analogs': 'analog-grid',
}
INFO_KINDS = ('highlight', 'warning', 'danger')
LABELS = {
    'en': {'one_question': 'The one question', 'takeaways': 'Three takeaways', 'missing': 'Not available in this version.',
           'high': 'high', 'medium': 'medium', 'low': 'low', 'strengths': 'Strengths', 'weaknesses': 'Weaknesses',
           'opportunities': 'Opportunities', 'threats': 'Threats', 'appendix_id': 'ID', 'appendix_source': 'Source',
           'appendix_link': 'Link or file', 'appendix_conf': 'Confidence', 'requests': 'User data requests',
           'further': 'Areas for further diligence', 'tagline': 'Investment research report'},
    'zh': {'one_question': '最重要的问题', 'takeaways': '三个要点', 'missing': '本版本缺失。', 'high': '高', 'medium': '中',
           'low': '低', 'strengths': '优势', 'weaknesses': '劣势', 'opportunities': '机会', 'threats': '威胁',
           'appendix_id': '编号', 'appendix_source': '来源', 'appendix_link': '链接或文件', 'appendix_conf': '置信度',
           'requests': '监管数据库信息请求', 'further': '待尽调事项', 'tagline': '投资分析报告'},
}
# The template's chrome is Chinese, with bilingual section titles. A report in English gets the English beside the
# cover's labels, the briefing's subtitle and the disclaimers; the Chinese stays, since check_report.py looks for it.
ENGLISH_CHROME = (
    ('<span>报告日期</span>', '<span>报告日期 Report date</span>'),
    ('<span>数据截至</span>', '<span>数据截至 Data as of</span>'),
    ('<span>行业</span>', '<span>行业 Industry</span>'),
    ('<span>总部</span>', '<span>总部 Headquarters</span>'),
    ('<span>阶段</span>', '<span>阶段 Stage</span>'),
    ('先读这里即可了解总体判断、核心理由、主要风险和下一步尽调重点。</p>',
     '先读这里即可了解总体判断、核心理由、主要风险和下一步尽调重点。<br>Read this first for the overall judgement, the '
     'core reasons, the main risks and the next diligence steps.</p>'),
    ('<strong>重要声明：</strong>', '<strong>重要声明 Important notice：</strong>'),
    ('本报告由 AI 辅助生成，分析独立，未受被分析公司委托或资助。',
     '本报告由 AI 辅助生成，分析独立，未受被分析公司委托或资助。<br>This report was generated from public information, '
     'materials the user provided and web research, for investment research only; it is not investment advice. It may '
     'be incomplete, out of date or biased by its sources: investment decisions need professional judgement and a '
     'licensed adviser. It was produced with AI assistance, independently, and was neither commissioned nor paid for by '
     'the company analysed.'),
    ('<p>本报告由 AI 辅助生成，基于公开信息独立分析，不构成投资建议。</p>',
     '<p>本报告由 AI 辅助生成，基于公开信息独立分析，不构成投资建议。<br>Produced with AI assistance from public '
     'information, independently; for research only and not investment advice.</p>'),
)
QUADRANTS = {'strength': ('strength', 's', '优势'), 'weakness': ('weakness', 'w', '劣势'),
             'opportunity': ('opportunit', 'o', '机会'), 'threat': ('threat', 't', '威胁')}
QUADRANT_LABELS = {'strength': 'strengths', 'weakness': 'weaknesses', 'opportunity': 'opportunities',
                   'threat': 'threats'}


class ComponentError(ValueError):
    """A fenced component the renderer cannot read; the message says how to write it."""


@dataclass
class Cover:
    company: str
    tagline: str = ''
    business_summary: str = ''
    industry: str = ''
    headquarters: str = ''
    stage: str = ''


def language_of(text: str) -> str:
    """'zh' when the text is mostly Chinese, else 'en' (the report matches the user's language)."""
    cjk = len(re.findall(r'[一-鿿]', text or ''))
    return 'zh' if cjk >= max(4, len(re.findall(r'[A-Za-z]{2,}', text or '')) // 4) else 'en'


# Markdown pieces

def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def table_rows(markdown: str) -> list[list[str]]:
    """The first Markdown table in the text as rows of cells, header first; [] when there is none."""
    rows = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith('|'):
            if re.fullmatch(r'\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?', stripped):
                continue
            rows.append(_cells(stripped))
        elif rows:
            break
    return rows


def list_items(markdown: str) -> list[str]:
    """The items of a Markdown list (bulleted or numbered), continuation lines joined."""
    items: list[str] = []
    for line in markdown.splitlines():
        match = re.match(r'^\s*(?:[-*+]|\d+[.)])\s+(.*)$', line)
        if match:
            items.append(match.group(1).strip())
        elif items and line.strip():
            items[-1] += ' ' + line.strip()
    return items


def split_components(markdown: str) -> list[tuple[str | None, str | None, str]]:
    """The section as (kind, modifier, body) pieces in order; kind is None for plain Markdown."""
    pieces: list[tuple[str | None, str | None, str]] = []
    plain: list[str] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        opening = FENCE_OPEN_RE.match(lines[i].strip())
        if not opening:
            plain.append(lines[i])
            i += 1
            continue
        kind, modifier = opening.groups()
        if kind not in COMPONENTS:
            raise ComponentError(f'unknown component "::: {kind}". Components: {", ".join(COMPONENTS)}.')
        end = next((j for j in range(i + 1, len(lines)) if FENCE_CLOSE_RE.match(lines[j].strip())), None)
        if end is None:
            raise ComponentError(f'"::: {kind}" has no closing ":::" line.')
        if plain:
            pieces.append((None, None, '\n'.join(plain)))
            plain = []
        pieces.append((kind, modifier, '\n'.join(lines[i + 1:end])))
        i = end + 1
    if plain:
        pieces.append((None, None, '\n'.join(plain)))
    return pieces


def plain_markdown(markdown: str) -> str:
    """The section as readable Markdown: fence lines dropped, the content they hold kept."""
    return '\n'.join(line for line in markdown.splitlines()
                     if not (FENCE_OPEN_RE.match(line.strip()) or FENCE_CLOSE_RE.match(line.strip())))


# Citations

def _confidence(source: dict | None) -> str:
    value = (source or {}).get('confidence', '').lower()
    return next((level for level in ('low', 'medium', 'high') if level in value), 'medium')


def _lowest(levels: list[str]) -> str:
    return min(levels, key=('low', 'medium', 'high').index) if levels else 'medium'


def _link(source_id: str, by_id: dict) -> str:
    if source_id in by_id:
        return f'<a href="#src-{source_id}">{source_id}</a>'
    return source_id


def _text_nodes(fragment: str, change) -> str:
    """Apply change to the text between tags, never to a tag or its attributes."""
    parts = TAG_RE.split(fragment)
    return ''.join(part if part.startswith('<') else change(part) for part in parts)


def _refs(text: str, by_id: dict) -> str:
    """Source IDs in a table cell or a card's source line as plain links to the appendix: a table carries a source
    on every row, so these do not count against the limit on inline tags."""
    text = re.sub(r'\[(\s*S\d+(?:\s*[,;，、]\s*S\d+)*\s*)\]', r'\1', text)
    return SOURCE_ID_RE.sub(
        lambda m: f'<a class="src-ref" href="#src-{m.group()}">{m.group()}</a>' if m.group() in by_id else m.group(),
        text)


def _prose_citations(fragment: str, by_id: dict, labels: dict) -> str:
    def tag(match: re.Match) -> str:
        ids = list(dict.fromkeys(SOURCE_ID_RE.findall(match.group())))
        level = _lowest([_confidence(by_id.get(i)) for i in ids if i in by_id])
        if len(ids) == 1 and ids[0] in by_id:
            pill = f'<a href="#src-{ids[0]}" class="source-tag">[{ids[0]}]</a>'
        else:
            pill = '<span class="source-tag">[' + ', '.join(_link(i, by_id) for i in ids) + ']</span>'
        return pill + f'<span class="source-confidence conf-{level}">{labels[level]}</span>'
    return _text_nodes(fragment, lambda text: CITE_GROUP_RE.sub(tag, text))


def _citations(fragment: str, by_id: dict, labels: dict) -> str:
    """Citations in rendered HTML: tags in prose, plain links in tables."""
    out, last = [], 0
    for match in TABLE_RE.finditer(fragment):
        out.append(_prose_citations(fragment[last:match.start()], by_id, labels))
        out.append(_text_nodes(match.group(), lambda text: _refs(text, by_id)))
        last = match.end()
    out.append(_prose_citations(fragment[last:], by_id, labels))
    return ''.join(out)


def _inline(text: str) -> str:
    """One line of Markdown (bold, italics, code) as inline HTML."""
    return MD.renderInline(text)


def _blocks(markdown: str) -> str:
    """Markdown inside a card: paragraphs become divs, so only a section's prose counts as its paragraphs."""
    rendered = MD.render(markdown).strip()
    return re.sub(r'<p>(.*?)</p>', r'<div class="card-text">\1</div>', rendered, flags=re.S)


def _data_tables(rendered: str, extra_class: str = '') -> str:
    classes = ' '.join(filter(None, ('data-table', extra_class)))
    return rendered.replace('<table>', f'<div class="table-wrap"><table class="{classes}">').replace(
        '</table>', '</table></div>')


# Components

def _need_table(kind: str, rows: list[list[str]], columns: str) -> list[list[str]]:
    if len(rows) < 2:
        raise ComponentError(f'"::: {kind}" needs a Markdown table: {columns}.')
    return rows


def _column(header: list[str], *words: str) -> int | None:
    return next((i for i, cell in enumerate(header) if any(word in cell.lower() for word in words)), None)


def _source_cell(header: list[str], row: list[str], by_id: dict) -> str:
    column = _column(header, 'source', '来源')
    cell = row[column] if column is not None and column < len(row) else ''
    return f'<span class="card-sources">{_refs(html.escape(cell), by_id)}</span>' if cell else ''


def _render_component(kind: str, modifier: str | None, body: str, labels: dict, by_id: dict) -> str:
    rows = table_rows(body)
    if kind == 'verdict':
        header, *data = _need_table(kind, rows, 'one row such as | Rating | Action | Score | Confidence | Horizon | '
                                                'Source |')
        values = data[0]
        source = _column(header, 'source', '来源')
        parts = ''.join(f'<span>{_inline(h)}: {_inline(v)}</span>' for i, (h, v) in enumerate(zip(header, values))
                        if i and v and i != source)
        return (f'<div class="verdict-strip"><strong>{_inline(values[0])}</strong>{parts}'
                f'{_source_cell(header, values, by_id)}</div>')
    if kind == 'briefing':
        cards = []
        if rows:
            header, *data = rows
            for row in data:
                text = row[1] if len(row) > 1 else ''
                cards.append((row[0], _inline(text) + ' ' + _source_cell(header, row, by_id)))
        else:
            for item in list_items(body):
                title, _, text = item.partition(':')
                cards.append((title.strip('* '), _inline(text.strip())))
        if not cards:
            raise ComponentError('"::: briefing" needs a table | Card | Text | Source | or a list of "**Title:** text" items.')
        return '<div class="briefing-grid">' + ''.join(
            f'<div class="brief-card"><h4>{_inline(t)}</h4><p>{x}</p></div>' for t, x in cards) + '</div>'
    if kind == 'kpi':
        header, *data = _need_table(kind, rows, '| Metric | Value | Benchmark | Signal | Source |')
        signal = _column(header, 'signal', '信号', 'status')
        cards = []
        for row in data:
            tone = (row[signal] if signal is not None and signal < len(row) else '').lower()
            card, bench = ('kpi-critical', ' worse') if re.search(r'critical|bad|red|危', tone) else \
                (('kpi-warn', ' worse') if re.search(r'warn|amber|watch|警', tone) else
                 (('kpi-good', ' better') if re.search(r'good|green|strong|好|优', tone) else ('', '')))
            benchmark = row[2] if len(row) > 2 and (signal is None or signal != 2) else ''
            source = _source_cell(header, row, by_id)
            classes = ' '.join(filter(None, ('kpi-card', card)))
            cards.append(f'<div class="{classes}"><div class="kpi-label">{_inline(row[0])}</div>'
                         f'<div class="kpi-value">{_inline(row[1] if len(row) > 1 else "")}</div>'
                         f'<div class="kpi-benchmark{bench}">{_inline(benchmark)} {source}</div></div>')
        return '<div class="kpi-dashboard">' + ''.join(cards) + '</div>'
    if kind == 'efficiency':
        header, *data = _need_table(kind, rows, '| Measure | Value | Source |')
        return '<div class="efficiency-strip">' + ''.join(
            f'<div class="eff-card"><div class="eff-value">{_inline(row[1] if len(row) > 1 else "")}</div>'
            f'<div class="eff-label">{_inline(row[0])} {_source_cell(header, row, by_id)}</div></div>' for row in data) + '</div>'
    if kind == 'one-question':
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
        if not paragraphs:
            raise ComponentError('"::: one-question" needs the question, then a paragraph on why it decides the case.')
        why = ' '.join(paragraphs[1:])
        return (f'<div class="one-question"><div class="question-label">{labels["one_question"]}</div>'
                f'<blockquote>{_inline(paragraphs[0])}</blockquote>'
                + (f'<div class="why">{_inline(why)}</div>' if why else '') + '</div>')
    if kind == 'takeaways':
        items = list_items(body)
        if not items:
            raise ComponentError('"::: takeaways" needs a numbered list of three takeaways.')
        return (f'<div class="takeaway-strip"><h4>{labels["takeaways"]}</h4>'
                + ''.join(f'<div class="takeaway-item"><span>{_inline(item)}</span></div>' for item in items) + '</div>')
    if kind == 'scenarios':
        _need_table(kind, rows, '| Scenario | Probability | Drivers | Outcome | Signposts | Source |')
        rendered = _data_tables(MD.render(body), 'scenario-table')

        def case_class(match: re.Match) -> str:
            row = match.group()
            first = re.search(r'<td>(.*?)</td>', row, re.S)
            label = (first.group(1) if first else '').lower()
            case = next((c for c, words in (('bull', ('bull', '牛')), ('base', ('base', '基准', '基本')),
                                            ('bear', ('bear', '熊'))) if any(w in label for w in words)), None)
            return row.replace('<tr>', f'<tr class="{case}">', 1) if case else row
        return re.sub(r'<tr>.*?</tr>', case_class, rendered, flags=re.S)
    if kind in ('sensitivity', 'risk-matrix'):
        columns = ('| Rank | Assumption | Base | What would disprove it | Impact on value | Impact level | Early warning | Source |'
                   if kind == 'sensitivity' else
                   '| Risk | Probability | Impact | Level | Timing | Signpost | Mitigation | Source |')
        _need_table(kind, rows, columns)
        rendered = _data_tables(MD.render(body), COMPONENTS[kind])
        levels = (('critical', ('critical', 'fatal', '致命')), ('high', ('high', '高')),
                  ('medium', ('medium', 'moderate', '中')), ('low', ('low', '低')))

        def level_cell(match: re.Match) -> str:
            text = re.sub(r'<[^>]+>', '', match.group(1)).strip().lower()
            if len(text) > 12:
                return match.group()
            level = next((name for name, words in levels if any(text.startswith(w) for w in words)), None)
            if not level:
                return match.group()
            if kind == 'sensitivity':
                level = 'high' if level == 'critical' else level
                return f'<td class="{level}-impact">{match.group(1)}</td>'
            return f'<td class="level-{level}">{match.group(1)}</td>'
        return re.sub(r'<td>(.*?)</td>', level_cell, rendered, flags=re.S)
    if kind == 'timeline':
        header, *data = _need_table(kind, rows, '| Date | Event | Significance | Source |')
        items = []
        for row in data:
            significance = row[2] if len(row) > 2 and _column(header, 'source', '来源') != 2 else ''
            items.append(f'<div class="timeline-item"><div class="date">{_inline(row[0])}</div>'
                         f'<div><strong>{_inline(row[1] if len(row) > 1 else "")}</strong>'
                         + (f' — {_inline(significance)}' if significance else '')
                         + f' {_source_cell(header, row, by_id)}</div></div>')
        return '<div class="timeline">' + ''.join(items) + '</div>'
    if kind == 'info':
        variant = modifier if modifier in INFO_KINDS else 'highlight'
        return f'<div class="info-card {variant}">{_blocks(body)}</div>'
    if kind == 'evidence':
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
        if not paragraphs:
            raise ComponentError('"::: evidence" needs a bold claim line, then the evidence for it with source IDs.')
        title = paragraphs[0].strip('* ')
        return (f'<div class="evidence-card"><strong>{_inline(title)}</strong>'
                + _blocks('\n\n'.join(paragraphs[1:])) + '</div>')
    if kind == 'quad':
        header, *data = _need_table(kind, rows, '| Quadrant | Points | Source | with Strengths, Weaknesses, '
                                                'Opportunities and Threats rows')
        boxes = []
        for row in data:
            label = row[0].strip('* ').lower()
            quadrant = next((q for q, words in QUADRANTS.items()
                             if any(label.startswith(w) if len(w) == 1 else w in label for w in words)), None)
            if not quadrant:
                raise ComponentError(f'"::: quad" row "{row[0]}" is not Strengths, Weaknesses, Opportunities or Threats.')
            points = [p.strip() for p in re.split(r';|；', row[1] if len(row) > 1 else '') if p.strip()]
            title = labels[QUADRANT_LABELS[quadrant]]
            boxes.append(f'<div class="quad-item quad-{quadrant}"><h4>{title}</h4><ul>'
                         + ''.join(f'<li>{_inline(p)}</li>' for p in points)
                         + f'</ul><div class="card-text">{_source_cell(header, row, by_id)}</div></div>')
        return '<div class="quad-grid">' + ''.join(boxes) + '</div>'
    if kind == 'analogs':
        header, *data = _need_table(kind, rows, '| Analog | Kind (best or cautionary) | Period | Lesson | Source |')
        kind_col = _column(header, 'kind', 'type', '类型')
        lesson_col = _column(header, 'lesson', '启示', '教训')
        period_col = _column(header, 'period', 'year', '时间')
        cards = []
        for row in data:
            label = (row[kind_col] if kind_col is not None and kind_col < len(row) else '').lower()
            variant = 'cautionary' if re.search(r'caution|warning|negative|警示|反面', label) else 'best'
            period = row[period_col] if period_col is not None and period_col < len(row) else ''
            lesson = row[lesson_col] if lesson_col is not None and lesson_col < len(row) else row[-1]
            cards.append(f'<div class="analog-card {variant}"><h4>{_inline(row[0])}'
                         + (f' ({_inline(period)})' if period else '') + '</h4>'
                         f'<div class="lesson">{_inline(lesson)} {_source_cell(header, row, by_id)}</div></div>')
        return '<div class="analog-grid">' + ''.join(cards) + '</div>'
    raise ComponentError(f'unknown component "::: {kind}".')


def render_section(markdown: str, sources: list[dict], language: str = 'en') -> str:
    """A section's Markdown as the template's HTML. Raises ComponentError for a component it cannot read."""
    labels = LABELS.get(language, LABELS['en'])
    by_id = {source['id']: source for source in sources}
    out = []
    for kind, modifier, body in split_components(markdown):
        if kind is None:
            out.append(_data_tables(MD.render(body)))
        else:
            out.append(_render_component(kind, modifier, body, labels, by_id))
    return _citations('\n'.join(out), by_id, labels)


def components_in(markdown: str) -> list[str]:
    """The component kinds a section holds, in order."""
    return [kind for kind, _, _ in split_components(markdown) if kind]


# The whole report

def source_appendix(sources: list[dict], cited: set[str], language: str, requests: list[dict] | None = None,
                    further: list[str] | None = None) -> str:
    """The appendix rows for every cited source, then any user data requests and open diligence items."""
    labels = LABELS.get(language, LABELS['en'])
    rows = []
    for source in sources:
        if source['id'] not in cited:
            continue
        location = source.get('location', '')
        # A web source links to its URL, a client document to its copy in the delivery folder's sources/.
        href = (location if re.match(r'https?://', location) else
                location.split(' ')[0] if location.startswith('sources/') else '')
        description = ' · '.join(filter(None, (source.get('title', ''), source.get('source_type', ''),
                                                source.get('date', ''))))
        claims = source.get('claims', '')
        level = _confidence(source)
        rows.append(f'<tr id="src-{source["id"]}"><td class="src-id">{source["id"]}</td>'
                    f'<td class="src-desc">{html.escape(description)}'
                    + (f'<br><span class="src-claims">{html.escape(claims)}</span>' if claims else '') + '</td>'
                    f'<td class="src-url">' + (f'<a href="{html.escape(href, quote=True)}">{html.escape(location)}</a>'
                                               if href else html.escape(location)) + '</td>'
                    f'<td class="src-conf"><span class="source-confidence conf-{level}">{labels[level]}</span></td></tr>')
    parts = [f'<table class="source-appendix-table"><thead><tr><th>{labels["appendix_id"]}</th>'
             f'<th>{labels["appendix_source"]}</th><th>{labels["appendix_link"]}</th><th>{labels["appendix_conf"]}</th>'
             f'</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>']
    if requests:
        parts.append(f'<h4>{labels["requests"]}</h4><div class="table-wrap"><table class="data-table"><thead><tr>'
                     '<th>#</th><th>Database</th><th>What to look up</th><th>Why it matters</th><th>How to get it</th>'
                     '</tr></thead><tbody>' + ''.join(
                         f'<tr><td>{n}</td><td>{html.escape(r["database"])}</td><td>{html.escape(r["query"])}</td>'
                         f'<td>{html.escape(r["why"])}</td><td>{html.escape(r["how"])}</td></tr>'
                         for n, r in enumerate(requests, 1)) + '</tbody></table></div>')
    if further:
        parts.append(f'<h4>{labels["further"]}</h4><ul>' + ''.join(f'<li>{html.escape(item)}</li>' for item in further)
                     + '</ul>')
    return '\n'.join(parts)


def cited_ids(markdowns) -> set[str]:
    return {i for text in markdowns for i in SOURCE_ID_RE.findall(re.sub(r'https?://\S+', '', text or ''))}


def render_report(section_markdown: dict[str, str], sources: list[dict], cover: Cover, data_as_of: str,
                  composite_score: str, language: str = 'en', requests: list[dict] | None = None,
                  further: list[str] | None = None, report_date: str | None = None) -> str:
    """The full HTML report: the template with every placeholder filled. A section missing from the
    version says so in its place."""
    labels = LABELS.get(language, LABELS['en'])
    text = TEMPLATE.read_text()
    if language != 'zh':
        text = text.replace('<html lang="zh-CN">', '<html lang="en">', 1)
        for chinese, bilingual in ENGLISH_CHROME:
            text = text.replace(chinese, bilingual, 1)

    def body(key: str) -> str:
        markdown = (section_markdown.get(key) or '').strip()
        if not markdown:
            return f'<div class="info-card warning">{labels["missing"]}</div>'
        try:
            return render_section(markdown, sources, language)
        except ComponentError as error:
            return f'<div class="info-card danger">{html.escape(str(error))}</div>' + _data_tables(
                MD.render(plain_markdown(markdown)))

    today = report_date or date.today().isoformat()
    cited = cited_ids(section_markdown.values())
    values = {
        'COMPANY_NAME': cover.company, 'COMPANY_TAGLINE': cover.tagline or labels['tagline'],
        'COMPANY_BUSINESS_SUMMARY': cover.business_summary, 'REPORT_DATE': today, 'DATA_AS_OF': data_as_of,
        'INDUSTRY': cover.industry, 'HEADQUARTERS': cover.headquarters, 'STAGE': cover.stage,
        'COMPOSITE_SCORE': composite_score, 'YEAR': today[:4],
    }
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', html.escape(value or '—'))
    text = text.replace('{{EXECUTIVE_SUMMARY}}', body(sections.EXECUTIVE_SUMMARY.key))
    for section in sections.SECTIONS:
        text = text.replace('{{SECTION_%d}}' % section.number, body(section.key))
    return text.replace('{{SOURCE_APPENDIX}}', source_appendix(sources, cited, language, requests, further))


def plain_report(section_markdown: dict[str, str], sources: list[dict], cover: Cover, rating: str, data_as_of: str,
                 composite_score: str, language: str = 'en') -> str:
    """The report as Markdown, for traces and the dashboard: every section under its template title, then the
    cited sources and the disclaimer."""
    lines = [f'# {cover.company}: {LABELS[language]["tagline"]}', f'Rating: {rating}', f'Composite score: {composite_score}',
             f'Data as of: {data_as_of}', '']
    for section in sections.ALL_SECTIONS:
        markdown = plain_markdown(section_markdown.get(section.key) or '').strip()
        lines += [f'## {section.title}', '', markdown or f'_{LABELS[language]["missing"]}_', '']
    cited = cited_ids(section_markdown.values())
    lines += ['## 数据来源与引用 Source Appendix', '', '| ID | Source | Type | Date | Link | Confidence |',
              '|---|---|---|---|---|---|']
    for source in sources:
        if source['id'] in cited:
            cells = [source['id'], source.get('title', ''), source.get('source_type', ''), source.get('date', ''),
                     source.get('location', ''), source.get('confidence', '')]
            lines.append('| ' + ' | '.join(str(c).replace('|', '/').replace('\n', ' ') for c in cells) + ' |')
    lines += ['', DISCLAIMER, '']
    return '\n'.join(lines)


DISCLAIMER = 'For research purposes only; not investment advice.'


# PDF and delivery

def _library_paths() -> str:
    """Where Homebrew or the system keeps Pango, which WeasyPrint loads at import (macOS needs it named)."""
    found = [path for path in ('/opt/homebrew/lib', '/usr/local/lib') if Path(path, 'libgobject-2.0.0.dylib').exists()
             or Path(path, 'libpango-1.0.0.dylib').exists()]
    existing = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '')
    return ':'.join(filter(None, [existing] + found))


def write_pdf(html_path: Path, pdf_path: Path, timeout: int = 180) -> dict:
    """Print the HTML to PDF with WeasyPrint, in a child process so the library
    path WeasyPrint needs is set before it loads. Returns {'pdf': path} or {'error': reason}."""
    env = dict(os.environ, DYLD_FALLBACK_LIBRARY_PATH=_library_paths())
    try:
        done = subprocess.run([sys.executable, '-m', 'tools.pdf', str(html_path), str(pdf_path)], env=env,
                              cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'error': f'PDF printing took longer than {timeout} seconds'}
    if done.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
        return {'error': (done.stderr or done.stdout or 'no PDF written').strip().splitlines()[-1][:300]}
    return {'pdf': str(pdf_path), 'bytes': pdf_path.stat().st_size}


def folder_name(company: str, summary: str) -> str:
    """The [CompanyName]_[BusinessSummary] folder name, safe for any file system."""
    def clean(text: str) -> str:
        return re.sub(r'[^\w一-鿿-]+', '', re.sub(r'\s+', '', text.title() if text.isascii() else text))[:40]
    return '_'.join(filter(None, (clean(company), clean(summary)))) or 'Report'


def report_file_name(company: str, language: str) -> str:
    stem = re.sub(r'[^\w一-鿿-]+', '', company.replace(' ', '')) or 'Company'
    return f'{stem}_投资分析报告' if language == 'zh' else f'{stem}_Investment_Report'


def write_delivery(folder: Path, report_html: str, file_stem: str, documents: list[Path]) -> dict:
    """The delivery folder: sources/ (the client's original documents), the
    HTML report and its PDF, and nothing else."""
    if folder.exists():
        shutil.rmtree(folder)
    (folder / 'sources').mkdir(parents=True)
    for document in documents:
        if document.exists():
            shutil.copy2(document, folder / 'sources' / document.name)
    html_path = folder / f'{file_stem}.html'
    html_path.write_text(report_html)
    pdf = write_pdf(html_path, folder / f'{file_stem}.pdf')
    return {'folder': str(folder), 'html': str(html_path), **pdf}
