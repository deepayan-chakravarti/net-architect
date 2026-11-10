"""VLSM allocator: zero overlap, alignment, exhaustion, edge-case prefixes."""

import ipaddress
import random

import pytest

from netarchitect import ipmath as ip
from netarchitect.errors import AddressSpaceExhaustedError, InvalidPrefixError
from netarchitect.vlsm import (SubnetRequest, allocate, allocate_hierarchical,
                               verify_no_overlap)


def oracle_check(root: str, subnets, requests):
    """Independent verification with the stdlib ipaddress module."""
    root_net = ipaddress.ip_network(root)
    nets = []
    for s in subnets:
        n = ipaddress.ip_network(s.cidr)            # strict=True -> raises if misaligned
        assert n.subnet_of(root_net), f"{n} escapes {root_net}"
        assert str(n.broadcast_address) == ip.int_to_ip(s.broadcast)
        assert str(n.netmask) == ip.int_to_ip(s.mask)
        assert str(n.hostmask) == ip.int_to_ip(s.wildcard)
        if s.kind == "lan":
            assert s.usable >= s.hosts_requested + 1
            assert ip.int_to_ip(s.gateway) == str(n.network_address + 1)
        nets.append(n)
    for i, a in enumerate(nets):
        for b in nets[i + 1:]:
            assert not a.overlaps(b), f"{a} overlaps {b}"
    assert len(subnets) == len(requests)


def test_textbook_allocation():
    reqs = [SubnetRequest("A", 100), SubnetRequest("B", 50), SubnetRequest("C", 25),
            SubnetRequest("D", 10)]
    alloc = allocate("192.168.10.0/24", reqs)
    got = {s.name: s.cidr for s in alloc.subnets}
    assert got == {"A": "192.168.10.0/25", "B": "192.168.10.128/26",
                   "C": "192.168.10.192/27", "D": "192.168.10.224/28"}
    oracle_check("192.168.10.0/24", alloc.subnets, reqs)


def test_input_order_does_not_matter():
    reqs = [SubnetRequest("D", 10), SubnetRequest("A", 100), SubnetRequest("C", 25),
            SubnetRequest("B", 50)]
    got = {s.name: s.cidr for s in allocate("192.168.10.0/24", reqs).subnets}
    assert got["A"] == "192.168.10.0/25" and got["D"] == "192.168.10.224/28"


def test_randomised_property_zero_overlap():
    rng = random.Random(2026)
    for _ in range(300):
        root_prefix = rng.randint(16, 24)
        root = f"10.{rng.randint(0, 255)}.0.0/{root_prefix}"
        root = ip.cidr_str(ip.network_of(ip.parse_cidr(root, strict=False)[0], root_prefix),
                           root_prefix)
        reqs = [SubnetRequest(f"N{i}", rng.choice([1, 2, 5, 14, 30, 60, 120, 250, 500, 1000]))
                for i in range(rng.randint(1, 12))]
        reqs += [SubnetRequest(f"P{i}", 2, "p2p") for i in range(rng.randint(0, 4))]
        try:
            alloc = allocate(root, reqs)
        except AddressSpaceExhaustedError as exc:
            assert exc.required > exc.available
            continue
        oracle_check(root, alloc.subnets, reqs)


def test_exact_fit_uses_whole_root():
    reqs = [SubnetRequest("A", 125), SubnetRequest("B", 125)]   # 125+3 = 128 each
    alloc = allocate("10.0.0.0/24", reqs)
    assert alloc.allocated == 256
    oracle_check("10.0.0.0/24", alloc.subnets, reqs)


def test_exhaustion_reports_required_available_and_minimum_prefix():
    with pytest.raises(AddressSpaceExhaustedError) as exc:
        allocate("10.0.0.0/24", [SubnetRequest("A", 200), SubnetRequest("B", 100)])
    e = exc.value
    assert e.required == 384 and e.available == 256 and e.minimum_prefix == 23
    assert e.exit_code == 4
    assert "/23" in e.message


def test_one_address_over_capacity_is_exhausted():
    # 126 hosts + gw + 2 = 129 -> needs a /24 block; root is a /25
    with pytest.raises(AddressSpaceExhaustedError, match="larger than the whole"):
        allocate("10.0.0.0/25", [SubnetRequest("A", 126)])


def test_p2p_slash30_and_slash31():
    a30 = allocate("10.255.0.0/29", [SubnetRequest("L1", 2, "p2p"), SubnetRequest("L2", 2, "p2p")])
    assert [s.cidr for s in a30.subnets] == ["10.255.0.0/30", "10.255.0.4/30"]
    assert ip.int_to_ip(a30.subnets[0].first_usable) == "10.255.0.1"
    a31 = allocate("10.255.0.0/30", [SubnetRequest("L1", 2, "p2p"), SubnetRequest("L2", 2, "p2p")],
                   p2p_prefix=31)
    assert [s.cidr for s in a31.subnets] == ["10.255.0.0/31", "10.255.0.2/31"]
    assert a31.subnets[0].usable == 2
    assert a31.subnets[0].first_usable == a31.subnets[0].network      # RFC 3021: no net/bcast


def test_slash30_root_holds_exactly_one_p2p():
    allocate("10.0.0.0/30", [SubnetRequest("L1", 2, "p2p")])
    with pytest.raises(AddressSpaceExhaustedError):
        allocate("10.0.0.0/30", [SubnetRequest("L1", 2, "p2p"), SubnetRequest("L2", 2, "p2p")])


def test_loopbacks_are_host_routes():
    alloc = allocate("10.0.0.0/29", [SubnetRequest(f"LO{i}", 1, "loopback") for i in range(8)])
    assert all(s.prefix == 32 for s in alloc.subnets)
    assert len({s.network for s in alloc.subnets}) == 8


@pytest.mark.parametrize("bad", [0, -3, True, 1.5])
def test_invalid_host_counts(bad):
    with pytest.raises(ValueError):
        allocate("10.0.0.0/24", [SubnetRequest("A", bad)])


def test_root_with_host_bits_rejected():
    with pytest.raises(InvalidPrefixError):
        allocate("10.0.0.5/24", [SubnetRequest("A", 10)])


def test_verify_no_overlap_detects_corruption():
    alloc = allocate("10.0.0.0/24", [SubnetRequest("A", 100), SubnetRequest("B", 100)])
    alloc.subnets[1].network = alloc.subnets[0].network     # force a collision
    with pytest.raises(AssertionError, match="overlap"):
        verify_no_overlap(alloc.subnets)


def test_hierarchical_blocks_are_summarisable():
    sites = {
        "HQ": [SubnetRequest("USERS", 250), SubnetRequest("VOICE", 120), SubnetRequest("MGMT", 16)],
        "BR1": [SubnetRequest("USERS", 120), SubnetRequest("MGMT", 8)],
        "INFRA": [SubnetRequest("P2P", 2, "p2p"), SubnetRequest("LO", 1, "loopback")],
    }
    addr = allocate_hierarchical("172.16.0.0/16", sites)
    blocks = [ipaddress.ip_network(b.cidr) for b in addr.blocks]
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            assert not a.overlaps(b)
    for b in addr.blocks:
        blk = ipaddress.ip_network(b.cidr)
        for s in b.allocation.subnets:
            assert ipaddress.ip_network(s.cidr).subnet_of(blk)
    assert addr.block("HQ").cidr == "172.16.0.0/23"


def test_hierarchical_exhaustion():
    sites = {"A": [SubnetRequest("X", 500)], "B": [SubnetRequest("Y", 500)]}
    with pytest.raises(AddressSpaceExhaustedError):
        allocate_hierarchical("10.0.0.0/23", sites)


def test_utilisation_and_efficiency_reported():
    alloc = allocate("10.0.0.0/24", [SubnetRequest("A", 61)])
    s = alloc.subnets[0]
    assert s.prefix == 26 and s.utilization == pytest.approx(62 / 62)
    d = alloc.to_dict()
    assert d["allocated"] == 64 and d["free"] == 192
