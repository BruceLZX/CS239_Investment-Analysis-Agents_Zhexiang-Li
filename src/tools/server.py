"""MCP server for the investment research bot team.

One server holds every tool; Rakazo limits each bot to its own tools with per-bot
allowlists. Each bot calls it at its own endpoint, /mcp?agent=<key>, so every call is
credited to the agent that made it. Each call is appended to the active run's
tool_log.jsonl. From src/:

    .venv/bin/python -m tools.server
"""
from contextvars import ContextVar
import functools
import json
import os
import time
from urllib.parse import parse_qs

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
import uvicorn

from . import case_file, filings, memo, prices, sec_edgar, valuation
from .agents import AGENTS, ANALYSTS
from .case_file import now, open_case, read_case
from .env import load_env
from .retrieved import Retrieved

server = MCPServer('Investment research',
                   instructions='Research tools, a shared source register and the case file for one investment memo.')
# The agent whose endpoint the current request came in on; None for an endpoint without a known ?agent= key.
CALLER: ContextVar[str | None] = ContextVar('caller', default=None)
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
READ_WEB = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
# Rakazo passes at most 12,000 characters of a tool result's text to the model and drops the rest:
# https://github.com/elie222/rakazo/blob/b445fe90522d5e5da1e47879f6e4fa9be504f530/packages/adapters/src/pi-runtime-limits.ts#L22
# Longer results are cut here instead, so the model sees that they were.
MAX_RESULT = 12_000
TRUNCATED = '\n[truncated]'
# What a read of memo parts or packets may return; past it the tool asks for less instead of cutting text.
MAX_READ = 11_500
SOURCES_PER_PAGE = 40
MEMO_RATINGS = {'buy', 'add', 'hold', 'reduce', 'sell', 'watchlist', 'hold-off', 'invest', 'wait', 'pass'}
REVIEW_VERDICTS = {'approve', 'revise', 'reject'}
PART_KEYS = ', '.join(part.key for part in memo.PARTS)
EVIDENCE_FROM = {'fundamentals': AGENTS['fundamentals'], 'market': AGENTS['market']}


def _plain(value):
    """A tool argument as JSON for the tool log: review items arrive as pydantic models."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def tool(annotations: ToolAnnotations):
    """Register a logged tool. structured_output=False keeps a single copy of each result,
    because Rakazo counts both copies against its 12,000-character tool-output limit."""
    def register(fn):
        @functools.wraps(fn)
        def logged(**arguments):
            started = time.monotonic()
            entry = {'ts': now(), 'agent': CALLER.get(), 'tool': fn.__name__,
                     'arguments': {name: _plain(value) for name, value in arguments.items()}}
            try:
                result = fn(**arguments)
                text = result if isinstance(result, str) else json.dumps(result, indent=1)
                if len(text) > MAX_RESULT:
                    text = text[:MAX_RESULT - len(TRUNCATED)] + TRUNCATED
                entry['result'] = text
                return text
            except Exception as exc:
                entry['error'] = f'{type(exc).__name__}: {exc}'
                # Only ToolError messages reach the model; any other exception arrives as a bare failure.
                raise ToolError(str(exc)) from exc
            finally:
                entry['duration_ms'] = round((time.monotonic() - started) * 1000)
                case_file.log_tool_call(entry)
        return server.tool(annotations=annotations, structured_output=False)(logged)
    return register


def _version(case: dict, version: int) -> dict:
    """A saved memo version; 0 means the latest."""
    versions = case['memo_drafts']
    if not versions:
        raise ValueError('No memo version has been saved yet.')
    if version == 0:
        return versions[-1]
    for saved in versions:
        if saved['version'] == version:
            return saved
    raise ValueError(f'No memo version {version}; latest is {versions[-1]["version"]}.')


def _listed(case: dict) -> bool:
    return (case.get('scope') or {}).get('type') != 'private'


def _part_key(part: str, allow_sources: bool = False) -> str:
    key = part.strip().lower()
    if key in memo.PART_BY_KEY or (allow_sources and key == 'sources'):
        return key
    raise ValueError(f'No memo part {part!r}. Parts: {PART_KEYS}' + (', sources' if allow_sources else '') + '.')


def _rating(rating: str) -> str:
    if rating.strip().lower() not in MEMO_RATINGS:
        raise ValueError('rating must be one of Buy, Add, Hold, Reduce, Sell, Watchlist, Hold-off (listed) '
                         'or Invest, Wait, Pass (private).')
    return rating.strip()


def _check_summary(check: dict, per_part: int = 4) -> dict:
    """A version check short enough to read in one result: rule findings, and the first depth problems per part."""
    failing = {key: part['depth'][:per_part] + ([f"and {len(part['depth']) - per_part} more"]
                                                if len(part['depth']) > per_part else [])
               for key, part in check['parts'].items() if not part['passed'] and part['depth']}
    rules = {key: part['findings'] for key, part in check['parts'].items() if part['findings']}
    return {'passed': check['passed'], 'findings': check['findings'], 'part_rule_findings': rules,
            'part_depth': failing, 'memo_depth': check['depth']}


def _registered(retrieved: Retrieved, via: str) -> str:
    """A data tool's result with its sources registered for the calling agent, and the IDs to cite them by."""
    try:
        with open_case() as case:
            ids = [case_file.add_source(case, s['title'], s['source_type'], s['location'], s['date'], s['confidence'],
                                        s['claims'], registered_by=CALLER.get(), via=via) for s in retrieved.sources]
    except RuntimeError:  # no active run, e.g. a tool tried by hand
        return retrieved.text + '\n\nSources (not registered: no active run):\n' + '\n'.join(
            f"- {s['label']}: {s['location']}" for s in retrieved.sources)
    # The location shows in the result too, as the record that the tool retrieved it.
    listed = dict.fromkeys((source_id, s['label'] if s['location'] in s['label'] else f"{s['label']}, {s['location']}")
                           for source_id, s in zip(ids, retrieved.sources))
    return (f'{retrieved.text}\n\nSources registered for you (cite these IDs; do not register them again):\n'
            + '\n'.join(f'- [{source_id}] {label}' for source_id, label in listed))


# Research (Fundamentals Analyst; the Market Analyst also reads filings)

@tool(READ_WEB)
def find_sec_company(ticker: str) -> dict:
    """Look up a US-listed company's SEC registration (CIK and legal name) by ticker symbol."""
    return sec_edgar.find_company(ticker)


@tool(READ_WEB)
def get_sec_financials(ticker: str, years: int = 3) -> str:
    """Financial statements from the company's 10-K and 10-Q XBRL filings: about 28 income statement, cash flow
    and balance sheet lines for up to five fiscal years (years: 1-5), with growth, margins, free cash flow, debt and
    net cash worked out, and the latest quarter, year to date and trailing twelve months. The filings are registered
    as sources, and the result lists the IDs to cite. XBRL has no segment split; read it with read_sec_filing."""
    return _registered(sec_edgar.statements(ticker, years), 'get_sec_financials')


@tool(READ_WEB)
def list_sec_filings(ticker: str, forms: list[str] | None = None, limit: int = 8) -> str:
    """Recent SEC filings (default forms 10-K, 10-Q, 8-K, DEF 14A) with dates, accession numbers and links."""
    return sec_edgar.recent_filings(ticker, forms, limit)


@tool(READ_WEB)
def read_sec_filing(ticker: str, form: str = '10-K', item: str = '7', page: int = 1,
                    keywords: list[str] | None = None, accession: str | None = None) -> str:
    """Read the text of the company's latest 10-K or 10-Q, one item a page (about 9,000 characters) at a time.
    10-K items: 1 business and segments, 1A risk factors, 7 management's discussion and analysis, 7A market risk,
    8 financial statements and notes. 10-Q items: 1 financial statements, 2 management's discussion, 1A risk
    factors. keywords: return only the paragraphs mentioning any of them, within the item or, with item empty, the
    whole filing; the search runs on this server. accession: a specific filing instead of the latest. The filing
    is registered as a source, and the result gives the ID to cite."""
    return _registered(filings.read_filing(ticker, form, item, page, keywords, accession), 'read_sec_filing')


@tool(READ_WEB)
def get_price_history(ticker: str, period: str = '1y') -> str:
    """Latest price and the range of daily closes over a period (1mo, 3mo, 6mo, 1y, 2y or 5y), with exchange,
    currency and timestamp, the 52-week range, the price change over 1, 3, 6 and 12 months, and the market's
    backdrop (S&P 500, VIX, 10-year Treasury yield). The price data is registered as a source."""
    return _registered(prices.price_summary(ticker, period), 'get_price_history')


@tool(READ_WEB)
def get_valuation_snapshot(ticker: str, peers: list[str] | None = None) -> str:
    """Price, market cap, enterprise value and multiples (P/E, EV/Sales, EV/EBITDA, FCF yield, P/B, trailing twelve
    months) for the company and up to four peers, worked out from SEC XBRL filings and Yahoo prices; the company's
    P/E and EV/Sales at its last five fiscal year ends; the peer median and the company's premium or discount to it.
    Peers that do not file US GAAP statements with the SEC show as n/a. Every filing and price used is registered as
    a source, and the result lists the IDs to cite."""
    return _registered(valuation.snapshot(ticker, peers), 'get_valuation_snapshot')


# Shared source register and case file

@tool(WRITE)
def register_source(title: str, source_type: str, location: str, date: str, confidence: str, claims: str) -> dict:
    """Add a source you retrieved in this run to the shared register and get its ID (S1, S2, ...) to cite as [S1].
    source_type: primary filing, company website, market data, company-provided, independent media, industry data
    or other. location: the URL you retrieved, or the client document's name. date: publication or retrieval date.
    confidence: high, medium or low. claims: what the source supports. Registering the same location again returns
    its existing ID."""
    with open_case() as case:
        source_id = case_file.add_source(case, title, source_type, location, date, confidence, claims,
                                         registered_by=CALLER.get())
    return {'id': source_id, 'cite_as': f'[{source_id}]'}


@tool(READ)
def list_sources(page: int = 1) -> str:
    """The shared source register: each source ID with its title, type, location, date and confidence,
    40 sources a page."""
    sources = read_case()['sources']
    if not sources:
        return 'The source register is empty.'
    pages = (len(sources) - 1) // SOURCES_PER_PAGE + 1
    page = min(max(page, 1), pages)
    shown = sources[(page - 1) * SOURCES_PER_PAGE:page * SOURCES_PER_PAGE]
    rows = ([f'Page {page} of {pages} ({len(sources)} sources).'] if pages > 1 else []) + [
        '| ID | Title | Type | Location | Date | Confidence |', '|---|---|---|---|---|---|']
    rows += [f"| {s['id']} | {s['title']} | {s['source_type']} | {s['location']} | {s['date']} | {s['confidence']} |"
             for s in shown]
    return '\n'.join(rows)


@tool(READ)
def get_case_status() -> dict:
    """What has arrived in this case so far: its scope, client documents, evidence packets, each memo part's latest
    revision and check, the latest version and review, and deliveries. Call it once at the start of a turn,
    not repeatedly."""
    return case_file.status_summary(read_case())


@tool(WRITE)
def set_case_scope(company: str, ticker: str | None, company_type: str, decision: str) -> dict:
    """Record what this case is about, before briefing anyone: the company, its ticker (empty for a private
    company), company_type "listed" or "private", and the decision the memo serves. The memo's header and each
    part's listed or private standard follow it. Set it once; a later change is recorded."""
    company_type = company_type.strip().lower()
    if company_type not in ('listed', 'private'):
        raise ValueError('company_type must be "listed" or "private".')
    ticker = (ticker or '').strip().upper()
    scope = {'company': company.strip(), 'type': company_type, 'decision': decision.strip(),
             'ticker': None if company_type == 'private' or ticker in ('', 'PRIVATE', 'NONE', 'N/A') else ticker,
             'set_by': CALLER.get(), 'set_at': now()}
    with open_case() as case:
        earlier = case.get('scope')
        if earlier and any(earlier[k] != scope[k] for k in ('company', 'ticker', 'type')):
            case.setdefault('scope_changes', []).append(earlier)
        case['scope'] = scope
    return {k: scope[k] for k in ('company', 'ticker', 'type', 'decision')}


@tool(READ)
def read_client_document(name: str) -> str:
    """Read a document the client attached to this request, with its confidentiality label."""
    case = read_case()
    for document in case['client_documents']:
        if document['name'].lower() == name.strip().lower():
            text = (case_file.ROOT / document['file']).read_text()
            return f"[{document['confidentiality'].upper()}: {document['name']}]\n{text}"
    names = ', '.join(d['name'] for d in case['client_documents']) or 'none'
    raise ValueError(f'No client document named {name!r}. Attached: {names}.')


@tool(WRITE)
def save_evidence_packet(topic: str, summary: str, findings: list[str], source_ids: list[str],
                         counter_evidence: str, gaps: list[str], parts: list[str] | None = None,
                         risks: list[str] | None = None, scenario_drivers: list[str] | None = None,
                         searches: list[str] | None = None) -> dict:
    """Save research findings to the case file for the Lead Analyst. Each finding, risk and scenario driver carries
    its source IDs, e.g. "Revenue grew 6% in FY2025 [S2]". counter_evidence: the strongest evidence against the
    thesis. gaps: what could not be verified, and any check problem you could not fix. parts: the memo parts this
    research supports. risks: the main risks in your area, for the Lead's Risks part. scenario_drivers: what would
    move the outcome up or down. searches: the queries and filing reads you ran, with the part each served. The
    packet is credited to the analyst making the call; one saved after a review answers that review's requests."""
    with open_case() as case:
        packet_id = f"E{len(case['evidence_packets']) + 1}"
        unknown = sorted(set(source_ids) - {s['id'] for s in case['sources']})
        follow_up_for = case['reviews'][-1]['id'] if case['reviews'] else None
        case['evidence_packets'].append({
            'id': packet_id, 'analyst': CALLER.get(), 'follow_up_for': follow_up_for, 'topic': topic,
            'summary': summary, 'findings': findings, 'source_ids': source_ids,
            'counter_evidence': counter_evidence, 'gaps': gaps, 'parts': parts or [], 'risks': risks or [],
            'scenario_drivers': scenario_drivers or [], 'searches': searches or [], 'saved_at': now(),
        })
    return {'id': packet_id, 'analyst': CALLER.get(), 'follow_up_for': follow_up_for,
            'unregistered_source_ids': unknown}


def _packet_text(p: dict) -> str:
    by = p.get('analyst') or 'unknown analyst'
    if p.get('follow_up_for'):
        by += f", follow-up for review {p['follow_up_for']}"
    lines = [f"## {p['id']} ({by}): {p['topic']}", p['summary']]
    if p.get('parts'):
        lines.append('Parts: ' + ', '.join(p['parts']))
    lines += ['Findings:'] + [f'- {f}' for f in p['findings']]
    for label, key in (('Risks', 'risks'), ('Scenario drivers', 'scenario_drivers')):
        if p.get(key):
            lines += [f'{label}:'] + [f'- {item}' for item in p[key]]
    lines += [f"Counter-evidence: {p['counter_evidence']}", 'Gaps: ' + '; '.join(p['gaps'])]
    return '\n'.join(lines)


@tool(READ)
def get_evidence_packets(packet_ids: list[str] | None = None) -> str:
    """Saved evidence packets with their analyst, the parts they support, findings, risks, scenario drivers,
    counter-evidence and gaps. packet_ids: the packets to read (E1, E2, ...); empty for all of them. When they don't
    fit in one result, you get a list of the packets to read a few at a time instead."""
    packets = read_case()['evidence_packets']
    if not packets:
        return 'No evidence packets saved yet.'
    wanted = {i.strip().upper() for i in packet_ids or []}
    chosen = [p for p in packets if not wanted or p['id'] in wanted]
    if not chosen:
        raise ValueError('No packets with those IDs. Saved: ' + ', '.join(p['id'] for p in packets) + '.')
    text = '\n\n'.join(_packet_text(p) for p in chosen)
    if len(text) <= MAX_READ:
        return text
    rows = ['| ID | Analyst | Follow-up for | Topic | Parts | Characters |', '|---|---|---|---|---|---|']
    rows += [f"| {p['id']} | {p.get('analyst')} | {p.get('follow_up_for') or ''} | {p['topic']} | "
             f"{', '.join(p.get('parts') or [])} | {len(_packet_text(p)):,} |" for p in chosen]
    return (f'These packets add up to {len(text):,} characters, more than one result holds. '
            'Read them a few at a time with packet_ids:\n' + '\n'.join(rows))


# Memo (every author, the Lead Analyst and the IC Reviewer)

@tool(WRITE)
def save_memo_part(part: str, markdown: str) -> dict:
    """Save your revision of one memo part and get its check: the rules and the part's depth standard. part: one
    of executive_summary, business, financials, valuation, competition, risks, scenarios, one_question, takeaways.
    markdown: the part's text with inline [S#] citations, without its heading; at most 9,000 characters. Fix what
    the check reports and save again."""
    key = _part_key(part)
    text = memo.normalize_part(key, markdown)
    if len(text) > memo.MAX_PART_CHARS:
        raise ValueError(f'This part is {len(text):,} characters; a part holds at most {memo.MAX_PART_CHARS:,}, '
                         'so that a reader can take it with others in one result. Tighten it and save it again.')
    with open_case() as case:
        check = memo.check_part(key, text, case['sources'], _listed(case))
        revision = case_file.save_part(case, key, text, CALLER.get(), check)
        scoped = bool(case.get('scope'))
    result = {'part': key, 'revision': revision['revision'], 'chars': len(text),
              'owner': memo.PART_BY_KEY[key].owner, 'saved_by': CALLER.get(),
              'check': {'passed': check['passed'], 'findings': check['findings'], 'depth': check['depth']}}
    if not scoped:
        result['note'] = 'The case has no scope yet, so the part was checked as a listed company.'
    return result


@tool(READ)
def get_memo_parts(parts: list[str] | None = None, version: int | None = None) -> str:
    """Read memo parts whole. parts: part keys (executive_summary, business, financials, valuation, competition,
    risks, scenarios, one_question, takeaways, sources); empty for a list of the parts with their revisions,
    authors, sizes and checks. version: a saved version's number, 0 for the latest version, or empty for the parts
    as they are now. If the parts add up to more than one result holds, ask for fewer at a time."""
    case = read_case()
    if version is None:
        current = case_file.current_parts(case)
        texts = {key: r['markdown'] for key, r in current.items()}
        about = {key: f"revision {r['revision']} by {r['author'] or 'unknown'}" for key, r in current.items()}
        checks = {key: r['passed'] for key, r in current.items()}
        where = 'as saved now'
    else:
        saved = _version(case, version)
        texts = case_file.version_parts(case, saved)
        about = {key: f"revision {ref['revision']} by {ref['author'] or 'unknown'}"
                      + (', changed since the previous version' if key in saved['changed_parts'] else '')
                 for key, ref in saved['parts'].items()}
        revisions = case.get('memo_parts') or {}
        checks = {key: revisions[key][ref['revision'] - 1]['passed'] for key, ref in saved['parts'].items()}
        where = f"in version {saved['version']} (rating {saved['rating']})"
    if not parts:
        rows = [f'Memo parts {where}:', '| Part | Key | Owner | Revision | Characters | Check |', '|---|---|---|---|---|---|']
        for part in memo.PARTS:
            if part.key in texts:
                rows.append(f"| {part.heading} | {part.key} | {part.owner} | {about[part.key]} | "
                            f"{len(texts[part.key]):,} | {'passed' if checks[part.key] else 'problems'} |")
            else:
                rows.append(f'| {part.heading} | {part.key} | {part.owner} | not saved | | |')
        return '\n'.join(rows)
    blocks = []
    for key in [_part_key(p, allow_sources=True) for p in parts]:
        if key == 'sources':
            cited = memo._ids(memo.URL_RE.sub('', '\n'.join(texts.values())))
            blocks.append(f'## Sources (generated from the register, {where})\n'
                          + memo.sources_table(case['sources'], cited))
        elif key in texts:
            heading = memo.PART_BY_KEY[key].heading
            blocks.append(f'## {heading} ({key}, {about[key]}, {len(texts[key]):,} characters)\n{texts[key]}')
        else:
            blocks.append(f'## {memo.PART_BY_KEY[key].heading} ({key}): not saved {where}')
    text = '\n\n'.join(blocks)
    if len(text) > MAX_READ:
        raise ValueError(f'These parts add up to {len(text):,} characters, more than one result holds '
                         f'({MAX_READ:,}). Ask for fewer parts at a time.')
    return text


@tool(WRITE)
def save_memo_version(rating: str, data_as_of: str) -> dict:
    """Save the memo parts as they are now as a new version for review; a version never changes. The header,
    the Sources part and the disclaimer are generated. rating: for listed companies Buy, Add, Hold, Reduce, Sell,
    Watchlist or Hold-off; for private companies Invest, Wait or Pass. data_as_of: YYYY-MM-DD. Returns the version
    number, the parts changed since the last version and the whole memo's check."""
    rating = _rating(rating)
    with open_case() as case:
        texts = {key: r['markdown'] for key, r in case_file.current_parts(case).items()}
        markdown = memo.assemble(texts, case.get('scope') or {}, rating, data_as_of, case['sources'])
        check = memo.check_version(markdown, texts, rating, case['sources'], _listed(case))
        version = case_file.add_version(case, rating, data_as_of, markdown, check)
    return {'version': version['version'], 'rating': rating, 'changed_parts': version['changed_parts'],
            'missing_parts': version['missing_parts'], 'check': _check_summary(check)}


@tool(READ)
def get_memo_check(version: int | None = None, part: str | None = None) -> dict:
    """Check the memo against the team's rules (source IDs missing from the register, numbers without sources,
    company claims without a verification status, the rating's evidence gate, internal working material) and each
    part's depth standard. part: one part's key, or empty for the whole memo. version: a saved version's number,
    0 for the latest, or empty for the parts as they are now. Reports only."""
    case = read_case()
    listed = _listed(case)
    if version is None:
        texts = {key: r['markdown'] for key, r in case_file.current_parts(case).items()}
        rating, data_as_of, label = None, None, 'parts as saved now'
    else:
        saved = _version(case, version)
        texts, rating, data_as_of = case_file.version_parts(case, saved), saved['rating'], saved['data_as_of']
        label = f"version {saved['version']}"
    if part:
        key = _part_key(part)
        if key not in texts:
            raise ValueError(f'The {key} part is not saved ({label}).')
        return {'checked': f'{key}, {label}', **memo.check_part(key, texts[key], case['sources'], listed)}
    markdown = memo.assemble(texts, case.get('scope') or {}, rating or '(not set)', data_as_of or '(not set)',
                             case['sources'])
    check = memo.check_version(markdown, texts, rating, case['sources'], listed)
    return {'checked': label, **_check_summary(check)}


class ReviewItem(BaseModel):
    part: str = Field(description='The part to change, by its key, or "memo" for a problem across parts.')
    issue: str = Field(description='What is wrong, and why it matters to the decision.')
    fix: str = Field(description='What the author should change.')
    evidence_from: str = Field('', description='"fundamentals" or "market" when the fix needs evidence the team '
                                               'has not gathered (first review only); empty otherwise.')


@tool(WRITE)
def save_review(memo_version: int, verdict: str, must_fix: list[ReviewItem], should_fix: list[str]) -> dict:
    """Save the investment committee review of one memo version. verdict: approve, revise or reject. must_fix:
    the items to change, each naming its part; each goes to that part's owner, and any that needs new evidence
    names the analyst who should gather it. should_fix: smaller suggestions."""
    if verdict.strip().lower() not in REVIEW_VERDICTS:
        raise ValueError('verdict must be approve, revise or reject.')
    items = []
    for item in must_fix:
        key = item.part.strip().lower()
        if key != 'memo':
            key = _part_key(key)
        evidence_from = item.evidence_from.strip().lower().removesuffix(' analyst')
        if evidence_from and evidence_from not in EVIDENCE_FROM:
            raise ValueError('evidence_from must be "fundamentals", "market" or empty.')
        items.append({'part': key, 'owner': memo.PART_BY_KEY[key].owner if key in memo.PART_BY_KEY else AGENTS['lead'],
                      'issue': item.issue, 'fix': item.fix, 'evidence_from': EVIDENCE_FROM.get(evidence_from)})
    revisions, requests = {}, {}
    for item in items:
        revisions.setdefault(item['owner'], [])
        if item['part'] not in revisions[item['owner']]:
            revisions[item['owner']].append(item['part'])
        if item['evidence_from']:
            requests.setdefault(item['evidence_from'], []).append(f"{item['issue']} {item['fix']}")
    with open_case() as case:
        _version(case, memo_version)
        review_id = f"R{len(case['reviews']) + 1}"
        review = {'id': review_id, 'memo_version': memo_version, 'round': len(case['reviews']) + 1,
                  'verdict': verdict.strip().lower(), 'items': items,
                  'must_fix': [f"{i['part']}: {i['issue']} Fix: {i['fix']}" for i in items], 'should_fix': should_fix,
                  'revision_requests': revisions, 'evidence_requests': requests, 'saved_at': now()}
        case['reviews'].append(review)
    return {'id': review_id, 'round': review['round'], 'revisions_requested_from': list(revisions),
            'evidence_requested_from': list(requests)}


@tool(READ)
def get_latest_review() -> str:
    """The most recent investment committee review: the version and round it covers, the verdict, the must-fix
    items grouped by the owner who should fix them, any evidence it asks the analysts for, and should-fix items."""
    reviews = read_case()['reviews']
    if not reviews:
        return 'No review saved yet.'
    r = reviews[-1]
    lines = [f"Review {r['id']} of memo version {r['memo_version']} (round {r.get('round', len(reviews))} of "
             f"{case_file.MAX_REVIEW_ROUNDS}): verdict {r['verdict']}"]
    items = r.get('items') or [{'part': 'memo', 'owner': AGENTS['lead'], 'issue': text, 'fix': '', 'evidence_from': None}
                               for text in r['must_fix']]
    for owner in [owner for owner in AGENTS.values() if any(i['owner'] == owner for i in items)]:
        lines.append(f'Must fix, for the {owner}:')
        lines += [f"- [{i['part']}] {i['issue']}" + (f" Fix: {i['fix']}" if i['fix'] else '')
                  + (f" (new evidence from the {i['evidence_from']})" if i['evidence_from'] else '')
                  for i in items if i['owner'] == owner]
    if not items:
        lines.append('Must fix: none')
    lines.append('Should fix:' + (''.join(f'\n- {item}' for item in r['should_fix']) or ' none'))
    requests = r.get('evidence_requests') or {}
    lines.append('Evidence requests:' + (''.join(f'\n- {analyst}: {ask}' for analyst, asks in requests.items()
                                                 for ask in asks) or ' none'))
    return '\n'.join(lines)


@tool(WRITE)
def deliver_memo(version: int = 0) -> dict:
    """Deliver a memo version to the user as the final report. version 0 means the latest.
    Returns the delivery record: whether the version passed review, and the memo check's findings."""
    with open_case() as case:
        saved = _version(case, version)
        report = memo.check_memo(saved['markdown'], case['sources'])
        gate = case_file.review_gate(case, saved['version'])
        path = case_file.active_run_dir() / f"memo_v{saved['version']}.md"
        path.write_text(saved['markdown'])
        case['deliveries'].append({'memo_version': saved['version'], 'file': path.name, 'memo_check': report,
                                   'review_gate': gate, 'delivered_at': now()})
    return {'delivered_version': saved['version'], 'review_gate': gate, 'memo_check_findings': report['findings'],
            'note': 'Report only: delivery is never blocked.'}


class CallerFromEndpoint:
    """ASGI middleware: note which agent's endpoint (/mcp?agent=<key>) each request came in on."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        key = parse_qs(scope.get('query_string', b'').decode()).get('agent', [''])[0]
        token = CALLER.set(AGENTS.get(key))
        try:
            await self.app(scope, receive, send)
        finally:
            CALLER.reset(token)


def http_app(host: str = '127.0.0.1') -> CallerFromEndpoint:
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=['127.0.0.1:*', 'localhost:*', 'host.docker.internal:*'],
        allowed_origins=['http://127.0.0.1:*', 'http://localhost:*'])
    return CallerFromEndpoint(server.streamable_http_app(stateless_http=True, transport_security=security, host=host))


def main() -> None:
    load_env()
    host = os.environ.get('MCP_HOST', '127.0.0.1')
    uvicorn.run(http_app(host), host=host, port=int(os.environ.get('MCP_PORT', '8766')))


if __name__ == '__main__':
    main()
