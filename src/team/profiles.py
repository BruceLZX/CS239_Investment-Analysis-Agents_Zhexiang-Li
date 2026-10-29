"""The four bots: role prompts, model, and the tools each role may use.

Each bot's instructions are its role prompt, the standards for the memo parts it writes (the IC Reviewer gets all of
them) and the must-never rules. Tool limits are role design (each bot gets what its job needs), not policy
enforcement: the rules in prompts/rules.md are instructions only, for the Phase 2 framework to enforce.
"""
import os
from pathlib import Path

from tools import memo
from tools.agents import AGENTS

from .rakazo_client import BotProfile, MCPConnection, ModelChoice

PROMPTS = Path(__file__).resolve().parent / 'prompts'
LEAD, FUNDAMENTALS, MARKET, REVIEWER = AGENTS['lead'], AGENTS['fundamentals'], AGENTS['market'], AGENTS['reviewer']
# Bots from earlier versions of the team. Setting up the team archives them, so no bot lists them as teammates.
RETIRED = ('Research Analyst',)

# Every built-in tool on the pinned Rakazo build (packages/contracts/src/builtin-tools.ts).
BUILTIN_TOOLS = (
    'computer_observe', 'computer_act', 'browser_navigate', 'browser_snapshot', 'browser_act',
    'list_files', 'read_file', 'write_file', 'attach_file', 'shell', 'open_path', 'launch_app',
    'request_takeover', 'ask_user', 'connect_app', 'message_user', 'request_secret', 'list_secrets',
    'secret_request', 'forget_secret', 'render_plot', 'generate_image', 'generate_video', 'add_mcp_server',
    'remember', 'save_shared_memory', 'web_search', 'web_fetch', 'cloud_agent_launch', 'cloud_agent_status',
    'cloud_agent_reply', 'cloud_agent_cancel', 'search_history', 'read_history', 'save_memory',
    'recall_memory', 'forget_memory', 'task_catalog', 'scratchpad_list', 'scratchpad_add',
    'scratchpad_update', 'scratchpad_complete', 'scratchpad_remove', 'board_tickets', 'ticket_get',
    'ticket_create', 'ticket_update', 'ticket_comment', 'schedule_create', 'schedule_list',
    'schedule_cancel', 'end_call', 'call_user', 'skill_read', 'skill_create', 'skill_update',
    'skill_delete', 'run_subagent', 'propose_instructions_update', 'create_space', 'spawn_bot',
    'update_bot', 'list_fleet', 'create_group', 'update_group', 'organize_bot', 'set_child_instructions',
    'set_child_bot_model', 'create_child_routine', 'archive_bot', 'message_bot', 'handoff_to_bot',
    'connect_agent', 'respond_agent_connection', 'message_agent',
)


def _part_sections() -> dict[str, str]:
    """prompts/parts.md by section: the writing standard, then each part's standard by its key."""
    sections: dict[str, list[str]] = {}
    key = None
    for line in (PROMPTS / 'parts.md').read_text().splitlines():
        if line.startswith('## '):
            key = line[3:].strip()
            sections[key] = []
        elif key:
            sections[key].append(line)
    return {key: '\n'.join(lines).strip() for key, lines in sections.items()}


def _part_heading(part: memo.Part) -> str:
    """A part's title with the floors its check holds it to, from tools/memo.py."""
    floor, ceiling = part.chars
    tables = f', {part.tables} table{"s" if part.tables > 1 else ""}' if part.tables else ''
    return (f'### {part.heading} (`{part.key}`, written by the {part.owner}): {floor:,}-{ceiling:,} characters, '
            f'at least {part.numbers} sourced figures and {part.source_ids} distinct source IDs{tables}')


def _instructions(prompt_file: str, owner: str | None = None) -> str:
    """The role prompt, then the standards for the owner's parts (every part when owner is None), then the rules."""
    sections = _part_sections()
    parts = [part for part in memo.PARTS if owner is None or part.owner == owner]
    title = '## Your parts and their standards' if owner else "## The memo's parts and their standards"
    return '\n\n'.join([
        (PROMPTS / prompt_file).read_text().strip(),
        '## The writing standard for every part\n' + sections['standard'],
        title + '\n' + '\n\n'.join(_part_heading(part) + '\n' + sections[part.key] for part in parts),
        (PROMPTS / 'rules.md').read_text().strip(),
    ])


def _disabled(*kept: str) -> tuple[str, ...]:
    return tuple(tool for tool in BUILTIN_TOOLS if tool not in kept)


def model_choice() -> ModelChoice:
    return ModelChoice('deepseek', os.environ.get('MODEL_ID', 'deepseek-flash'),
                       os.environ.get('THINKING_LEVEL', 'max'))


def mcp_connection(agent: str) -> MCPConnection:
    """The bot's own entry for the team's MCP server. Its ?agent= key tells the server who is calling,
    and the bot cannot change it: add_mcp_server is switched off for every bot."""
    key = next(key for key, name in AGENTS.items() if name == agent)
    endpoint = os.environ.get('MCP_ENDPOINT', 'http://host.docker.internal:8766/mcp')
    return MCPConnection(f'Investment research ({agent})', f'research-{key}', f'{endpoint}?agent={key}')


def team_profiles() -> list[BotProfile]:
    model = model_choice()
    memo_tools = ('get_memo_parts', 'save_memo_part', 'get_memo_check')
    return [
        BotProfile(
            LEAD, 'Leads the investment research team: sets the case scope, briefs the Fundamentals and Market '
                  'Analysts, writes the memo\'s summary, risks, scenarios, diligence question and takeaways, and is '
                  'the only bot that talks to the user.',
            _instructions('lead_analyst.md', LEAD), model, mcp_connection(LEAD),
            mcp_tools=('read_client_document', 'get_case_status', 'set_case_scope', 'list_sources',
                       'get_evidence_packets', *memo_tools, 'save_memo_version', 'get_latest_review',
                       'deliver_memo'),
            disabled_builtin_tools=_disabled('message_bot')),
        BotProfile(
            FUNDAMENTALS, 'Researches and writes the memo\'s Financials and Valuation and price parts from SEC '
                          'filings, prices and valuation data, and saves evidence packets for the Lead Analyst.',
            _instructions('fundamentals_analyst.md', FUNDAMENTALS), model, mcp_connection(FUNDAMENTALS),
            mcp_tools=('read_client_document', 'find_sec_company', 'get_sec_financials', 'list_sec_filings',
                       'read_sec_filing', 'get_price_history', 'get_valuation_snapshot', 'register_source',
                       'list_sources', *memo_tools, 'save_evidence_packet'),
            disabled_builtin_tools=_disabled('web_search', 'web_fetch')),
        BotProfile(
            MARKET, 'Researches and writes the memo\'s Business and Competition and market parts from filings '
                    'and the web: products, customers, competitors, market size, news and regulation. Saves '
                    'evidence packets for the Lead Analyst.',
            _instructions('market_analyst.md', MARKET), model, mcp_connection(MARKET),
            mcp_tools=('read_client_document', 'read_sec_filing', 'register_source', 'list_sources', *memo_tools,
                       'save_evidence_packet'),
            disabled_builtin_tools=_disabled('web_search', 'web_fetch')),
        BotProfile(
            REVIEWER, 'Reviews each memo version part by part like a skeptical investment committee partner, and '
                      'approves it or sends it back to the Lead Analyst with must-fix items for each part\'s owner '
                      'and any evidence the analysts should add.',
            _instructions('ic_reviewer.md'), model, mcp_connection(REVIEWER),
            mcp_tools=('get_memo_parts', 'get_memo_check', 'list_sources', 'get_evidence_packets',
                       'get_latest_review', 'save_review'),
            disabled_builtin_tools=_disabled()),
    ]
