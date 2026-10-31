"""Applies the rule table at the MCP server's dispatch, and keeps what the rules need to know about a run.

before() runs ahead of every tool: in enforce mode a broken rule raises Refused, whose text reaches the model. after()
runs on the result: it counts budgets, remembers what was retrieved and takes instructions out of documents and pages.
A case file with no policy_mode has no enforcement, and neither does a call with no active run.
"""
import json
from pathlib import Path
import re

from tools import case_file

from . import quarantine, rules
from .rules import Call

ENFORCE, OBSERVE = 'enforce', 'observe'
LOG, STATE, WINDOWS = 'policy_log.jsonl', 'policy_state.json', 'policy_windows.json'
URL_RE = re.compile(r'https?://[^\s<>"\'\\\])|]+')
QUARANTINED_TOOLS = ('read_client_document', 'web_fetch')
# A tool's result lists URLs only where it retrieved them, so these results say what the team has retrieved.
RETRIEVING_TOOLS = rules.RESEARCH_TOOLS


class Refused(ValueError):
    """A tool call the rules refuse. The server turns it into a tool error, so the model reads it."""


def _context(tool: str, agent: str | None, arguments: dict) -> tuple[Call, str, Path] | None:
    try:
        run_dir = case_file.active_run_dir()
        case = case_file.read_case()
    except (RuntimeError, FileNotFoundError):
        return None
    mode = case.get('policy_mode')
    if not mode:
        return None
    state_file = run_dir / STATE
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    windows_file = run_dir / WINDOWS
    windows = json.loads(windows_file.read_text()) if windows_file.exists() else {}
    window = windows.get(agent or '', 1)
    if agent and state.setdefault('window', {}).get(agent) != window:
        state['window'][agent] = window
        state.setdefault('used', {})[agent] = {}
    return Call(agent, tool, arguments, case, state, window), mode, run_dir


def _save_state(run_dir: Path, state: dict) -> None:
    (run_dir / STATE).write_text(json.dumps(state))


def log_decision(run_dir: Path, rule_id: str, policies: tuple[str, ...], action: str, agent: str | None, tool: str,
                 detail: str) -> None:
    entry = {'ts': case_file.now(), 'rule': rule_id, 'policies': list(policies), 'action': action, 'agent': agent,
             'tool': tool, 'detail': detail}
    with (run_dir / LOG).open('a') as log:
        log.write(json.dumps(entry, ensure_ascii=False) + '\n')


def read_decisions(run_dir: Path) -> list[dict]:
    path = run_dir / LOG
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def before(tool: str, agent: str | None, arguments: dict) -> None:
    """Check a call against the rules for its tool; raise Refused for the first broken one when enforcing."""
    with case_file._lock:
        context = _context(tool, agent, arguments)
        if not context:
            return
        call, mode, run_dir = context
        refusal = None
        for rule in rules.rules_for(tool):
            text = rule.check(call)
            if not text:
                continue
            once_key = f'{rule.id}:{agent}:{arguments.get("section", "")}'
            if rule.action == 'refuse once' and once_key in call.state.get('refused_once', []):
                log_decision(run_dir, rule.id, rule.policies, 'allowed after a refusal', agent, tool, text)
                continue
            log_decision(run_dir, rule.id, rule.policies, 'refused' if mode == ENFORCE else 'would refuse', agent, tool, text)
            if rule.action == 'refuse once':
                call.state.setdefault('refused_once', []).append(once_key)
            refusal = refusal or f"Refused by rule {rule.id}: {text}"
        if not refusal or mode != ENFORCE:
            used = call.state.setdefault('used', {}).setdefault(agent or '', {})
            used['calls'] = used.get('calls', 0) + 1
        _save_state(run_dir, call.state)
    if refusal and mode == ENFORCE:
        raise Refused(refusal)


def _returned_results(result) -> bool:
    """A search that found nothing costs no budget: about a third of the baseline's did."""
    return not isinstance(result, dict) or bool(result.get('results'))


def after(tool: str, agent: str | None, arguments: dict, result):
    """Count the call, remember what it retrieved, and take instructions out of what it returned."""
    with case_file._lock:
        context = _context(tool, agent, arguments)
        if not context:
            return result
        call, mode, run_dir = context
        state = call.state
        used = state.setdefault('used', {}).setdefault(agent or '', {})
        if tool in ('web_search', 'web_fetch') and _returned_results(result):
            used[tool] = used.get(tool, 0) + 1
            if agent == rules.LEAD and tool == 'web_search':
                state['lead_searches'] = state.get('lead_searches', 0) + 1
        if tool in rules.RESEARCH_TOOLS and agent:
            state.setdefault('research', {})[agent] = state.get('research', {}).get(agent, 0) + 1
        if tool in RETRIEVING_TOOLS:
            from .confidential import normalize_url
            text = result if isinstance(result, str) else json.dumps(result)
            found = {normalize_url(url) for url in URL_RE.findall(text)}
            if tool == 'web_fetch':
                found.add(normalize_url(str(arguments.get('url') or '')))
            state['retrieved'] = sorted(set(state.get('retrieved', [])) | found)
        if tool == 'leave_note' and not arguments.get('answers'):
            used['new_notes'] = used.get('new_notes', 0) + 1
        if tool in rules.REVIEW_READS:
            state['review_reads'] = sorted(set(state.get('review_reads', [])) | {tool})
        if tool == 'start_review':
            state['review_reads'] = []
            result = _warn_unresearched(run_dir, call, result)
        if tool == 'finish_review':
            state.setdefault('research_at', {})[str(result.get('review_id'))] = dict(state.get('research', {}))
        _save_state(run_dir, state)
        if tool in ('web_search', 'web_fetch') and isinstance(result, dict):
            line = rules.budget_line(agent, tool, state, call.window)
            result = {**result, 'budget': line} if line else result
        if tool in QUARANTINED_TOOLS:
            return _quarantined(run_dir, mode, agent, tool, result)
        return result


def _warn_unresearched(run_dir: Path, call: Call, result: dict) -> dict:
    """N11 as a warning: each Critical item of the last review whose owners have researched nothing since. A known
    source or a stated limitation can answer an item, so this tells the reviewer rather than refusing anyone."""
    finished = [r for r in call.case['reviews'] if r.get('verdict')]
    if not finished or not isinstance(result, dict):
        return result
    last = finished[-1]
    then, now = call.state.get('research_at', {}).get(last['id'], {}), call.state.get('research', {})
    idle = [item for item in last.get('items') or [] if item['severity'] == 'Critical'
            and not any(now.get(owner, 0) > then.get(owner, 0) for owner in item['owners'])]
    if not idle:
        return result
    detail = '; '.join(', '.join(item['sections']) for item in idle)
    log_decision(run_dir, 'N11', ('P39',), 'warned', call.agent, call.tool, f'Critical items with no research since: {detail}')
    return {**result, 'critical_items_without_new_research': [
        {'sections': item['sections'], 'owners': item['owners'], 'issue': item['issue'][:200]} for item in idle]}


def _quarantined(run_dir: Path, mode: str, agent: str | None, tool: str, result):
    text = result.get('text', '') if isinstance(result, dict) else result
    cleaned, removed = quarantine.clean(text)
    if not removed:
        return result
    enforcing = mode == ENFORCE
    log_decision(run_dir, 'N8', ('P29',), 'quarantined' if enforcing else 'would quarantine', agent, tool,
                 f'{removed} line(s) addressed to AI tools')
    if not enforcing:
        return result
    return {**result, 'text': cleaned} if isinstance(result, dict) else cleaned


def write_windows(run_dir: Path, windows: dict[str, int]) -> None:
    """Called by the runner: the server sees tool calls, not messages, so only the runner knows when a brief or a turn
    begins. Each agent's count opens a new budget window when it rises."""
    temporary = run_dir / f'{WINDOWS}.tmp'
    temporary.write_text(json.dumps(windows))
    temporary.replace(run_dir / WINDOWS)
