"""Copy everything a trace is built from out of Rakazo, right after a run.

Rakazo prunes its per-run transcripts (30 days, 100 per bot), so team.run_scenario calls
capture_run at the end of every scenario.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

WORKER = os.environ.get('RAKAZO_WORKER_CONTAINER', 'cs239-agent-team-rakazo-worker-1')


def copy_transcripts(dest: Path) -> int:
    """Copy the worker's Pi session recordings; returns how many transcript files were copied."""
    target = dest / 'pi-sessions'
    if target.exists():
        shutil.rmtree(target)
    result = subprocess.run(['docker', 'cp', f'{WORKER}:/data/pi-sessions', str(target)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f'Could not copy transcripts from {WORKER}: {result.stderr.strip()}')
        return 0
    return sum(1 for _ in target.rglob('*.jsonl'))


def capture_run(app, bot_ids: dict[str, str], run_dir: Path) -> dict:
    raw = run_dir / 'rakazo'
    raw.mkdir(exist_ok=True)
    messages = {name: app.messages(bot_id) for name, bot_id in bot_ids.items()}
    (raw / 'messages.json').write_text(json.dumps({'bots': bot_ids, 'messages': messages}, indent=1))
    (raw / 'usage.json').write_text(json.dumps(app.usage(), indent=1))
    return {'transcript_files': copy_transcripts(raw),
            'messages': {name: len(items) for name, items in messages.items()}}
