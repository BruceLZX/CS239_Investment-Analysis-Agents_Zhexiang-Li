"""Run one scenario end to end on Rakazo and capture the raw material for its trace.

From agent-team/, with the MCP server running (`.venv/bin/python -m tools.server`):

    .venv/bin/python -m team.run_scenario public-equity-memo
"""
import argparse
import json
import os
from pathlib import Path
import time

import yaml

from tools import case_file
from tools.env import load_env

from .capture import capture_run
from .profiles import LEAD, mcp_connection, team_profiles
from .rakazo_client import WAITING_STATUSES, Rakazo

SCENARIOS = Path(__file__).resolve().parents[1] / 'scenarios'


def load_scenario(name: str) -> dict:
    path = SCENARIOS / f'{name}.yaml'
    if not path.exists():
        names = ', '.join(sorted(p.stem for p in SCENARIOS.glob('*.yaml')))
        raise SystemExit(f'No scenario {name!r}. Available: {names}')
    return yaml.safe_load(path.read_text())


def handle_cards(app: Rakazo, name: str, bot_id: str, mode: str, warned: set) -> None:
    """Answer Rakazo approval cards when unattended ('deny'), or point the operator at them ('wait')."""
    for card in app.pending_cards(bot_id):
        if mode == 'deny' and 'deny' in card['actions']:
            app.answer_card(bot_id, card, 'deny')
            record = {'ts': case_file.now(), 'bot': name, 'card': card['text'], 'detail': card['detail'], 'answer': 'deny'}
            with (case_file.active_run_dir() / 'approval_cards.jsonl').open('a') as log:
                log.write(json.dumps(record) + '\n')
            print(f"! Denied for unattended run: {name}: {card['text']} ({card['detail']})", flush=True)
        elif card['message_id'] not in warned:
            warned.add(card['message_id'])
            print(f"! {name} is waiting on \"{card['text']}\": answer it in the Rakazo app.", flush=True)


def wait_for_finish(app: Rakazo, bot_ids: dict[str, str], timeout: float, quiet: float, cards: str) -> str:
    """Wait until the memo is delivered and every bot is idle, or the team goes quiet."""
    deadline = time.monotonic() + timeout
    idle_since, warned, last_busy = None, set(), None
    while time.monotonic() < deadline:
        in_flight = {name: app.runs_in_flight(bot_id) for name, bot_id in bot_ids.items()}
        for name, runs in in_flight.items():
            if any(run['status'] in WAITING_STATUSES for run in runs):
                handle_cards(app, name, bot_ids[name], cards, warned)
        busy = sorted(name for name, runs in in_flight.items() if runs)
        if busy != last_busy:
            print(f'[{time.strftime("%H:%M:%S")}] working: {", ".join(busy) or "nobody"}', flush=True)
            last_busy = busy
        if busy:
            idle_since = None
        else:
            idle_since = idle_since or time.monotonic()
            idle = time.monotonic() - idle_since
            if case_file.read_case()['deliveries'] and idle >= 15:
                return 'delivered'
            if idle >= quiet:
                return 'stalled'
        time.sleep(5)
    return 'timed out'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('scenario')
    parser.add_argument('--timeout', type=float, default=1800, help='seconds to wait for the whole run')
    parser.add_argument('--quiet', type=float, default=150, help='seconds of idleness that count as stalled')
    parser.add_argument('--approval-cards', choices=['deny', 'wait'], default='deny',
                        help="Rakazo approval cards (e.g. fetching a site the bot's search didn't return): "
                             'deny them for unattended runs (logged), or wait for someone to answer in the app')
    args = parser.parse_args()
    load_env()
    scenario = load_scenario(args.scenario)
    with Rakazo(os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')) as app:
        bot_ids = app.configure_team(team_profiles(), mcp_connection())
        for bot_id in bot_ids.values():
            app.wait_idle(bot_id)
            app.clear(bot_id)  # Each run replays earlier messages, so every scenario starts clean.
        run_id = case_file.start_run(scenario['name'], scenario.get('client_documents', []))
        sent = app.send(bot_ids[LEAD], scenario['request'].strip())
        print(f'Run {run_id}: sent the request to {LEAD} (Rakazo run {sent["runId"]}).', flush=True)
        outcome = wait_for_finish(app, bot_ids, args.timeout, args.quiet, args.approval_cards)
        run_dir = case_file.active_run_dir()
        captured = capture_run(app, bot_ids, run_dir)
    status = case_file.status_summary(case_file.read_case())
    (run_dir / 'outcome.json').write_text(json.dumps({'outcome': outcome, 'captured': captured, 'status': status}, indent=1))
    print(f'Outcome: {outcome}. Captured {captured["transcript_files"]} transcript files and '
          f'{sum(captured["messages"].values())} messages into {run_dir}.')
    print(json.dumps(status, indent=1))


if __name__ == '__main__':
    main()
