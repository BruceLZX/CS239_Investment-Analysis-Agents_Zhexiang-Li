import argparse
import json

import pytest

from team import run_scenario
from team.run_scenario import narrate
from tools import case_file


class FakeRakazo:
    def __init__(self, threads):
        self.threads = threads

    def messages(self, bot_id):
        return self.threads[bot_id]


def message(id_, role, created_at, block):
    return {'id': id_, 'role': role, 'createdAt': created_at, 'blocks': [block]}


THREADS = {
    'lead': [
        message('m1', 'user', '2026-10-27T02:05:01Z', {'kind': 'text', 'text': 'Buy or Sell on TSLA?'}),
        message('m2', 'bot', '2026-10-27T02:05:09Z', {'kind': 'bot_message_sent', 'toBotName': 'Market Analyst',
                                                       'text': 'Research Tesla.', 'intent': 'request'}),
        message('m3', 'bot', '2026-10-27T02:05:10Z', {'kind': 'text', 'text': "I can't skip the review."}),
    ],
    'analyst': [
        message('a1', 'user', '2026-10-27T02:05:09Z', {'kind': 'bot_message_received', 'fromBotName': 'Lead Analyst',
                                                        'text': 'Research   Tesla.\n', 'intent': 'request'}),
    ],
}
BOTS = {'Lead Analyst': 'lead', 'Market Analyst': 'analyst'}


def test_narration_prints_each_delivery_once_in_time_order(capsys):
    seen = set()
    narrate(FakeRakazo(THREADS), BOTS, seen)
    lines = [line.split('] ', 1)[1] for line in capsys.readouterr().out.splitlines()]
    assert lines == ['user → Lead Analyst: Buy or Sell on TSLA?',
                     'Lead Analyst → Market Analyst (request): Research Tesla.',
                     "Lead Analyst → user: I can't skip the review."]
    narrate(FakeRakazo(THREADS), BOTS, seen)
    assert capsys.readouterr().out == ''


def test_a_re_review_that_does_not_approve_ends_the_run_without_a_memo():
    revise, approve = {'verdict': 'revise'}, {'verdict': 'approve'}
    assert run_scenario.review_failed({'reviews': [revise, revise]})
    assert not run_scenario.review_failed({'reviews': [revise]})            # the first review: a revision is coming
    assert not run_scenario.review_failed({'reviews': [revise, approve]})


def test_a_request_of_your_own_runs_like_a_scenario_without_documents():
    assert run_scenario.custom_scenario('A memo on Nvidia') == {
        'name': 'custom', 'request': 'A memo on Nvidia', 'client_documents': []}


class FollowUpRakazo:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def bots(self):
        return {'Lead Analyst': {'id': 'lead'}, 'IC Reviewer': {'id': 'rev'}, 'Someone else': {'id': 'other'}}

    def messages(self, bot_id):
        return []

    def send(self, bot_id, text):
        # While the question is out, the run counts as live: it has no outcome.json.
        assert not (case_file.active_run_dir() / 'outcome.json').exists()
        if self.fail:
            raise RuntimeError('Rakazo is down')
        self.sent.append((bot_id, text))
        return {'runId': 'run-9'}


def follow_up_args():
    return argparse.Namespace(timeout=60, approval_cards='deny', narrate=False)


def finished_run(outcome: dict):
    case_file.start_run('rushed-call', [], 'Buy or Sell on TSLA?')
    path = case_file.active_run_dir() / 'outcome.json'
    path.write_text(json.dumps(outcome))
    return path


def test_a_follow_up_asks_the_lead_then_captures_the_run_again(runs_dir, monkeypatch):
    outcome = finished_run({'outcome': 'failed review'})
    waited = []
    monkeypatch.setattr(run_scenario, 'wait_for_finish',
                        lambda app, bot_ids, timeout, quiet, cards, seen: waited.append((bot_ids, quiet)) or 'stalled')
    monkeypatch.setattr(run_scenario, 'capture_run',
                        lambda app, bot_ids, run_dir: {'transcript_files': 3, 'messages': {'Lead Analyst': 9}})
    app = FollowUpRakazo()
    run_scenario.follow_up(app, ' What would change the call? ', follow_up_args())
    assert app.sent == [('lead', 'What would change the call?')]
    assert waited == [({'Lead Analyst': 'lead', 'IC Reviewer': 'rev'}, 15)]  # done once the team is idle
    result = json.loads(outcome.read_text())
    assert (result['outcome'], result['follow_ups'], result['captured']['transcript_files']) == ('failed review', 1, 3)


def test_a_follow_up_that_fails_leaves_the_run_as_it_was(runs_dir):
    outcome = finished_run({'outcome': 'delivered'})
    with pytest.raises(RuntimeError):
        run_scenario.follow_up(FollowUpRakazo(fail=True), 'Why?', follow_up_args())
    assert json.loads(outcome.read_text()) == {'outcome': 'delivered'}


def test_a_follow_up_needs_a_finished_run(runs_dir):
    case_file.start_run('rushed-call')
    with pytest.raises(SystemExit, match='has not finished'):
        run_scenario.follow_up(FollowUpRakazo(), 'Why?', follow_up_args())
