"""Bitwise IPv4 primitives.

This module deliberately does *not* use the stdlib ``ipaddress`` module: every
mask, wildcard, broadcast and alignment computation is done with explicit
32-bit integer operations so it can be audited line by line.  The test-suite
cross-checks these results against ``ipaddress`` as an independent oracle.

All addresses are handled as unsigned 32-bit integers.  Python integers are
arbitrary precision and ``~x`` is *negative*, so every inversion is masked
with ``MAX32`` (see AI audit log, instance #1).
"""

from __future__ import annotations

from .errors import InvalidAddressError, InvalidPrefixError

MAX32 = 0xFFFFFFFF

RFC1918 = (
    (0x0A000000, 8),   # 10.0.0.0/8
    (0xAC100000, 12),  # 172.16.0.0/12
    (0xC0A80000, 16),  # 192.168.0.0/16
)


# --------------------------------------------------------------------------- #
# Conversion
# --------------------------------------------------------------------------- #
def ip_to_int(ip: str) -> int:
    """Dotted quad -> 32-bit int. Rejects leading zeros, unicode digits, etc."""
    if not isinstance(ip, str):
        raise InvalidAddressError(f"IPv4 address must be a string, got {type(ip).__name__}")
    parts = ip.strip().split(".")
    if len(parts) != 4:
        raise InvalidAddressError(f"'{ip}' is not a dotted-quad IPv4 address")
    value = 0
    for part in parts:
        if not (part.isascii() and part.isdigit()):
            raise InvalidAddressError(f"'{ip}': octet '{part}' is not a decimal number")
        if len(part) > 1 and part[0] == "0":
            raise InvalidAddressError(
                f"'{ip}': octet '{part}' has a leading zero (ambiguous octal notation)")
        octet = int(part)
        if octet > 255:
            raise InvalidAddressError(f"'{ip}': octet {octet} exceeds 255")
        value = (value << 8) | octet
    return value


def int_to_ip(value: int) -> str:
    if not isinstance(value, int) or value < 0 or value > MAX32:
        raise InvalidAddressError(f"{value!r} is outside the 32-bit IPv4 range")
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


# --------------------------------------------------------------------------- #
# Masks
# --------------------------------------------------------------------------- #
def _check_prefix(prefix: int) -> int:
    if isinstance(prefix, bool) or not isinstance(prefix, int) or not 0 <= prefix <= 32:
        raise InvalidPrefixError(f"Prefix length {prefix!r} must be an integer 0-32")
    return prefix


def prefix_to_mask(prefix: int) -> int:
    """/22 -> 0xFFFFFC00.  Shifting by 32 for /0 yields 0 after masking."""
    _check_prefix(prefix)
    return (MAX32 << (32 - prefix)) & MAX32


def wildcard(prefix: int) -> int:
    """Cisco wildcard (inverse) mask: bitwise NOT of the netmask, kept unsigned."""
    return ~prefix_to_mask(prefix) & MAX32


def mask_to_prefix(mask: int | str) -> int:
    """Netmask -> prefix length, rejecting non-contiguous masks like 255.0.255.0."""
    mask_int = ip_to_int(mask) if isinstance(mask, str) else mask
    if not 0 <= mask_int <= MAX32:
        raise InvalidPrefixError(f"Mask {mask!r} outside 32-bit range")
    host_bits = ~mask_int & MAX32
    # A valid mask's host part is 2^k - 1, i.e. all ones in the low k bits.
    if host_bits & (host_bits + 1):
        raise InvalidPrefixError(f"Mask {int_to_ip(mask_int)} has non-contiguous one bits")
    return 32 - host_bits.bit_length()


def mask_str(prefix: int) -> str:
    return int_to_ip(prefix_to_mask(prefix))


def wildcard_str(prefix: int) -> str:
    return int_to_ip(wildcard(prefix))


# --------------------------------------------------------------------------- #
# Network arithmetic
# --------------------------------------------------------------------------- #
def block_size(prefix: int) -> int:
    return 1 << (32 - _check_prefix(prefix))


def network_of(address: int, prefix: int) -> int:
    return address & prefix_to_mask(prefix)


def broadcast_of(network: int, prefix: int) -> int:
    return network | wildcard(prefix)


def usable_hosts(prefix: int) -> int:
    """Usable host addresses. /31 = 2 (RFC 3021 point-to-point), /32 = 1 (host route)."""
    _check_prefix(prefix)
    if prefix == 32:
        return 1
    if prefix == 31:
        return 2
    return block_size(prefix) - 2


def next_pow2(n: int) -> int:
    """Smallest power of two >= n (n >= 1)."""
    if n < 1:
        raise ValueError("next_pow2 requires n >= 1")
    return 1 << (n - 1).bit_length()


def prefix_for_block(size: int) -> int:
    """Block of 2^k addresses -> /(32-k)."""
    if size < 1 or size & (size - 1):
        raise ValueError(f"block size {size} is not a power of two")
    prefix = 32 - (size.bit_length() - 1)
    return _check_prefix(prefix)


def prefix_for_hosts(hosts: int, reserve_gateway: bool = True) -> int:
    """Smallest prefix whose *usable* range holds ``hosts`` (+1 gateway).

    needed = hosts + gateway + network id + broadcast, rounded up to 2^k.
    The naive ``32 - ceil(log2(hosts))`` forgets the +2/+1 overhead and puts
    a host on the broadcast address (AI audit log, instance #2).
    """
    if isinstance(hosts, bool) or not isinstance(hosts, int) or hosts < 1:
        raise InvalidPrefixError(f"Host count {hosts!r} must be a positive integer")
    needed = hosts + (1 if reserve_gateway else 0) + 2
    size = next_pow2(needed)
    if size > (1 << 32):
        raise InvalidPrefixError(f"{hosts} hosts cannot fit in IPv4 space")
    prefix = 32 - (size.bit_length() - 1)
    return min(prefix, 30)


def parse_cidr(cidr: str, strict: bool = True) -> tuple[int, int]:
    """'10.0.0.0/16' -> (network_int, 16). strict=True rejects host bits."""
    if not isinstance(cidr, str) or cidr.count("/") != 1:
        raise InvalidPrefixError(f"'{cidr}' is not in a.b.c.d/nn CIDR notation")
    addr_s, prefix_s = cidr.strip().split("/")
    if not (prefix_s.isascii() and prefix_s.isdigit()):
        raise InvalidPrefixError(f"'{cidr}': prefix '{prefix_s}' is not a number")
    prefix = _check_prefix(int(prefix_s))
    address = ip_to_int(addr_s)
    network = network_of(address, prefix)
    if strict and network != address:
        raise InvalidPrefixError(
            f"'{cidr}' has host bits set; the network address is "
            f"{int_to_ip(network)}/{prefix}")
    return network, prefix


def cidr_str(network: int, prefix: int) -> str:
    return f"{int_to_ip(network)}/{prefix}"


def overlaps(a_net: int, a_prefix: int, b_net: int, b_prefix: int) -> bool:
    a_end = broadcast_of(a_net, a_prefix)
    b_end = broadcast_of(b_net, b_prefix)
    return a_net <= b_end and b_net <= a_end


def contains(network: int, prefix: int, address: int) -> bool:
    return (address & prefix_to_mask(prefix)) == network


def is_rfc1918(network: int, prefix: int) -> bool:
    return any(prefix >= p and contains(n, p, network) for n, p in RFC1918)


def common_supernet(networks: list[tuple[int, int]]) -> tuple[int, int]:
    """Smallest single prefix covering every (network, prefix) given."""
    if not networks:
        raise ValueError("common_supernet needs at least one network")
    low = min(n for n, _ in networks)
    high = max(broadcast_of(n, p) for n, p in networks)
    diff = low ^ high
    prefix = 32 - diff.bit_length()
    return network_of(low, prefix), prefix
