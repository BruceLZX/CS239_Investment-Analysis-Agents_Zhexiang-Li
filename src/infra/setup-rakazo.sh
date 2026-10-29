#!/usr/bin/env bash
# Install, start, stop or inspect the pinned Rakazo stack the agent team runs on.
# Adapted from the CS239 tutorial's setup-rakazo.sh: same pinned-installer pattern, plus the
# settings this project needs written before the first start.
set -euo pipefail
SCRIPT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_ROOT/../.." && pwd)
readonly RAKAZO_REVISION=b445fe90522d5e5da1e47879f6e4fa9be504f530
readonly INSTALLER_SHA256=e0e8d27347304db73c0e4dc3188b627d027b55c9b00460f48d7c35b03bdc3484
# Generated credentials live outside the repository so they can never be committed.
RUNTIME_DIR="${RAKAZO_RUNTIME_DIR:-$(dirname "$REPO_ROOT")/rakazo-runtime}"
export COMPOSE_PROJECT_NAME=cs239-agent-team-rakazo
export RAKAZO_API_PORT=23100
# Rakazo's default web port 5173 is also Vite's dev-server default, so use the next one.
export RAKAZO_WEB_PORT="${RAKAZO_WEB_PORT:-5174}"
readonly RAKAZO_ORIGIN="http://127.0.0.1:$RAKAZO_WEB_PORT"
export RAKAZO_DOWNLOAD_BASE="https://raw.githubusercontent.com/elie222/rakazo/$RAKAZO_REVISION/infra/compose"

for task_command in docker curl openssl python3; do
  command -v "$task_command" >/dev/null || { echo "Install $task_command first (Docker Desktop includes Docker Compose)." >&2; exit 1; }
done
docker compose version >/dev/null
docker info >/dev/null 2>&1 || { echo 'Start Docker Desktop / Docker Engine first.' >&2; exit 1; }

compose() {
  (cd "$RUNTIME_DIR" && docker compose --env-file .env -f docker-compose.images.yml "$@")
}

case "${1:-start}" in
  stop)
    [[ -f "$RUNTIME_DIR/docker-compose.images.yml" ]] || { echo 'No Rakazo stack has been installed.'; exit 0; }
    compose down
    exit 0
    ;;
  status)
    [[ -f "$RUNTIME_DIR/docker-compose.images.yml" ]] || { echo 'No Rakazo stack has been installed.'; exit 0; }
    compose ps
    exit 0
    ;;
  start) ;;
  *) echo 'Usage: bash setup-rakazo.sh [start|stop|status]' >&2; exit 2 ;;
esac

if python3 -c 'import socket, sys; s=socket.socket(); result=s.connect_ex(("127.0.0.1", int(sys.argv[1]))); s.close(); raise SystemExit(0 if result == 0 else 1)' "$RAKAZO_WEB_PORT"; then
  if [[ ! -f "$RUNTIME_DIR/docker-compose.images.yml" || ! -f "$RUNTIME_DIR/.env" ]] ||
     ! compose ps --status running --services | grep -qx web; then
    echo "Port $RAKAZO_WEB_PORT is already in use by another app. Free it or set RAKAZO_WEB_PORT." >&2
    exit 1
  fi
fi

umask 077
mkdir -p "$RUNTIME_DIR"
cd "$RUNTIME_DIR"
# Verify the pinned upstream installer before running it.
curl -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 \
  "$RAKAZO_DOWNLOAD_BASE/install-images.sh" -o install-images.sh.download
python3 - "$INSTALLER_SHA256" <<'PY'
import hashlib, sys
from pathlib import Path
path = Path('install-images.sh.download')
if hashlib.sha256(path.read_bytes()).hexdigest() != sys.argv[1]:
    path.unlink()
    raise SystemExit('Upstream installer checksum mismatch; startup refused.')
path.replace('install-images.sh')
PY
bash install-images.sh --prepare-only --local

# Both agent processes (api and worker) must reach the MCP server on the host.
[[ $(grep -c 'host.docker.internal:host-gateway' docker-compose.images.yml) -ge 2 ]] ||
  { echo 'Compose file lacks host.docker.internal for api and worker; startup refused.' >&2; exit 1; }

set_env() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path
key, value = sys.argv[1], sys.argv[2]
path = Path('.env')
lines = path.read_text().splitlines()
kept = [line for line in lines if not line.startswith(f'{key}=')]
kept.append(f'{key}={value}')
path.write_text('\n'.join(kept) + '\n')
PY
}
set_env COMPOSE_PROJECT_NAME "$COMPOSE_PROJECT_NAME"
set_env RAKAZO_API_PORT "$RAKAZO_API_PORT"
set_env RAKAZO_WEB_PORT "$RAKAZO_WEB_PORT"
# Sign-in checks the browser origin, so every origin setting must name the chosen web port.
for origin_key in BETTER_AUTH_URL WEB_ORIGIN API_URL; do
  set_env "$origin_key" "$RAKAZO_ORIGIN"
done
# Run the exact build whose source this project was designed against.
set_env RAKAZO_IMAGE_TAG "sha-$RAKAZO_REVISION"
set_env RAKAZO_COMPUTER_IMAGE_TAG "sha-$RAKAZO_REVISION"
# Per-run transcripts with thinking, tool calls and results: the source of the traces.
set_env PI_SESSION_RECORDING true
# Lets Rakazo reach the MCP server at http://host.docker.internal:8766.
set_env MCP_ALLOW_PRIVATE_ENDPOINT true
# Bot-to-bot messages one request may chain (Rakazo's default is 6). Rakazo counts hops only on messages a bot
# sends, not on the replies it returns, so the Lead's sends land on odd hops. The team's longest path ends with the
# Lead's seventh send at hop 13: briefs, the red-team request, the review request, revision briefs, the re-review
# request, second revision briefs and the final review request. Four more leave room to resend a brief whose run
# failed (P2), as the first Apple run of the four-bot team needed, and a follow-up question.
set_env BOT_MESSAGE_MAX_HOPS 17
# A model stream that breaks off is retried (Rakazo's default is once); a dropped connection ended a run.
set_env MODEL_STREAM_MAX_RETRIES 3

bash install-images.sh --local
