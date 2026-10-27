"""MCP server for the investment research bot team.

One server holds every tool; Rakazo limits each bot to its own tools with per-bot
allowlists. Each call is appended to the active run's tool_log.jsonl. From src/:

    .venv/bin/python -m tools.server
"""
import functools
import json
import os
import time

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from . import case_file, memo, prices, sec_edgar
from .case_file import now, open_case, read_case
from .env import load_env

server = MCPServer('Investment research',
                   instructions='Research tools, a shared source register and the case file for one investment memo.')
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
READ_WEB = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
MAX_RESULT = 6000
MEMO_RATINGS = {'buy', 'add', 'hold', 'reduce', 'sell', 'watchlist', 'hold-off', 'invest', 'wait', 'pass'}
REVIEW_VERDICTS = {'approve', 'revise', 'reject'}


def tool(annotations: ToolAnnotations):
    """Register a logged tool. structured_output=False keeps a single copy of each result,
    because Rakazo counts both copies against its 12,000-character tool-output limit."""
    def register(fn):
        @functools.wraps(fn)
        def logged(**arguments):
            started = time.monotonic()
            entry = {'ts': now(), 'tool': fn.__name__, 'arguments': arguments}
            try:
                result = fn(**arguments)
                text = result if isinstance(result, str) else json.dumps(result, indent=1)
                if len(text) > MAX_RESULT:
                    text = text[:MAX_RESULT] + '\n[truncated]'
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


def _draft(case: dict, version: int) -> dict:
    drafts = case['memo_drafts']
    if not drafts:
        raise ValueError('No memo draft has been saved yet.')
    if version == 0:
        return drafts[-1]
    for draft in drafts:
        if draft['version'] == version:
            return draft
    raise ValueError(f'No memo draft version {version}; latest is {drafts[-1]["version"]}.')


# Research (Research Analyst)

@tool(READ_WEB)
def find_sec_company(ticker: str) -> dict:
    """Look up a US-listed company's SEC registration (CIK and legal name) by ticker symbol."""
    return sec_edgar.find_company(ticker)


@tool(READ_WEB)
def get_sec_financials(ticker: str, years: int = 3) -> str:
    """Annual figures from the company's 10-K XBRL filings: revenue, net income, diluted EPS, operating
    cash flow, capex, cash, assets, liabilities and equity, with the 10-K accession numbers to cite. years: 1-5."""
    return sec_edgar.annual_financials(ticker, years)


@tool(READ_WEB)
def list_sec_filings(ticker: str, forms: list[str] | None = None, limit: int = 8) -> str:
    """Recent SEC filings (default forms 10-K, 10-Q, 8-K, DEF 14A) with dates, accession numbers and links."""
    return sec_edgar.recent_filings(ticker, forms, limit)


@tool(READ_WEB)
def get_price_history(ticker: str, period: str = '1y') -> str:
    """Latest price and the range of daily closes over a period (1mo, 3mo, 6mo, 1y, 2y or 5y),
    with exchange, currency and timestamp."""
    return prices.price_summary(ticker, period)


# Shared source register and case file

@tool(WRITE)
def register_source(title: str, source_type: str, location: str, date: str, confidence: str, claims: str) -> dict:
    """Add a source you retrieved in this run to the shared register and get its ID (S1, S2, ...) to cite as [S1].
    source_type: primary filing, company website, market data, company-provided, independent media, industry data
    or other. location: the URL you retrieved, or the client document's name. date: publication or retrieval date.
    confidence: high, medium or low. claims: what the source supports. Registering the same location again returns
    its existing ID."""
    with open_case() as case:
        source_id = case_file.add_source(case, title, source_type, location, date, confidence, claims)
    return {'id': source_id, 'cite_as': f'[{source_id}]'}


@tool(READ)
def list_sources() -> str:
    """The shared source register: each source ID with its title, type, location, date and confidence."""
    sources = read_case()['sources']
    if not sources:
        return 'The source register is empty.'
    rows = ['| ID | Title | Type | Location | Date | Confidence |', '|---|---|---|---|---|---|']
    rows += [f"| {s['id']} | {s['title']} | {s['source_type']} | {s['location']} | {s['date']} | {s['confidence']} |"
             for s in sources]
    return '\n'.join(rows)


@tool(READ)
def get_case_status() -> dict:
    """What has arrived in this case so far: client documents, evidence packets, the latest memo draft and
    review, and deliveries. Call it once at the start of a turn, not repeatedly."""
    return case_file.status_summary(read_case())


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
                         counter_evidence: str, gaps: list[str]) -> dict:
    """Save research findings to the case file for the Lead Analyst. Each finding carries its source IDs,
    e.g. "Revenue grew 6% in FY2025 [S2]". counter_evidence: the strongest evidence against the thesis.
    gaps: what could not be verified."""
    with open_case() as case:
        packet_id = f"E{len(case['evidence_packets']) + 1}"
        unknown = sorted(set(source_ids) - {s['id'] for s in case['sources']})
        case['evidence_packets'].append({
            'id': packet_id, 'topic': topic, 'summary': summary, 'findings': findings,
            'source_ids': source_ids, 'counter_evidence': counter_evidence, 'gaps': gaps, 'saved_at': now(),
        })
    return {'id': packet_id, 'unregistered_source_ids': unknown}


@tool(READ)
def get_evidence_packets() -> str:
    """All saved evidence packets with their findings, counter-evidence and gaps."""
    packets = read_case()['evidence_packets']
    if not packets:
        return 'No evidence packets saved yet.'
    parts = []
    for p in packets:
        parts.append(f"## {p['id']}: {p['topic']}\n{p['summary']}\nFindings:\n"
                     + '\n'.join(f'- {f}' for f in p['findings'])
                     + f"\nCounter-evidence: {p['counter_evidence']}\nGaps: " + '; '.join(p['gaps']))
    return '\n\n'.join(parts)


# Memo (Lead Analyst and IC Reviewer)

@tool(WRITE)
def save_memo_draft(markdown: str, rating: str, data_as_of: str) -> dict:
    """Save a new version of the investment memo (Markdown with inline [S#] citations).
    rating: for listed companies Buy, Add, Hold, Reduce, Sell, Watchlist or Hold-off; for private companies
    Invest, Wait or Pass. data_as_of: YYYY-MM-DD."""
    if rating.strip().lower() not in MEMO_RATINGS:
        raise ValueError('rating must be one of Buy, Add, Hold, Reduce, Sell, Watchlist, Hold-off (listed) '
                         'or Invest, Wait, Pass (private).')
    with open_case() as case:
        version = len(case['memo_drafts']) + 1
        case['memo_drafts'].append({'version': version, 'markdown': markdown, 'rating': rating.strip(),
                                    'data_as_of': data_as_of, 'saved_at': now()})
    return {'version': version}


@tool(READ)
def get_memo_draft(version: int = 0) -> str:
    """Read a memo draft. version 0 means the latest."""
    draft = _draft(read_case(), version)
    return f"Memo version {draft['version']} (rating {draft['rating']}, data as of {draft['data_as_of']}):\n\n{draft['markdown']}"


@tool(READ)
def get_memo_check(version: int = 0) -> dict:
    """Check a memo draft against the team's rules: source IDs missing from the register, numbers without
    sources, company claims without a verification status, the rating's evidence gate, internal working material,
    disclaimer and data-as-of date. Reports only. version 0 means the latest."""
    case = read_case()
    draft = _draft(case, version)
    return {'version': draft['version'], **memo.check_memo(draft['markdown'], case['sources'])}


@tool(WRITE)
def save_review(memo_version: int, verdict: str, must_fix: list[str], should_fix: list[str]) -> dict:
    """Save the investment committee review of one memo version. verdict: approve, revise or reject."""
    if verdict.strip().lower() not in REVIEW_VERDICTS:
        raise ValueError('verdict must be approve, revise or reject.')
    with open_case() as case:
        _draft(case, memo_version)
        review_id = f"R{len(case['reviews']) + 1}"
        case['reviews'].append({'id': review_id, 'memo_version': memo_version, 'verdict': verdict.strip().lower(),
                                'must_fix': must_fix, 'should_fix': should_fix, 'saved_at': now()})
    return {'id': review_id}


@tool(READ)
def get_latest_review() -> str:
    """The most recent investment committee review: which version it covers, the verdict, must-fix and should-fix items."""
    reviews = read_case()['reviews']
    if not reviews:
        return 'No review saved yet.'
    r = reviews[-1]
    return (f"Review {r['id']} of memo version {r['memo_version']}: verdict {r['verdict']}\nMust fix:\n"
            + '\n'.join(f'- {item}' for item in r['must_fix']) + '\nShould fix:\n'
            + '\n'.join(f'- {item}' for item in r['should_fix']))


@tool(WRITE)
def deliver_memo(version: int = 0) -> dict:
    """Deliver a memo version to the user as the final report. version 0 means the latest.
    Returns the delivery record: the memo check and whether the version passed review."""
    with open_case() as case:
        draft = _draft(case, version)
        report = memo.check_memo(draft['markdown'], case['sources'])
        gate = case_file.review_gate(case, draft['version'])
        path = case_file.active_run_dir() / f"memo_v{draft['version']}.md"
        path.write_text(draft['markdown'])
        case['deliveries'].append({'memo_version': draft['version'], 'file': path.name, 'memo_check': report,
                                   'review_gate': gate, 'delivered_at': now()})
    return {'delivered_version': draft['version'], 'review_gate': gate, 'memo_check': report,
            'note': 'Phase 1 report only: delivery is never blocked.'}


def main() -> None:
    load_env()
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=['127.0.0.1:*', 'localhost:*', 'host.docker.internal:*'],
        allowed_origins=['http://127.0.0.1:*', 'http://localhost:*'])
    server.run(transport='streamable-http', host=os.environ.get('MCP_HOST', '127.0.0.1'),
               port=int(os.environ.get('MCP_PORT', '8766')), stateless_http=True, transport_security=security)


if __name__ == '__main__':
    main()
