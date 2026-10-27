from team.run_scenario import narrate


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
        message('m2', 'bot', '2026-10-27T02:05:09Z', {'kind': 'bot_message_sent', 'toBotName': 'Research Analyst',
                                                       'text': 'Research Tesla.', 'intent': 'request'}),
        message('m3', 'bot', '2026-10-27T02:05:10Z', {'kind': 'text', 'text': "I can't skip the review."}),
    ],
    'analyst': [
        message('a1', 'user', '2026-10-27T02:05:09Z', {'kind': 'bot_message_received', 'fromBotName': 'Lead Analyst',
                                                        'text': 'Research   Tesla.\n', 'intent': 'request'}),
    ],
}
BOTS = {'Lead Analyst': 'lead', 'Research Analyst': 'analyst'}


def test_narration_prints_each_delivery_once_in_time_order(capsys):
    seen = set()
    narrate(FakeRakazo(THREADS), BOTS, seen)
    lines = [line.split('] ', 1)[1] for line in capsys.readouterr().out.splitlines()]
    assert lines == ['user → Lead Analyst: Buy or Sell on TSLA?',
                     'Lead Analyst → Research Analyst (request): Research Tesla.',
                     "Lead Analyst → user: I can't skip the review."]
    narrate(FakeRakazo(THREADS), BOTS, seen)
    assert capsys.readouterr().out == ''
