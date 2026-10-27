import json

import httpx

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
