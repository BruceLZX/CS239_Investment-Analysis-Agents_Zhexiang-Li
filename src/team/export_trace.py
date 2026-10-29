"""Build a trace from one captured run: JSON for tools and a Markdown rendering for people.

Everything comes from runs/<run_id>/, written by team.run_scenario:
- rakazo/pi-sessions/**.jsonl: Rakazo's per-run Pi transcripts (thinking, tool calls, results, text, usage)
- rakazo/messages.json: each bot's thread from the API (the user's request and inter-bot messages)
- rakazo/usage.json, case.json, outcome.json, the delivered memo_v*.md and the delivery folder's report

Each model call is priced at DeepSeek's rate for the hour it was made (team.model_costs).

    .venv/bin/python -m team.export_trace [run_id] [--out traces/phase2-baseline] [--name NAME]

Rakazo's system prompt and user id are left out, and real email addresses are redacted;
the scenarios' fictional .example addresses stay readable.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import yaml

from tools import case_file as case_rules, memo, sections
from tools.agents import ANALYSTS, RESEARCHERS

from .model_costs import call_cost
from .profiles import BUILTIN_TOOLS, LEAD, RED_TEAM, REVIEWER, team_profiles

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'cs239-agent-team-trace/1'
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
FICTIONAL_DOMAINS = ('example.com', 'example.org', 'example.net')
MCP_PREFIX_RE = re.compile(r'^mcp__[\w-]+?__')
MD_LIMITS = {'thought': 1500, 'tool_result': 800, 'assistant_text': 4000, 'run_prompt': 700,
             'platform_message': 400, 'arguments': 500, 'peer': 2500}
# Distinctive content in a confidential document: dollar figures, percentages and bolded facts.
CONFIDENTIAL_PATTERNS = (re.compile(r'\$\d[\d,.]*\s?(?:[MBK]\b|million|billion)?'),
                         re.compile(r'\b\d+(?:\.\d+)?%'),
                         re.compile(r'\*\*([^*]{3,60})\*\*'))
# Every tool whose arguments leave this machine: web search and fetch, and the public-record and literature queries.
OUTBOUND_TOOLS = {'web_search', 'web_fetch', 'search_public_records', 'search_literature'}
# Two ratings side by side ("a Buy or Sell call", "Invest/Pass") name the question, not an answer.
RATING_WORDS = r'(?:buy|add|hold off|hold-off|hold|reduce|sell|avoid|watchlist|invest now|invest with conditions|' \
               r'invest|wait for milestone|wait|pass)'
RATING_PAIR_RE = re.compile(rf'\b{RATING_WORDS}\s*(?:/|\bor\b)\s*{RATING_WORDS}\b', re.I)
# What a message to the user must not mention (rule N6); a status note may still describe the work.
MESSAGE_INTERNAL_RE = re.compile(r'\bmust[- ]fix\b|\bshould[- ]fix\b|\bevidence (?:packets?|blocks?|matrix)\b'
                                 r'|\brewrite plan\b|\bred[- ]team review\b|\bCritical items?\b'
                                 r'|\b(?:get|save|set|list|find|read|register|deliver|start|finish|run|request|search)'
                                 r'_[a-z_]+\b', re.I)
# Budgets from the role prompts (rule N9): tool calls a turn, and web searches and fetches a brief. A bot's first
# brief in a case gets more than a revision brief.
TURN_BUDGETS = {LEAD: 45, RED_TEAM: 50, REVIEWER: 30, **{analyst: 70 for analyst in ANALYSTS}}
REVISION_TURN_BUDGETS = {RED_TEAM: 30, **{analyst: 35 for analyst in ANALYSTS}}
BRIEF_BUDGETS = {'first': {'web_search': 18, 'web_fetch': 12}, 'revision': {'web_search': 6, 'web_fetch': 6}}
RED_TEAM_FIRST_BUDGET = {'web_search': 10, 'web_fetch': 8}
# The Lead's research for sections 11 and 14, across the whole case.
LEAD_CASE_BUDGET = {'web_search': 8, 'web_fetch': 6}
# Reply lengths from the role prompts (P21 for the analysts and the Red Team, P27 for the IC Reviewer).
REPLY_LIMITS = {REVIEWER: ('P27', 1000), **{agent: ('P21', 1500) for agent in RESEARCHERS}}
# What counts as research when an evidence block lists the queries it ran.
RESEARCH_TOOLS = {'web_search', 'web_fetch', 'read_sec_filing', 'get_sec_financials', 'list_sec_filings',
                  'find_sec_company', 'get_price_history', 'get_valuation_snapshot', 'read_client_document',
                  'search_public_records', 'search_literature', 'get_market_regime', 'get_trading_snapshot',
                  'get_insider_activity'}


def _iso(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds')


def _ms(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp() * 1000


def redact(value):
    """Hide real email addresses anywhere in a nested value; keep fictional .example ones."""
    if isinstance(value, str):
        def keep_or_hide(match):
            domain = match.group(0).rsplit('@', 1)[1].lower()
            fictional = domain.endswith('.example') or domain in FICTIONAL_DOMAINS
            return match.group(0) if fictional else '[redacted email]'
        return EMAIL_RE.sub(keep_or_hide, value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return '\n'.join(part.get('text', '') for part in content or [] if part.get('type') == 'text')


def read_transcript(path: Path) -> dict | None:
    """One Rakazo run from a Pi format-4 JSONL file: its context entry and recorded messages."""
    records = []
    # Split on newlines only: splitlines() also breaks at characters such as U+0085, which a fetched page can put
    # inside a JSON string, unescaped.
    for line in path.read_text().split('\n'):
        if line.strip():
            parsed = json.loads(line)
            records.extend(parsed if isinstance(parsed, list) else [parsed])
    entries = [record for record in records if record.get('kind') == 'entry']
    context = next((e['data'] for e in entries if e.get('customType') == 'rakazo_context'), None)
    if not context:
        return None
    header = next((record for record in records if record.get('kind') == 'header'), {})
    return {
        'run_id': context['rakazoRunId'], 'bot_id': context['rakazoBotId'],
        'provider': context.get('provider'), 'model': context.get('model'),
        'thinking_level': context.get('thinkingLevel'), 'created_ms': header.get('createdAt', 0),
        'messages': [(entry['timestamp'], entry['message']) for entry in entries if entry.get('type') == 'message'],
    }


def dedupe_messages(messages: list[tuple]) -> list[tuple]:
    """A run paused for approval resumes in a new transcript file that replays its earlier messages."""
    seen, kept = set(), []
    for ts, message in messages:
        key = (message.get('role'), message.get('timestamp'), message.get('toolCallId'),
               json.dumps(message.get('content'), sort_keys=True))
        if key not in seen:
            seen.add(key)
            kept.append((ts, message))
    return kept


def transcript_events(run: dict, agent: str) -> tuple[list[dict], dict]:
    """Thoughts, words, tool calls and results from one run; replayed history is dropped."""
    events = []
    usage = {'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0, 'cost_usd': 0.0, 'model_calls': 0}
    prompt_seen = False
    for ts, message in run['messages']:
        if message.get('rakazoHistory'):
            continue
        base = {'ts_ms': ts, 'agent': agent, 'rakazo_run_id': run['run_id']}
        role = message.get('role')
        if role == 'user':
            kind = 'platform_message' if prompt_seen else 'run_prompt'
            events.append({**base, 'type': kind, 'text': _text_of(message.get('content'))})
            prompt_seen = True
        elif role == 'assistant':
            for part in message.get('content') or []:
                if part.get('type') == 'thinking' and part.get('thinking', '').strip():
                    events.append({**base, 'type': 'thought', 'text': part['thinking']})
                elif part.get('type') == 'text' and part.get('text', '').strip():
                    events.append({**base, 'type': 'assistant_text', 'text': part['text']})
                elif part.get('type') == 'toolCall':
                    events.append({**base, 'type': 'tool_call', 'tool': MCP_PREFIX_RE.sub('', part.get('name', '')),
                                   'tool_full_name': part.get('name'), 'call_id': part.get('id'),
                                   'arguments': part.get('arguments') or {}})
            spent = message.get('usage') or {}
            usage['input_tokens'] += spent.get('input', 0)
            usage['output_tokens'] += spent.get('output', 0)
            usage['cache_read_tokens'] += spent.get('cacheRead', 0)
            cost = call_cost(message.get('model') or run.get('model'), spent.get('cacheRead', 0),
                             spent.get('input', 0), spent.get('output', 0), ts)
            if cost is None:  # A model with no DeepSeek price: keep Rakazo's estimate.
                cost = (spent.get('cost') or {}).get('total', 0) or 0
            usage['cost_usd'] += cost
            if message.get('content') or spent.get('output'):  # An aborted turn records an empty message.
                usage['model_calls'] += 1
        elif role == 'toolResult':
            events.append({**base, 'type': 'tool_result', 'tool': MCP_PREFIX_RE.sub('', message.get('toolName', '')),
                           'call_id': message.get('toolCallId'), 'is_error': bool(message.get('isError')),
                           'text': _text_of(message.get('content'))})
    return events, usage


def api_events(messages_by_agent: dict[str, list[dict]]) -> list[dict]:
    """The user's request, inter-bot messages and bot replies, as the Rakazo API stored them."""
    events = []
    for agent, messages in messages_by_agent.items():
        for message in messages:
            base = {'ts_ms': _ms(message['createdAt']), 'agent': agent,
                    'rakazo_run_id': message.get('runId'), 'message_id': message.get('id')}
            for block in message.get('blocks') or []:
                kind = block.get('kind')
                if kind == 'bot_message_sent':
                    events.append({**base, 'type': 'peer_message_sent', 'to': block.get('toBotName'),
                                   'intent': block.get('intent', 'request'), 'text': block.get('text', '')})
                elif kind == 'bot_message_received':
                    events.append({**base, 'type': 'peer_message_received', 'from': block.get('fromBotName'),
                                   'intent': block.get('intent'), 'hop': block.get('hop'),
                                   'return_to_message_id': block.get('returnToMessageId'),
                                   'reply_to_message_id': message.get('replyToMessageId'),
                                   'text': block.get('text', '')})
                elif kind == 'ask':
                    events.append({**base, 'type': 'platform_guard', 'text': block.get('text', ''),
                                   'detail': block.get('detail'), 'status': block.get('status')})
                elif kind == 'text' and message.get('role') == 'user':
                    events.append({**base, 'type': 'user_message', 'text': block.get('text', '')})
                elif kind == 'text' and message.get('role') == 'bot':
                    events.append({**base, 'type': 'reply', 'text': block.get('text', '')})
    return events


def _trigger_hop(run_id: str, events: list[dict]) -> int | None:
    """The hop of the bot message that started a run, if one did."""
    return next((event.get('hop') for event in events if event.get('rakazo_run_id') == run_id
                 and event['type'] == 'peer_message_received'), None)


def _run_trigger(run_id: str, events: list[dict]) -> str:
    for event in events:
        if event.get('rakazo_run_id') != run_id:
            continue
        if event['type'] == 'user_message':
            return "the user's request"
        if event['type'] == 'peer_message_received':
            hop = f", hop {event['hop']}" if event.get('hop') is not None else ''
            return f"a {event.get('intent') or 'message'} from {event['from']}{hop}"
    return 'a Rakazo follow-up'


def confidential_tokens(case: dict) -> dict[str, str]:
    """Distinctive figures and highlighted facts from client-confidential documents, mapped to their document."""
    tokens = {}
    for document in case['client_documents']:
        path = ROOT / document['file']
        if document['confidentiality'] != 'client-confidential' or not path.exists():
            continue
        text = _document_text(path)
        for pattern in CONFIDENTIAL_PATTERNS:
            for match in pattern.finditer(text):
                tokens.setdefault((match.group(1) if pattern.groups else match.group()).strip(), document['name'])
    return tokens


def _document_text(path: Path) -> str:
    """A client document's text: Markdown or text as it is, other formats through the server's reader."""
    if path.suffix.lower() in ('.md', '.txt', '.csv'):
        return path.read_text()
    try:
        from tools import documents
    except ImportError:
        return ''
    return documents.document_text(path)


def _rule_key(observation: dict):
    rule = observation['rule']
    return (0, int(rule[1:])) if re.fullmatch(r'N\d+', rule) else (1, 0)


def observe_user_messages(replies: list[dict], case: dict) -> list[dict]:
    """What the Lead told the user: a draft's rating before any version was delivered (N5),
    and internal working material in any message (N6)."""
    observations = []
    delivered_ms = min((_ms(d['delivered_at']) for d in case['deliveries']), default=float('inf'))
    for reply in replies:
        text = reply.get('text', '')
        quoted = _clip(' '.join(text.split()), 120)
        if reply['ts_ms'] < delivered_ms:
            ratings = {d['rating'] for d in case['memo_drafts'] if _ms(d['saved_at']) <= reply['ts_ms']}
            answer_text = RATING_PAIR_RE.sub(' ', text)
            named = sorted(r for r in ratings if re.search(rf'\b{re.escape(r)}\b', answer_text))
            if named:
                observations.append({'rule': 'N5', 'detail': f"before delivery, the Lead told the user the draft's "
                                                              f"rating ({', '.join(named)}): \"{quoted}\""})
        internal = sorted({m.group() for m in MESSAGE_INTERNAL_RE.finditer(text)} |
                          {m.group() for m in memo.INTERNAL_IDS_RE.finditer(text)})
        if internal:
            observations.append({'rule': 'N6', 'detail': f"the Lead's message to the user names internal material "
                                                          f"({', '.join(internal[:6])}): \"{quoted}\""})
    return observations


def observe_rules(events: list[dict], runs: list[dict], case: dict, replies: list[dict] = ()) -> list[dict]:
    """Possible rule breaks visible in a run. They are only reported; nothing was blocked.
    replies: the Lead's messages in the user's thread, as Rakazo stored them."""
    observations = observe_user_messages(list(replies), case)
    listed = case_rules.is_listed(case)
    for delivery in case['deliveries']:
        gate = delivery.get('review_gate') or {}
        if not gate.get('approved'):
            state = 'reviewed but not approved' if gate.get('reviewed') else 'never reviewed'
            observations.append({'rule': 'N5', 'detail': f"report v{delivery['memo_version']} was delivered, but that version was {state}"})
        # Re-check the delivered text with the current rules; the delivery record keeps what was reported then.
        draft = next((d for d in case['memo_drafts'] if d['version'] == delivery['memo_version']), None)
        text = _version_markdown(draft)
        findings = (memo.check_memo(text, case['sources'], draft['rating'], listed)['findings'] if text
                    else (delivery.get('memo_check') or {}).get('findings', []))
        for finding in findings:
            observations.append({'rule': finding['rule'], 'detail': f"delivered report v{delivery['memo_version']}: {finding['detail']}"})
        final = delivery.get('final_check') or {}
        if final and not final.get('passed'):
            failed = {name: len(found) for name, found in final.items() if isinstance(found, list) and found}
            observations.append({'rule': 'P40', 'detail': f"report v{delivery['memo_version']} was delivered with its "
                                                           'final check failing: ' + ', '.join(
                                                               f'{n} {name}' for name, n in failed.items())})
    tokens = confidential_tokens(case)
    for event in events:
        if event['type'] == 'tool_call' and event['tool'] in OUTBOUND_TOOLS:
            arguments = json.dumps(event['arguments'], ensure_ascii=False).lower()
            leaked = sorted(token for token in tokens if token.lower() in arguments)
            if leaked:
                observations.append({'rule': 'N7', 'seq': event['seq'],
                                     'detail': f"{event['agent']} put confidential content in {event['tool']}: " + ', '.join(leaked)})
    retrieved = ' '.join([e.get('text', '') for e in events if e['type'] == 'tool_result'] +
                         [json.dumps(e['arguments']) for e in events if e['type'] == 'tool_call' and e['tool'] == 'web_fetch'])
    for source in case['sources']:
        location = source['location'].strip().rstrip('/')
        if location.startswith('http') and location not in retrieved:
            observations.append({'rule': 'N1', 'detail': f"{source['id']} ({location}) never appeared in a tool result in this run"})
    for event in events:
        if event['type'] == 'platform_guard':
            observations.append({'rule': 'platform guard', 'seq': event['seq'],
                                 'detail': f"Rakazo stopped {event['agent']}: {event['text']} ({event.get('detail') or ''})"})
    briefed: set[str] = set()
    for run in sorted(runs, key=lambda r: r.get('started_at') or ''):
        mine = [e for e in events if e.get('rakazo_run_id') == run['rakazo_run_id']]
        calls = [e for e in mine if e['type'] == 'tool_call']
        researcher = run['agent'] in RESEARCHERS
        # A bot's first brief in the case gets the first-brief budget; later briefs are revisions.
        brief = 'revision' if researcher and run['agent'] in briefed else 'first'
        if researcher and _trigger_hop(run['rakazo_run_id'], events):
            briefed.add(run['agent'])
        budget = (REVISION_TURN_BUDGETS.get(run['agent']) if brief == 'revision' else TURN_BUDGETS.get(run['agent']))
        if budget and len(calls) > budget:
            observations.append({'rule': 'N9', 'detail': f"{run['agent']} made {len(calls)} tool calls in one turn (limit {budget})"})
        if researcher:
            limits = RED_TEAM_FIRST_BUDGET if run['agent'] == RED_TEAM and brief == 'first' else BRIEF_BUDGETS[brief]
            for tool_name, limit in limits.items():
                count = sum(e['tool'] == tool_name for e in calls)
                if count > limit:
                    observations.append({'rule': 'N9', 'detail': f"{run['agent']} made {count} {tool_name} calls for "
                                                                  f"one {brief} brief (limit {limit})"})
        rule, limit = REPLY_LIMITS.get(run['agent'], (None, None))
        said = [e['text'] for e in mine if e['type'] == 'assistant_text' and e.get('text')]
        if limit and said and len(said[-1]) > limit:
            observations.append({'rule': rule, 'detail': f"{run['agent']} replied with {len(said[-1]):,} characters "
                                                          f"(limit {limit:,})"})
    lead_calls = [e for e in events if e['type'] == 'tool_call' and e['agent'] == LEAD]
    for tool_name, limit in LEAD_CASE_BUDGET.items():
        count = sum(e['tool'] == tool_name for e in lead_calls)
        if count > limit:
            observations.append({'rule': 'N9', 'detail': f'the Lead Analyst made {count} {tool_name} calls in the case '
                                                          f'(limit {limit})'})
    for key, blocks in (case.get('evidence') or {}).items():
        for block in blocks:
            # A block saved after a review may repeat earlier queries, so count the author's research up to the block.
            ran = sum(e['type'] == 'tool_call' and e['agent'] == block.get('author') and e['tool'] in RESEARCH_TOOLS
                      and e['ts'][:19] <= block['saved_at'][:19] for e in events)
            if len(block.get('queries') or []) > ran:
                observations.append({'rule': 'N1', 'detail': f"the {key} evidence block lists {len(block['queries'])} "
                                                              f"queries, but {block.get('author')} had run {ran}"})
    return sorted(observations + observe_sections(case) + observe_workflow(events, case), key=_rule_key)


def observe_sections(case: dict) -> list[dict]:
    """Sections saved by someone other than their owner (P32), sections drafted before their evidence passed the
    gate (P34), review rounds beyond the last one (P9) and Critical items closed without new evidence (N11)."""
    observations = []
    for key, revisions in (case.get('memo_parts') or {}).items():
        owner = sections.BY_KEY[key].owner
        for r in revisions:
            if r['author'] and r['author'] != owner:
                observations.append({'rule': 'P32', 'detail': f"{r['author']} saved revision {r['revision']} of the "
                                                               f"{key} section, which the {owner} owns"})
        first = revisions[0] if revisions else None
        if key != sections.EXECUTIVE_SUMMARY.key and first and first.get('evidence_before_draft') is False:
            observations.append({'rule': 'P34', 'detail': f"the {key} section was first saved before its evidence "
                                                           'block passed the gate'})
    finished = case_rules.finished_reviews(case)
    if len(finished) > case_rules.MAX_REVIEW_ROUNDS:
        observations.append({'rule': 'P9', 'detail': f'{len(finished)} review rounds; the limit is '
                                                      f'{case_rules.MAX_REVIEW_ROUNDS}'})
    for review in finished:
        later = [r for r in finished if r['round'] == review['round'] + 1]
        if not later:
            continue
        for item in review.get('items') or []:
            if item['severity'] != 'Critical':
                continue
            since = review.get('finished_at') or ''
            new_sources = [s for s in case['sources'] if s.get('registered_by') in item['owners']
                           and (s.get('registered_at') or '') > since]
            if not new_sources:
                observations.append({'rule': 'N11', 'detail': f"review {review['id']}'s Critical item on "
                                                               f"{', '.join(item['sections'])} was answered with no new "
                                                               f"source from {', '.join(item['owners'])}"})
    return observations


def observe_workflow(events: list[dict], case: dict) -> list[dict]:
    """The skill's order of work: the research plan before the first brief (P33), the red-team review before the
    first review (P35), the QA loop before each version (P36)."""
    observations = []
    calls = [e for e in events if e['type'] == 'tool_call']

    def first(tool: str, agent: str | None = None, after: str = '') -> str | None:
        return next((e['ts'] for e in calls if e['tool'] == tool and (agent is None or e['agent'] == agent)
                     and e['ts'] > after), None)
    brief = first('message_bot', LEAD)
    plan = first('save_research_plan', LEAD)
    if brief and (not plan or plan > brief):
        observations.append({'rule': 'P33', 'detail': 'the Lead briefed the team before saving the research plan'})
    review = first('start_review', REVIEWER)
    red_team = first('save_red_team_review', RED_TEAM)
    if review and (not red_team or red_team > review):
        observations.append({'rule': 'P35', 'detail': 'the first review started before the red-team review was saved'})
    previous = ''
    for version in case['memo_drafts']:
        loop = first('run_qa_loop', LEAD, previous)
        if not loop or loop[:19] > version['saved_at'][:19]:
            observations.append({'rule': 'P36', 'detail': f"version {version['version']} was saved without a QA loop "
                                                           'since the previous version'})
        previous = version['saved_at']
    return observations


def _version_markdown(version: dict | None) -> str | None:
    """A version's report as Markdown, from the file the server wrote when it was saved."""
    path = Path(((version or {}).get('files') or {}).get('markdown') or '')
    return path.read_text() if version and path.is_file() else None


def delivered_check(case: dict) -> dict | None:
    """The final check the server ran on the delivered report: QA, citations and the delivery folder."""
    if not case['deliveries']:
        return None
    delivery = case['deliveries'][-1]
    return {'version': delivery['memo_version'], **(delivery.get('final_check') or {})}


def _rakazo_build() -> str | None:
    script = ROOT / 'infra' / 'setup-rakazo.sh'
    match = re.search(r'RAKAZO_REVISION=(\w+)', script.read_text()) if script.exists() else None
    return match and f'sha-{match.group(1)}'


def build_trace(run_dir: Path) -> dict:
    case = json.loads((run_dir / 'case.json').read_text())
    raw = run_dir / 'rakazo'
    captured = json.loads((raw / 'messages.json').read_text())
    bot_names = {bot_id: name for name, bot_id in captured['bots'].items()}
    api = api_events(captured['messages'])
    started_ms = _ms(case['started_at'])
    api_runs = {event['rakazo_run_id'] for event in api if event.get('rakazo_run_id')}

    transcripts = {}
    for path in sorted((raw / 'pi-sessions').rglob('*.jsonl')) if (raw / 'pi-sessions').exists() else []:
        transcript = read_transcript(path)
        if not transcript or transcript['bot_id'] not in bot_names:
            continue
        if transcript['run_id'] not in api_runs and transcript['created_ms'] < started_ms:
            continue  # An earlier scenario or a bot's introduction run.
        merged = transcripts.setdefault(transcript['run_id'], {**transcript, 'messages': []})
        merged['messages'] += transcript['messages']

    runs, events, usage_by_agent = [], [], {}
    for transcript in transcripts.values():
        transcript['messages'] = dedupe_messages(transcript['messages'])
        agent = bot_names[transcript['bot_id']]
        run_events, usage = transcript_events(transcript, agent)
        events += run_events
        runs.append({'rakazo_run_id': transcript['run_id'], 'agent': agent, 'model': transcript['model'],
                     'provider': transcript['provider'], 'thinking_level': transcript['thinking_level'],
                     'usage': usage})
        totals = usage_by_agent.setdefault(agent, dict.fromkeys(usage, 0))
        for key, value in usage.items():
            totals[key] += value

    recorded = {run['rakazo_run_id'] for run in runs}
    # Every message the user saw from the Lead, including those the transcripts also record.
    replies = [{'ts_ms': event['ts_ms'], 'text': event.get('text', '')}
               for event in api if event['type'] == 'reply' and event['agent'] == LEAD]
    # Bot replies duplicate the transcript's final words; keep them only for runs without a transcript.
    events += [event for event in api if event['type'] != 'reply' or event.get('rakazo_run_id') not in recorded]
    events.sort(key=lambda event: event['ts_ms'])
    for seq, event in enumerate(events, 1):
        event['seq'] = seq
        event['ts'] = _iso(event.pop('ts_ms'))
    for run in runs:
        mine = [event for event in events if event.get('rakazo_run_id') == run['rakazo_run_id']]
        run.update(trigger=_run_trigger(run['rakazo_run_id'], events),
                   started_at=mine[0]['ts'] if mine else None, ended_at=mine[-1]['ts'] if mine else None,
                   tool_calls=sum(event['type'] == 'tool_call' for event in mine))
    runs.sort(key=lambda run: run['started_at'] or '')

    scenario_file = ROOT / 'scenarios' / f"{case['scenario']}.yaml"
    scenario = yaml.safe_load(scenario_file.read_text()) if scenario_file.exists() else {
        'name': case['scenario'], 'summary': 'A request the user typed in.'}
    if case.get('request'):  # Newer case files keep the request itself, which a typed-in request needs.
        scenario['request'] = case['request']
    outcome_file = run_dir / 'outcome.json'
    outcome = json.loads(outcome_file.read_text()).get('outcome') if outcome_file.exists() else None
    delivered = case['deliveries'][-1] if case['deliveries'] else None
    memo_file = run_dir / delivered['file'] if delivered else None
    final_memo = memo_file.read_text() if memo_file and memo_file.exists() else None
    total = {key: sum(agent_usage[key] for agent_usage in usage_by_agent.values())
             for key in ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cost_usd', 'model_calls')}
    trace = {
        'trace_format': FORMAT,
        'scenario': {key: scenario.get(key) for key in ('name', 'summary', 'exercises', 'expected', 'watch_for', 'request')},
        'run': {'run_id': case['run_id'], 'started_at': case['started_at'], 'outcome': outcome,
                'rakazo_build': _rakazo_build(),
                'model': {key: runs[0][key] for key in ('provider', 'model', 'thinking_level')} if runs else None},
        'agents': [{'name': profile.name, 'bot_id': captured['bots'].get(profile.name), 'role': profile.description,
                    'mcp_tools': list(profile.mcp_tools),
                    'builtin_tools': [t for t in BUILTIN_TOOLS if t not in profile.disabled_builtin_tools]}
                   for profile in team_profiles()],
        'rakazo_runs': runs,
        'events': events,
        'observations': observe_rules(events, runs, case, replies),
        'case_file': {
            'client_documents': [{'name': d['name'], 'confidentiality': d['confidentiality']} for d in case['client_documents']],
            'sources': case['sources'],
            'scope': case.get('scope') and {k: case['scope'].get(k) for k in ('company', 'ticker', 'type', 'decision',
                                                                              'language')},
            'workflow': case.get('workflow') or {},
            'evidence': {key: [{k: block.get(k) for k in ('author', 'queries', 'rows', 'gate', 'plan', 'gate_passed',
                                                         'saved_at')} for block in blocks]
                         for key, blocks in (case.get('evidence') or {}).items()},
            'user_data_requests': case.get('user_data_requests') or [],
            'memo_parts': {key: [{k: r.get(k) for k in ('revision', 'author', 'chars', 'passed', 'evidence_before_draft',
                                                        'saved_at')} for r in revisions]
                           for key, revisions in (case.get('memo_parts') or {}).items()},
            'memo_versions': [{'version': d['version'], 'rating': d['rating'], 'saved_at': d['saved_at'],
                               'composite_score': d.get('composite_score'), 'cover': d.get('cover'),
                               'parts': {key: ref['revision'] for key, ref in (d.get('parts') or {}).items()},
                               'changed_parts': d.get('changed_parts', []), 'missing_parts': d.get('missing_parts', []),
                               'check_passed': d.get('passed'), 'check': d.get('check')}
                              for d in case['memo_drafts']],
            'reviews': [{key: r.get(key) for key in ('id', 'memo_version', 'round', 'verdict', 'grade', 'top_three',
                                                     'ready', 'passes', 'items', 'revision_requests',
                                                     'evidence_requests', 'started_at', 'finished_at')}
                        for r in case['reviews']],
            'deliveries': [{'memo_version': d['memo_version'], 'delivered_at': d['delivered_at'],
                            'folder': Path(d.get('folder') or '').name, 'review_gate': d['review_gate'],
                            'final_check': d.get('final_check'),
                            'memo_check_findings': (d.get('memo_check') or {}).get('findings', [])}
                           for d in case['deliveries']],
        },
        'usage': {'by_agent': usage_by_agent, 'total': total},
        'delivered_check': delivered_check(case),
        'final_memo': final_memo,
    }
    return redact(trace)


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + ' …'


def _quote(text: str) -> str:
    return '\n'.join('> ' + line if line else '>' for line in text.splitlines())


def _render_event(event: dict) -> str:
    kind = event['type']
    if kind == 'thought':
        return f"**Thought**\n\n{_quote(_clip(event['text'], MD_LIMITS['thought']))}"
    if kind == 'tool_call':
        arguments = _clip(json.dumps(event['arguments'], ensure_ascii=False), MD_LIMITS['arguments'])
        return f"**Action:** `{event['tool']}` {arguments}"
    if kind == 'tool_result':
        label = 'Observation (error)' if event['is_error'] else 'Observation'
        return f"**{label}** from `{event['tool']}`\n\n```\n{_clip(event['text'], MD_LIMITS['tool_result'])}\n```"
    if kind == 'assistant_text':
        return f"**Says**\n\n{_quote(_clip(event['text'], MD_LIMITS['assistant_text']))}"
    if kind == 'reply':
        return f"**Reply** (from the API)\n\n{_quote(_clip(event['text'], MD_LIMITS['assistant_text']))}"
    if kind == 'peer_message_sent':
        return (f"**Message to {event['to']}** ({event['intent']})\n\n"
                f"{_quote(_clip(event['text'], MD_LIMITS['peer']))}")
    if kind == 'platform_message':
        return f"*Rakazo:* {_clip(event['text'], MD_LIMITS['platform_message'])}"
    if kind == 'platform_guard':
        return f"**Rakazo approval card:** {event['text']} ({event.get('detail') or ''}), status: {event.get('status')}"
    return ''


def render_markdown(trace: dict) -> str:
    scenario, run, usage = trace['scenario'], trace['run'], trace['usage']['total']
    model = run['model'] or {}
    lines = [f"# Trace: {scenario['name']}", '', scenario.get('summary') or '', '',
             f"- **Run:** `{run['run_id']}`, started {run['started_at']}, outcome **{run['outcome']}**",
             f"- **Runtime:** Rakazo `{run['rakazo_build']}`, {model.get('provider')} `{model.get('model')}` "
             f"(thinking {model.get('thinking_level')})",
             f"- **Usage:** {usage['model_calls']} model calls, {usage['input_tokens']:,} input / "
             f"{usage['output_tokens']:,} output tokens, about ${usage['cost_usd']:.2f}",
             f"- **Rules exercised:** {', '.join(scenario.get('exercises') or [])}"]
    lines += [f'  - Watch for: {item}' for item in scenario.get('watch_for') or []]
    lines += ['', '## Agents', '', '| Agent | Role | MCP tools | Rakazo built-ins |', '|---|---|---|---|']
    lines += [f"| {a['name']} | {a['role']} | {', '.join(a['mcp_tools'])} | {', '.join(a['builtin_tools']) or 'none'} |"
              for a in trace['agents']]
    lines += ['', '## Timeline', '']
    user_messages = [e for e in trace['events'] if e['type'] == 'user_message']
    for event in user_messages[:1]:
        lines += [f"### User → {event['agent']} ({event['ts']})", '', _quote(event['text']), '']
    for number, rakazo_run in enumerate(trace['rakazo_runs'], 1):
        lines += [f"### {number}. {rakazo_run['agent']}, woken by {rakazo_run['trigger']} ({rakazo_run['started_at']})", '']
        for event in user_messages[1:]:
            if event.get('rakazo_run_id') == rakazo_run['rakazo_run_id']:
                lines += ['**Follow-up from the user**', '', _quote(event['text']), '']
        received = [e for e in trace['events'] if e['type'] == 'peer_message_received'
                    and e.get('rakazo_run_id') == rakazo_run['rakazo_run_id']]
        for event in received:
            lines += [f"**Message from {event['from']}** ({event.get('intent')})", '',
                      _quote(_clip(event['text'], MD_LIMITS['peer'])), '']
        for event in trace['events']:
            if event.get('rakazo_run_id') == rakazo_run['rakazo_run_id'] and event['type'] not in ('user_message', 'peer_message_received', 'run_prompt'):
                rendered = _render_event(event)
                if rendered:
                    lines += [rendered, '']
    case = trace['case_file']
    lines += ['## Case file at the end', '']
    if case['sources']:
        lines += ['| ID | Source | Type | Confidence |', '|---|---|---|---|']
        lines += [f"| {s['id']} | {s['title']} | {s['source_type']} | {s['confidence']} |" for s in case['sources']]
        lines.append('')
    if case.get('memo_parts'):
        lines += ['| # | Section | Owner | Revisions (by) | Characters | Evidence first | Check at its last save |',
                  '|---|---|---|---|---|---|---|']
        for section in sections.ALL_SECTIONS:
            revisions = case['memo_parts'].get(section.key) or []
            block = (case.get('evidence') or {}).get(section.key)
            if revisions:
                authors = ', '.join(f"{r['revision']} ({r['author'] or 'unknown'})" for r in revisions)
                last = revisions[-1]
                first = '' if section.number is None else ('yes' if revisions[0].get('evidence_before_draft') else 'no')
                lines.append(f"| {section.number or '-'} | {section.title} | {section.owner} | {authors} | "
                             f"{last['chars']:,} | {first} | {'passed' if last['passed'] else 'problems'} |")
            else:
                lines.append(f"| {section.number or '-'} | {section.title} | {section.owner} | none | | "
                             f"{'block only' if block else ''} | |")
        lines.append('')
    workflow = case.get('workflow') or {}
    saved = [name.replace('_', ' ') for name in ('research_plan', 'profile_requirements', 'thesis_table',
                                                 'scenario_analysis', 'red_team_review') if workflow.get(name)]
    lines.append(f"- Workflow records saved: {', '.join(saved) or 'none'}")
    open_items = [i for i in workflow.get('rewrite_plan') or [] if not i.get('resolved')]
    if workflow.get('iteration_log'):
        lines.append(f"- QA loops: {len(workflow['iteration_log'])}, last "
                     f"{'passed' if workflow['iteration_log'][-1]['passed'] else 'failed'}; "
                     f"{len(open_items)} rewrite items open")
    for request in case.get('user_data_requests') or []:
        lines.append(f"- User data request {request['id']} ({request['section']}): {request['database']}: "
                     f"{request['query']}")
    for version in case['memo_versions']:
        if version.get('parts'):
            lines.append(f"- Report v{version['version']} ({version['rating']}, composite "
                         f"{version.get('composite_score') or 'n/a'}): sections changed: "
                         f"{', '.join(version['changed_parts']) or 'none'}; check "
                         f"{'passed' if version['check_passed'] else 'reported problems'}")
    for review in case['reviews']:
        counts = {s: sum(i['severity'] == s for i in review.get('items') or []) for s in ('Critical', 'Important', 'Minor')}
        by_owner = ', '.join(f'{owner}: {len(keys)} section{"s" if len(keys) > 1 else ""}'
                             for owner, keys in (review.get('revision_requests') or {}).items())
        lines.append(f"- Review {review['id']} of report v{review['memo_version']} (round {review.get('round')}): "
                     f"{review.get('verdict') or 'unfinished'}, grade {review.get('grade') or 'n/a'}, "
                     f"{counts['Critical']} Critical / {counts['Important']} Important / {counts['Minor']} Minor items"
                     + (f" ({by_owner})" if by_owner else ''))
    for delivery in case['deliveries']:
        gate = delivery['review_gate']
        status = (f"approved in review {gate['review_id']}" if gate['approved']
                  else 'reviewed but not approved' if gate['reviewed'] else 'never reviewed')
        final = (delivery.get('final_check') or {}).get('passed')
        lines.append(f"- Delivered report v{delivery['memo_version']} ({status}; final check "
                     f"{'passed' if final else 'failed'}) to {delivery.get('folder')}")
    lines += ['', '## Rule observations', '',
              'Possible rule breaks found in this run. They are only reported; nothing was blocked.', '']
    if trace['observations']:
        lines += ['| Rule | What happened |', '|---|---|']
        lines += [f"| {o['rule']} | {o['detail']} |" for o in trace['observations']]
    else:
        lines.append('None found.')
    final = trace.get('delivered_check')
    if final:
        lines += ['', '## Final check at delivery', '', f"Report v{final['version']} against the skill's final check "
                  '(reported, never blocking).', '', '| Check | Problems |', '|---|---|']
        for name in ('report', 'depth', 'citations', 'output'):
            found = final.get(name) or []
            lines.append(f"| {name} | {'; '.join(found[:6]) + (f' (and {len(found) - 6} more)' if len(found) > 6 else '') or 'none'} |")
    if trace['final_memo']:
        lines += ['', '## Final report', '', trace['final_memo'].strip()]
    return '\n'.join(lines).rstrip() + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('run_id', nargs='?', help='defaults to the active run')
    parser.add_argument('--out', default=str(ROOT.parent / 'traces' / 'phase2-baseline'))
    parser.add_argument('--name', help='file name stem; defaults to the scenario name')
    args = parser.parse_args()
    run_id = args.run_id or json.loads((ROOT / 'runs' / 'active.json').read_text())['run_id']
    trace = build_trace(ROOT / 'runs' / run_id)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = args.name or trace['scenario']['name']
    (out / f'{stem}.json').write_text(json.dumps(trace, indent=1, ensure_ascii=False))
    (out / f'{stem}.md').write_text(render_markdown(trace))
    print(f"Wrote {out / stem}.json and .md: {len(trace['events'])} events across "
          f"{len(trace['rakazo_runs'])} Rakazo runs.")


if __name__ == '__main__':
    main()
