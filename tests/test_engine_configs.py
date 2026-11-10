"""End-to-end presets, generated IOS correctness, explainability coverage, exports."""

import ipaddress
import re

import pytest

from netarchitect import plan
from netarchitect.cli import export_plan
from netarchitect.errors import AddressSpaceExhaustedError, PhysicalDistanceViolationError
from netarchitect.presets import PRESET_IDS

IP = r"(\d+\.\d+\.\d+\.\d+)"


@pytest.fixture(scope="module")
def results():
    from netarchitect.presets import load_preset
    return {pid: plan(load_preset(pid)) for pid in PRESET_IDS}


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_preset_runs_and_all_packet_flow_checks_pass(results, pid):
    r = results[pid]
    assert r["verification"]["total"] > 0
    assert r["verification"]["passed"] == r["verification"]["total"]


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_every_decision_domain_is_explained(results, pid):
    domains = {e["domain"] for e in results[pid]["rationale"]}
    assert {"L1 Media", "L2 Switching", "Topology", "L3 VLSM", "L3 Routing"} <= domains
    for e in results[pid]["rationale"]:
        assert len(e["justification"]) > 40, e


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_every_link_has_a_media_justification(results, pid):
    r = results[pid]
    subjects = {e["subject"] for e in r["rationale"] if e["domain"] == "L1 Media"}
    for l in r["media"]["links"]:
        assert l["subject"] in subjects


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_ospf_network_wildcards_are_inverse_masks(results, pid):
    for dev, cfg in results[pid]["configs"].items():
        for net, wc in re.findall(rf"^ network {IP} {IP} area \d+$", cfg, re.M):
            wc_int = int(ipaddress.IPv4Address(wc))
            prefix = 32 - wc_int.bit_length()
            assert wc_int == (1 << (32 - prefix)) - 1, f"{dev}: {wc} is not a contiguous wildcard"
            ipaddress.ip_network(f"{net}/{prefix}")          # strict: raises if misaligned


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_interface_addresses_are_usable_hosts(results, pid):
    """No interface may sit on a network ID or broadcast address (prefix < 31)."""
    for dev, cfg in results[pid]["configs"].items():
        for addr, mask in re.findall(rf"^ ip address {IP} {IP}$", cfg, re.M):
            iface = ipaddress.ip_interface(f"{addr}/{mask}")
            if iface.network.prefixlen < 31:
                assert iface.ip not in (iface.network.network_address,
                                        iface.network.broadcast_address), f"{dev}: {iface}"


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_trunks_are_constrained(results, pid):
    for dev, cfg in results[pid]["configs"].items():
        assert "allowed vlan all" not in cfg
        blocks = re.split(r"^interface ", cfg, flags=re.M)
        for b in blocks:
            if " switchport mode trunk" in b:
                assert "switchport trunk allowed vlan" in b, f"{dev}: unconstrained trunk"
                assert "switchport nonegotiate" in b, f"{dev}: DTP left on"


@pytest.mark.parametrize("pid", PRESET_IDS)
def test_no_duplicate_ip_addresses_across_devices(results, pid):
    seen = {}
    for dev, cfg in results[pid]["configs"].items():
        if "ASW1" in dev:          # templates are replicated, skip
            continue
        for addr in re.findall(rf"^ ip address {IP} ", cfg, re.M):
            assert addr not in seen, f"{addr} on {dev} and {seen[addr]}"
            seen[addr] = dev


def test_campus_configs(results):
    cfg = results["campus_lan"]["configs"]["BLDG-A-DSW1"]
    assert "ip routing" in cfg and "spanning-tree mode rapid-pvst" in cfg
    assert re.search(r"^interface Vlan110$", cfg, re.M)
    assert "ip access-group GUEST-IN-V140 in" in cfg
    assert "switchport trunk native vlan 999" in cfg
    assert "router ospf 1" in cfg and "passive-interface default" in cfg
    acc = results["campus_lan"]["configs"]["BLDG-A-ASW1"]
    assert "switchport voice vlan 120" in acc and "spanning-tree bpduguard enable" in acc


def test_metro_configs(results):
    cfg = results["metro_man"]["configs"]["REMOTE-1-RTR1"]
    assert "bfd interval 50 min_rx 50 multiplier 3" in cfg
    assert "ip ospf cost 100" in cfg and "ip ospf cost 10" in cfg
    assert "priority percent 30" in cfg and "shape average 1000000000" in cfg
    assert "service-policy output WAN-SHAPE-1000M" in cfg
    assert "CARRIER-EVPL-SIM" in results["metro_man"]["configs"]


def test_wan_configs(results):
    r = results["global_wan"]
    lon = r["configs"]["LONDON-RTR1"]
    assert "tunnel protection ipsec profile IPSEC-GRE" in lon
    assert re.search(r"^ area 1 range 10\.64\.\d+\.0 255\.255\.252\.0$", lon, re.M)
    nyc = r["configs"]["NYC-RTR1"]
    assert "router bgp 65010" in nyc and "remote-as 64512" in nyc
    assert "prefix-list TO-CLOUD out" in nyc and "redistribute bgp 65010 subnets" in nyc
    # the public underlay must never be advertised into OSPF (recursive routing)
    for dev in ("NYC-RTR1", "LONDON-RTR1", "SINGAPORE-RTR1", "MUMBAI-RTR1"):
        assert not re.search(r"^ network 203\.0\.113\.", r["configs"][dev], re.M)
    assert {"ISP-SIM", "ISP-SW", "CLOUD-VPC-VGW-SIM"} <= set(r["configs"])


def test_psk_matches_on_both_tunnel_ends(results):
    cfgs = results["global_wan"]["configs"]
    keys = {}
    for dev, cfg in cfgs.items():
        for k, addr in re.findall(r"crypto isakmp key (\S+) address " + IP, cfg):
            keys.setdefault(k, []).append(dev)
    assert keys and all(len(devs) == 2 for devs in keys.values())


def test_engine_raises_distance_violation_for_custom_copper(mini):
    p = mini()
    p["links"][0].update({"distance_m": 180, "media": "copper"})
    with pytest.raises(PhysicalDistanceViolationError):
        plan(p)


def test_engine_raises_exhaustion_for_tiny_root(mini):
    with pytest.raises(AddressSpaceExhaustedError):
        plan(mini(root_prefix="10.0.0.0/26"))


def test_export_writes_combined_and_per_device_files(results, tmp_path):
    files = export_plan(results["campus_lan"], tmp_path, "campus_lan")
    combined = tmp_path / "campus_lan_configs.txt"
    assert combined.exists() and "CABLING PLAN" in combined.read_text()
    assert (tmp_path / "campus_lan" / "BLDG-A-DSW1.cfg").exists()
    assert (tmp_path / "campus_lan_rationale.md").exists()
    assert len(files) == 3 + len(results["campus_lan"]["configs"])
