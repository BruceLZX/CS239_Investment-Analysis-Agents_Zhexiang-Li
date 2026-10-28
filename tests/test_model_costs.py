from datetime import datetime

import pytest

from team.model_costs import call_cost, is_peak


def ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


@pytest.mark.parametrize('iso, peak', [
    ('2026-10-28T00:59:59+00:00', False),  # a Wednesday
    ('2026-10-28T01:00:00+00:00', True),
    ('2026-10-28T03:59:59+00:00', True),
    ('2026-10-28T04:00:00+00:00', False),
    ('2026-10-28T06:00:00+00:00', True),
    ('2026-10-28T09:59:59+00:00', True),
    ('2026-10-28T10:00:00+00:00', False),
    ('2026-10-31T02:00:00+00:00', False),  # a Saturday
    ('2026-10-27T18:30:00-07:00', True),   # 6:30 PM in Los Angeles is 01:30 UTC on Wednesday
])
def test_peak_hours_are_deepseeks(iso, peak):
    assert is_peak(ms(iso)) is peak


def test_a_peak_call_costs_what_rakazo_recorded():
    # A deepseek-v4-pro call from the submitted rushed-call run, which Rakazo's usage record puts at $0.004736072.
    at = ms('2026-10-28T02:00:51.772+00:00')
    assert call_cost('deepseek-v4-pro', 16768, 1367, 554, at) == pytest.approx(0.004736072)


def test_an_off_peak_call_costs_half():
    peak = call_cost('deepseek-v4-pro', 16768, 1367, 554, ms('2026-10-28T02:00:00+00:00'))
    assert call_cost('deepseek-v4-pro', 16768, 1367, 554, ms('2026-10-28T12:00:00+00:00')) == pytest.approx(peak / 2)


def test_flash_has_its_own_price_and_its_retired_names_bill_the_same():
    at = ms('2026-10-28T02:00:00+00:00')
    assert call_cost('deepseek-flash', 1_000_000, 1_000_000, 1_000_000, at) == pytest.approx(0.006 + 0.3 + 1.2)
    assert call_cost('deepseek-v4-flash', 1_000_000, 1_000_000, 1_000_000, at) == pytest.approx(0.006 + 0.3 + 1.2)


def test_a_model_without_a_price_has_no_cost_here():
    assert call_cost('unpriced-model', 0, 1000, 1000, 0) is None
    assert call_cost(None, 0, 1000, 1000, 0) is None
