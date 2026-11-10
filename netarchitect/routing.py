"""L3 Routing Protocol selection.

Rules (assignment section 3):
  * single autonomous system, < 50 subnets, no untrusted/multi-site WAN
      -> OSPF single area 0 (link-state, fast convergence)
  * >= 50 subnets, or geographically dispersed sites over a routed/Internet WAN
      -> multi-area OSPF, one area per site, summarised at the ABR
  * a cloud VPC or any external AS
      -> eBGP at that boundary (private ASNs, RFC 6996)
"""

from __future__ import annotations

from . import ipmath as ip
from .rationale import RationaleLog
from .vlsm import Addressing

SUBNET_THRESHOLD = 50
DEFAULT_ENTERPRISE_ASN = 65010
DEFAULT_CLOUD_ASN = 64512


def find_hub(params: dict) -> str:
    if params.get("hub"):
        return params["hub"]
    degree: dict[str, int] = {s["name"]: 0 for s in params["sites"] if not s.get("cloud")}
    for link in params["links"]:
        for end in (link["a"], link["b"]):
            if end in degree:
                degree[end] += 1
    return max(degree, key=lambda k: (degree[k], -list(degree).index(k)))


def select_routing(params: dict, addressing: Addressing, log: RationaleLog) -> dict:
    sites = [s for s in params["sites"] if not s.get("cloud")]
    clouds = [s for s in params["sites"] if s.get("cloud")]
    transports = {l["transport"] for l in params["links"]}
    subnet_count = len(addressing.all_subnets())
    hub = find_hub(params)
    untrusted = "internet" in transports

    multi_area = subnet_count >= SUBNET_THRESHOLD or (untrusted and len(sites) >= 3)
    plan: dict = {
        "igp": "OSPFv2",
        "process_id": 1,
        "reference_bandwidth_mbps": 100_000,
        "hub": hub,
        "areas": {},
        "summaries": {},
        "bfd": False,
        "bgp": None,
        "subnet_count": subnet_count,
    }

    if multi_area:
        reasons = []
        if subnet_count >= SUBNET_THRESHOLD:
            reasons.append(f"{subnet_count} subnets >= {SUBNET_THRESHOLD}, so a single LSDB would "
                           f"force every router to re-run SPF on any change anywhere")
        if untrusted:
            reasons.append(f"{len(sites)} geographically dispersed sites interconnect over an "
                           f"Internet/IPsec WAN whose tunnels can flap independently")
        area_no = 0
        for s in sites:
            if s["name"] == hub:
                plan["areas"][s["name"]] = 0
            else:
                area_no += 1
                plan["areas"][s["name"]] = area_no
                block = addressing.block(s["name"])
                plan["summaries"][s["name"]] = {
                    "area": area_no, "network": ip.int_to_ip(block.network),
                    "mask": ip.mask_str(block.prefix), "cidr": block.cidr,
                    "lan_subnets": len(block.allocation.subnets),
                }
        plan["design"] = "Multi-area OSPF"
        log.add("L3 Routing", "Interior gateway protocol",
                "Multi-area OSPFv2 (area 0 backbone at " + hub + ", one area per remote site)",
                "Selected multi-area OSPF because " + " and ".join(reasons) + ". Areas confine "
                "Type-1/2 LSA flooding and SPF recalculation to the site where a change "
                "happens; area 0 carries only inter-area summaries. OSPF remains vendor-neutral "
                "and converges in seconds as a link-state protocol.",
                ["RFC 2328 (OSPFv2) section 3", "RFC 3509 (ABR behaviour)"],
                {"subnets": subnet_count, "areas": dict(plan["areas"])})
        for site, summ in plan["summaries"].items():
            log.add("L3 Routing", f"Area {summ['area']} summary ({site})",
                    f"area {summ['area']} range {summ['network']} {summ['mask']}",
                    f"The ABR at {site} advertises {summ['lan_subnets']} intra-area subnets into "
                    f"area 0 as one Type-3 LSA {summ['cidr']}. This works only because the VLSM "
                    f"engine allocated the site as one contiguous, bit-aligned block; it shrinks "
                    f"every other router's routing table and hides intra-site flaps from the "
                    f"backbone.", ["RFC 2328 section 12.4.3", "RFC 4632"], summ)
    else:
        for s in sites:
            plan["areas"][s["name"]] = 0
        plan["design"] = "Single-area OSPF"
        evpl = "evpl" in transports
        why_single = (f"Although there are {len(sites)} sites, the carrier EVPL circuits are "
                      f"Layer-2 point-to-point Ethernet, so all routers form direct OSPF "
                      f"adjacencies as if on one campus. " if evpl and len(sites) > 1 else "")
        log.add("L3 Routing", "Interior gateway protocol", "OSPFv2 single area 0",
                f"{why_single}The design is a single autonomous system with {subnet_count} "
                f"subnets (< {SUBNET_THRESHOLD}), so one LSDB stays small and SPF runs in "
                f"milliseconds. A link-state protocol gives sub-second-to-seconds convergence "
                f"without the hop-count limits and slow count-to-infinity behaviour of "
                f"distance-vector RIP, and avoids the ABR/summarisation complexity that "
                f"multi-area would add with no scaling benefit.",
                ["RFC 2328 (OSPFv2)"], {"subnets": subnet_count})

    log.add("L3 Routing", "OSPF reference bandwidth", "auto-cost reference-bandwidth 100000",
            "The default 100 Mbps reference gives FastEthernet, 1G and 10G links the same cost "
            "(1). Raising it to 100 Gbps makes cost = 100000 / link Mbps, so 10G = 10, 1G = 100 "
            "and SPF prefers the faster path. Must be identical on every router.",
            ["RFC 2328 Appendix C.3"])

    if params.get("resiliency") == "dual_homed":
        plan["bfd"] = True
        log.add("L3 Routing", "Failure detection", "BFD 50 ms x 3 on WAN links + cost-based primary",
                "Dual-homed failover requires detecting a carrier fault faster than OSPF's 40 s "
                "dead interval. BFD (50 ms interval, multiplier 3) declares the neighbour down in "
                "150 ms and triggers immediate SPF; primary circuits use OSPF cost 10 and "
                "secondary circuits cost 100 so traffic only shifts on failure.",
                ["RFC 5880 (BFD)", "RFC 5882 (BFD for OSPF)"])

    if clouds:
        asn = params.get("bgp_asn") or DEFAULT_ENTERPRISE_ASN
        peers = []
        for c in clouds:
            peers.append({"site": c["name"], "asn": c.get("asn") or DEFAULT_CLOUD_ASN,
                          "prefix": c.get("vpc_cidr")})
        plan["bgp"] = {"asn": asn, "peers": peers,
                       "advertise": [params["root_prefix"]]}
        log.add("L3 Routing", "Cloud boundary", f"eBGP AS{asn} <-> " +
                ", ".join(f"AS{p['asn']} ({p['site']})" for p in peers),
                "The cloud VPC is a separate administrative and routing domain; cloud VPN "
                "gateways only exchange dynamic routes via BGP. eBGP isolates the domains: the "
                "enterprise advertises one aggregate (" + params["root_prefix"] + ") filtered by "
                "prefix-list, and accepts only the VPC CIDR, so a mistake on either side cannot "
                "leak or black-hole the other's routes. Private ASNs from 64512-65534 are used.",
                ["RFC 4271 (BGP-4)", "RFC 6996 (private ASNs)", "RFC 7454 (BGP filtering)"],
                plan["bgp"])
        log.add("L3 Routing", "BGP -> OSPF", "Redistribute VPC prefix into OSPF at " + hub,
                "Spokes keep a local Internet default route (split tunnelling), so the VPC prefix "
                "must be injected into OSPF as an E2 route by the hub that terminates the eBGP "
                "session; a route-map limits redistribution to the VPC CIDR only.",
                ["RFC 2328 section 2.3 (AS-external routes)"])
    return plan
