"""Check that a trace has every element the course spec asks for.

Each agent that took part must show thoughts, tool calls with arguments and tool results;
the run must contain the user's request, inter-agent messages both ways and a final reply.

    .venv/bin/python -m team.check_trace traces/phase1/<scenario>.json [more traces...]
"""
import json
from pathlib import Path
import sys

from .profiles import LEAD


def problems(trace: dict) -> list[str]:
    events = trace['events']
    found = []
    agents = sorted({e['agent'] for e in events if e['type'] in ('thought', 'tool_call', 'assistant_text')})
    if len(agents) < 2:
        found.append(f'only {len(agents)} agent(s) took part; the spec needs at least two communicating agents')
    for agent in agents:
        mine = [e for e in events if e['agent'] == agent]
        for kind, label in (('thought', 'thoughts'), ('tool_call', 'tool calls'), ('tool_result', 'tool results')):
            if not any(e['type'] == kind for e in mine):
                found.append(f'{agent}: no {label}')
        if any(e['type'] == 'tool_call' and 'arguments' not in e for e in mine):
            found.append(f'{agent}: a tool call without recorded arguments')
    if not any(e['type'] == 'user_message' for e in events):
        found.append("no user request")
    if not any(e['type'] == 'peer_message_sent' for e in events):
        found.append('no inter-agent message sent')
    if not any(e['type'] == 'peer_message_received' for e in events):
        found.append('no inter-agent message received')
    if not any(e['type'] in ('assistant_text', 'reply') and e['agent'] == LEAD for e in events):
        found.append(f'no reply from the {LEAD}')
    return found


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    failed = False
    for path in map(Path, sys.argv[1:]):
        issues = problems(json.loads(path.read_text()))
        failed |= bool(issues)
        print(f"{path.name}: {'complete' if not issues else 'INCOMPLETE'}")
        for issue in issues:
            print(f'  - {issue}')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
