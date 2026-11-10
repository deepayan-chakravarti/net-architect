"""Parameter validation (distance, density, resiliency) and routing protocol selection."""

import copy

import pytest

from netarchitect import plan
from netarchitect.errors import ValidationError
from netarchitect.validator import validate


def issues_of(params) -> list[str]:
    with pytest.raises(ValidationError) as exc:
        validate(params)
    return exc.value.issues


def test_minimal_campus_is_valid(mini):
    params, warnings = validate(mini())
    assert params["resiliency"] == "single" and params["p2p_prefix"] == 30


def test_all_issues_reported_at_once(mini):
    p = mini(name="", root_prefix="10.0.0.1/16", resiliency="triple")
    p["sites"][0]["vlans"][0]["hosts"] = 0
    issues = issues_of(p)
    assert len(issues) >= 4
    text = " ".join(issues)
    assert "name" in text and "host bits" in text and "resiliency" in text and "hosts" in text


@pytest.mark.parametrize("root,needle", [("10.0.0.0/7", "/8 and /30"), ("10.0.0.0/31", "/8 and /30"),
                                         ("banana", "CIDR"), ("300.0.0.0/8", "exceeds 255")])
def test_bad_root_prefix(mini, root, needle):
    assert any(needle in i for i in issues_of(mini(root_prefix=root)))


@pytest.mark.parametrize("vid", [1, 999, 998, 1002, 1005, 0, 4095, "10"])
def test_reserved_or_invalid_vlan_ids(mini, vid):
    p = mini()
    p["sites"][0]["vlans"][0]["vlan_id"] = vid
    assert any("vlan_id" in i for i in issues_of(p))


def test_duplicate_vlan_id_in_site(mini):
    p = mini()
    p["sites"][0]["vlans"][1]["vlan_id"] = 10
    assert any("duplicate vlan_id" in i for i in issues_of(p))


@pytest.mark.parametrize("link,needle", [
    ({"a": "A", "b": "Z", "distance_m": 10}, "defined sites"),
    ({"a": "A", "b": "A", "distance_m": 10}, "itself"),
    ({"a": "A", "b": "B", "distance_m": -5}, "positive"),
    ({"a": "A", "b": "B", "distance_m": 0}, "positive"),
    ({"a": "A", "b": "B"}, "required"),
    ({"a": "A", "b": "B", "distance_m": 5, "distance_km": 1}, "not both"),
    ({"a": "A", "b": "B", "distance_km": 30000}, "circumference"),
    ({"a": "A", "b": "B", "distance_m": 5, "media": "laser"}, "media"),
    ({"a": "A", "b": "B", "distance_m": 5, "bandwidth_gbps": 400}, "bandwidth"),
])
def test_link_distance_and_field_validation(mini, link, needle):
    assert any(needle in i for i in issues_of(mini(links=[link])))


def test_disconnected_topology(mini):
    p = mini(links=[])
    assert any("disconnected" in i for i in issues_of(p))


def test_redundant_resiliency_detects_single_point_of_failure(mini):
    assert any("single point of failure" in i for i in issues_of(mini(resiliency="redundant")))


def test_dual_homed_requires_two_uplinks(preset):
    p = preset("metro_man")
    p["links"] = [l for l in p["links"] if not (l["a"] == "REMOTE-2" and l["b"] == "COLO")]
    issues = issues_of(p)
    assert any("REMOTE-2 has 1 uplink" in i for i in issues)


def test_density_warning_for_huge_broadcast_domain(mini):
    p = mini()
    p["sites"][0]["vlans"][0]["hosts"] = 1500
    _, warnings = validate(p)
    assert any("broadcast domain" in w for w in warnings)


def test_cloud_vpc_must_not_overlap_root(preset):
    p = preset("global_wan")
    p["sites"][-1]["vpc_cidr"] = "10.64.128.0/17"
    assert any("overlaps root_prefix" in i for i in issues_of(p))


def test_qos_overcommit_and_unknown_class(preset):
    p = preset("metro_man")
    p["qos"]["classes"][1]["percent"] = 60
    assert any("75%" in i for i in issues_of(p))
    p = preset("metro_man")
    p["sites"][0]["vlans"][0]["qos_class"] = "GOLD"
    assert any("GOLD" in i for i in issues_of(p))


def test_reserved_site_name(mini):
    p = mini()
    p["sites"][0]["name"] = "INFRA"
    p["links"][0]["a"] = "INFRA"
    assert any("reserved" in i for i in issues_of(p))


def test_wan_requires_internet_transport(preset):
    p = preset("global_wan")
    p["links"][0]["transport"] = "evpl"
    assert any("transport 'internet'" in i for i in issues_of(p))


def test_non_object_input():
    with pytest.raises(ValidationError):
        validate(["not", "an", "object"])


# --------------------------------------------------------------------------- routing
def test_campus_selects_single_area_ospf(preset):
    r = plan(preset("campus_lan"))
    assert r["routing"]["design"] == "Single-area OSPF"
    assert set(r["routing"]["areas"].values()) == {0}
    assert r["routing"]["bgp"] is None
    assert r["routing"]["subnet_count"] < 50


def test_wan_selects_multi_area_with_summaries_and_ebgp(preset):
    r = plan(preset("global_wan"))
    rt = r["routing"]
    assert rt["design"] == "Multi-area OSPF"
    assert rt["areas"]["NYC"] == 0
    assert sorted(v for k, v in rt["areas"].items() if k != "NYC") == [1, 2, 3]
    assert rt["summaries"]["LONDON"]["cidr"] == r["addressing"]["blocks"][1]["block"] or \
        rt["summaries"]["LONDON"]["cidr"] in {b["block"] for b in r["addressing"]["blocks"]}
    assert rt["bgp"]["asn"] == 65010 and rt["bgp"]["peers"][0]["asn"] == 64512


def test_fifty_subnets_forces_multi_area(mini):
    p = mini()
    p["sites"][0]["vlans"] = [{"name": f"V{i}", "vlan_id": 100 + i, "hosts": 10}
                              for i in range(50)] + [{"name": "MGMT", "vlan_id": 99, "hosts": 10,
                                                      "role": "mgmt"}]
    r = plan(p)
    assert r["routing"]["subnet_count"] >= 50
    assert r["routing"]["design"] == "Multi-area OSPF"


def test_dual_homed_enables_bfd(preset):
    assert plan(preset("metro_man"))["routing"]["bfd"] is True
    assert plan(preset("campus_lan"))["routing"]["bfd"] is False


def test_metro_latency_within_budget_including_failover(preset):
    lat = plan(preset("metro_man"))["latency"]
    assert lat["budget_ms"] == 5
    assert all(p["within_budget"] for p in lat["pairs"])
    assert any("failover_of" in p for p in lat["pairs"])
