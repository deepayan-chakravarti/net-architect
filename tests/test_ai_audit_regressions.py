"""Regression tests for the AI-generated flaws documented in ai_audit_log.md.

Each test first reproduces the *buggy* AI suggestion (kept verbatim as a local
function) to prove the failure is real, then asserts the shipped code is fixed.
"""

import ipaddress
import math

import pytest

from netarchitect import ipmath as ip
from netarchitect import plan
from netarchitect.media import SMF_OPTICS, optical_budget, select_media
from netarchitect.packetflow import ACE, ACL, Match, lpm_candidates
from netarchitect.presets import load_preset
from netarchitect.vlsm import SubnetRequest, allocate


# --- Instance 1: wildcard mask via Python's ~ operator ----------------------------
def ai_wildcard(prefix):                      # AI suggestion (buggy)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return ~mask


def test_instance1_ai_wildcard_is_negative():
    assert ai_wildcard(24) == -4294967041     # ~x == -(x+1): Python ints are signed
    with pytest.raises(Exception):
        ip.int_to_ip(ai_wildcard(24))


def test_instance1_ai_wildcard_silently_disables_overlap_detection():
    def ai_overlaps(a_net, a_p, b_net, b_p):          # overlap check built on the buggy wildcard
        a_b = a_net | ai_wildcard(a_p)
        b_b = b_net | ai_wildcard(b_p)
        return a_net <= b_b and b_net <= a_b
    a = ip.parse_cidr("10.0.0.0/23")
    b = ip.parse_cidr("10.0.1.0/24")                   # b is inside a
    assert not ai_overlaps(*a, *b)                     # buggy: collision NOT detected
    assert ip.overlaps(*a, *b)                         # fixed


def test_instance1_fixed_wildcard_and_acl_semantics():
    assert ip.wildcard_str(24) == "0.0.0.255"
    # packet-flow proof: the ACL built from the fixed wildcard matches exactly the /22
    acl = ACL("T", "extended", [ACE("permit", "ip", Match.cidr(*ip.parse_cidr("10.1.4.0/22")))])
    assert acl.evaluate("tcp", ip.ip_to_int("10.1.7.255"), 0, 80)[0] == "permit"
    assert acl.evaluate("tcp", ip.ip_to_int("10.1.8.0"), 0, 80)[0] == "deny"


# --- Instance 2: host count -> prefix ignores network/broadcast/gateway ----------
def ai_prefix_for_hosts(hosts):               # AI suggestion (buggy)
    return 32 - math.ceil(math.log2(hosts))


def test_instance2_ai_sizing_puts_hosts_on_broadcast():
    p = ai_prefix_for_hosts(256)              # -> /24
    net = ipaddress.ip_network(f"10.0.0.0/{p}")
    assert net.num_addresses - 2 < 256        # only 254 usable for 256 hosts
    assert ai_prefix_for_hosts(1) == 32       # one LAN host gets a /32 - no gateway at all
    assert ai_prefix_for_hosts(64) == 26      # 64 hosts in a /26 (62 usable) - 2 stranded


@pytest.mark.parametrize("hosts", [1, 2, 62, 64, 126, 254, 256, 500, 1022])
def test_instance2_fixed_sizing(hosts):
    p = ip.prefix_for_hosts(hosts)
    assert ip.usable_hosts(p) >= hosts + 1    # every host + the gateway gets a real address


# --- Instance 3: unsorted, unaligned VLSM ---------------------------------------
def ai_allocate(root, hosts_list):            # AI suggestion (buggy)
    net = ipaddress.ip_network(root)
    cursor = int(net.network_address)
    out = []
    for h in hosts_list:                      # no sort, no alignment
        prefix = 32 - math.ceil(math.log2(h + 2))
        out.append(f"{ipaddress.ip_address(cursor)}/{prefix}")
        cursor += 2 ** (32 - prefix)
    return out


def test_instance3_ai_allocator_produces_misaligned_networks():
    subnets = ai_allocate("192.168.1.0/24", [50, 100])
    assert subnets == ["192.168.1.0/26", "192.168.1.64/25"]
    with pytest.raises(ValueError):                       # host bits set -> IOS rejects it
        ipaddress.ip_network(subnets[1])
    # packet flow: 192.168.1.70 matches BOTH the /26 interpretation and the /25 one
    routes = [(ip.ip_to_int("192.168.1.0"), 26, "A"), (ip.ip_to_int("192.168.1.0"), 25, "B")]
    assert len(lpm_candidates(routes, ip.ip_to_int("192.168.1.10"))) == 2


def test_instance3_fixed_allocator():
    alloc = allocate("192.168.1.0/24", [SubnetRequest("A", 50), SubnetRequest("B", 100)])
    for s in alloc.subnets:
        ipaddress.ip_network(s.cidr)                      # strict: aligned
    got = {s.name: s.cidr for s in alloc.subnets}
    assert got == {"B": "192.168.1.0/25", "A": "192.168.1.128/26"}


# --- Instance 4: optical budget ignores connectors/splices/margin ---------------
def ai_er_ok(km):                             # AI suggestion (buggy): fibre loss only
    return km * 0.3 <= 11.0 and km <= 40


def test_instance4_ai_budget_accepts_35km_er():
    assert ai_er_ok(35)


def test_instance4_fixed_budget_rejects_35km_er():
    er = next(o for o in SMF_OPTICS if o.name == "10GBASE-ER")
    b = optical_budget(er, 35_000, 1.0)
    assert b.total_with_margin_db > er.max_loss_db
    assert select_media(35_000, 10).transceiver == "10GBASE-ZR"


# --- Instance 5: unconstrained trunk ---------------------------------------------
def test_instance5_generated_trunks_are_pruned_and_native_moved():
    r = plan(load_preset("campus_lan"))
    for cfg in r["configs"].values():
        assert "allowed vlan all" not in cfg
        if "switchport mode trunk" in cfg:
            assert "switchport trunk native vlan" in cfg
            assert "switchport nonegotiate" in cfg


# --- Guest ACL order: deny-before-permit (packet walk) --------------------------
def test_guest_acl_order_blocks_lateral_traffic():
    r = plan(load_preset("campus_lan"))
    walks = [c for c in r["verification"]["checks"] if c["type"] == "acl"]
    assert walks and all(c["pass"] for c in walks)
    lateral = [c for c in walks if "SMB" in c["flow"]]
    assert lateral and all(c["result"] == "deny" for c in lateral)
