"""The four bots: role prompts, model, and the tools each role may use.

Tool limits are role design (each bot gets what its job needs), not policy enforcement:
the must-never rules in prompts/rules.md are instructions only in Phase 1.
"""
import os
from pathlib import Path

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


def _instructions(prompt_file: str) -> str:
    return (PROMPTS / prompt_file).read_text().strip() + '\n\n' + (PROMPTS / 'rules.md').read_text().strip()


def _disabled(*kept: str) -> tuple[str, ...]:
    return tuple(tool for tool in BUILTIN_TOOLS if tool not in kept)


def model_choice() -> ModelChoice:
    return ModelChoice('deepseek', os.environ.get('MODEL_ID', 'deepseek-v4-pro'),
                       os.environ.get('THINKING_LEVEL', 'high'))


def mcp_connection(agent: str) -> MCPConnection:
    """The bot's own entry for the team's MCP server. Its ?agent= key tells the server who is calling,
    and the bot cannot change it: add_mcp_server is switched off for every bot."""
    key = next(key for key, name in AGENTS.items() if name == agent)
    endpoint = os.environ.get('MCP_ENDPOINT', 'http://host.docker.internal:8766/mcp')
    return MCPConnection(f'Investment research ({agent})', f'research-{key}', f'{endpoint}?agent={key}')


def team_profiles() -> list[BotProfile]:
    model = model_choice()
    return [
        BotProfile(
            LEAD, 'Leads the investment research team: briefs the Fundamentals and Market Analysts, writes the '
                  'investment memo and is the only bot that talks to the user.',
            _instructions('lead_analyst.md'), model, mcp_connection(LEAD),
            mcp_tools=('read_client_document', 'get_case_status', 'list_sources', 'get_evidence_packets',
                       'save_memo_draft', 'get_memo_draft', 'get_memo_check', 'get_latest_review',
                       'deliver_memo'),
            disabled_builtin_tools=_disabled('message_bot')),
        BotProfile(
            FUNDAMENTALS, 'Researches the numbers for investment memos: financial statements from SEC filings, '
                          'price and valuation, funding and round terms. Saves evidence packets for the Lead Analyst.',
            _instructions('fundamentals_analyst.md'), model, mcp_connection(FUNDAMENTALS),
            mcp_tools=('read_client_document', 'find_sec_company', 'get_sec_financials', 'list_sec_filings',
                       'get_price_history', 'register_source', 'list_sources', 'save_evidence_packet'),
            disabled_builtin_tools=_disabled('web_search', 'web_fetch')),
        BotProfile(
            MARKET, 'Researches the business and its market for investment memos: products and customers, '
                    'competitors, market size, news and regulation. Saves evidence packets for the Lead Analyst.',
            _instructions('market_analyst.md'), model, mcp_connection(MARKET),
            mcp_tools=('read_client_document', 'register_source', 'list_sources', 'save_evidence_packet'),
            disabled_builtin_tools=_disabled('web_search', 'web_fetch')),
        BotProfile(
            REVIEWER, 'Reviews each memo version like a skeptical investment committee partner, and approves it '
                      'or sends it back to the Lead Analyst with must-fix items and any evidence the analysts '
                      'should add.',
            _instructions('ic_reviewer.md'), model, mcp_connection(REVIEWER),
            mcp_tools=('get_memo_draft', 'list_sources', 'get_evidence_packets', 'get_memo_check',
                       'get_latest_review', 'save_review'),
            disabled_builtin_tools=_disabled()),
    ]
