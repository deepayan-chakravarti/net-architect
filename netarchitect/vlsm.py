"""L3 VLSM Engine - bitwise subnet allocator.

Algorithm
---------
1. Convert every request to a power-of-two block:
     LAN      : hosts + 1 gateway + network id + broadcast -> next 2^k
     p2p      : /30 (or /31 per RFC 3021 when p2p_prefix=31)
     loopback : /32
2. Sort blocks largest-first (stable, so equal blocks keep input order).
3. Walk a cursor through the parent prefix.  Each block's network address is
   the cursor rounded *up* to a multiple of the block size:
       aligned = (cursor + size - 1) & ~(size - 1)
   Because blocks are sorted descending and every size is a power of two,
   the cursor is always already aligned, so the packing has zero gaps and
   zero overlap ("buddy" packing).  The rounding is kept as a safety net.
4. If the next block would pass the parent's broadcast address, raise
   AddressSpaceExhaustedError with the minimum prefix that *would* fit.

``allocate_hierarchical`` runs the same packer twice: first it carves one
contiguous block per site out of the root (so each site can be summarised
by a single route at the ABR), then it packs each site's subnets inside its
own block.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ipmath as ip
from .errors import AddressSpaceExhaustedError
from .rationale import RationaleLog


@dataclass
class SubnetRequest:
    name: str
    hosts: int
    kind: str = "lan"              # lan | p2p | loopback | block
    site: str = ""
    vlan_id: int | None = None
    role: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class Subnet:
    name: str
    site: str
    kind: str
    hosts_requested: int
    network: int
    prefix: int
    vlan_id: int | None = None
    role: str = ""
    meta: dict = field(default_factory=dict)

    # ---- derived values (all bitwise) ---------------------------------------
    @property
    def size(self) -> int:
        return ip.block_size(self.prefix)

    @property
    def broadcast(self) -> int:
        return ip.broadcast_of(self.network, self.prefix)

    @property
    def mask(self) -> int:
        return ip.prefix_to_mask(self.prefix)

    @property
    def wildcard(self) -> int:
        return ip.wildcard(self.prefix)

    @property
    def usable(self) -> int:
        return ip.usable_hosts(self.prefix)

    @property
    def first_usable(self) -> int:
        return self.network if self.prefix >= 31 else self.network + 1

    @property
    def last_usable(self) -> int:
        return self.broadcast if self.prefix >= 31 else self.broadcast - 1

    @property
    def gateway(self) -> int | None:
        return self.first_usable if self.kind == "lan" else None

    @property
    def utilization(self) -> float:
        demand = self.hosts_requested + (1 if self.kind == "lan" else 0)
        return demand / self.usable if self.usable else 0.0

    @property
    def cidr(self) -> str:
        return ip.cidr_str(self.network, self.prefix)

    def host(self, n: int) -> int:
        """n-th usable address (1-based)."""
        addr = self.first_usable + n - 1
        if addr > self.last_usable:
            raise IndexError(f"{self.cidr} has no host #{n}")
        return addr

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "site": self.site,
            "kind": self.kind,
            "role": self.role,
            "vlan_id": self.vlan_id,
            "hosts_requested": self.hosts_requested,
            "cidr": self.cidr,
            "network": ip.int_to_ip(self.network),
            "prefix": self.prefix,
            "mask": ip.int_to_ip(self.mask),
            "wildcard": ip.int_to_ip(self.wildcard),
            "broadcast": ip.int_to_ip(self.broadcast),
            "gateway": ip.int_to_ip(self.gateway) if self.gateway is not None else None,
            "first_usable": ip.int_to_ip(self.first_usable),
            "last_usable": ip.int_to_ip(self.last_usable),
            "usable": self.usable,
            "block_size": self.size,
            "utilization_pct": round(self.utilization * 100, 1),
        }


def block_for(req: SubnetRequest, p2p_prefix: int = 30) -> int:
    """Return the prefix length required for one request."""
    if req.kind == "p2p":
        return p2p_prefix
    if req.kind == "loopback":
        return 32
    if req.kind == "block":            # pre-sized block: hosts == size
        return ip.prefix_for_block(req.hosts)
    return ip.prefix_for_hosts(req.hosts, reserve_gateway=True)


def _sizing_reason(req: SubnetRequest, prefix: int, p2p_prefix: int) -> str:
    if req.kind == "p2p":
        return ("point-to-point link: /31 per RFC 3021 (no network/broadcast waste)"
                if p2p_prefix == 31 else
                "point-to-point link: /30 gives exactly 2 usable addresses")
    if req.kind == "loopback":
        return "router loopback: /32 host route (stable OSPF/BGP router-id)"
    needed = req.hosts + 3
    k = 32 - prefix
    smaller = (1 << (k - 1)) - 2 if k > 1 else 0
    return (f"{req.hosts} hosts + 1 gateway + network + broadcast = {needed} addresses -> "
            f"2^{k} = {1 << k} block (/{prefix}); /{prefix + 1} would offer only {smaller} "
            f"usable < {req.hosts + 1} required")


def minimum_prefix_for(total_addresses: int) -> int | None:
    size = ip.next_pow2(max(total_addresses, 1))
    if size > 1 << 32:
        return None
    return 32 - (size.bit_length() - 1)


def _pack(root_net: int, root_prefix: int, sized: list[tuple[int, int]],
          label: str) -> list[tuple[int, int, int]]:
    """Pack (index, prefix) items into the root. Returns (index, network, prefix)."""
    root_size = ip.block_size(root_prefix)
    root_end = root_net + root_size - 1
    total = sum(ip.block_size(p) for _, p in sized)
    if total > root_size:
        need = minimum_prefix_for(total)
        raise AddressSpaceExhaustedError(
            f"Address space exhausted in {label} {ip.cidr_str(root_net, root_prefix)}: the "
            f"requested blocks need {total:,} addresses but only {root_size:,} exist "
            f"(short by {total - root_size:,}). Minimum parent prefix: "
            f"/{need}" + ("" if need is None else
                          f" (e.g. {ip.cidr_str(ip.network_of(root_net, need), need)})") + ".",
            required=total, available=root_size,
            root=ip.cidr_str(root_net, root_prefix), minimum_prefix=need)
    order = sorted(sized, key=lambda item: (item[1], item[0]))   # small prefix = big block first
    cursor = root_net
    placed = []
    for index, prefix in order:
        size = ip.block_size(prefix)
        aligned = (cursor + size - 1) & ~(size - 1) & ip.MAX32
        if aligned + size - 1 > root_end:          # pragma: no cover - guarded above
            raise AddressSpaceExhaustedError(
                f"Address space exhausted in {label}", required=total, available=root_size,
                root=ip.cidr_str(root_net, root_prefix), minimum_prefix=minimum_prefix_for(total))
        placed.append((index, aligned, prefix))
        cursor = aligned + size
    return placed


@dataclass
class Allocation:
    root: str
    root_network: int
    root_prefix: int
    subnets: list[Subnet]

    @property
    def allocated(self) -> int:
        return sum(s.size for s in self.subnets)

    @property
    def requested_hosts(self) -> int:
        return sum(s.hosts_requested for s in self.subnets)

    def to_dict(self) -> dict:
        size = ip.block_size(self.root_prefix)
        return {
            "root": self.root,
            "root_size": size,
            "allocated": self.allocated,
            "free": size - self.allocated,
            "root_utilization_pct": round(self.allocated / size * 100, 2),
            "subnets": [s.to_dict() for s in self.subnets],
        }


def allocate(root_cidr: str, requests: list[SubnetRequest], p2p_prefix: int = 30,
             log: RationaleLog | None = None, label: str = "root") -> Allocation:
    """Flat VLSM allocation of ``requests`` inside ``root_cidr``."""
    root_net, root_prefix = ip.parse_cidr(root_cidr)
    prefixes = []
    for i, req in enumerate(requests):
        if isinstance(req.hosts, bool) or not isinstance(req.hosts, int) or req.hosts < 1:
            raise ValueError(f"Subnet '{req.name}': host count must be a positive integer")
        prefixes.append((i, block_for(req, p2p_prefix)))
    for i, prefix in prefixes:
        if prefix < root_prefix:
            req = requests[i]
            raise AddressSpaceExhaustedError(
                f"Subnet '{req.name}' needs a /{prefix} ({ip.block_size(prefix):,} addresses) "
                f"which is larger than the whole {label} {root_cidr}.",
                required=ip.block_size(prefix), available=ip.block_size(root_prefix),
                root=root_cidr, minimum_prefix=prefix)
    placed = _pack(root_net, root_prefix, prefixes, label)
    subnets = []
    for index, network, prefix in placed:
        req = requests[index]
        sub = Subnet(req.name, req.site, req.kind, req.hosts, network, prefix,
                     req.vlan_id, req.role, dict(req.meta))
        subnets.append(sub)
        if log is not None and req.kind == "lan":
            log.add("L3 VLSM", f"{req.site + ' ' if req.site else ''}{req.name}",
                    f"{sub.cidr} (gw {ip.int_to_ip(sub.gateway)}, bcast "
                    f"{ip.int_to_ip(sub.broadcast)})",
                    f"{_sizing_reason(req, prefix, p2p_prefix)}. Utilisation "
                    f"{sub.utilization * 100:.1f}% of {sub.usable} usable. Network address is a "
                    f"multiple of the {sub.size}-address block size, so it is bit-aligned "
                    f"(host bits all zero).",
                    ["RFC 950", "RFC 1878", "RFC 4632"], sub.to_dict())
    verify_no_overlap(subnets)
    return Allocation(root_cidr, root_net, root_prefix, subnets)


def verify_no_overlap(subnets: list[Subnet]) -> None:
    """Sort by network and assert each block ends before the next begins."""
    ordered = sorted(subnets, key=lambda s: s.network)
    for a, b in zip(ordered, ordered[1:]):
        if a.broadcast >= b.network:
            raise AssertionError(f"VLSM overlap detected: {a.name} {a.cidr} and {b.name} {b.cidr}")
    for s in subnets:
        if s.network & s.wildcard:
            raise AssertionError(f"{s.name} {s.cidr} is not aligned to its prefix")


# --------------------------------------------------------------------------- #
# Hierarchical allocation (per-site blocks -> summarisable)
# --------------------------------------------------------------------------- #
@dataclass
class SiteBlock:
    site: str
    network: int
    prefix: int
    allocation: Allocation

    @property
    def cidr(self) -> str:
        return ip.cidr_str(self.network, self.prefix)

    def to_dict(self) -> dict:
        d = self.allocation.to_dict()
        d.update({"site": self.site, "block": self.cidr,
                  "mask": ip.mask_str(self.prefix), "wildcard": ip.wildcard_str(self.prefix)})
        return d


@dataclass
class Addressing:
    root: str
    root_network: int
    root_prefix: int
    blocks: list[SiteBlock]
    flsm_equivalent: int = 0

    def all_subnets(self) -> list[Subnet]:
        return [s for b in self.blocks for s in b.allocation.subnets]

    def block(self, site: str) -> SiteBlock:
        return next(b for b in self.blocks if b.site == site)

    def subnet(self, site: str, name: str) -> Subnet:
        return next(s for s in self.block(site).allocation.subnets if s.name == name)

    def to_dict(self) -> dict:
        root_size = ip.block_size(self.root_prefix)
        in_root = [b for b in self.blocks if ip.contains(self.root_network, self.root_prefix,
                                                          b.network)]
        allocated = sum(ip.block_size(b.prefix) for b in in_root)
        subnets = self.all_subnets()
        demand = sum(s.hosts_requested + (1 if s.kind == "lan" else 0) for s in subnets)
        sized = sum(s.size for s in subnets)
        return {
            "root": self.root,
            "root_size": root_size,
            "site_blocks_allocated": allocated,
            "root_utilization_pct": round(allocated / root_size * 100, 2),
            "subnet_count": len(subnets),
            "address_efficiency_pct": round(demand / sized * 100, 2) if sized else 0,
            "flsm_equivalent_addresses": self.flsm_equivalent,
            "vlsm_addresses": sized,
            "blocks": [b.to_dict() for b in self.blocks],
        }


def allocate_hierarchical(root_cidr: str, site_requests: dict[str, list[SubnetRequest]],
                          p2p_prefix: int = 30, log: RationaleLog | None = None,
                          external_roots: dict[str, str] | None = None) -> Addressing:
    """Allocate one summarisable block per site, then VLSM inside each block.

    ``external_roots`` maps a site to its own pre-assigned prefix (e.g. a cloud
    VPC CIDR) that is allocated independently of the enterprise root.
    """
    external_roots = external_roots or {}
    root_net, root_prefix = ip.parse_cidr(root_cidr)
    internal = [s for s in site_requests if s not in external_roots]

    sizes = []
    for i, site in enumerate(internal):
        reqs = site_requests[site]
        total = sum(ip.block_size(block_for(r, p2p_prefix)) for r in reqs)
        sizes.append((i, ip.prefix_for_block(ip.next_pow2(total))))
    placed = _pack(root_net, root_prefix, sizes, "root (per-site summary blocks)")

    blocks = []
    for index, network, prefix in sorted(placed, key=lambda p: p[1]):
        site = internal[index]
        alloc = allocate(ip.cidr_str(network, prefix), site_requests[site], p2p_prefix,
                         log, label=f"site block {site}")
        blocks.append(SiteBlock(site, network, prefix, alloc))
        if log is not None:
            demand = sum(ip.block_size(block_for(r, p2p_prefix)) for r in site_requests[site])
            log.add("L3 VLSM", f"Site block {site}", ip.cidr_str(network, prefix),
                    f"Sum of {site}'s subnet blocks = {demand:,} addresses, rounded up to the "
                    f"next power of two ({ip.block_size(prefix):,}) so the whole site is one "
                    f"bit-aligned prefix /{prefix}. This lets the site be advertised as a single "
                    f"summary route (wildcard {ip.wildcard_str(prefix)}).",
                    ["RFC 4632 (CIDR aggregation)"],
                    {"block": ip.cidr_str(network, prefix), "demand": demand})

    for site, ext in external_roots.items():
        alloc = allocate(ext, site_requests[site], p2p_prefix, log, label=f"external {site}")
        net, pre = ip.parse_cidr(ext)
        blocks.append(SiteBlock(site, net, pre, alloc))
        if log is not None:
            log.add("L3 VLSM", f"Site block {site}", ext,
                    f"{site} keeps its own provider-assigned prefix {ext}, allocated outside "
                    f"the enterprise root {root_cidr} so cloud and on-prem routes never overlap "
                    f"and each side can be summarised independently.", ["RFC 4632"])

    all_subs = [s for b in blocks for s in b.allocation.subnets]
    verify_no_overlap(all_subs)
    lan = [s for s in all_subs if s.kind == "lan"]
    flsm = max((s.size for s in lan), default=0) * len(lan) + sum(
        s.size for s in all_subs if s.kind != "lan")
    addressing = Addressing(root_cidr, root_net, root_prefix, blocks, flsm)
    if log is not None:
        d = addressing.to_dict()
        log.add("L3 VLSM", "Root utilisation", f"{d['root_utilization_pct']}% of {root_cidr}",
                f"{d['subnet_count']} subnets packed largest-first with zero overlap (verified by "
                f"sorting on network address and checking each broadcast < next network). Host "
                f"demand fills {d['address_efficiency_pct']}% of allocated addresses. A fixed-"
                f"length design using the largest LAN block everywhere would consume "
                f"{flsm:,} addresses vs {d['vlsm_addresses']:,} with VLSM.",
                ["RFC 1878", "RFC 4632"],
                {k: d[k] for k in ("root_utilization_pct", "address_efficiency_pct",
                                   "flsm_equivalent_addresses", "vlsm_addresses")})
    return addressing
