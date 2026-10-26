"""The three bots: role prompts, model, and the tools each role may use.

Tool limits are role design (each bot gets what its job needs), not policy enforcement:
the must-never rules in prompts/rules.md are instructions only in Phase 1.
"""
import os
from pathlib import Path

from .rakazo_client import BotProfile, MCPConnection, ModelChoice

PROMPTS = Path(__file__).resolve().parent / 'prompts'
LEAD, ANALYST, REVIEWER = 'Lead Analyst', 'Research Analyst', 'IC Reviewer'

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


def mcp_connection() -> MCPConnection:
    return MCPConnection('Investment research', 'investment-research',
                         os.environ.get('MCP_ENDPOINT', 'http://host.docker.internal:8766/mcp'))


def team_profiles() -> list[BotProfile]:
    model = model_choice()
    return [
        BotProfile(
            LEAD, 'Leads the investment research team: plans the research, writes the investment memo '
                  'and is the only bot that talks to the user.',
            _instructions('lead_analyst.md'), model,
            mcp_tools=('read_client_document', 'get_case_status', 'list_sources', 'get_evidence_packets',
                       'save_memo_draft', 'get_memo_draft', 'get_memo_check', 'get_latest_review',
                       'deliver_memo'),
            disabled_builtin_tools=_disabled('message_bot')),
        BotProfile(
            ANALYST, 'Gathers evidence for investment memos from SEC filings, price data and web search, '
                     'and saves evidence packets for the Lead Analyst.',
            _instructions('research_analyst.md'), model,
            mcp_tools=('read_client_document', 'find_sec_company', 'get_sec_financials', 'list_sec_filings',
                       'get_price_history', 'register_source', 'list_sources', 'save_evidence_packet'),
            disabled_builtin_tools=_disabled('web_search', 'web_fetch')),
        BotProfile(
            REVIEWER, 'Reviews each memo version like a skeptical investment committee partner, and '
                      'approves it or sends it back to the Lead Analyst with must-fix items.',
            _instructions('ic_reviewer.md'), model,
            mcp_tools=('get_memo_draft', 'list_sources', 'get_evidence_packets', 'get_memo_check',
                       'get_latest_review', 'save_review'),
            disabled_builtin_tools=_disabled()),
    ]
