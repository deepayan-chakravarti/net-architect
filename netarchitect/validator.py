"""Parameter Engine - validates and normalises preset / custom JSON input.

All problems are collected (not fail-fast) so a user editing custom JSON sees
every issue at once.  Hard problems raise :class:`ValidationError`; soft ones
are returned as warnings.
"""

from __future__ import annotations

import copy
import re

from . import ipmath as ip
from .errors import InvalidAddressError, ValidationError

NETWORK_TYPES = ("campus", "metro", "wan")
RESILIENCY = ("single", "redundant", "dual_homed")
MEDIA_PREFS = ("auto", "copper", "fiber")
TRANSPORTS = ("fiber", "evpl", "internet")
LINK_ROLES = ("primary", "secondary")
VLAN_ROLES = ("data", "voice", "wireless", "guest", "mgmt", "ap", "iot", "server")
RESERVED_VLANS = {1, 998, 999} | set(range(1002, 1006))
RESERVED_SITE_NAMES = {"INFRA", "ISP", "CARRIER"}
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,30}$")
MAX_DISTANCE_M = 20_037_000            # half Earth's circumference
LARGE_BROADCAST_DOMAIN = 1000

TOP_KEYS = {"name", "profile", "description", "network_type", "root_prefix", "p2p_prefix",
            "resiliency", "latency_budget_ms", "optical_margin_db", "growth_factor",
            "ports_per_switch", "bgp_asn", "hub", "sites", "links", "qos", "dns_server",
            "domain_name"}


def _num(value, positive=True) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > 0 if positive else value >= 0


def _distance_m(obj: dict, where: str, issues: list[str]) -> float | None:
    has_m, has_km = "distance_m" in obj, "distance_km" in obj
    if has_m and has_km:
        issues.append(f"{where}: give distance_m or distance_km, not both")
        return None
    if not (has_m or has_km):
        issues.append(f"{where}: distance_m or distance_km is required")
        return None
    raw = obj["distance_m"] if has_m else obj["distance_km"]
    if not _num(raw):
        issues.append(f"{where}: distance must be a positive number (got {raw!r})")
        return None
    meters = float(raw) if has_m else float(raw) * 1000.0
    if meters > MAX_DISTANCE_M:
        issues.append(f"{where}: {meters / 1000:,.0f} km exceeds half the Earth's circumference")
        return None
    return meters


def _connected(nodes: set[str], edges: list[tuple[str, str]]) -> bool:
    if not nodes:
        return True
    adj = {n: set() for n in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        for nxt in adj[stack.pop()] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return seen == nodes


def validate(raw: dict) -> tuple[dict, list[str]]:
    """Return (normalised_params, warnings) or raise ValidationError."""
    issues: list[str] = []
    warnings: list[str] = []
    if not isinstance(raw, dict):
        raise ValidationError(["top-level input must be a JSON object"])
    p = copy.deepcopy(raw)

    for key in sorted(set(p) - TOP_KEYS):
        warnings.append(f"unknown top-level key '{key}' ignored")

    if not isinstance(p.get("name"), str) or not p["name"].strip():
        issues.append("name: a non-empty string is required")
    p.setdefault("profile", "custom")
    if p.get("network_type") not in NETWORK_TYPES:
        issues.append(f"network_type must be one of {NETWORK_TYPES} (got {p.get('network_type')!r})")

    # ---- addressing --------------------------------------------------------- #
    root = None
    try:
        root = ip.parse_cidr(p.get("root_prefix", ""))
        if not 8 <= root[1] <= 30:
            issues.append(f"root_prefix /{root[1]} must be between /8 and /30")
        elif not ip.is_rfc1918(*root):
            warnings.append(f"root_prefix {p['root_prefix']} is not RFC 1918 private space")
    except InvalidAddressError as exc:
        issues.append(f"root_prefix: {exc.message}")
        root = None

    p.setdefault("p2p_prefix", 30)
    if p["p2p_prefix"] not in (30, 31):
        issues.append("p2p_prefix must be 30 or 31")

    p.setdefault("resiliency", "single")
    if p["resiliency"] not in RESILIENCY:
        issues.append(f"resiliency must be one of {RESILIENCY}")

    for key, default, low, high in (("optical_margin_db", 1.0, 0, 10),
                                    ("growth_factor", 0.2, 0, 2),
                                    ("ports_per_switch", 48, 8, 96)):
        p.setdefault(key, default)
        val = p[key]
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not low <= val <= high:
            issues.append(f"{key} must be a number between {low} and {high} (got {val!r})")
    if "latency_budget_ms" in p and p["latency_budget_ms"] is not None and \
            not _num(p["latency_budget_ms"]):
        issues.append("latency_budget_ms must be a positive number")
    p.setdefault("latency_budget_ms", None)
    if "bgp_asn" in p and not (isinstance(p["bgp_asn"], int) and 1 <= p["bgp_asn"] <= 4294967294):
        issues.append("bgp_asn must be an integer 1-4294967294")
    p.setdefault("dns_server", "1.1.1.1")
    try:
        ip.ip_to_int(p["dns_server"])
    except InvalidAddressError as exc:
        issues.append(f"dns_server: {exc.message}")
    p.setdefault("domain_name", "netarch.lab")

    # ---- sites -------------------------------------------------------------- #
    sites = p.get("sites")
    names: set[str] = set()
    if not isinstance(sites, list) or not sites:
        issues.append("sites: at least one site is required")
        sites = []
    for si, site in enumerate(sites):
        where = f"sites[{si}]"
        if not isinstance(site, dict):
            issues.append(f"{where}: must be an object")
            continue
        name = site.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            issues.append(f"{where}: name {name!r} must start with a letter and use only "
                          f"letters, digits, '-' or '_' (max 31 chars; used in IOS hostnames)")
        elif name.upper() in RESERVED_SITE_NAMES:
            issues.append(f"{where}: site name '{name}' is reserved by the engine")
        elif name in names:
            issues.append(f"{where}: duplicate site name '{name}'")
        else:
            names.add(name)
            where = f"site {name}"
        site.setdefault("cloud", False)
        site.setdefault("aps", 0)
        site.setdefault("cable_runs", [])
        if not isinstance(site["aps"], int) or isinstance(site["aps"], bool) or site["aps"] < 0:
            issues.append(f"{where}: aps must be a non-negative integer")
        if site["cloud"]:
            if p.get("network_type") != "wan":
                issues.append(f"{where}: cloud sites are only supported with network_type 'wan'")
            try:
                vnet = ip.parse_cidr(site.get("vpc_cidr", ""))
                if root and ip.overlaps(*vnet, *root):
                    issues.append(f"{where}: vpc_cidr {site['vpc_cidr']} overlaps root_prefix "
                                  f"{p['root_prefix']}")
            except InvalidAddressError as exc:
                issues.append(f"{where}: cloud site needs a valid vpc_cidr ({exc.message})")
            if "asn" in site and not (isinstance(site["asn"], int) and
                                      1 <= site["asn"] <= 4294967294):
                issues.append(f"{where}: asn must be an integer 1-4294967294")
        vlans = site.get("vlans")
        if not isinstance(vlans, list) or not vlans:
            issues.append(f"{where}: at least one VLAN/subnet is required")
            vlans = []
        vids: set[int] = set()
        vnames: set[str] = set()
        for vi, vlan in enumerate(vlans):
            vw = f"{where} vlans[{vi}]"
            if not isinstance(vlan, dict):
                issues.append(f"{vw}: must be an object")
                continue
            vname = vlan.get("name")
            if not isinstance(vname, str) or not NAME_RE.match(vname):
                issues.append(f"{vw}: invalid VLAN name {vname!r}")
            elif vname in vnames:
                issues.append(f"{vw}: duplicate VLAN name '{vname}' in {where}")
            else:
                vnames.add(vname)
                vw = f"{where} VLAN {vname}"
            hosts = vlan.get("hosts")
            if isinstance(hosts, bool) or not isinstance(hosts, int) or hosts < 1:
                issues.append(f"{vw}: hosts must be a positive integer (got {hosts!r})")
            elif hosts > LARGE_BROADCAST_DOMAIN and not site["cloud"]:
                warnings.append(f"{vw}: {hosts} hosts in one broadcast domain; consider "
                                f"splitting (ARP/broadcast load, STP blast radius)")
            vid = vlan.get("vlan_id")
            if not site["cloud"]:
                if isinstance(vid, bool) or not isinstance(vid, int) or not 2 <= vid <= 4094:
                    issues.append(f"{vw}: vlan_id must be an integer 2-4094 (got {vid!r})")
                elif vid in RESERVED_VLANS:
                    issues.append(f"{vw}: vlan_id {vid} is reserved (1 default, 998 black-hole, "
                                  f"999 native, 1002-1005 legacy)")
                elif vid in vids:
                    issues.append(f"{vw}: duplicate vlan_id {vid} in {where}")
                else:
                    vids.add(vid)
            vlan.setdefault("role", "data")
            if vlan["role"] not in VLAN_ROLES:
                issues.append(f"{vw}: role must be one of {VLAN_ROLES}")
        if not site["cloud"] and vlans and not any(v.get("role") == "mgmt" for v in vlans
                                                   if isinstance(v, dict)):
            warnings.append(f"{where}: no 'mgmt' VLAN; VTY access ACL will fall back to the "
                            f"first subnet")
        for ri, run in enumerate(site["cable_runs"]):
            rw = f"{where} cable_runs[{ri}]"
            if not isinstance(run, dict):
                issues.append(f"{rw}: must be an object")
                continue
            run["distance_m"] = _distance_m(run, rw, issues)
            run.pop("distance_km", None)
            run.setdefault("name", f"run-{ri + 1}")
            run.setdefault("bandwidth_gbps", 10)
            run.setdefault("media", "auto")
            run.setdefault("poe", False)
            if run["media"] not in MEDIA_PREFS:
                issues.append(f"{rw}: media must be one of {MEDIA_PREFS}")
            if not _num(run["bandwidth_gbps"]) or run["bandwidth_gbps"] > 100:
                issues.append(f"{rw}: bandwidth_gbps must be > 0 and <= 100")

    # ---- links -------------------------------------------------------------- #
    links = p.get("links", [])
    if not isinstance(links, list):
        issues.append("links must be a list")
        links = []
    p["links"] = links
    edges = []
    seen_pairs = set()
    for li, link in enumerate(links):
        lw = f"links[{li}]"
        if not isinstance(link, dict):
            issues.append(f"{lw}: must be an object")
            continue
        a, b = link.get("a"), link.get("b")
        if a not in names or b not in names:
            issues.append(f"{lw}: endpoints {a!r} / {b!r} must reference defined sites")
        elif a == b:
            issues.append(f"{lw}: a link cannot connect site '{a}' to itself")
        else:
            lw = f"link {a}<->{b}"
            pair = frozenset((a, b))
            if pair in seen_pairs:
                issues.append(f"{lw}: duplicate link (use bandwidth_gbps for capacity)")
            seen_pairs.add(pair)
            edges.append((a, b))
        link["distance_m"] = _distance_m(link, lw, issues)
        link.pop("distance_km", None)
        link.setdefault("bandwidth_gbps", 10)
        link.setdefault("media", "auto")
        link.setdefault("transport", "fiber")
        link.setdefault("role", "primary")
        if link["media"] not in MEDIA_PREFS:
            issues.append(f"{lw}: media must be one of {MEDIA_PREFS}")
        if link["transport"] not in TRANSPORTS:
            issues.append(f"{lw}: transport must be one of {TRANSPORTS}")
        if link["role"] not in LINK_ROLES:
            issues.append(f"{lw}: role must be one of {LINK_ROLES}")
        if not _num(link["bandwidth_gbps"]) or link["bandwidth_gbps"] > 100:
            issues.append(f"{lw}: bandwidth_gbps must be > 0 and <= 100")
        if link["transport"] == "internet" and link["media"] == "copper":
            issues.append(f"{lw}: copper media cannot be requested for an Internet transport")
        if p.get("network_type") == "wan" and link["transport"] != "internet":
            issues.append(f"{lw}: network_type 'wan' links must use transport 'internet' "
                          f"(IPsec overlay)")
        if p.get("network_type") != "wan" and link["transport"] == "internet":
            issues.append(f"{lw}: transport 'internet' requires network_type 'wan'")

    # ---- topology / resiliency --------------------------------------------- #
    if len(names) > 1 and not _connected(names, edges):
        issues.append("topology: not every site is reachable - the link graph is disconnected")
    hub = p.get("hub")
    if hub is not None and hub not in names:
        issues.append(f"hub '{hub}' is not a defined site")
    if p["resiliency"] in ("redundant", "dual_homed") and len(names) > 1 and \
            _connected(names, edges):
        for e in edges:
            rest = list(edges)
            rest.remove(e)
            if not _connected(names, rest):
                issues.append(f"resiliency '{p['resiliency']}': link {e[0]}<->{e[1]} is a single "
                              f"point of failure (removing it partitions the network)")
        if p["resiliency"] == "dual_homed":
            degree = {n: 0 for n in names}
            for a, b in edges:
                degree[a] += 1
                degree[b] += 1
            for n, d in degree.items():
                if d < 2:
                    issues.append(f"resiliency 'dual_homed': site {n} has {d} uplink(s); "
                                  f"at least 2 diverse uplinks are required")

    # ---- QoS ---------------------------------------------------------------- #
    qos = p.get("qos")
    if qos is not None:
        classes = qos.get("classes") if isinstance(qos, dict) else None
        if not isinstance(classes, list) or not classes:
            issues.append("qos.classes must be a non-empty list")
        else:
            total = 0
            for ci, c in enumerate(classes):
                if not isinstance(c, dict) or not isinstance(c.get("name"), str) or \
                        not NAME_RE.match(c["name"]):
                    issues.append(f"qos.classes[{ci}]: invalid class")
                    continue
                if not isinstance(c.get("dscp"), str):
                    issues.append(f"qos class {c['name']}: dscp name required (e.g. 'ef')")
                pct = c.get("percent")
                if not _num(pct) or pct > 100:
                    issues.append(f"qos class {c['name']}: percent must be 1-100")
                else:
                    total += pct
                if c.get("priority") and _num(pct) and pct > 33:
                    warnings.append(f"qos class {c['name']}: priority queue > 33% can starve "
                                    f"other classes (Cisco/RFC 4594 guidance)")
            if total > 75:
                issues.append(f"qos: reserved bandwidth {total}% exceeds the 75% max-reserved "
                              f"default (leave room for routing protocol & default class)")

    # ---- QoS class references -------------------------------------------------
    if isinstance(qos, dict) and isinstance(qos.get("classes"), list):
        known = {c.get("name") for c in qos["classes"] if isinstance(c, dict)}
    elif p.get("network_type") == "metro":
        known = {"REALTIME", "TRADING", "MGMT"}
    else:
        known = set()
    for site in sites:
        if not isinstance(site, dict):
            continue
        for vlan in site.get("vlans") or []:
            if isinstance(vlan, dict) and vlan.get("qos_class") is not None and \
                    vlan["qos_class"] not in known:
                issues.append(f"site {site.get('name')} VLAN {vlan.get('name')}: qos_class "
                              f"'{vlan['qos_class']}' is not a defined QoS class "
                              f"{sorted(known) or '(no QoS policy configured)'}")

    if issues:
        raise ValidationError(issues, warnings)
    return p, warnings
