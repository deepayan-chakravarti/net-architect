"""Orchestrator: Input -> L1/L2 media -> L3 VLSM & routing -> explainable export."""

from __future__ import annotations

from . import ipmath as ip
from . import configgen, media, packetflow, routing, topology
from .rationale import RationaleLog
from .validator import validate
from .vlsm import SubnetRequest, allocate_hierarchical

VERSION = "1.0.0"


def _build_requests(params: dict, links: list[dict]) -> tuple[dict, dict]:
    site_reqs: dict[str, list[SubnetRequest]] = {}
    external: dict[str, str] = {}
    for s in params["sites"]:
        reqs = []
        for v in s["vlans"]:
            meta = {"qos_class": v["qos_class"]} if v.get("qos_class") else {}
            reqs.append(SubnetRequest(v["name"], v["hosts"], "lan", s["name"],
                                      v.get("vlan_id"), v.get("role", "data"), meta))
        site_reqs[s["name"]] = reqs
        if s.get("cloud"):
            external[s["name"]] = s["vpc_cidr"]
    infra = []
    for link in links:
        if link["cloud"]:
            continue
        infra.append(SubnetRequest(f"P2P-{link['a']}-{link['b']}", 2, "p2p", "INFRA",
                                   meta={"link": link["id"]}))
    for s in params["sites"]:
        if not s.get("cloud"):
            infra.append(SubnetRequest(f"LO-{s['name']}", 1, "loopback", "INFRA"))
    site_reqs["INFRA"] = infra
    return site_reqs, external


def _verify(ctx: dict, gen: dict) -> list[dict]:
    """Packet-flow checks proving routes and ACLs behave as intended."""
    checks = []
    subs = ctx["addressing"].all_subnets()
    routes = [(s.network, s.prefix, f"{s.site}/{s.name}") for s in subs]
    for s in subs:
        if s.kind != "lan":
            continue
        probe = s.last_usable
        hit = packetflow.lpm_lookup(routes, probe)
        cands = packetflow.lpm_candidates(routes, probe)
        checks.append({"type": "lpm", "flow": f"dst {ip.int_to_ip(probe)}",
                       "expected": f"{s.site}/{s.name}", "result": hit[0] if hit else None,
                       "pass": hit is not None and hit[0] == f"{s.site}/{s.name}"
                       and len(cands) == 1})
    dns = ip.ip_to_int(ctx["params"]["dns_server"])
    internal = next((s for s in subs if s.role in ("data", "server") and s.kind == "lan"), None)
    for site, acls in gen["acls"].items():
        for vid, acl in acls["by_vlan"].items():
            src_sub = next(s for s in subs if s.site == site and s.vlan_id == vid)
            src = src_sub.host(5) if src_sub.usable >= 5 else src_sub.first_usable
            flows = [("udp", ip.ip_to_int("0.0.0.0"), ip.ip_to_int("255.255.255.255"), 67, 68,
                      "permit", "DHCP discover"),
                     ("udp", src, dns, 53, 40000, "permit", "DNS query"),
                     ("tcp", src, ip.ip_to_int("93.184.216.34"), 443, 40000,
                      "permit" if "GUEST" in acl.name else "deny", "Internet HTTPS")]
            if internal:
                flows.append(("tcp", src, internal.host(1), 445, 40000, "deny",
                              f"to internal {internal.site}/{internal.name} SMB"))
            cloud = [s for s in subs if s.site in {c["name"] for c in ctx["params"]["sites"]
                                                   if c.get("cloud")}]
            if "IOT" in acl.name and cloud:
                flows.append(("tcp", src, cloud[0].host(10), 8883, 40000, "permit",
                              "MQTT/TLS to cloud"))
                flows.append(("tcp", src, cloud[0].host(10), 22, 40000, "deny",
                              "SSH to cloud"))
            for proto, s_ip, d_ip, dport, sport, expect, label in flows:
                action, idx = acl.evaluate(proto, s_ip, d_ip, dport, sport)
                checks.append({"type": "acl", "acl": acl.name,
                               "flow": f"{label}: {proto} {ip.int_to_ip(s_ip)} -> "
                                       f"{ip.int_to_ip(d_ip)}:{dport}",
                               "expected": expect, "result": action,
                               "matched_entry": idx, "pass": action == expect})
    return checks


def plan(raw: dict) -> dict:
    """Run the full pipeline and return a JSON-serialisable plan."""
    params, warnings = validate(raw)
    log = RationaleLog()
    for w in warnings:
        log.warn("Input", "Parameter validation", w)

    log.add("Input", params["name"],
            f"{params['network_type']} profile, {len(params['sites'])} sites, "
            f"{len(params['links'])} links, root {params['root_prefix']}",
            f"Parameters validated: {sum(v['hosts'] for s in params['sites'] for v in s['vlans']):,}"
            f" hosts across {sum(len(s['vlans']) for s in params['sites'])} subnets, resiliency "
            f"'{params['resiliency']}'" + (f", latency budget {params['latency_budget_ms']} ms"
                                           if params["latency_budget_ms"] else "") + ".")

    cloud_names = {s["name"] for s in params["sites"] if s.get("cloud")}
    links = []
    for i, l in enumerate(params["links"], 1):
        link = dict(l)
        link["id"] = f"L{i}"
        link["cloud"] = l["a"] in cloud_names or l["b"] in cloud_names
        link["tunnel_id"] = i
        link["evc"] = configgen.EVC_BASE + i - 1
        links.append(link)
    params["links"] = links

    # ---- L1 media ----------------------------------------------------------- #
    media_out = {}
    for link in links:
        subject = f"{link['a']} <-> {link['b']}"
        dec = media.select_media(link["distance_m"], link["bandwidth_gbps"], link["media"],
                                 False, link["transport"], subject,
                                 params["optical_margin_db"], log)
        link["media_decision"] = dec
        media_out[link["id"]] = dec
    runs_out = []
    for s in params["sites"]:
        for run in s.get("cable_runs", []):
            subject = f"{s['name']} {run['name']}"
            dec = media.select_media(run["distance_m"], run["bandwidth_gbps"], run["media"],
                                     run["poe"], "fiber", subject, params["optical_margin_db"],
                                     log)
            runs_out.append(dec)

    # ---- L2 / topology ------------------------------------------------------ #
    l2 = topology.design_l2(params, log)

    # ---- L3 addressing ------------------------------------------------------ #
    site_reqs, external = _build_requests(params, links)
    addressing = allocate_hierarchical(params["root_prefix"], site_reqs, params["p2p_prefix"],
                                       log, external)
    infra = addressing.block("INFRA").allocation.subnets
    for link in links:
        if link["cloud"]:
            link["inside_net"] = ip.ip_to_int("169.254.10.0") + 4 * (link["tunnel_id"] - 1)
        else:
            link["subnet"] = next(s for s in infra if s.meta.get("link") == link["id"])
    if any(l["cloud"] for l in links):
        log.add("L3 VLSM", "Cloud tunnel inside addresses", "169.254.10.0/24 carved into /30s",
                "Cloud VPN gateways number the BGP-over-IPsec inside interfaces from the IPv4 "
                "link-local range; using it keeps tunnel addressing out of both the enterprise "
                "root and the VPC CIDR.", ["RFC 3927"])
    if params["network_type"] == "wan":
        log.add("L3 VLSM", "Internet underlay addresses", "203.0.113.0/24 /30 per site (lab)",
                "Public WAN addresses in the lab use the RFC 5737 documentation block so the "
                "configs never collide with real Internet space; replace with ISP-assigned "
                "addresses in production.", ["RFC 5737"])

    # ---- L3 routing --------------------------------------------------------- #
    route_plan = routing.select_routing(params, addressing, log)

    # ---- QoS / latency ------------------------------------------------------ #
    latency = topology.path_latency(params, media_out, log)
    qos = topology.plan_qos(params, log)

    # ---- configs ------------------------------------------------------------ #
    ctx = {"params": params, "addressing": addressing, "routing": route_plan, "l2": l2,
           "links": links, "qos": qos, "log": log}
    gen = configgen.generate(ctx)
    checks = _verify(ctx, gen)
    passed = sum(c["pass"] for c in checks)
    log.add("Verification", "Packet-flow simulation", f"{passed}/{len(checks)} checks passed",
            "Every LAN's last usable address was resolved by longest-prefix match to exactly one "
            "subnet (proves zero overlap), and representative flows (DHCP, DNS, Internet, "
            "lateral SMB, cloud MQTT/SSH) were walked through each generated ACL entry-by-entry "
            "using the same wildcard arithmetic the router applies.", [],
            {"passed": passed, "total": len(checks)})

    return {
        "version": VERSION,
        "meta": {"name": params["name"], "profile": params["profile"],
                 "network_type": params["network_type"], "resiliency": params["resiliency"],
                 "root_prefix": params["root_prefix"], "warnings": warnings},
        "topology": {"tier": l2["tier"], "sites": l2["sites"],
                     "access_switches_total": l2["access_switches_total"]},
        "media": {"links": [dict(media_out[l["id"]].to_dict(), id=l["id"], a=l["a"], b=l["b"],
                                 role=l["role"]) for l in links],
                  "cable_runs": [d.to_dict() for d in runs_out]},
        "addressing": addressing.to_dict(),
        "routing": route_plan,
        "latency": latency,
        "qos": qos,
        "acls": [acl.to_dict() for site in gen["acls"].values()
                 for acl in list(site["by_vlan"].values()) + site["qos"]] +
                ([next(iter(gen["acls"].values()))["vty"].to_dict()] if gen["acls"] else []),
        "configs": gen["configs"],
        "cabling": gen["cabling"],
        "verification": {"passed": passed, "total": len(checks), "checks": checks},
        "rationale": log.to_dicts(),
        "rationale_text": log.to_text(),
    }
