"""The nine bots' instructions and tools: each fits Rakazo's limit and holds what its job needs."""
from team import profiles
from tools import sections, server
from tools.agents import ANALYSTS


def by_name() -> dict:
    return {profile.name: profile for profile in profiles.team_profiles()}


def test_every_bots_instructions_fit_rakazos_limit():
    for profile in profiles.team_profiles():
        assert len(profile.instructions) <= profiles.MAX_INSTRUCTIONS, (profile.name, len(profile.instructions))


def test_every_tool_a_bot_is_given_exists_on_the_server():
    names = set(server.server._tool_manager._tools)
    for profile in profiles.team_profiles():
        assert set(profile.mcp_tools) <= names, profile.name


def test_each_writer_gets_the_standards_for_exactly_its_own_sections():
    bots = by_name()
    for section in sections.ALL_SECTIONS:
        heading = f'(`{section.key}`'
        holders = [name for name, profile in bots.items() if heading in profile.instructions]
        assert section.owner in holders, section.key
        assert set(holders) <= {section.owner, profiles.REVIEWER}, (section.key, holders)


def test_only_the_lead_messages_other_bots_and_only_researchers_search_the_web():
    for name, profile in by_name().items():
        builtins = set(profiles.BUILTIN_TOOLS) - set(profile.disabled_builtin_tools)
        assert ('message_bot' in builtins) == (name == profiles.LEAD), name
        if name == profiles.REVIEWER:
            assert builtins == set()
        else:
            assert {'web_search', 'web_fetch'} <= builtins, name


def test_the_analysts_share_the_workflow_and_the_writers_tools():
    bots = by_name()
    for analyst in ANALYSTS:
        assert '## How you work' in bots[analyst].instructions
        assert set(profiles.WRITER_TOOLS) <= set(bots[analyst].mcp_tools)
    assert 'save_red_team_review' in bots[profiles.RED_TEAM].mcp_tools
    assert {'start_review', 'save_review_pass', 'finish_review'} <= set(bots[profiles.REVIEWER].mcp_tools)
    assert {'save_memo_version', 'deliver_memo', 'run_qa_loop'} <= set(bots[profiles.LEAD].mcp_tools)


def test_the_instructions_name_the_components_each_section_requires():
    bots = by_name()
    lead = bots[profiles.LEAD].instructions
    assert '- **verdict:**' in lead and '- **sensitivity:**' in lead and '- **kpi:**' not in lead
    assert '- **kpi:**' in bots[profiles.COMPANY].instructions
