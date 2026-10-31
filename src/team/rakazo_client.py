"""Small client for the pinned Rakazo build's authenticated HTTP API (see infra/setup-rakazo.sh).

Adapted from the CS239 tutorial's examples/movie_night/rakazo.py; not an official Rakazo SDK.
`python -m team.login` saves the session cookie to runs/.session.json, so later scripts
never handle the password.
"""
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import time

import httpx

# The MCP SDK turns on INFO logging, which would print every polling request.
logging.getLogger('httpx').setLevel(logging.WARNING)

SESSION_FILE = Path(__file__).resolve().parents[1] / 'runs' / '.session.json'
ACTIVE_STATUSES = {'queued', 'leased', 'running'}
WAITING_STATUSES = {'waiting_input', 'waiting_takeover'}


@dataclass(frozen=True)
class ModelChoice:
    provider: str
    model_id: str
    thinking_level: str | None = None


@dataclass(frozen=True)
class MCPConnection:
    name: str
    slug: str
    endpoint: str


@dataclass(frozen=True)
class BotProfile:
    name: str
    description: str  # Short: Rakazo shows it to every other bot in its teammate directory.
    instructions: str
    model: ModelChoice
    mcp: MCPConnection | None = None  # The bot's own entry for the MCP server, carrying its identity.
    mcp_tools: tuple[str, ...] = ()
    disabled_builtin_tools: tuple[str, ...] = ()


class RakazoError(RuntimeError):
    pass


class Rakazo:
    def __init__(self, url: str, session_file: Path = SESSION_FILE):
        self.url = url.rstrip('/')
        self.session_file = session_file
        # Rakazo checks the Origin header against its configured web origin.
        self.http = httpx.Client(base_url=self.url, timeout=60, headers={'Origin': self.url})
        if session_file.exists():
            self.http.cookies.update(json.loads(session_file.read_text()))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.http.close()

    def sign_up(self, name: str, email: str, password: str) -> None:
        response = self.http.post('/api/auth/sign-up/email', json={'name': name, 'email': email, 'password': password})
        if not response.is_success:
            raise RakazoError(f'Sign-up failed (HTTP {response.status_code}). Check that sign-ups are enabled.')

    def login(self, email: str, password: str) -> None:
        # A saved cookie has no domain; signing in again would add a second one with the same name.
        self.http.cookies.clear()
        response = self.http.post('/api/auth/sign-in/email', json={'email': email, 'password': password})
        if not response.is_success:
            raise RakazoError(f'Login failed (HTTP {response.status_code}). Check the account and RAKAZO_URL.')
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(json.dumps({cookie.name: cookie.value for cookie in self.http.cookies.jar}))
        self.session_file.chmod(0o600)

    def rpc(self, route: str, data: dict | None = None):
        response = self.http.post('/rpc/' + route, json={'json': data or {}})
        if response.status_code == 401:
            raise RakazoError('Not signed in to Rakazo. Run: .venv/bin/python -m team.login')
        if not response.is_success:
            # Show only the error message: full bodies from some routes can echo credentials.
            try:
                message = str(response.json().get('json', {}).get('message', ''))[:300]
            except ValueError:
                message = ''
            raise RakazoError(f'{route} failed (HTTP {response.status_code}). {message}'.strip())
        body = response.json()
        if 'json' not in body:
            raise RakazoError(f'{route} returned an unexpected response')
        return body['json']

    def bots(self) -> dict[str, dict]:
        return {bot['name']: bot for bot in self.rpc('bots/list')}

    def ensure_mcp_server(self, mcp: MCPConnection) -> dict:
        servers = {server['slug']: server for server in self.rpc('mcp/servers/list')}
        server = servers.get(mcp.slug)
        if server is None:
            return self.rpc('mcp/servers/create', {'name': mcp.name, 'slug': mcp.slug,
                                                   'endpoint': mcp.endpoint, 'transport': 'streamable_http'})
        if server.get('endpoint') != mcp.endpoint:
            raise RakazoError(f'MCP server {mcp.slug!r} points to {server.get("endpoint")}; '
                              'change it in Rakazo or use another slug.')
        return server

    def configure_team(self, profiles: list[BotProfile], retired: tuple[str, ...] = ()) -> dict[str, str]:
        """Archive retired bots, create missing ones and bring every bot's prompt, model and tools up to date."""
        existing = self.bots()
        for name in retired:
            if name in existing:
                self.rpc('bots/archive', {'botId': existing.pop(name)['id']})
        ids = {}
        for profile in profiles:
            bot = existing.get(profile.name)
            if bot is None:
                bot = self.rpc('bots/create', {
                    'name': profile.name, 'description': profile.description,
                    'instructions': profile.instructions, 'notifyOnFinish': False,
                    'spawnKey': 'cs239-' + profile.name.lower().replace(' ', '-')})
                self.wait_idle(bot['id'])  # A new bot first posts a short introduction.
            self.rpc('bots/update', {
                'botId': bot['id'], 'description': profile.description, 'instructions': profile.instructions,
                'modelProvider': profile.model.provider, 'modelId': profile.model.model_id,
                'thinkingLevel': profile.model.thinking_level, 'notifyOnFinish': False,
                'disabledBuiltinTools': list(profile.disabled_builtin_tools)})
            assignments = [{'serverId': self.ensure_mcp_server(profile.mcp)['id'], 'allowAllTools': False,
                            'allowedTools': list(profile.mcp_tools)}] if profile.mcp and profile.mcp_tools else []
            self.rpc('mcp/assignments/replace', {'botId': bot['id'], 'assignments': assignments})
            ids[profile.name] = bot['id']
        return ids

    def runs_in_flight(self, bot_id: str) -> list[dict]:
        snapshot = self.rpc('threads/get', {'botId': bot_id})
        runs = snapshot.get('activeRuns') or ([snapshot['run']] if snapshot.get('run') else [])
        return [run for run in runs if run['status'] in ACTIVE_STATUSES | WAITING_STATUSES]

    def wait_idle(self, bot_id: str, timeout: float = 600, poll: float = 3) -> None:
        deadline = time.monotonic() + timeout
        while runs := self.runs_in_flight(bot_id):
            waiting = [run for run in runs if run['status'] in WAITING_STATUSES]
            if waiting:
                raise RakazoError(f"Run {waiting[0]['id']} is waiting for input (an approval card?). "
                                  'Answer it in the Rakazo app, then rerun.')
            if time.monotonic() > deadline:
                raise RakazoError(f'Timed out after {timeout:.0f}s waiting for bot {bot_id} to finish.')
            time.sleep(poll)

    def pending_cards(self, bot_id: str) -> list[dict]:
        """Approval cards a bot's waiting run is blocked on, e.g. Rakazo's check before fetching a new site."""
        snapshot = self.rpc('threads/get', {'botId': bot_id})
        waiting = {run['id'] for run in snapshot.get('activeRuns') or [] if run['status'] in WAITING_STATUSES}
        cards = []
        for message in snapshot['messages']:
            for block in message.get('blocks') or []:
                if block.get('kind') == 'ask' and block.get('status') == 'pending' and message.get('runId') in waiting:
                    cards.append({'run_id': message['runId'], 'message_id': message['id'], 'text': block.get('text'),
                                  'detail': block.get('detail'), 'actions': [a['id'] for a in block.get('actions') or []]})
        return cards

    def received_requests(self, bot_id: str) -> list[str]:
        """The IDs of the recent requests from other bots in a bot's thread."""
        snapshot = self.rpc('threads/get', {'botId': bot_id})
        return [message['id'] for message in snapshot['messages'] for block in message.get('blocks') or []
                if block.get('kind') == 'bot_message_received' and (block.get('intent') or 'request') == 'request']

    def answer_card(self, bot_id: str, card: dict, answer: str) -> None:
        self.rpc('threads/answer', {'botId': bot_id, 'runId': card['run_id'], 'messageId': card['message_id'],
                                    'answer': answer})

    def send(self, bot_id: str, text: str) -> dict:
        # A busy bot queues the message and the response names the busy run instead.
        self.wait_idle(bot_id)
        return self.rpc('threads/send', {'botId': bot_id, 'text': text})

    def messages(self, bot_id: str, max_pages: int = 200) -> list[dict]:
        """Every message in a bot's thread, oldest first, including peer runs and receipts. Paging stops at a
        cursor seen before or a page with nothing new, so a cursor that comes round again cannot hold up the
        runner, which also answers approval cards between reads."""
        messages, before, cursors, ids = [], None, set(), set()
        for _ in range(max_pages):
            request = {'botId': bot_id, 'includePeerRuns': True, 'includePeerReceipts': True}
            if before is not None:
                request['before'] = before
            page = self.rpc('threads/messages', request)
            new = [message for message in page['messages'] if message['id'] not in ids]
            ids.update(message['id'] for message in new)
            messages = new + messages
            before = page.get('olderCursor')
            if before is None or not new or before in cursors:
                break
            cursors.add(before)
        return messages

    def clear(self, bot_id: str) -> None:
        self.rpc('threads/clear', {'botId': bot_id})

    def usage(self) -> list[dict]:
        return self.rpc('usage/list')
