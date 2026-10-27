"""Load src/.env into the environment without overriding values already set."""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / '.env'


def load_env(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if value.strip():
            os.environ.setdefault(key.strip(), value.strip())
