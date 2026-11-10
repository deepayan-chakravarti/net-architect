"""Topology tier, L2 design, PoE budget, path latency and QoS decisions."""

from __future__ import annotations

import heapq
import math

from .rationale import RationaleLog

POE_W = {"ap": 30.0, "voice": 15.4}          # 802.3at Class 4 AP, 802.3af phone (PSE side)
PORT_ROLES = ("data", "iot", "server", "ap")  # roles that consume a physical access port
PER_HOP_MS = 0.05                             # store-and-forward + lookup budget per router

DEFAULT_QOS = {
    "classes": [
        {"name": "REALTIME", "dscp": "ef", "percent": 30, "priority": True},
        {"name": "TRADING", "dscp": "af41", "percent": 30, "priority": False},
        {"name": "MGMT", "dscp": "cs6", "percent": 5, "priority": False},
    ]
}


def design_l2(params: dict, log: RationaleLog) -> dict:
    """Access-switch sizing, PoE budget, STP/VLAN/trunk policy, topology tier."""
    ntype = params["network_type"]
    growth = params["growth_factor"]
    ports = params["ports_per_switch"]
    sites_out = {}
    for site in params["sites"]:
        if site.get("cloud"):
            continue
        vlans = site["vlans"]
        port_hosts = sum(v["hosts"] for v in vlans if v["role"] in PORT_ROLES)
        aps = site.get("aps", 0)
        ap_vlan = sum(v["hosts"] for v in vlans if v["role"] == "ap")
        port_demand = port_hosts if ap_vlan else port_hosts + aps
        voice = sum(v["hosts"] for v in vlans if v["role"] == "voice")
        wireless = sum(v["hosts"] for v in vlans if v["role"] in ("wireless", "guest"))
        switches = max(1, math.ceil(port_demand * (1 + growth) / ports))
        poe = aps * POE_W["ap"] + voice * POE_W["voice"]
        sites_out[site["name"]] = {
            "port_demand": port_demand, "access_switches": switches, "aps": aps,
            "voice_phones": voice, "wireless_clients": wireless,
            "poe_total_w": round(poe, 1),
            "poe_per_switch_w": round(poe / switches, 1),
        }
        log.add("L2 Switching", f"{site['name']} access layer",
                f"{switches} x {ports}-port access switch(es)",
                f"Ports are consumed by wired data/IoT/server endpoints and APs ({port_demand})"
                + (f"; {voice} IP phones share the PC's port via the voice VLAN" if voice else "")
                + (f"; {wireless} wireless clients attach through {aps} APs" if wireless else "")
                + f", so only port-consuming endpoints are counted. "
                f"ceil({port_demand} x (1 + {growth:.0%} growth) / {ports}) = {switches}.",
                ["IEEE 802.1Q (voice VLAN)"], sites_out[site["name"]])
        if poe:
            log.add("L2 Switching", f"{site['name']} PoE budget",
                    f"{poe:,.0f} W total, ~{poe / switches:,.0f} W per switch",
                    f"{aps} APs x 30 W (802.3at Class 4 at the PSE) + {voice} phones x 15.4 W "
                    f"(802.3af) = {poe:,.0f} W. Specify PoE+ access switches with at least "
                    f"{math.ceil(poe / switches / 50) * 50} W PoE budget each (rounded up to the "
                    f"next 50 W PSU tier).", ["IEEE 802.3at", "IEEE 802.3af"])

    log.add("L2 Switching", "Spanning tree", "Rapid PVST+ (802.1w per VLAN), root at distribution",
            "RSTP converges in under a second via proposal/agreement instead of 802.1D's "
            "30-50 s listening/learning timers. The distribution switch is pinned as root "
            "(priority 4096) so the L2 forwarding path matches the L3 gateway, and PortFast + "
            "BPDU Guard on edge ports stop a rogue switch from triggering a topology change.",
            ["IEEE 802.1w", "IEEE 802.1D-2004"])
    log.add("L2 Switching", "Trunk policy",
            "802.1Q trunks, explicit allowed list, native VLAN 999, DTP off",
            "Trunks carry only the VLANs that exist at that site (no 'allowed vlan all'), the "
            "native VLAN is moved to unused VLAN 999 and DTP is disabled with 'nonegotiate'. "
            "This blocks double-tagging VLAN hopping and switch-spoofing attacks; unused ports "
            "are shut down in black-hole VLAN 998.", ["IEEE 802.1Q", "Cisco SAFE"])

    # ---- tier --------------------------------------------------------------- #
    non_cloud = [s for s in params["sites"] if not s.get("cloud")]
    total_sw = sum(s["access_switches"] for s in sites_out.values())
    if ntype == "campus":
        if total_sw <= 8:
            tier = "Two-tier collapsed core"
            why = (f"only {total_sw} access switches across {len(non_cloud)} building(s): each "
                   f"building's L3 switch can act as collapsed core/distribution, and a separate "
                   f"core layer would add cost and latency without improving scale")
        else:
            tier = "Three-tier hierarchical (core / distribution / access)"
            why = (f"{len(non_cloud)} buildings and {total_sw} access switches: each building "
                   f"gets an L3 distribution switch (failure-domain + STP boundary), and "
                   f"inter-building fibre terminates on a routed core, so no VLAN spans buildings")
    elif ntype == "metro":
        tier = ("Dual-homed hub-and-spoke over carrier EVPL" if params["resiliency"] ==
                "dual_homed" else "Hub-and-spoke over carrier EVPL")
        why = ("every remote site has diverse circuits to two hubs so the loss of one circuit "
               "or one hub never isolates a site" if params["resiliency"] == "dual_homed"
               else "remote sites home to the hub over point-to-point EVCs")
    else:
        tier = "Hub-and-spoke IPsec overlay with regional site LANs"
        why = ("sites are continents apart, so each has a collapsed site LAN and an edge router "
               "that builds encrypted GRE tunnels across the Internet to the hub (and backup "
               "peers); routing hierarchy follows the tunnel hierarchy")
    log.add("Topology", "Topology tier", tier, f"Chosen because {why}.",
            ["Cisco Enterprise Campus design guide"] if ntype == "campus" else [],
            {"access_switches_total": total_sw})
    return {"tier": tier, "sites": sites_out, "access_switches_total": total_sw}


def path_latency(params: dict, media: dict, log: RationaleLog) -> dict:
    """Dijkstra on one-way latency between every pair of sites."""
    adj: dict[str, list[tuple[str, float, str]]] = {s["name"]: [] for s in params["sites"]}
    for link in params["links"]:
        dec = media[link["id"]]
        cost = dec.latency_ms + PER_HOP_MS
        adj[link["a"]].append((link["b"], cost, link["id"]))
        adj[link["b"]].append((link["a"], cost, link["id"]))

    def dijkstra(src: str, banned: str | None = None):
        dist = {src: 0.0}
        prev: dict[str, str] = {}
        pq = [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, math.inf):
                continue
            for v, w, lid in adj[u]:
                if lid == banned:
                    continue
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def route(prev, src, dst):
        path = [dst]
        while path[-1] != src:
            path.append(prev[path[-1]])
        return list(reversed(path))

    budget = params.get("latency_budget_ms")
    pairs = []
    names = [s["name"] for s in params["sites"]]
    for i, a in enumerate(names):
        dist, prev = dijkstra(a)
        for b in names[i + 1:]:
            if b not in dist:
                continue
            entry = {"a": a, "b": b, "one_way_ms": round(dist[b], 3),
                     "path": route(prev, a, b)}
            if budget:
                entry["within_budget"] = dist[b] <= budget
            pairs.append(entry)
    worst = max(pairs, key=lambda e: e["one_way_ms"]) if pairs else None
    if budget and worst:
        ok = worst["one_way_ms"] <= budget
        log.add("QoS & Latency", "Latency budget",
                f"Worst path {' -> '.join(worst['path'])} = {worst['one_way_ms']} ms one-way "
                f"({'within' if ok else 'EXCEEDS'} {budget} ms)",
                f"Propagation in fibre is ~4.9 us/km (c / n with n ~ 1.47) plus a "
                f"{PER_HOP_MS} ms forwarding allowance per hop. The worst site pair uses "
                f"{worst['one_way_ms'] / budget:.1%} of the {budget} ms budget, so the remainder "
                f"is reserved for queuing delay - which is why latency-sensitive classes get a "
                f"strict-priority (LLQ) queue rather than relying on raw link speed.",
                ["ITU-T G.114", "RFC 4594"], {"worst": worst})
        if not ok:
            log.warn("QoS & Latency", "Latency budget",
                     f"Path {' -> '.join(worst['path'])} exceeds the {budget} ms budget on "
                     f"propagation alone; no QoS policy can fix physics - move the workload or "
                     f"shorten the path.")
        # failover latency for each secondary circuit
        for link in params["links"]:
            if link["role"] != "primary":
                continue
            dist, prev = dijkstra(link["a"], banned=link["id"])
            if link["b"] in dist:
                d = dist[link["b"]]
                pairs.append({"a": link["a"], "b": link["b"], "failover_of": link["id"],
                              "one_way_ms": round(d, 3), "path": route(prev, link["a"], link["b"]),
                              "within_budget": d <= budget})
        fo = [e for e in pairs if "failover_of" in e]
        if fo:
            w = max(fo, key=lambda e: e["one_way_ms"])
            log.add("QoS & Latency", "Failover latency",
                    f"Worst failover path {' -> '.join(w['path'])} = {w['one_way_ms']} ms "
                    f"({'within' if w['within_budget'] else 'EXCEEDS'} {budget} ms)",
                    f"Each primary circuit was removed in turn and the shortest surviving path "
                    f"recomputed (Dijkstra on latency). The worst case after a single failure "
                    f"still meets the budget, so dual-homing preserves the latency SLA, not just "
                    f"reachability." if w["within_budget"] else
                    "After a single circuit failure the surviving path breaks the latency "
                    "budget; add a more direct secondary circuit.",
                    ["RFC 2328 (SPF)", "ITU-T G.114"], {"worst_failover": w})
    elif worst:
        log.add("QoS & Latency", "Path latency",
                f"Worst path {' -> '.join(worst['path'])} = {worst['one_way_ms']} ms one-way",
                "Estimated from cable/route distance at ~4.9 us/km (Internet paths x1.4) plus "
                f"{PER_HOP_MS} ms per hop. Intercontinental latency is dominated by physics, so "
                "chatty IoT protocols should batch telemetry and use MQTT/HTTPS keep-alives "
                "rather than synchronous request/response.", ["ITU-T G.114"], {"worst": worst})
    return {"pairs": pairs, "worst": worst, "budget_ms": budget}


def plan_qos(params: dict, log: RationaleLog) -> dict | None:
    if params["network_type"] != "metro" and not params.get("qos"):
        return None
    qos = params.get("qos") or DEFAULT_QOS
    classes = qos["classes"]
    pr = [c for c in classes if c.get("priority")]
    desc = ", ".join(f"{c['name']} (DSCP {c['dscp'].upper()}, "
                     f"{'priority ' if c.get('priority') else ''}{c['percent']}%)" for c in classes)
    log.add("QoS & Latency", "WAN edge QoS", "Hierarchical shaper + LLQ: " + desc,
            "An EVPL is sold at a committed information rate, so the router first shapes to the "
            "CIR (otherwise the carrier polices excess and drops indiscriminately) and then "
            "queues inside the shaper: "
            + (f"{', '.join(c['name'] for c in pr)} uses the strict-priority LLQ to bound jitter "
               f"and delay for sub-5 ms trading/voice flows, " if pr else "")
            + "assured-forwarding classes get guaranteed minimum bandwidth, and class-default "
            "uses fair-queue. Traffic is marked by source subnet at the LAN ingress (wildcard-"
            "mask ACLs) so the classification is enforced at the trust boundary. IOS requires "
            "the shaper parent because CBWFQ cannot attach directly to a sub-interface.",
            ["RFC 4594 (DiffServ classes)", "RFC 3246 (EF PHB)", "RFC 2597 (AF PHB)", "MEF 10.3"],
            {"classes": classes})
    return {"classes": classes}
