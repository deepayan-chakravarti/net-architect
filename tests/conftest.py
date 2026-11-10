import copy

import pytest

from netarchitect.presets import load_preset


@pytest.fixture
def preset():
    """Return a fresh deep copy of a preset so tests can mutate it safely."""
    def _load(name: str) -> dict:
        return copy.deepcopy(load_preset(name))
    return _load


def minimal_campus(**overrides) -> dict:
    p = {
        "name": "Mini",
        "network_type": "campus",
        "root_prefix": "10.0.0.0/16",
        "sites": [
            {"name": "A", "vlans": [{"name": "DATA", "vlan_id": 10, "hosts": 50},
                                    {"name": "MGMT", "vlan_id": 99, "hosts": 10, "role": "mgmt"}]},
            {"name": "B", "vlans": [{"name": "DATA", "vlan_id": 20, "hosts": 50},
                                    {"name": "MGMT", "vlan_id": 199, "hosts": 10, "role": "mgmt"}]},
        ],
        "links": [{"a": "A", "b": "B", "distance_m": 200}],
    }
    p.update(overrides)
    return p


@pytest.fixture
def mini():
    return minimal_campus
