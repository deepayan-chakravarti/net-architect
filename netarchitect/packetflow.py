"""Structured ACLs and a tiny packet-flow simulator.

ACLs are built as data first, then rendered to Cisco IOS, so the exact same
entries can be *evaluated* against test packets.  This is how the engine (and
the AI audit log) proves a wildcard mask or an ACL order is correct: by
walking a packet through it, not by eyeballing the text.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ipmath as ip

PORT_NAMES = {53: "domain", 67: "bootps", 68: "bootpc", 22: "22", 443: "443", 8883: "8883"}


@dataclass
class Match:
    """Address match: network + wildcard.  any = 0.0.0.0 255.255.255.255."""
    network: int = 0
    wc: int = ip.MAX32

    @classmethod
    def any(cls) -> "Match":
        return cls(0, ip.MAX32)

    @classmethod
    def cidr(cls, network: int, prefix: int) -> "Match":
        return cls(network, ip.wildcard(prefix))

    @classmethod
    def host(cls, address: int) -> "Match":
        return cls(address, 0)

    def matches(self, address: int) -> bool:
        care = ~self.wc & ip.MAX32
        return (address & care) == (self.network & care)

    def ios(self) -> str:
        if self.wc == ip.MAX32:
            return "any"
        if self.wc == 0:
            return f"host {ip.int_to_ip(self.network)}"
        return f"{ip.int_to_ip(self.network)} {ip.int_to_ip(self.wc)}"


@dataclass
class ACE:
    action: str                    # permit | deny
    protocol: str = "ip"           # ip | tcp | udp | icmp
    src: Match = field(default_factory=Match.any)
    dst: Match = field(default_factory=Match.any)
    dst_port: int | None = None
    src_port: int | None = None
    log: bool = False
    remark: str = ""

    def matches(self, proto: str, src: int, dst: int, dport: int | None,
                sport: int | None = None) -> bool:
        if self.protocol != "ip" and self.protocol != proto:
            return False
        if not (self.src.matches(src) and self.dst.matches(dst)):
            return False
        if self.dst_port is not None and self.dst_port != dport:
            return False
        if self.src_port is not None and self.src_port != sport:
            return False
        return True

    def ios(self, standard: bool = False) -> str:
        if standard:
            return f" {self.action} {self.src.ios()}" + (" log" if self.log else "")
        parts = [f" {self.action} {self.protocol} {self.src.ios()}"]
        if self.src_port is not None:
            parts.append(f"eq {PORT_NAMES.get(self.src_port, self.src_port)}")
        parts.append(self.dst.ios())
        if self.dst_port is not None:
            parts.append(f"eq {PORT_NAMES.get(self.dst_port, self.dst_port)}")
        if self.log:
            parts.append("log")
        return " ".join(parts)


@dataclass
class ACL:
    name: str
    kind: str                      # standard | extended
    entries: list[ACE]
    purpose: str = ""

    def evaluate(self, proto: str, src: int, dst: int, dport: int | None = None,
                 sport: int | None = None) -> tuple[str, int | None]:
        """First match wins; implicit deny at the end (returns index None)."""
        for i, ace in enumerate(self.entries):
            if self.kind == "standard":
                if ace.src.matches(src):
                    return ace.action, i
            elif ace.matches(proto, src, dst, dport, sport):
                return ace.action, i
        return "deny", None

    def render(self) -> str:
        lines = [f"ip access-list {self.kind} {self.name}"]
        for ace in self.entries:
            if ace.remark:
                lines.append(f" remark {ace.remark}")
            lines.append(ace.ios(standard=self.kind == "standard"))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "purpose": self.purpose,
                "ios": self.render()}


def lpm_lookup(routes: list[tuple[int, int, str]], address: int) -> tuple[str, int] | None:
    """Longest-prefix match over (network, prefix, label). Returns (label, prefix)."""
    best = None
    for network, prefix, label in routes:
        if ip.contains(network, prefix, address) and (best is None or prefix > best[1]):
            best = (label, prefix)
    return best


def lpm_candidates(routes: list[tuple[int, int, str]], address: int) -> list[tuple[str, int]]:
    """Every route containing ``address`` - more than one at the same prefix = ambiguity."""
    return [(label, prefix) for network, prefix, label in routes
            if ip.contains(network, prefix, address)]
