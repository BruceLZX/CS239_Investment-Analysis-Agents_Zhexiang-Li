"""Run one scenario end to end on Rakazo and capture the raw material for its trace.

From src/, with the MCP server running (`.venv/bin/python -m tools.server`):

    .venv/bin/python -m team.run_scenario public-equity-memo
    .venv/bin/python -m team.run_scenario --request "Prepare an investment memo on Nvidia (NVDA)."
    .venv/bin/python -m team.run_scenario --follow-up "What would change the rating?"

A request of your own runs like a scenario with no attached documents. A follow-up goes to the
Lead Analyst in the latest run once it has finished, and the run is captured again afterwards.
"""
import argparse
from dataclasses import replace
from datetime import datetime
import json
import os
from pathlib import Path
import time

import yaml

from policy import engine as policy
from tools import case_file
from tools.env import load_env

from .capture import capture_run
from .profiles import LEAD, RETIRED, REVIEWER, team_profiles
from .rakazo_client import WAITING_STATUSES, Rakazo

SCENARIOS = Path(__file__).resolve().parents[1] / 'scenarios'
CUSTOM = 'custom'  # The scenario name of a request of the user's own.
# A model call can fail mid-stream. A failed analyst's reply still wakes the Lead, but a failed turn of the Lead leaves
# nobody to wake it once the team is idle, so the runner does, as a user would.
RESUME = 'Your last step stopped on a model error, and nothing is running now. Check the case status and carry on.'
MAX_RESUMES = 3


def custom_scenario(request: str) -> dict:
    """A request of the user's own: it runs like a scenario with no attached documents."""
    return {'name': CUSTOM, 'request': request, 'client_documents': []}


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


def _short(text: str | None, limit: int = 180) -> str:
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit].rstrip() + '…'


def narrate(app: Rakazo, bot_ids: dict[str, str], seen: set) -> None:
    """Print new conversation in time order: the request, the Lead's replies, every bot-to-bot message.
    Each delivery is printed once, from the receiving bot's thread."""
    lines = []
    for name, bot_id in bot_ids.items():
        for message in app.messages(bot_id):
            if message['id'] in seen:
                continue
            seen.add(message['id'])
            for block in message.get('blocks') or []:
                kind, role = block.get('kind'), message.get('role')
                if kind == 'bot_message_received':
                    line = f"{block.get('fromBotName')} → {name} ({block.get('intent') or 'message'}): {_short(block.get('text'))}"
                elif kind == 'text' and role == 'user':
                    line = f"user → {name}: {_short(block.get('text'))}"
                elif kind == 'text' and role == 'bot' and name == LEAD:
                    line = f"{name} → user: {_short(block.get('text'))}"
                elif kind == 'ask':
                    line = f"Rakazo approval card for {name}: {block.get('text')}"
                else:
                    continue
                lines.append((message['createdAt'], line))
    for created_at, line in sorted(lines):
        when = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone().strftime('%H:%M:%S')
        print(f'[{when}] {line}', flush=True)


def review_failed(case: dict) -> bool:
    """The final review round did not approve. The Lead must then deliver nothing (P9), so the run is over."""
    return case_file.final_review_failed(case)


def note_windows(app: Rakazo, bot_ids: dict[str, str], in_flight: dict[str, list], seen: dict[str, set],
                 resent: set[str]) -> None:
    """Tell the server when a budget window opens, which it cannot see from tool calls: a request an analyst or the Red
    Team receives, a new turn of the Lead or the IC Reviewer. A brief sent again before the analyst's first reply, as
    when a model error cuts its run off, is still a first brief (P17)."""
    changed = False
    for name, runs in in_flight.items():
        if not runs:
            continue
        ids = {run['id'] for run in runs} if name in (LEAD, REVIEWER) else set(app.received_requests(bot_ids[name]))
        if ids - seen.setdefault(name, set()):
            if seen[name] and name not in (LEAD, REVIEWER) and not app.has_reported(bot_ids[name]):
                resent.add(name)
            else:
                resent.discard(name)
            seen[name] |= ids
            changed = True
    if changed:
        windows = {name: len(ids) for name, ids in seen.items() if ids}
        policy.write_windows(case_file.active_run_dir(), {**windows, 'first_brief': sorted(resent)})


def wait_for_finish(app: Rakazo, bot_ids: dict[str, str], timeout: float, quiet: float, cards: str,
                    narrated: set | None = None) -> str:
    """Wait until the memo is delivered, or fails its final review, and every bot is idle; or the team goes quiet."""
    deadline = time.monotonic() + timeout
    idle_since, warned, last_busy, windows, resent, resumes = None, set(), None, {}, set(), 0
    while time.monotonic() < deadline:
        if narrated is not None:
            narrate(app, bot_ids, narrated)
        in_flight = {name: app.runs_in_flight(bot_id) for name, bot_id in bot_ids.items()}
        note_windows(app, bot_ids, in_flight, windows, resent)
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
            case = case_file.read_case()
            if case['deliveries'] and idle >= 15:
                return 'delivered'
            if review_failed(case) and idle >= 15:
                return 'failed review'
            if idle >= 15 and resumes < MAX_RESUMES and app.last_run_failed(bot_ids[LEAD]):
                resumes += 1
                print(f'[{time.strftime("%H:%M:%S")}] {LEAD} stopped on a model error; resuming it ({resumes} of '
                      f'{MAX_RESUMES}).', flush=True)
                app.send(bot_ids[LEAD], RESUME)
                idle_since, idle = None, 0
            if idle >= quiet:
                return 'stalled'
        # A brief's first tool call comes about two seconds after it arrives. Until its window opens, that call counts
        # against the brief before it, and is refused if that one had used up its budget.
        time.sleep(1)
    return 'timed out'


def finish(app: Rakazo, bot_ids: dict[str, str], outcome: dict) -> None:
    """Copy the run out of Rakazo, then write outcome.json, which marks the capture complete."""
    run_dir = case_file.active_run_dir()
    captured = capture_run(app, bot_ids, run_dir)
    status = case_file.status_summary(case_file.read_case())
    (run_dir / 'outcome.json').write_text(json.dumps({**outcome, 'captured': captured, 'status': status}, indent=1))
    print(f'Outcome: {outcome["outcome"]}. Captured {captured["transcript_files"]} transcript files and '
          f'{sum(captured["messages"].values())} messages into {run_dir}.')
    print(json.dumps(status, indent=1))


def run_case(app: Rakazo, scenario: dict, args) -> None:
    profiles = team_profiles()
    # A scenario may replace the Lead's instructions, to test what the rules do with a compromised agent. Adding a line
    # is not enough: in a live run, a Lead told to skip the review kept to the rules in the rest of its prompt.
    if scenario.get('lead_instructions'):
        profiles = [replace(p, instructions=scenario['lead_instructions'].strip()) if p.name == LEAD else p for p in profiles]
    bot_ids = app.configure_team(profiles, RETIRED)
    for bot_id in bot_ids.values():
        app.wait_idle(bot_id)
        app.clear(bot_id)  # Each run replays earlier messages, so every scenario starts clean.
    request = scenario['request'].strip()
    seed = json.loads((SCENARIOS.parent / scenario['seed']).read_text()) if scenario.get('seed') else None
    run_id = case_file.start_run(scenario['name'], scenario.get('client_documents', []), request, args.policy, seed)
    sent = app.send(bot_ids[LEAD], request)
    print(f'Run {run_id}: sent the request to {LEAD} (Rakazo run {sent["runId"]}).', flush=True)
    outcome = wait_for_finish(app, bot_ids, args.timeout, args.quiet, args.approval_cards,
                              set() if args.narrate else None)
    finish(app, bot_ids, {'outcome': outcome})


def follow_up(app: Rakazo, question: str, args) -> None:
    """Ask the Lead Analyst a follow-up question about the latest run once it has finished, then capture
    the run again so the question and the answer join its record."""
    run_dir = case_file.active_run_dir()
    outcome_file = run_dir / 'outcome.json'
    if not outcome_file.exists():
        raise SystemExit('The latest run has not finished yet; ask a follow-up once it has.')
    previous = json.loads(outcome_file.read_text())
    team = {profile.name for profile in team_profiles()}
    bot_ids = {name: bot['id'] for name, bot in app.bots().items() if name in team}
    seen = {m['id'] for bot_id in bot_ids.values() for m in app.messages(bot_id)} if args.narrate else None
    outcome_file.unlink()  # Until it is written again, the run counts as live and the dashboard follows it.
    try:
        sent = app.send(bot_ids[LEAD], question.strip())
        print(f'Run {run_dir.name}: sent a follow-up to {LEAD} (Rakazo run {sent["runId"]}).', flush=True)
        wait_for_finish(app, bot_ids, args.timeout, 15, args.approval_cards, seen)
    except BaseException:
        outcome_file.write_text(json.dumps(previous, indent=1))  # Leave the run as it was.
        raise
    finish(app, bot_ids, {'outcome': previous['outcome'], 'follow_ups': previous.get('follow_ups', 0) + 1})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('scenario', nargs='?', help='one of the scenarios in src/scenarios/')
    parser.add_argument('--request', help='run a request of your own instead of a scenario (no attached documents)')
    parser.add_argument('--follow-up', metavar='QUESTION',
                        help='ask the Lead Analyst a follow-up question about the latest run, once it has finished')
    parser.add_argument('--timeout', type=float, default=9000, help='seconds to wait for the whole run')
    parser.add_argument('--quiet', type=float, default=240, help='seconds of idleness that count as stalled')
    parser.add_argument('--approval-cards', choices=['deny', 'wait'], default='deny',
                        help="Rakazo approval cards (e.g. fetching a site the bot's search didn't return): "
                             'deny them for unattended runs (logged), or wait for someone to answer in the app')
    parser.add_argument('--policy', choices=['enforce', 'observe'], default='enforce',
                        help='enforce refuses what the rules forbid; observe only logs what they would have refused')
    parser.add_argument('--narrate', action='store_true',
                        help='print the conversation live: the request, the Lead\'s replies and messages between bots')
    args = parser.parse_args()
    if sum(bool(choice) for choice in (args.scenario, args.request, args.follow_up)) != 1:
        parser.error('give exactly one of: a scenario name, --request or --follow-up')
    load_env()
    scenario = None if args.follow_up else custom_scenario(args.request) if args.request else load_scenario(args.scenario)
    with Rakazo(os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')) as app:
        if args.follow_up:
            follow_up(app, args.follow_up, args)
        else:
            run_case(app, scenario, args)


if __name__ == '__main__':
    main()
