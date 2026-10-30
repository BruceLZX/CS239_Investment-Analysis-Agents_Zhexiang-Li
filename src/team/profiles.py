"""The nine bots: role prompts, model, and the tools each role may use.

Each bot's instructions are its role prompt, the analysts' shared workflow (for the six analysts and the Red Team),
the writing standard, the components its sections use, the standards for the sections it writes (from
prompts/sections.md, with the floors, components and tables from tools/sections.py) and the must-never rules. Tool
limits are role design (each bot gets what its job needs), not policy enforcement: the rules in prompts/rules.md are
instructions only, for the Phase 2 framework to enforce.
"""
import os
from pathlib import Path

from tools import report, sections
from tools.agents import AGENTS
from tools.qa import check_depth

from .rakazo_client import BotProfile, MCPConnection, ModelChoice

PROMPTS = Path(__file__).resolve().parent / 'prompts'
LEAD, REVIEWER, RED_TEAM = AGENTS['lead'], AGENTS['reviewer'], AGENTS['red_team']
COMPANY, PRODUCT, MARKET = AGENTS['company'], AGENTS['product'], AGENTS['market']
FUNDAMENTALS, VALUATION, REGULATORY = AGENTS['fundamentals'], AGENTS['valuation'], AGENTS['regulatory']
# Bots from earlier versions of the team. Setting up the team archives them, so no bot lists them as teammates.
RETIRED = ('Research Analyst',)
# Rakazo's limit on a bot's instructions (packages/contracts on the pinned build).
MAX_INSTRUCTIONS = 20_000

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

# The columns each component takes, for the bots' instructions (the renderer reads any columns in this order).
COMPONENT_GUIDE = {
    'verdict': 'one row: | Rating | Action | Composite score | Confidence | Horizon | Source |',
    'briefing': 'at least 5 rows: | Card | Text | Source |',
    'kpi': '4-8 rows: | Metric | Value | Benchmark | Signal | Source |, Signal good, warn or critical',
    'efficiency': '| Measure | Value | Source |',
    'one-question': 'the question, a blank line, then why its answer decides the case',
    'takeaways': 'three numbered decision statements, each with a figure and [S#]',
    'scenarios': '| Scenario | Probability | Drivers | Outcome | Signposts | Source | with Bull, Base and Bear rows',
    'sensitivity': '| Rank | Assumption | Base | What would disprove it | Impact on value | Impact level | Early warning '
                   '| Source |, Impact level high, medium or low',
    'risk-matrix': '| Risk | Probability | Impact | Level | Timing | Signpost | Mitigation | Source |, Level critical, '
                   'high, medium or low',
    'timeline': '8-15 rows: | Date | Event | Significance | Source |',
    'info': '"::: info warning" (or highlight, danger), then a short paragraph with its [S#]',
    'evidence': 'a bold claim line, a blank line, then the evidence with its [S#]',
    'quad': '| Quadrant | Points | Source | with Strengths, Weaknesses, Opportunities and Threats rows, points '
            'separated by ";"',
    'analogs': '| Analog | Kind | Period | Lesson | Source |, Kind best or cautionary',
}


def _sections_md() -> dict[str, str]:
    """prompts/sections.md by "##" heading: the standard, the components syntax and each section's standard."""
    parts: dict[str, list[str]] = {}
    key = None
    for line in (PROMPTS / 'sections.md').read_text().splitlines():
        if line.startswith('## '):
            key = line[3:].strip()
            parts[key] = []
        elif key:
            parts[key].append(line)
    return {key: '\n'.join(lines).strip() for key, lines in parts.items()}


def _section_heading(section: sections.Section) -> str:
    """A section's title, with what its check holds it to (tools/sections.py, tools/qa/check_depth.py)."""
    place = f'section {section.number}' if section.number else 'the executive summary'
    floors = ('at least 900 characters' if section.number is None else
              f'{check_depth.MIN_CHARS:,}-{sections.MAX_SECTION_CHARS:,} characters, {check_depth.MIN_PARAGRAPHS} '
              f'paragraphs, {check_depth.MIN_NUMBERS} figures, {check_depth.MIN_SOURCE_IDS} source IDs')
    components = ', '.join(f'"{kind}"' for kind in section.components) or 'none required'
    tables = '; tables: ' + ', '.join(t.name + (' (private)' if t.listed is False else '') for t in section.tables) \
        if section.tables else ''
    reading = '; read first: ' + '; '.join(f'{name} "{heading}"' if heading else name
                                            for name, heading in section.playbooks)
    return (f'### {section.title} (`{section.key}`, {place}): {floors}; components: {components}{tables}{reading}')


def _components(keys: list[str]) -> str:
    standard = _sections_md()['components']
    kinds = list(dict.fromkeys([kind for key in keys for kind in sections.BY_KEY[key].components] + ['info', 'evidence']))
    lines = [f'- **{kind}:** {COMPONENT_GUIDE[kind]}' for kind in kinds if kind in report.COMPONENTS]
    return '## Components\n' + standard + '\n\n' + '\n'.join(lines)


def _instructions(prompt_file: str, owner: str, workflow: bool = False) -> str:
    """The role prompt, the analysts' workflow, the writing standard, the components, the owner's sections and the
    rules."""
    standards = _sections_md()
    keys = list(sections.OWNED.get(owner, ()))
    blocks = [(PROMPTS / prompt_file).read_text().strip()]
    if workflow:
        blocks.append((PROMPTS / 'analyst_workflow.md').read_text().strip())
    blocks += ['## The writing standard for every section\n' + standards['standard'], _components(keys),
               '## Your sections and their standards\n' + '\n\n'.join(
                   _section_heading(sections.BY_KEY[key]) + '\n' + standards[key] for key in keys),
               (PROMPTS / 'rules.md').read_text().strip()]
    return '\n\n'.join(blocks)


def _reviewer_instructions() -> str:
    """The IC Reviewer reviews every section, so it gets each one's requirements in a line; the full standards are in
    the playbooks it reads."""
    standards = _sections_md()
    lines = [f'- {_section_heading(section)[4:]}; owner: {section.owner}' for section in sections.ALL_SECTIONS]
    return '\n\n'.join([(PROMPTS / 'ic_reviewer.md').read_text().strip(),
                        '## The writing standard for every section\n' + standards['standard'],
                        "## The report's sections\n" + '\n'.join(lines),
                        (PROMPTS / 'rules.md').read_text().strip()])


def _disabled(*kept: str) -> tuple[str, ...]:
    return tuple(tool for tool in BUILTIN_TOOLS if tool not in kept)


# Rakazo's thinking levels, lowest first (ThinkingLevelSchema on the pinned build).
THINKING_LEVELS = ('off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')


def model_choice(cap: str | None = None) -> ModelChoice:
    """The bots' model and thinking level (MODEL_ID, THINKING_LEVEL), with the thinking level at most cap."""
    level = os.environ.get('THINKING_LEVEL', 'max')
    if cap in THINKING_LEVELS and level in THINKING_LEVELS and THINKING_LEVELS.index(cap) < THINKING_LEVELS.index(level):
        level = cap
    return ModelChoice('deepseek', os.environ.get('MODEL_ID', 'deepseek-flash'), level)


def mcp_connection(agent: str) -> MCPConnection:
    """The bot's own entry for the team's MCP server. Its ?agent= key tells the server who is calling,
    and the bot cannot change it: add_mcp_server is switched off for every bot."""
    key = next(key for key, name in AGENTS.items() if name == agent)
    endpoint = os.environ.get('MCP_ENDPOINT', 'http://host.docker.internal:8766/mcp')
    return MCPConnection(f'Investment research ({agent})', f'research-{key}', f'{endpoint}?agent={key}')


# What every section writer needs: the playbooks, the register, its evidence, its sections and their checks.
WRITER_TOOLS = ('read_client_document', 'read_playbook', 'register_source', 'list_sources', 'save_evidence_block',
                'get_evidence_matrix', 'get_gate', 'get_memo_parts', 'save_memo_part', 'get_memo_check',
                'request_user_data', 'get_workflow_doc')
SEC_READING = ('find_sec_company', 'list_sec_filings', 'read_sec_filing')
# A bot with more than 20 MCP tools gets them from Rakazo only through a search, load and execute catalog, which
# hides each real call from the trace behind connectors_execute_tool and costs extra calls: DIRECT_TOOL_LIMIT in
# packages/adapters/src/lazy-tool-catalog.ts and discoverTools in mcp-connector.ts at the pinned build b445fe9. The
# Lead went through it with 24 tools; every bot now stays within the limit.
DIRECT_TOOL_LIMIT = 20
ANALYSTS = {
    COMPANY: ('Researches and writes the report\'s company overview (legal entities, timeline, cap table) and team '
              'sections from filings, registries and public records.', 'company_analyst.md',
              SEC_READING + ('get_insider_activity',)),
    PRODUCT: ('Researches and writes the report\'s technology and product and development strategy sections from papers, '
              'patents, regulators\' databases and product evidence.', 'product_analyst.md',
              SEC_READING + ('search_public_records', 'search_literature')),
    MARKET: ('Researches and writes the report\'s market and industry and competitive landscape sections, product by '
             'product and region by region.', 'market_analyst.md',
             SEC_READING + ('get_sec_financials', 'search_public_records')),
    FUNDAMENTALS: ('Researches and writes the report\'s business model and financial analysis sections from SEC '
                   'filings, their notes and unit economics.', 'fundamentals_analyst.md',
                   SEC_READING + ('get_sec_financials', 'get_price_history')),
    VALUATION: ('Researches and writes the report\'s funding history and valuation and exit strategy sections from '
                'prices, peer multiples, rounds and precedent exits.', 'valuation_analyst.md',
                ('list_sec_filings', 'read_sec_filing', 'get_sec_financials', 'get_price_history',
                 'get_valuation_snapshot', 'get_trading_snapshot', 'get_market_regime', 'get_insider_activity')),
    REGULATORY: ('Researches regulators\' and courts\' records and policy for the whole report, writes its ESG section '
                 'and files user data requests for records behind a login.', 'regulatory_analyst.md',
                 SEC_READING + ('search_public_records',)),
}


def team_profiles() -> list[BotProfile]:
    model = model_choice()
    # At max, the IC Reviewer's reasoning over a whole memo used up Rakazo's 32,768-token output limit before it wrote
    # a review, three times in one run, so its thinking is capped (REVIEWER_THINKING_LEVEL, default high).
    reviewer_model = model_choice(os.environ.get('REVIEWER_THINKING_LEVEL', 'high'))
    profiles = [BotProfile(
        LEAD, 'Leads the investment research team: sets the scope and research plan, briefs the six analysts and the '
              'Red Team, writes the thesis, scoring and executive summary, runs QA, and is the only bot that talks to '
              'the user.',
        _instructions('lead_analyst.md', LEAD), model, mcp_connection(LEAD),
        mcp_tools=('get_case_status', 'set_case_scope', 'read_client_document', 'read_playbook', 'register_source',
                   'list_sources', 'save_research_plan', 'save_profile_requirements', 'save_thesis_table',
                   'save_scenario_analysis', 'save_evidence_block', 'get_evidence_matrix', 'get_workflow_doc',
                   'get_memo_parts', 'save_memo_part', 'run_qa_loop', 'save_memo_version', 'get_latest_review',
                   'deliver_memo', 'get_market_regime'),
        disabled_builtin_tools=_disabled('message_bot', 'web_search', 'web_fetch'))]
    for name, (description, prompt_file, data_tools) in ANALYSTS.items():
        profiles.append(BotProfile(
            name, description, _instructions(prompt_file, name, workflow=True), model, mcp_connection(name),
            mcp_tools=WRITER_TOOLS + data_tools, disabled_builtin_tools=_disabled('web_search', 'web_fetch')))
    profiles.append(BotProfile(
        RED_TEAM, 'Attacks the thesis before review: researches the case against it, writes the report\'s risk '
                  'assessment and the red-team review.',
        _instructions('red_team_analyst.md', RED_TEAM), model, mcp_connection(RED_TEAM),
        mcp_tools=WRITER_TOOLS + ('save_red_team_review', 'list_sec_filings', 'read_sec_filing'),
        disabled_builtin_tools=_disabled('web_search', 'web_fetch')))
    profiles.append(BotProfile(
        REVIEWER, 'Reviews each report version like a skeptical investment committee partner, in five '
                  'passes, and approves it or returns Critical and Important items to each section\'s owner.',
        _reviewer_instructions(), reviewer_model, mcp_connection(REVIEWER),
        mcp_tools=('read_playbook', 'get_memo_parts', 'get_memo_check', 'list_sources', 'get_evidence_matrix',
                   'get_workflow_doc', 'get_latest_review', 'start_review', 'save_review_pass', 'finish_review'),
        disabled_builtin_tools=_disabled()))
    return profiles
