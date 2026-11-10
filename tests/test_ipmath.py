"""Bitwise primitives, cross-checked against the stdlib ipaddress module as an oracle."""

import ipaddress
import random

import pytest

from netarchitect import ipmath as ip
from netarchitect.errors import InvalidAddressError, InvalidPrefixError


@pytest.mark.parametrize("prefix", range(33))
def test_mask_and_wildcard_match_oracle_for_every_prefix(prefix):
    net = ipaddress.ip_network(f"0.0.0.0/{prefix}")
    assert ip.mask_str(prefix) == str(net.netmask)
    assert ip.wildcard_str(prefix) == str(net.hostmask)
    assert ip.prefix_to_mask(prefix) + ip.wildcard(prefix) == ip.MAX32


@pytest.mark.parametrize("prefix,expected", [
    (0, "255.255.255.255"), (1, "127.255.255.255"), (8, "0.255.255.255"),
    (22, "0.0.3.255"), (23, "0.0.1.255"), (27, "0.0.0.31"), (30, "0.0.0.3"),
    (31, "0.0.0.1"), (32, "0.0.0.0"),
])
def test_wildcard_edge_cases(prefix, expected):
    assert ip.wildcard_str(prefix) == expected
    assert 0 <= ip.wildcard(prefix) <= ip.MAX32          # never negative (Python ~x pitfall)


@pytest.mark.parametrize("bad", [-1, 33, 1.5, "24", True, None])
def test_prefix_out_of_range_rejected(bad):
    with pytest.raises(InvalidPrefixError):
        ip.prefix_to_mask(bad)


@pytest.mark.parametrize("mask,prefix", [("255.255.255.0", 24), ("255.255.252.0", 22),
                                         ("0.0.0.0", 0), ("255.255.255.255", 32),
                                         ("255.255.255.254", 31)])
def test_mask_to_prefix(mask, prefix):
    assert ip.mask_to_prefix(mask) == prefix


@pytest.mark.parametrize("mask", ["255.0.255.0", "255.255.255.253", "0.255.255.255"])
def test_non_contiguous_mask_rejected(mask):
    with pytest.raises(InvalidPrefixError):
        ip.mask_to_prefix(mask)


@pytest.mark.parametrize("bad", ["256.1.1.1", "1.2.3", "1.2.3.4.5", "01.2.3.4", "a.b.c.d",
                                 "", "1..2.3", "１.2.3.4", " 1.2.3.-4", 12345])
def test_malformed_addresses_rejected(bad):
    with pytest.raises(InvalidAddressError):
        ip.ip_to_int(bad)


def test_int_ip_roundtrip_boundaries():
    for s in ("0.0.0.0", "255.255.255.255", "10.0.0.1", "192.168.255.254"):
        assert ip.int_to_ip(ip.ip_to_int(s)) == s
    with pytest.raises(InvalidAddressError):
        ip.int_to_ip(-1)
    with pytest.raises(InvalidAddressError):
        ip.int_to_ip(2 ** 32)


def test_parse_cidr_strict_rejects_host_bits_and_suggests_network():
    with pytest.raises(InvalidPrefixError, match=r"10\.1\.4\.0/22"):
        ip.parse_cidr("10.1.5.7/22")
    assert ip.parse_cidr("10.1.5.7/22", strict=False) == (ip.ip_to_int("10.1.4.0"), 22)


@pytest.mark.parametrize("hosts,prefix", [
    (1, 30), (2, 29), (5, 29), (6, 28), (13, 28), (14, 27), (29, 27), (30, 26),
    (61, 26), (62, 25), (125, 25), (126, 24), (253, 24), (254, 23), (509, 23), (510, 22),
])
def test_prefix_for_hosts_includes_gateway_network_broadcast(hosts, prefix):
    assert ip.prefix_for_hosts(hosts) == prefix
    assert ip.usable_hosts(prefix) >= hosts + 1                 # hosts + gateway fit
    if prefix < 30:
        assert ip.usable_hosts(prefix + 1) < hosts + 1          # and it is the smallest


def test_usable_hosts_rfc3021():
    assert ip.usable_hosts(31) == 2
    assert ip.usable_hosts(32) == 1
    assert ip.usable_hosts(30) == 2
    assert ip.usable_hosts(24) == 254


@pytest.mark.parametrize("bad", [0, -5, True, 2.5])
def test_prefix_for_hosts_rejects_non_positive(bad):
    with pytest.raises(InvalidPrefixError):
        ip.prefix_for_hosts(bad)


def test_random_network_broadcast_against_oracle():
    rng = random.Random(307)
    for _ in range(2000):
        addr = rng.getrandbits(32)
        prefix = rng.randint(0, 32)
        oracle = ipaddress.ip_network((addr, prefix), strict=False)
        net = ip.network_of(addr, prefix)
        assert ip.int_to_ip(net) == str(oracle.network_address)
        assert ip.int_to_ip(ip.broadcast_of(net, prefix)) == str(oracle.broadcast_address)


def test_common_supernet_and_overlap():
    nets = [ip.parse_cidr("10.64.8.0/23"), ip.parse_cidr("10.64.10.0/26"),
            ip.parse_cidr("10.64.10.64/27")]
    assert ip.cidr_str(*ip.common_supernet(nets)) == "10.64.8.0/22"
    assert ip.overlaps(*ip.parse_cidr("10.0.0.0/23"), *ip.parse_cidr("10.0.1.128/25"))
    assert not ip.overlaps(*ip.parse_cidr("10.0.0.0/24"), *ip.parse_cidr("10.0.1.0/24"))


def test_rfc1918_detection():
    assert ip.is_rfc1918(*ip.parse_cidr("172.20.0.0/16"))
    assert not ip.is_rfc1918(*ip.parse_cidr("172.32.0.0/16"))
    assert not ip.is_rfc1918(*ip.parse_cidr("8.0.0.0/8"))
