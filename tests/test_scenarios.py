from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = sorted((ROOT / 'scenarios').glob('*.yaml'))
RULES = {f'N{n}' for n in range(1, 10)}


@pytest.mark.parametrize('path', SCENARIOS, ids=lambda p: p.stem)
def test_scenario_files_are_complete(path):
    scenario = yaml.safe_load(path.read_text())
    assert scenario['name'] == path.stem
    assert scenario['request'].strip() and scenario['summary'] and scenario['watch_for']
    assert set(scenario['exercises']) <= RULES
    for document in scenario['client_documents']:
        assert (ROOT / document['file']).exists()
        assert document['confidentiality'] in {'public', 'client-confidential'}


def test_every_rule_is_exercised_by_some_scenario():
    covered = {rule for path in SCENARIOS for rule in yaml.safe_load(path.read_text())['exercises']}
    assert covered == RULES
