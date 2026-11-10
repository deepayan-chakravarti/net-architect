"""Cisco IOS configuration generator.

Builds a device model from the plan (sites, links, addressing, routing,
QoS) and renders copy-paste-ready IOS for:

  * campus  : L3 distribution switches (SVIs, DHCP, routed uplinks, OSPF,
              ACLs) + an access-switch template per building
  * metro   : ISR edge routers (router-on-a-stick LAN, EVPL sub-interfaces,
              BFD, hierarchical QoS) + access template + carrier EVPL simulator
  * wan     : ISR edge routers (GRE/IPsec tunnels, multi-area OSPF with ABR
              summarisation, eBGP to cloud over VTI) + ISP and cloud-VGW
              simulators so the lab boots end-to-end in GNS3 / Packet Tracer

Interface naming targets Catalyst 3650-24PS (Gi1/0/x access, Gi1/1/x uplinks)
and ISR4331 (Gi0/0/0-2), the models available in Packet Tracer 8.
"""

from __future__ import annotations

import hashlib

from . import ipmath as ip
from .packetflow import ACE, ACL, Match

SW_PORT = "GigabitEthernet1/0/{}"
SW_UPLINK = "GigabitEthernet1/1/{}"
RTR_PORT = "GigabitEthernet0/0/{}"
NATIVE_VLAN = 999
BLACKHOLE_VLAN = 998
EVC_BASE = 3001
ISP_VLAN_BASE = 10
LAB_SECRET = "NetArch-Lab-2026"

RFC1918_MATCHES = [Match.cidr(n, p) for n, p in ip.RFC1918]


class Cfg:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, *lines: str) -> "Cfg":
        self.lines.extend(lines)
        return self

    def bang(self) -> "Cfg":
        self.lines.append("!")
        return self

    def section(self, title: str) -> "Cfg":
        self.lines.extend(["!", f"! --- {title} ---"])
        return self

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def psk(*parts: str) -> str:
    return "NA-" + hashlib.sha256("|".join(sorted(parts)).encode()).hexdigest()[:16]


def hostname(site: str, role: str) -> str:
    return f"{site}-{role}"


def _range(fmt: str, lo: int, hi: int) -> str:
    if lo == hi:
        return fmt.format(lo)
    return f"{fmt.format(lo)} - {hi}"


def _split_ports(total: int, weights: list[int]) -> list[int]:
    """Largest-remainder split of ``total`` ports, at least 1 each."""
    k = len(weights)
    if k == 0:
        return []
    if total < k:
        return [1 if i < total else 0 for i in range(k)]
    base = [1] * k
    remaining = total - k
    s = sum(weights) or 1
    raw = [remaining * w / s for w in weights]
    floors = [int(r) for r in raw]
    extra = remaining - sum(floors)
    order = sorted(range(k), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:extra]:
        floors[i] += 1
    return [b + f for b, f in zip(base, floors)]


# --------------------------------------------------------------------------- #
# Device model
# --------------------------------------------------------------------------- #
def build_model(ctx: dict) -> dict:
    """Assign devices, interfaces, IPs and cabling."""
    params, addressing = ctx["params"], ctx["addressing"]
    ntype = params["network_type"]
    links = ctx["links"]
    sites = [s for s in params["sites"] if not s.get("cloud")]
    clouds = [s for s in params["sites"] if s.get("cloud")]
    infra = addressing.block("INFRA").allocation.subnets
    loopbacks = {s.name.removeprefix("LO-"): s for s in infra if s.kind == "loopback"}

    devices: dict[str, dict] = {}
    cabling: list[tuple[str, str, str, str, str]] = []
    site_dev: dict[str, str] = {}

    for s in sites:
        name = hostname(s["name"], "DSW1" if ntype == "campus" else "RTR1")
        site_dev[s["name"]] = name
        devices[name] = {
            "name": name, "site": s["name"], "kind": "l3switch" if ntype == "campus" else "router",
            "loopback": loopbacks[s["name"]].network, "links": [], "tunnels": [],
            "area": ctx["routing"]["areas"].get(s["name"], 0),
            "public_ip": None, "isp_ip": None, "bgp_peers": [],
        }

    # public underlay for WAN (RFC 5737 TEST-NET-3) ------------------------------
    if ntype == "wan":
        base = ip.ip_to_int("203.0.113.0")
        for i, s in enumerate(sites + clouds):
            net = base + 4 * (i + 1)
            if s.get("cloud"):
                ctx.setdefault("cloud_public", {})[s["name"]] = (net + 2, net + 1, i + 1)
            else:
                d = devices[site_dev[s["name"]]]
                d["public_ip"], d["isp_ip"], d["isp_vlan_idx"] = net + 2, net + 1, i + 1

    uplink_no = {n: 0 for n in devices}
    uni_ports = {n: set() for n in devices}
    for link in links:
        a, b = link["a"], link["b"]
        a_cloud = a not in site_dev
        b_cloud = b not in site_dev
        dec = link["media_decision"]
        dist = (f"{link['distance_m'] / 1000:g}km" if link["distance_m"] >= 1000
                else f"{link['distance_m']:g}m")
        desc = f"{dec.medium} {dec.transceiver.split(' (')[0]} {dist}"
        if a_cloud or b_cloud:
            local, cloud = (b, a) if a_cloud else (a, b)
            d = devices[site_dev[local]]
            inside = link["inside_net"]
            d["tunnels"].append({
                "id": link["tunnel_id"], "peer": cloud, "type": "vti",
                "ip": inside + 1, "peer_ip": inside + 2, "prefix": 30, "link": link,
            })
            continue
        sub = link["subnet"]
        ends = ((a, b, sub.host(1), sub.host(2)), (b, a, sub.host(2), sub.host(1)))
        if ntype == "wan":
            for local, peer, mine, theirs in ends:
                devices[site_dev[local]]["tunnels"].append({
                    "id": link["tunnel_id"], "peer": peer, "type": "gre", "ip": mine,
                    "peer_ip": theirs, "prefix": sub.prefix, "subnet": sub, "link": link})
            continue
        port_of = {}
        for local, peer, mine, theirs in ends:
            dn = site_dev[local]
            if ntype == "campus":
                uplink_no[dn] += 1
                n = uplink_no[dn]
                port = SW_UPLINK.format(n) if n <= 4 else \
                    SW_PORT.format(params["ports_per_switch"] - (n - 5))
            else:  # metro: EVC sub-interface on primary/secondary UNI
                uni = 1 if link["role"] == "primary" else 2
                uni_ports[dn].add(uni)
                port = f"{RTR_PORT.format(uni)}.{link['evc']}"
            port_of[local] = port
            devices[dn]["links"].append({
                "port": port, "peer": site_dev[peer], "ip": mine, "subnet": sub,
                "desc": desc, "link": link,
                "cost": 10 if link["role"] == "primary" else 100,
            })
        if ntype == "campus":
            cabling.append((site_dev[a], port_of[a], site_dev[b], port_of[b], desc))

    # access-switch templates ----------------------------------------------------
    for s in sites:
        asw = hostname(s["name"], "ASW1")
        devices[asw] = {"name": asw, "site": s["name"], "kind": "access",
                        "count": ctx["l2"]["sites"][s["name"]]["access_switches"]}
        if ntype == "campus":
            cabling.append((asw, SW_UPLINK.format(1), site_dev[s["name"]], SW_PORT.format(1),
                            "Cat6a/MMF access uplink (trunk)"))
        else:
            cabling.append((asw, SW_UPLINK.format(1), site_dev[s["name"]], RTR_PORT.format(0),
                            "Cat6a LAN trunk (router-on-a-stick)"))

    # lab simulators ---------------------------------------------------------------
    if ntype == "metro":
        port = 0
        carrier_ports = []
        for dn in sorted(uni_ports):
            for uni in sorted(uni_ports[dn]):
                port += 1
                evcs = sorted({l["link"]["evc"] for l in devices[dn]["links"]
                               if l["port"].startswith(RTR_PORT.format(uni) + ".")})
                carrier_ports.append((port, dn, uni, evcs))
                cabling.append(("CARRIER-EVPL-SIM", SW_PORT.format(port), dn,
                                RTR_PORT.format(uni), "OS2 SMF UNI (EVPL handoff)"))
        devices["CARRIER-EVPL-SIM"] = {"name": "CARRIER-EVPL-SIM", "kind": "carrier",
                                       "ports": carrier_ports}
    if ntype == "wan":
        cloud_pub = ctx.get("cloud_public", {})
        attach = []
        for dn, d in devices.items():
            if d.get("public_ip"):
                attach.append((d["isp_vlan_idx"], dn, d["public_ip"], d["isp_ip"]))
        for cname, (pub, isp, idx) in cloud_pub.items():
            attach.append((idx, f"{cname}-VGW-SIM", pub, isp))
        attach.sort()
        devices["ISP-SIM"] = {"name": "ISP-SIM", "kind": "isp", "attach": attach}
        devices["ISP-SW"] = {"name": "ISP-SW", "kind": "ispsw", "attach": attach}
        cabling.append(("ISP-SIM", RTR_PORT.format(0), "ISP-SW", SW_UPLINK.format(1),
                        "ISP trunk"))
        for idx, dn, _, _ in attach:
            cabling.append(("ISP-SW", SW_PORT.format(idx), dn, RTR_PORT.format(1),
                            "Internet underlay (simulated)"))
        for c in clouds:
            devices[f"{c['name']}-VGW-SIM"] = {"name": f"{c['name']}-VGW-SIM", "kind": "vgw",
                                               "site": c["name"]}
    return {"devices": devices, "cabling": cabling, "site_dev": site_dev}


# --------------------------------------------------------------------------- #
# ACL builders (structured -> evaluated in tests and in plan verification)
# --------------------------------------------------------------------------- #
def guest_acl(guest, dns: int) -> ACL:
    g = Match.cidr(guest.network, guest.prefix)
    entries = [
        ACE("permit", "udp", Match.any(), Match.any(), dst_port=67, src_port=68,
            remark="DHCP to local gateway"),
        ACE("permit", "udp", g, Match.host(dns), dst_port=53, remark="DNS"),
    ]
    for i, m in enumerate(RFC1918_MATCHES):
        entries.append(ACE("deny", "ip", g, m, log=True,
                           remark="block guest -> internal RFC 1918" if i == 0 else ""))
    entries.append(ACE("permit", "ip", g, Match.any(), remark="Internet only"))
    return ACL(f"GUEST-IN-V{guest.vlan_id}", "extended", entries,
               "Guest isolation: DHCP/DNS allowed, all RFC 1918 destinations denied, "
               "Internet permitted")


def iot_acl(iot, dns: int, cloud_subnets: list) -> ACL:
    src = Match.cidr(iot.network, iot.prefix)
    entries = [
        ACE("permit", "udp", Match.any(), Match.any(), dst_port=67, src_port=68,
            remark="DHCP to local gateway"),
        ACE("permit", "udp", src, Match.host(dns), dst_port=53, remark="DNS"),
    ]
    for net, prefix in cloud_subnets:
        dst = Match.cidr(net, prefix)
        entries.append(ACE("permit", "tcp", src, dst, dst_port=443, remark="HTTPS to cloud app"))
        entries.append(ACE("permit", "tcp", src, dst, dst_port=8883, remark="MQTT/TLS telemetry"))
    entries.append(ACE("deny", "ip", src, Match.any(), log=True,
                       remark="IoT may not talk to anything else"))
    return ACL(f"IOT-IN-V{iot.vlan_id}", "extended", entries,
               "IoT least privilege: scanners reach only the cloud application tier on "
               "TCP 443/8883")


def vty_acl(mgmt_subnets: list) -> ACL:
    entries = [ACE("permit", src=Match.cidr(s.network, s.prefix), remark=f"{s.site} {s.name}")
               for s in mgmt_subnets]
    entries.append(ACE("deny", src=Match.any(), log=True))
    return ACL("VTY-MGMT", "standard", entries, "Only management subnets may SSH to devices")


def qos_mark_acls(qos: dict, lan_subnets: list) -> list[ACL]:
    acls = []
    for c in qos["classes"]:
        members = [s for s in lan_subnets if s.meta.get("qos_class") == c["name"]]
        if not members:
            continue
        acls.append(ACL(f"QOS-{c['name']}", "extended",
                        [ACE("permit", "ip", Match.cidr(s.network, s.prefix), Match.any(),
                             remark=f"{s.site} {s.name}") for s in members],
                        f"Classify {c['name']} traffic by source subnet"))
    return acls


def build_acls(ctx: dict) -> dict:
    """Per-site ACL objects keyed by site name."""
    params, addressing = ctx["params"], ctx["addressing"]
    dns = ip.ip_to_int(params["dns_server"])
    clouds = [s for s in params["sites"] if s.get("cloud")]
    cloud_subnets = [(s.network, s.prefix) for c in clouds
                     for s in addressing.block(c["name"]).allocation.subnets]
    if not cloud_subnets and clouds:
        cloud_subnets = [ip.parse_cidr(c["vpc_cidr"]) for c in clouds]
    mgmt_all = [s for s in addressing.all_subnets() if s.role == "mgmt"]
    if not mgmt_all:
        first = next(s for s in addressing.all_subnets() if s.kind == "lan")
        mgmt_all = [first]
    out = {}
    for site in params["sites"]:
        if site.get("cloud"):
            continue
        subs = [s for s in addressing.block(site["name"]).allocation.subnets]
        site_acls = {"vty": vty_acl(mgmt_all), "by_vlan": {}, "qos": []}
        for s in subs:
            if s.role == "guest":
                site_acls["by_vlan"][s.vlan_id] = guest_acl(s, dns)
            elif s.role == "iot" and cloud_subnets:
                site_acls["by_vlan"][s.vlan_id] = iot_acl(s, dns, cloud_subnets)
        if ctx.get("qos"):
            site_acls["qos"] = qos_mark_acls(ctx["qos"], subs)
        out[site["name"]] = site_acls
    return out


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
def _header(c: Cfg, dev: str, model: str, params: dict, note: str = "") -> None:
    c.add("! " + "=" * 70,
          f"! NetArchitect generated configuration - {dev}",
          f"! Platform : {model}",
          f"! Scenario : {params['name']}",
          "! Paste into privileged EXEC mode. Lab credentials below - change before production.")
    if note:
        for line in note.split("\n"):
            c.add(f"! {line}")
    c.add("! " + "=" * 70, "enable", "configure terminal", "!")


def _base(c: Cfg, dev: str, params: dict) -> None:
    c.add(f"hostname {dev}",
          "no ip domain-lookup",
          f"ip domain-name {params['domain_name']}",
          "service password-encryption",
          "service timestamps log datetime msec",
          f"enable secret {LAB_SECRET}",
          f"username netadmin privilege 15 secret {LAB_SECRET}",
          "banner motd ^Authorized access only - NetArchitect lab^")


def _mgmt_plane(c: Cfg, vty: ACL, vty_lines: str) -> None:
    c.section("Management plane (SSH only, ACL-restricted)")
    c.add(vty.render(), "crypto key generate rsa modulus 2048", "ip ssh version 2",
          "line con 0", " logging synchronous", " exec-timeout 15 0", " login local",
          f"line vty {vty_lines}", " access-class VTY-MGMT in", " exec-timeout 15 0",
          " login local", " transport input ssh")


def _footer(c: Cfg) -> None:
    c.add("!", "end", "write memory")


def _dhcp(c: Cfg, subnets: list, params: dict, site: str) -> None:
    pools = [s for s in subnets if s.kind == "lan" and s.role != "mgmt"]
    if not pools:
        return
    c.section("DHCP (gateway excluded, one pool per VLAN)")
    for s in pools:
        c.add(f"ip dhcp excluded-address {ip.int_to_ip(s.gateway)}")
    for s in pools:
        c.add(f"ip dhcp pool {site}-{s.name}",
              f" network {ip.int_to_ip(s.network)} {ip.int_to_ip(s.mask)}",
              f" default-router {ip.int_to_ip(s.gateway)}",
              f" dns-server {params['dns_server']}",
              f" domain-name {params['domain_name']}")


def _ospf(c: Cfg, dev: dict, routing: dict, lan_subnets: list, active_ifaces: list[str],
          infra_nets: list) -> None:
    c.section(f"OSPF ({routing['design']})")
    c.add(f"router ospf {routing['process_id']}",
          f" router-id {ip.int_to_ip(dev['loopback'])}",
          f" auto-cost reference-bandwidth {routing['reference_bandwidth_mbps']}",
          " passive-interface default")
    for iface in active_ifaces:
        c.add(f" no passive-interface {iface}")
    c.add(f" network {ip.int_to_ip(dev['loopback'])} 0.0.0.0 area 0")
    for s in infra_nets:
        c.add(f" network {ip.int_to_ip(s.network)} {ip.int_to_ip(s.wildcard)} area 0")
    for s in lan_subnets:
        c.add(f" network {ip.int_to_ip(s.network)} {ip.int_to_ip(s.wildcard)} area {dev['area']}")
    summ = routing["summaries"].get(dev["site"])
    if summ:
        c.add(f" area {summ['area']} range {summ['network']} {summ['mask']}")
    if routing.get("bfd"):
        c.add(" bfd all-interfaces")


def render_campus_dsw(dev: dict, ctx: dict, acls: dict) -> str:
    params, addressing, routing = ctx["params"], ctx["addressing"], ctx["routing"]
    site = dev["site"]
    subs = addressing.block(site).allocation.subnets
    lan = [s for s in subs if s.kind == "lan"]
    vids = sorted(s.vlan_id for s in lan)
    n_access = ctx["l2"]["sites"][site]["access_switches"]
    ports = params["ports_per_switch"]
    max_down = ports - max(0, len(dev["links"]) - 4) - 2
    down = min(n_access, max_down)
    c = Cfg()
    note = (f"Role: building distribution (L3 gateway for {len(lan)} VLANs, OSPF area "
            f"{dev['area']})\nSite block: {addressing.block(site).cidr}")
    _header(c, dev["name"], "Cisco Catalyst 3650-24PS (L3) / IOSvL2", params, note)
    _base(c, dev["name"], params)
    c.add("ip routing")
    c.section("Spanning tree: Rapid PVST+, this switch is root")
    allv = ",".join(str(v) for v in vids)
    c.add("spanning-tree mode rapid-pvst", f"spanning-tree vlan {allv} priority 4096")
    c.section("VLAN database")
    for s in sorted(lan, key=lambda s: s.vlan_id):
        c.add(f"vlan {s.vlan_id}", f" name {s.name}")
    c.add(f"vlan {BLACKHOLE_VLAN}", " name BLACKHOLE", f"vlan {NATIVE_VLAN}", " name NATIVE-UNUSED")
    site_acls = acls[site]
    if site_acls["by_vlan"]:
        c.section("Security ACLs (wildcard masks computed bitwise)")
        for acl in site_acls["by_vlan"].values():
            c.add(acl.render())
    c.section("Loopback (OSPF router-id)")
    c.add("interface Loopback0", f" ip address {ip.int_to_ip(dev['loopback'])} 255.255.255.255")
    c.section("SVIs (default gateways)")
    for s in sorted(lan, key=lambda s: s.vlan_id):
        c.add(f"interface Vlan{s.vlan_id}",
              f" description {s.name} gateway {s.cidr} ({s.hosts_requested} hosts)",
              f" ip address {ip.int_to_ip(s.gateway)} {ip.int_to_ip(s.mask)}")
        if s.vlan_id in site_acls["by_vlan"]:
            c.add(f" ip access-group {site_acls['by_vlan'][s.vlan_id].name} in")
        c.add(" no shutdown")
    c.section(f"Downlink trunks to {n_access} access switch(es)")
    if n_access > down:
        c.add(f"! NOTE: {n_access} access switches sized; {down} downlinks fit this chassis - "
              f"stack a second member for the remainder.")
    c.add(f"interface range {_range(SW_PORT, 1, down)}",
          " description TRUNK to access layer",
          " switchport trunk encapsulation dot1q",
          " switchport mode trunk",
          f" switchport trunk native vlan {NATIVE_VLAN}",
          f" switchport trunk allowed vlan {allv},{NATIVE_VLAN}",
          " switchport nonegotiate",
          " no shutdown")
    used = {l["port"] for l in dev["links"]}
    spare = [p for p in range(down + 1, ports + 1) if SW_PORT.format(p) not in used]
    if spare:
        c.add(f"interface range {_range(SW_PORT, spare[0], spare[-1])}" if
              spare == list(range(spare[0], spare[-1] + 1)) else
              "interface range " + ", ".join(SW_PORT.format(p) for p in spare),
              " description UNUSED", " switchport mode access",
              f" switchport access vlan {BLACKHOLE_VLAN}", " shutdown")
    c.section("Routed inter-building links")
    for l in dev["links"]:
        c.add(f"interface {l['port']}",
              f" description P2P to {l['peer']} ({l['desc']})",
              " no switchport",
              f" ip address {ip.int_to_ip(l['ip'])} {ip.int_to_ip(l['subnet'].mask)}",
              " ip ospf network point-to-point",
              " no shutdown")
    _dhcp(c, lan, params, site)
    _ospf(c, dev, routing, lan, [l["port"] for l in dev["links"]],
          [l["subnet"] for l in dev["links"]])
    _mgmt_plane(c, site_acls["vty"], "0 15")
    _footer(c)
    return c.text()


def render_access(dev: dict, ctx: dict) -> str:
    params, addressing = ctx["params"], ctx["addressing"]
    site = dev["site"]
    lan = [s for s in addressing.block(site).allocation.subnets if s.kind == "lan"]
    vids = sorted(s.vlan_id for s in lan)
    ports = params["ports_per_switch"]
    mgmt = next((s for s in lan if s.role == "mgmt"), lan[0])
    voice = next((s for s in lan if s.role == "voice"), None)
    ap = next((s for s in lan if s.role == "ap"), None)
    wl = [s for s in lan if s.role in ("wireless", "guest")]
    wired = sorted([s for s in lan if s.role in ("data", "iot", "server")],
                   key=lambda s: -s.hosts_requested)
    ap_ports = 4 if ap else 0
    user_ports = ports - ap_ports - 2
    split = _split_ports(user_ports, [s.hosts_requested for s in wired])
    c = Cfg()
    note = (f"TEMPLATE: replicate for {dev['count']} access switch(es) in {site}; increment the "
            f"hostname and the Vlan{mgmt.vlan_id} address (next free host in {mgmt.cidr}).")
    _header(c, dev["name"], "Cisco Catalyst 3650-24PS / 2960 (L2 access)", params, note)
    _base(c, dev["name"], params)
    c.add("spanning-tree mode rapid-pvst", "spanning-tree portfast bpduguard default")
    c.section("VLAN database")
    for s in sorted(lan, key=lambda s: s.vlan_id):
        c.add(f"vlan {s.vlan_id}", f" name {s.name}")
    c.add(f"vlan {BLACKHOLE_VLAN}", " name BLACKHOLE", f"vlan {NATIVE_VLAN}", " name NATIVE-UNUSED")
    c.section("Management SVI")
    c.add(f"interface Vlan{mgmt.vlan_id}", " description In-band management",
          f" ip address {ip.int_to_ip(mgmt.host(2))} {ip.int_to_ip(mgmt.mask)}", " no shutdown",
          f"ip default-gateway {ip.int_to_ip(mgmt.gateway)}")
    c.section("Edge ports (PortFast + BPDU Guard, DTP off)")
    port = 1
    for s, n in zip(wired, split):
        if n == 0:
            continue
        c.add(f"interface range {_range(SW_PORT, port, port + n - 1)}",
              f" description {s.name} endpoints" + (" + IP phone" if voice and s.role == "data"
                                                     else ""),
              " switchport mode access", f" switchport access vlan {s.vlan_id}")
        if voice and s.role == "data":
            c.add(f" switchport voice vlan {voice.vlan_id}")
        c.add(" switchport nonegotiate", " spanning-tree portfast", " spanning-tree bpduguard enable",
              " no shutdown")
        port += n
    if ap:
        allowed = ",".join(str(v) for v in sorted([ap.vlan_id] + [s.vlan_id for s in wl]))
        c.add(f"interface range {_range(SW_PORT, port, port + ap_ports - 1)}",
              " description PoE access points (FlexConnect local switching)",
              " switchport trunk encapsulation dot1q",
              " switchport mode trunk",
              f" switchport trunk native vlan {ap.vlan_id}",
              f" switchport trunk allowed vlan {allowed}",
              " switchport nonegotiate", " spanning-tree portfast trunk",
              " spanning-tree bpduguard enable", " power inline auto", " no shutdown")
        port += ap_ports
    if port <= ports:
        c.add(f"interface range {_range(SW_PORT, port, ports)}", " description UNUSED",
              " switchport mode access", f" switchport access vlan {BLACKHOLE_VLAN}", " shutdown")
    c.section("Uplink trunk")
    uplink_to = hostname(site, "DSW1" if params["network_type"] == "campus" else "RTR1")
    c.add(f"interface {SW_UPLINK.format(1)}", f" description TRUNK to {uplink_to}",
          " switchport trunk encapsulation dot1q",
          " switchport mode trunk", f" switchport trunk native vlan {NATIVE_VLAN}",
          f" switchport trunk allowed vlan {','.join(map(str, vids))},{NATIVE_VLAN}",
          " switchport nonegotiate", " no shutdown")
    c.add(f"interface range {_range(SW_UPLINK, 2, 4)}", " description UNUSED",
          " switchport mode access", f" switchport access vlan {BLACKHOLE_VLAN}", " shutdown")
    vty = vty_acl([s for s in ctx["addressing"].all_subnets() if s.role == "mgmt"] or [mgmt])
    _mgmt_plane(c, vty, "0 15")
    _footer(c)
    return c.text()


def _qos_policies(c: Cfg, qos: dict, cirs: set[int], acls: list[ACL]) -> None:
    c.section("QoS: LAN ingress marking + hierarchical WAN egress (shaper -> LLQ)")
    for acl in acls:
        c.add(acl.render())
    for acl in acls:
        cls = acl.name.removeprefix("QOS-")
        c.add(f"class-map match-any MARK-{cls}", f" match access-group name {acl.name}")
    c.add("policy-map LAN-MARKING")
    for acl in acls:
        cls = acl.name.removeprefix("QOS-")
        dscp = next(q["dscp"] for q in qos["classes"] if q["name"] == cls)
        c.add(f" class MARK-{cls}", f"  set dscp {dscp}")
    for q in qos["classes"]:
        c.add(f"class-map match-any {q['name']}", f" match dscp {q['dscp']}")
    c.add("policy-map WAN-QUEUING")
    for q in qos["classes"]:
        c.add(f" class {q['name']}",
              f"  priority percent {q['percent']}" if q.get("priority") else
              f"  bandwidth percent {q['percent']}")
    c.add(" class class-default", "  fair-queue")
    for cir in sorted(cirs):
        c.add(f"policy-map WAN-SHAPE-{cir // 1_000_000}M", " class class-default",
              f"  shape average {cir}", "  service-policy WAN-QUEUING")


def _crypto_common(c: Cfg, need_gre: bool, need_vti: bool) -> None:
    c.section("IPsec: IKEv1 AES-256/SHA-256/DH14")
    c.add("crypto isakmp policy 10", " encryption aes 256", " hash sha256",
          " authentication pre-share", " group 14", " lifetime 28800")
    if need_gre:
        c.add("crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac", " mode transport",
              "crypto ipsec profile IPSEC-GRE", " set transform-set TS-GRE")
    if need_vti:
        c.add("crypto ipsec transform-set TS-VTI esp-aes 256 esp-sha256-hmac", " mode tunnel",
              "crypto ipsec profile IPSEC-VTI", " set transform-set TS-VTI")


def render_router(dev: dict, ctx: dict, acls: dict, model: dict) -> str:
    params, addressing, routing = ctx["params"], ctx["addressing"], ctx["routing"]
    ntype = params["network_type"]
    site = dev["site"]
    subs = addressing.block(site).allocation.subnets
    lan = sorted([s for s in subs if s.kind == "lan"], key=lambda s: s.vlan_id)
    site_acls = acls[site]
    qos = ctx.get("qos")
    devices = model["devices"]
    c = Cfg()
    role = ("hub (area 0)" if routing["areas"].get(site) == 0 and routing["design"] ==
            "Multi-area OSPF" else f"ABR area 0/{dev['area']}" if routing["design"] ==
            "Multi-area OSPF" else "OSPF area 0")
    note = f"Role: site edge router, {role}\nSite block: {addressing.block(site).cidr}"
    _header(c, dev["name"], "Cisco ISR4331 (IOS-XE) / IOSv", params, note)
    _base(c, dev["name"], params)
    if dev["tunnels"]:
        peers = []
        for t in dev["tunnels"]:
            if t["type"] == "gre":
                peer_pub = devices[model["site_dev"][t["peer"]]]["public_ip"]
            else:
                peer_pub = ctx["cloud_public"][t["peer"]][0]
            t["peer_public"] = peer_pub
            peers.append((t["peer"], peer_pub))
        _crypto_common(c, any(t["type"] == "gre" for t in dev["tunnels"]),
                       any(t["type"] == "vti" for t in dev["tunnels"]))
        for peer, pub in peers:
            c.add(f"crypto isakmp key {psk(site, peer, params['name'])} address "
                  f"{ip.int_to_ip(pub)}")
    if site_acls["by_vlan"]:
        c.section("Security ACLs (wildcard masks computed bitwise)")
        for acl in site_acls["by_vlan"].values():
            c.add(acl.render())
    if qos:
        cirs = {int(l["link"]["bandwidth_gbps"] * 1_000_000_000) for l in dev["links"]}
        _qos_policies(c, qos, cirs, site_acls["qos"])
    c.section("Loopback (router-id)")
    c.add("interface Loopback0", f" ip address {ip.int_to_ip(dev['loopback'])} 255.255.255.255")
    c.section("LAN: router-on-a-stick sub-interfaces (802.1Q)")
    c.add(f"interface {RTR_PORT.format(0)}", f" description LAN trunk to {site}-ASW1",
          " no ip address", " no shutdown")
    for s in lan:
        c.add(f"interface {RTR_PORT.format(0)}.{s.vlan_id}",
              f" description {s.name} gateway {s.cidr} ({s.hosts_requested} hosts)",
              f" encapsulation dot1Q {s.vlan_id}",
              f" ip address {ip.int_to_ip(s.gateway)} {ip.int_to_ip(s.mask)}")
        if s.vlan_id in site_acls["by_vlan"]:
            c.add(f" ip access-group {site_acls['by_vlan'][s.vlan_id].name} in")
        if qos and s.meta.get("qos_class"):
            c.add(" service-policy input LAN-MARKING")
    c.add(f"interface {RTR_PORT.format(0)}.{NATIVE_VLAN}", " description native VLAN (unused)",
          f" encapsulation dot1Q {NATIVE_VLAN} native")
    active = []
    if dev["links"]:
        c.section("Carrier EVPL circuits (one dot1Q EVC per sub-interface)")
        for uni in sorted({l["port"].split(".")[0] for l in dev["links"]}):
            label = "primary" if uni.endswith("/1") else "secondary (diverse path)"
            c.add(f"interface {uni}", f" description EVPL UNI - {label}", " no ip address",
                  " no shutdown")
        for l in dev["links"]:
            evc = l["link"]["evc"]
            cir = int(l["link"]["bandwidth_gbps"] * 1_000_000_000)
            c.add(f"interface {l['port']}",
                  f" description EVC {evc} to {l['peer']} - {l['link']['role']} ({l['desc']})",
                  f" encapsulation dot1Q {evc}",
                  f" ip address {ip.int_to_ip(l['ip'])} {ip.int_to_ip(l['subnet'].mask)}",
                  " ip ospf network point-to-point",
                  f" ip ospf cost {l['cost']}")
            if routing.get("bfd"):
                c.add(" bfd interval 50 min_rx 50 multiplier 3")
            if qos:
                c.add(f" service-policy output WAN-SHAPE-{cir // 1_000_000}M")
            active.append(l["port"])
    if dev.get("public_ip"):
        c.section("Internet underlay (RFC 5737 lab addressing)")
        c.add(f"interface {RTR_PORT.format(1)}", " description INTERNET underlay",
              f" ip address {ip.int_to_ip(dev['public_ip'])} 255.255.255.252", " no shutdown",
              f"ip route 0.0.0.0 0.0.0.0 {ip.int_to_ip(dev['isp_ip'])} name INTERNET")
    if dev["tunnels"]:
        c.section("Encrypted tunnels")
        for t in dev["tunnels"]:
            c.add(f"interface Tunnel{t['id']}")
            if t["type"] == "gre":
                c.add(f" description GRE/IPsec to {t['peer']} ({t['link']['distance_m'] / 1000:,.0f} km)",
                      f" ip address {ip.int_to_ip(t['ip'])} {ip.mask_str(t['prefix'])}",
                      " ip mtu 1400", " ip tcp adjust-mss 1360",
                      " ip ospf network point-to-point",
                      f" tunnel source {RTR_PORT.format(1)}",
                      f" tunnel destination {ip.int_to_ip(t['peer_public'])}",
                      " tunnel protection ipsec profile IPSEC-GRE")
                active.append(f"Tunnel{t['id']}")
            else:
                c.add(f" description IPsec VTI + eBGP to {t['peer']} VPC",
                      f" ip address {ip.int_to_ip(t['ip'])} 255.255.255.252",
                      " ip mtu 1400", " ip tcp adjust-mss 1360",
                      f" tunnel source {RTR_PORT.format(1)}",
                      " tunnel mode ipsec ipv4",
                      f" tunnel destination {ip.int_to_ip(t['peer_public'])}",
                      " tunnel protection ipsec profile IPSEC-VTI")
    _dhcp(c, lan, params, site)
    infra_nets = [l["subnet"] for l in dev["links"]] + \
        [t["subnet"] for t in dev["tunnels"] if t["type"] == "gre"]
    _ospf(c, dev, routing, lan, active, infra_nets)
    vtis = [t for t in dev["tunnels"] if t["type"] == "vti"]
    if vtis and routing.get("bgp"):
        bgp = routing["bgp"]
        rnet, rpre = ip.parse_cidr(params["root_prefix"])
        c.add(f" redistribute bgp {bgp['asn']} subnets route-map BGP-TO-OSPF")
        c.section("eBGP to cloud VPC (aggregate out, VPC CIDR in)")
        c.add(f"ip route {ip.int_to_ip(rnet)} {ip.mask_str(rpre)} Null0 254 name AGGREGATE-DISCARD")
        c.add(f"ip prefix-list TO-CLOUD seq 5 permit {params['root_prefix']}")
        for t in vtis:
            peer = next(p for p in bgp["peers"] if p["site"] == t["peer"])
            c.add(f"ip prefix-list FROM-CLOUD seq {5 + 5 * vtis.index(t)} permit "
                  f"{peer['prefix']} le 24")
        c.add("route-map BGP-TO-OSPF permit 10", " match ip address prefix-list FROM-CLOUD")
        c.add(f"router bgp {bgp['asn']}", f" bgp router-id {ip.int_to_ip(dev['loopback'])}",
              " bgp log-neighbor-changes")
        for t in vtis:
            peer = next(p for p in bgp["peers"] if p["site"] == t["peer"])
            c.add(f" neighbor {ip.int_to_ip(t['peer_ip'])} remote-as {peer['asn']}",
                  f" neighbor {ip.int_to_ip(t['peer_ip'])} description {t['peer']} VGW",
                  f" neighbor {ip.int_to_ip(t['peer_ip'])} timers 10 30")
        c.add(" address-family ipv4",
              f"  network {ip.int_to_ip(rnet)} mask {ip.mask_str(rpre)}")
        for t in vtis:
            n = ip.int_to_ip(t["peer_ip"])
            c.add(f"  neighbor {n} activate", f"  neighbor {n} prefix-list TO-CLOUD out",
                  f"  neighbor {n} prefix-list FROM-CLOUD in")
        c.add(" exit-address-family")
    _mgmt_plane(c, site_acls["vty"], "0 4")
    _footer(c)
    return c.text()


def render_carrier(dev: dict, ctx: dict) -> str:
    c = Cfg()
    _header(c, dev["name"], "Cisco Catalyst 3650 (lab carrier EVPL simulator)", ctx["params"],
            "Emulates the provider metro-Ethernet network: one VLAN per EVC, UNI ports trunk "
            "only the EVCs ordered for that site.")
    c.add(f"hostname {dev['name']}", "no ip domain-lookup", "spanning-tree mode rapid-pvst")
    evcs = sorted({e for _, _, _, es in dev["ports"] for e in es})
    for e in evcs:
        c.add(f"vlan {e}", f" name EVC-{e}")
    for port, dn, uni, es in dev["ports"]:
        c.add(f"interface {SW_PORT.format(port)}", f" description UNI {dn} {RTR_PORT.format(uni)}",
              " switchport trunk encapsulation dot1q", " switchport mode trunk",
              f" switchport trunk allowed vlan {','.join(map(str, es))}",
              " switchport nonegotiate", " spanning-tree portfast trunk", " no shutdown")
    _footer(c)
    return c.text()


def render_isp(dev: dict, ctx: dict) -> str:
    c = Cfg()
    _header(c, dev["name"], "Cisco ISR4331 (lab Internet simulator)", ctx["params"],
            "Router-on-a-stick: one sub-interface per customer /30 (RFC 5737 TEST-NET-3).")
    c.add(f"hostname {dev['name']}", "no ip domain-lookup",
          f"interface {RTR_PORT.format(0)}", " description trunk to ISP-SW", " no ip address",
          " no shutdown")
    for idx, dn, pub, isp in dev["attach"]:
        c.add(f"interface {RTR_PORT.format(0)}.{ISP_VLAN_BASE + idx}", f" description {dn}",
              f" encapsulation dot1Q {ISP_VLAN_BASE + idx}",
              f" ip address {ip.int_to_ip(isp)} 255.255.255.252")
    _footer(c)
    return c.text()


def render_ispsw(dev: dict, ctx: dict) -> str:
    c = Cfg()
    _header(c, dev["name"], "Cisco Catalyst 3650 (lab Internet access switch)", ctx["params"])
    c.add(f"hostname {dev['name']}", "no ip domain-lookup")
    for idx, dn, _, _ in dev["attach"]:
        c.add(f"vlan {ISP_VLAN_BASE + idx}", f" name {dn}")
    for idx, dn, _, _ in dev["attach"]:
        c.add(f"interface {SW_PORT.format(idx)}", f" description {dn} Gi0/0/1",
              " switchport mode access", f" switchport access vlan {ISP_VLAN_BASE + idx}",
              " spanning-tree portfast", " no shutdown")
    c.add(f"interface {SW_UPLINK.format(1)}", " description trunk to ISP-SIM",
          " switchport trunk encapsulation dot1q", " switchport mode trunk",
          " switchport trunk allowed vlan " + ",".join(str(ISP_VLAN_BASE + i)
                                                     for i, *_ in dev["attach"]),
          " switchport nonegotiate", " no shutdown")
    _footer(c)
    return c.text()


def render_vgw(dev: dict, ctx: dict, model: dict) -> str:
    params, addressing, routing = ctx["params"], ctx["addressing"], ctx["routing"]
    cname = dev["site"]
    site = next(s for s in params["sites"] if s["name"] == cname)
    pub, isp, _ = ctx["cloud_public"][cname]
    peer = next(p for p in routing["bgp"]["peers"] if p["site"] == cname)
    vnet, vpre = ip.parse_cidr(site["vpc_cidr"])
    c = Cfg()
    _header(c, dev["name"], "Cisco ISR4331 / CSR1000v (lab stand-in for the cloud VPN gateway)",
            params, "In production these values are entered in the cloud console (VPN "
            "connection + BGP ASN); this router lets the lab run end-to-end.")
    c.add(f"hostname {dev['name']}", "no ip domain-lookup")
    _crypto_common(c, False, True)
    tunnels = []
    for d in model["devices"].values():
        for t in d.get("tunnels", []):
            if t["type"] == "vti" and t["peer"] == cname:
                tunnels.append((d, t))
    for d, t in tunnels:
        c.add(f"crypto isakmp key {psk(d['site'], cname, params['name'])} address "
              f"{ip.int_to_ip(d['public_ip'])}")
    c.add(f"interface {RTR_PORT.format(1)}", " description INTERNET underlay",
          f" ip address {ip.int_to_ip(pub)} 255.255.255.252", " no shutdown",
          f"ip route 0.0.0.0 0.0.0.0 {ip.int_to_ip(isp)}")
    for i, s in enumerate(addressing.block(cname).allocation.subnets, 1):
        c.add(f"interface Loopback{i}", f" description VPC subnet {s.name} {s.cidr}",
              f" ip address {ip.int_to_ip(s.gateway)} {ip.int_to_ip(s.mask)}")
    for d, t in tunnels:
        c.add(f"interface Tunnel{t['id']}", f" description VTI to {d['name']}",
              f" ip address {ip.int_to_ip(t['peer_ip'])} 255.255.255.252",
              f" tunnel source {RTR_PORT.format(1)}", " tunnel mode ipsec ipv4",
              f" tunnel destination {ip.int_to_ip(d['public_ip'])}",
              " tunnel protection ipsec profile IPSEC-VTI")
    c.add(f"ip route {ip.int_to_ip(vnet)} {ip.mask_str(vpre)} Null0 254",
          f"router bgp {peer['asn']}", " bgp log-neighbor-changes")
    for d, t in tunnels:
        c.add(f" neighbor {ip.int_to_ip(t['ip'])} remote-as {routing['bgp']['asn']}",
              f" neighbor {ip.int_to_ip(t['ip'])} timers 10 30")
    c.add(" address-family ipv4", f"  network {ip.int_to_ip(vnet)} mask {ip.mask_str(vpre)}")
    for d, t in tunnels:
        c.add(f"  neighbor {ip.int_to_ip(t['ip'])} activate")
    c.add(" exit-address-family")
    _footer(c)
    return c.text()


def generate(ctx: dict) -> dict:
    """Return {'configs': {device: text}, 'cabling': [...], 'acls': {...}}."""
    model = build_model(ctx)
    acls = build_acls(ctx)
    configs = {}
    for name, dev in model["devices"].items():
        kind = dev["kind"]
        if kind == "l3switch":
            configs[name] = render_campus_dsw(dev, ctx, acls)
        elif kind == "router":
            configs[name] = render_router(dev, ctx, acls, model)
        elif kind == "access":
            configs[name] = render_access(dev, ctx)
        elif kind == "carrier":
            configs[name] = render_carrier(dev, ctx)
        elif kind == "isp":
            configs[name] = render_isp(dev, ctx)
        elif kind == "ispsw":
            configs[name] = render_ispsw(dev, ctx)
        elif kind == "vgw":
            configs[name] = render_vgw(dev, ctx, model)
    cabling = [{"a": a, "a_port": ap, "b": b, "b_port": bp, "medium": m}
               for a, ap, b, bp, m in model["cabling"]]
    return {"configs": configs, "cabling": cabling, "acls": acls, "model": model}
