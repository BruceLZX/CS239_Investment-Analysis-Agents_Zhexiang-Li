"""Cut a recorded run back to the moment before its first version, for a scenario that starts from a saved case: every
section written and the red team done, so the team reaches its first delivery decision in minutes, not an hour.

    .venv/bin/python fixtures/build_seed.py <path to a run's case.json> fixtures/seeds/<name>.json
"""
import json
from pathlib import Path
import sys


def before_first_version(case: dict) -> dict:
    cut = case['memo_drafts'][0]['saved_at']
    keep = lambda when: bool(when) and when < cut  # noqa: E731
    # The records as they ended up: the plan and the thesis table were written before the version, and only touched
    # up after it. The QA log and rewrite plan are left out, so the Lead runs its own QA loop.
    workflow = {kind: record for kind, record in (case.get('workflow') or {}).items() if isinstance(record, dict)}
    return {
        'scope': case['scope'],
        'sources': [s for s in case['sources'] if keep(s.get('registered_at'))],
        'evidence': {key: kept for key, blocks in (case.get('evidence') or {}).items()
                     if (kept := [block for block in blocks if keep(block.get('saved_at'))])},
        'workflow': workflow,
        'user_data_requests': [r for r in case.get('user_data_requests') or [] if keep(r.get('requested_at'))],
        'notes': [note for note in case.get('notes') or [] if keep(note.get('at'))],
        'memo_parts': {key: kept for key, revisions in (case.get('memo_parts') or {}).items()
                       if (kept := [r for r in revisions if keep(r.get('saved_at'))])},
    }


def main() -> None:
    case = json.loads(Path(sys.argv[1]).read_text())
    seed = before_first_version(case)
    Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[2]).write_text(json.dumps(seed, indent=1, ensure_ascii=False))
    print(f"Wrote {sys.argv[2]}: {len(seed['memo_parts'])} sections, {len(seed['sources'])} sources, "
          f"{len(seed['workflow'])} workflow records.")


if __name__ == '__main__':
    main()
