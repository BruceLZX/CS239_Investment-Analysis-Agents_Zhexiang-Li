import json

import httpx

from team.profiles import RETIRED, team_profiles
from team.rakazo_client import Rakazo


def test_signing_in_again_replaces_the_saved_session(tmp_path):
    # Found when refreshing a live login: the saved cookie (no domain) collided with the new one.
    session = tmp_path / '.session.json'
    session.write_text(json.dumps({'better-auth.session_token': 'old'}))
    app = Rakazo('http://127.0.0.1:5174', session_file=session)
    sign_in = lambda request: httpx.Response(200, json={}, headers={
        'set-cookie': 'better-auth.session_token=new; Path=/; HttpOnly'})
    app.http = httpx.Client(base_url=app.url, transport=httpx.MockTransport(sign_in), cookies=app.http.cookies)
    app.login('owner@cs239-agent-team.test', 'test-password')
    assert json.loads(session.read_text()) == {'better-auth.session_token': 'new'}


def test_setting_up_the_team_archives_retired_bots_and_gives_each_bot_its_own_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv('MCP_ENDPOINT', raising=False)
    calls = []

    def rpc(route, data=None):
        calls.append((route, data))
        if route == 'bots/list':
            return [{'id': 'bot-old', 'name': 'Research Analyst'}, {'id': 'bot-lead', 'name': 'Lead Analyst'}]
        if route == 'mcp/servers/create':
            return {'id': 'server-' + data['slug'], **data}
        if route == 'bots/create':
            return {'id': 'bot-' + data['name'].split()[0].lower()}
        return {'activeRuns': []} if route == 'threads/get' else []

    app = Rakazo('http://127.0.0.1:5174', session_file=tmp_path / '.session.json')
    app.rpc = rpc
    ids = app.configure_team(team_profiles(), RETIRED)
    assert ('bots/archive', {'botId': 'bot-old'}) in calls
    assert list(ids) == ['Lead Analyst', 'Company Analyst', 'Product Analyst', 'Market Analyst', 'Fundamentals Analyst',
                         'Valuation Analyst', 'Regulatory Analyst', 'Red Team Analyst', 'IC Reviewer']
    assert [data['endpoint'] for route, data in calls if route == 'mcp/servers/create'] == [
        f'http://host.docker.internal:8766/mcp?agent={key}' for key in (
            'lead', 'company', 'product', 'market', 'fundamentals', 'valuation', 'regulatory', 'red_team', 'reviewer')]
    assigned = {data['botId']: data['assignments'][0] for route, data in calls if route == 'mcp/assignments/replace'}
    assert assigned['bot-market']['serverId'] == 'server-research-market'
    assert 'get_sec_financials' not in assigned['bot-company']['allowedTools']
    assert 'save_red_team_review' in assigned['bot-red']['allowedTools']


def test_the_reviewers_thinking_is_capped(monkeypatch):
    # At max, the reviewer's reasoning over a whole memo used up Rakazo's 32,768-token output limit three times.
    thinking = lambda: {profile.name: profile.model.thinking_level for profile in team_profiles()}
    monkeypatch.setenv('THINKING_LEVEL', 'max')
    monkeypatch.delenv('REVIEWER_THINKING_LEVEL', raising=False)
    assert {name: level for name, level in thinking().items() if level != 'max'} == {'IC Reviewer': 'high'}
    monkeypatch.setenv('THINKING_LEVEL', 'low')
    assert thinking()['IC Reviewer'] == 'low'  # a cap, never a raise
    monkeypatch.setenv('THINKING_LEVEL', 'max')
    monkeypatch.setenv('REVIEWER_THINKING_LEVEL', 'max')
    assert thinking()['IC Reviewer'] == 'max'
