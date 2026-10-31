"""Write policy_rules.md, the enforceable form of policy.md, from the rule table, so it cannot drift from the code. From
src/:

    .venv/bin/python -m policy.docs
"""
from pathlib import Path
import re

from . import rules

ROOT = Path(__file__).resolve().parents[2]


def _natural(rule_id: str) -> tuple[int, int]:
    return (0 if rule_id.startswith('N') else 1, int(rule_id[1:]))


def _tools(rule: rules.Rule) -> str:
    return 'every tool' if '*' in rule.tools else ', '.join(f'`{tool}`' for tool in rule.tools)


def render() -> str:
    table = ['| Rule | Policies | What it holds | Where | On a break |', '|---|---|---|---|---|']
    for rule in rules.RULES:
        table.append(f"| {rule.id} | {', '.join(rule.policies)} | {rule.title} | {_tools(rule)} | {rule.action} |")
    statuses = ['| ID | Status | How |', '|---|---|---|']
    for rule_id in sorted(rules.DISPOSITIONS, key=_natural):
        status, how = rules.DISPOSITIONS[rule_id]
        statuses.append(f'| {rule_id} | {status} | {how} |')
    return '\n'.join([
        '# Enforceable rules',
        '',
        'This is `policy.md` converted into rules the app enforces. It is generated from `src/policy/rules.py`: run '
        '`.venv/bin/python -m policy.docs` from `src/`.',
        '',
        "The course's policy-assurance framework has not been released, so these rules run in the app's own layer "
        '(`src/policy/`). It checks every tool call on the MCP server before the tool runs. A refused call does not '
        'happen: the agent gets an error naming the rule and its next legal step, and the decision goes to the run\'s '
        '`policy_log.jsonl` and into the trace. `team.run_scenario --policy observe` logs the same decisions without '
        'refusing anything.',
        '',
        '## The rules',
        '',
        *table,
        '',
        'A rule marked "refuse once" lets the second attempt through and records it, because the evidence or the section '
        'it asks for may be impossible to get, and a refusal with no way forward would stall the run.',
        '',
        'Besides refusing calls, rule N8 removes each line addressed to AI tools from `read_client_document` and '
        '`web_fetch` results before the model reads them, and N11 warns the IC Reviewer at `start_review`.',
        '',
        '## Every policy and must-never rule',
        '',
        *statuses,
        '',
        '## What this layer cannot stop',
        '',
        "- **Messages between bots and their replies** (P2, P21, P27). Rakazo delivers `message_bot` and returns a bot's "
        'reply inside its own process. An approval rule could pause `message_bot`, but its card omits the message, so '
        'the trace export reports these instead.',
        "- **The Lead's own text in Rakazo's thread.** The user reads what passes `tell_user`, on this app's dashboard, "
        "but Rakazo's own interface still shows the Lead's raw text in its thread.",
        '- **Judgement calls** (N10, N11, P26, P38, P39, P41). A check cannot tell whether a section should have asked '
        'the user for a record, so these stay with the IC Reviewer and the trace export.',
        '',
    ])


def main() -> None:
    path = ROOT / 'policy_rules.md'
    path.write_text(render())
    print(f'Wrote {path.name}: {len(rules.RULES)} rules, {len(rules.DISPOSITIONS)} policies and must-never rules.')


if __name__ == '__main__':
    main()
