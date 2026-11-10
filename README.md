# NetArchitect: Recommendation & Config Engine

**CIC-307 Computer Networks mini-project.** Algorithmic network planning with a self-explaining architecture engine.

NetArchitect takes a preset or custom JSON description of an enterprise network and runs it through a set of rule
engines. It returns infrastructure recommendations (media, transceivers, topology tier, VLSM plan, routing design,
QoS) and copy-paste-ready **Cisco IOS configurations**. Every choice comes with an **architectural rationale**:
a natural-language justification backed by the arithmetic and the IEEE/RFC reference behind it.

It ships with both a **CLI** and a **web dashboard**, needs **no third-party runtime dependencies** (Python ≥ 3.10
stdlib only), and has a **pytest suite of 239 tests**.

```
Input Ingestion  ->  L1/L2 Media Engine  ->  L3 VLSM & Routing  ->  Explainable Exporter
preset / custom      distance & bandwidth    bitwise subnet          IOS configs + rationale log
JSON + validator     physics, optical        allocator, OSPF/BGP     + packet-flow verification
                     budget, PoE, RSTP       selection, QoS
```

---

## Quick start

```bash
pip install pytest          # only needed for the test suite
```

```bash
python -m netarchitect serve
```
Then open <http://127.0.0.1:8080>.

```bash
python -m netarchitect plan --preset campus_lan
```

```bash
python -m pytest
```

### CLI reference

| Command | Purpose |
|---|---|
| `python -m netarchitect presets` | List the 3 preset profiles |
| `python -m netarchitect plan --preset metro_man` | Full engine run, text report + rationale log |
| `python -m netarchitect plan --input examples/custom_branch_office.json --format json` | Run on custom JSON (`text`, `json`, `markdown`) |
| `python -m netarchitect plan --preset global_wan --configs` | Include the device configs in the text output |
| `python -m netarchitect plan --preset campus_lan --export out/` | Write the combined config file, per-device `.cfg` files, rationale `.md` and plan `.json` |
| `python -m netarchitect export-all --out exports` | Regenerate the three verification exports |
| `python -m netarchitect vlsm 192.168.1.0/24 100 50 25 --p2p 2` | Stand-alone VLSM calculator |
| `python -m netarchitect media --distance 150 --prefer copper` | Stand-alone L1 selector (this one raises `PhysicalDistanceViolationError`) |
| `python -m netarchitect wildcard 10.1.4.0/22` | Mask / wildcard / broadcast |
| `python -m netarchitect serve --port 8080` | Web dashboard |

**Exit codes:** `0` ok · `1` generic / unreadable file · `2` validation or address error · `3` physical distance
violation · `4` address-space exhaustion.

### Web dashboard

* **Scenario selector:** Campus LAN, Metro MAN, Global WAN, or Custom (edit the JSON, or load a file).
* **Overview:** KPIs, topology tier, routing design, warnings (e.g. low optical headroom, attenuator required).
* **Topology:** generated diagram colour-coded by medium, access-layer sizing, PoE budget, cabling plan.
* **L1 Media:** every link and cable run with its transceiver, optical loss vs budget, headroom and latency.
* **VLSM:** address map of the root prefix plus per-site tables (CIDR, mask, wildcard, gateway, range, broadcast,
  utilisation).
* **Routing & QoS:** OSPF areas and ABR summaries, eBGP peers, BFD, QoS classes, Dijkstra path latency including
  failover paths.
* **Configs:** per-device IOS with syntax highlighting, copy, `.cfg` download, and "download all".
* **Rationale:** the full architectural rationale log, filterable by domain and searchable.
* **Verification:** packet-flow simulation results (LPM overlap probes + ACL packet walks).
* **Tools:** media checker, VLSM calculator, wildcard calculator. Errors such as
  `PhysicalDistanceViolationError` show up as structured cards with the attenuation warning.

The JSON API is documented at the top of [netarchitect/web/server.py](netarchitect/web/server.py)
(`/api/plan`, `/api/vlsm`, `/api/media`, `/api/wildcard`, `/api/presets`). Domain errors return HTTP 422 with
`{error, code, message, details}`.

---

## Preset scenarios

| Profile | Scale | What the engine decides |
|---|---|---|
| **Campus LAN** (`campus_lan`) | 3 buildings, 250–380 m apart, 1,600 endpoints, 95 PoE APs | OM4 + 10GBASE-SR between buildings, Cat6a/10GBASE-T to desks, PoE budget, 41 access switches, 3-tier hierarchy, 802.1Q VLANs per building, Rapid-PVST+, guest isolation ACLs, **single-area OSPF** (24 subnets < 50) |
| **Metro MAN** (`metro_man`) | HQ + 2 remotes (22 / 35 km) + FinTech colo (15 km), 450 users | OS2 SMF with optical-budget-driven ER/ZR selection (plus an attenuator warning), carrier **EVPL** sub-interfaces, **dual-homed** primary/secondary circuits (OSPF cost 10/100), **BFD** 150 ms, hierarchical shaper + LLQ QoS, latency proof vs the **5 ms** budget including failover paths |
| **Global WAN** (`global_wan`) | NYC hub, London, Singapore, Mumbai + cloud VPC, 2,000 IoT scanners | Internet underlay + **GRE/IPsec** overlay, **multi-area OSPF** (one area per city) with **ABR summarisation** of contiguous site blocks, **eBGP** to the cloud VPC over IPsec VTI with prefix-list filtering, IoT least-privilege ACLs, ISP and cloud-gateway simulators so the lab runs end to end |

---

## Decision rules (explainable engine)

| Domain | Condition | Output + justification |
|---|---|---|
| L1 copper | run ≤ 100 m | Cat6a + 10GBASE-T (IEEE 802.3an 100 m channel; PoE 802.3bt) |
| L1 multimode | 100 m < run ≤ 400 m | OM4 + 10GBASE-SR (850 nm modal-dispersion limit; 3.5 dB/km + 1.5 dB connectors ≤ 2.9 dB) |
| L1 single-mode | run > 400 m | OS2 + the first of 10GBASE-LR → ER → ZR whose **budget** (fibre + connectors + splices + margin ≤ max loss) passes; also flags receiver overload (attenuator). Beyond 80 km: carrier service |
| L1 speed | > 10 Gbps | 40/100GBASE-SR4 within OM4 reach, otherwise LR4/ER4 |
| **Boundary error** | copper (or PoE) > 100 m, or copper > 10 Gbps | `PhysicalDistanceViolationError` with a projected Cat6a insertion-loss / attenuation warning |
| VLSM | root prefix + host array | hosts + gateway + net + bcast → 2^k, sort descending, bit-align, zero overlap, utilisation and FLSM-vs-VLSM rationale; per-site summary blocks |
| **Boundary error** | blocks > root | `AddressSpaceExhaustedError` giving required vs available addresses and the minimum prefix that would fit |
| L3 routing | single AS, < 50 subnets, no Internet WAN | OSPF area 0 (link-state, fast convergence) |
| L3 routing | ≥ 50 subnets or ≥ 3 sites over an Internet/IPsec WAN | Multi-area OSPF, area per site, `area N range` at the ABR |
| L3 routing | cloud VPC / external AS | eBGP (private ASNs, RFC 6996), aggregate out / VPC CIDR in, redistributed into OSPF |
| Resiliency | `dual_homed` | ≥ 2 diverse uplinks per site (validated), BFD, primary/secondary costs, failover latency checked |
| Topology tier | access-switch count, site count, network type | collapsed core / 3-tier / dual-homed hub-and-spoke / IPsec hub-and-spoke |

---

## Input schema (custom JSON)

```jsonc
{
  "name": "My network",
  "network_type": "campus | metro | wan",
  "root_prefix": "10.10.0.0/16",          // /8 - /30, host bits must be zero
  "p2p_prefix": 30,                        // or 31 (RFC 3021)
  "resiliency": "single | redundant | dual_homed",
  "latency_budget_ms": 5,                  // optional
  "optical_margin_db": 1.0, "growth_factor": 0.2, "ports_per_switch": 24,
  "hub": "HQ", "bgp_asn": 65010,           // optional
  "qos": {"classes": [{"name": "REALTIME", "dscp": "ef", "percent": 30, "priority": true}]},
  "sites": [{
    "name": "HQ", "aps": 10,
    "cloud": false, "vpc_cidr": "10.200.0.0/16", "asn": 64512,         // cloud sites only (wan)
    "vlans": [{"name": "USERS", "vlan_id": 10, "hosts": 250,
               "role": "data|voice|wireless|guest|mgmt|ap|iot|server", "qos_class": "REALTIME"}],
    "cable_runs": [{"name": "desk", "distance_m": 85, "bandwidth_gbps": 1,
                    "media": "auto|copper|fiber", "poe": false}]
  }],
  "links": [{"a": "HQ", "b": "BR1", "distance_km": 22, "bandwidth_gbps": 1,
             "media": "auto", "transport": "fiber|evpl|internet", "role": "primary|secondary"}]
}
```
The validator collects **all** issues in one pass: ranges, reserved VLANs (1, 998, 999, 1002–1005), duplicates,
unknown link endpoints, disconnected graphs, single points of failure under `redundant`, fewer than 2 uplinks
under `dual_homed`, VPC/root overlap, QoS over-subscription (> 75 %), and so on. See
[examples/](examples/) for one valid custom network and three inputs that deliberately trigger each error class.

---

## Verification exports (Packet Tracer / GNS3)

[exports/](exports/) holds the output for the three presets (regenerate with `python -m netarchitect export-all`):

* `<profile>_configs.txt`: **cabling plan** plus every device config in one file
* `<profile>/<DEVICE>.cfg`: one file per device, ready to paste
* `<profile>_rationale.md`: the rationale log; `<profile>_plan.json`: the full plan

**Loading a lab**
1. Add the devices named in the cabling plan. Use **Catalyst 3650-24PS** for `*-DSW1`, `*-ASW1`, `ISP-SW` and
   `CARRIER-EVPL-SIM`, and **ISR4331** for `*-RTR1`, `ISP-SIM` and `*-VGW-SIM`.
2. Cable the ports exactly as the cabling plan lists them. Fibre links need SFP/GLC modules.
3. Paste each `.cfg` into the device CLI (the file begins with `enable` / `configure terminal`).
4. Verify with `show ip ospf neighbor`, `show ip route ospf`, `show ip bgp summary`,
   `show crypto isakmp sa`, `show interfaces trunk`, `show spanning-tree root`, and pings between site LANs.

**Platform notes**
* *Campus LAN* uses only features Packet Tracer 8 supports (VLANs, trunks, SVIs, Rapid-PVST+, OSPF, DHCP, ACLs, SSH).
* *Metro MAN* and *Global WAN* use BFD, hierarchical QoS, IKE/IPsec profiles and VTI tunnels. These run fully on
  **GNS3 with IOSv / CSR1000v**. Packet Tracer ignores or rejects some of those lines; the OSPF/EVPL/GRE core
  still comes up.
* On IOSv/IOSvL2, rename the interfaces (e.g. `Gi0/0/0` → `Gi0/0`, `Gi1/0/1` → `Gi0/1`).
* Lab credentials (`NetArch-Lab-2026`), the deterministic IPsec PSKs and the RFC 5737 public addresses are
  placeholders. Replace them before any real deployment.

---

## Testing

```bash
python -m pytest
```

| File | Covers |
|---|---|
| `test_ipmath.py` | masks and wildcards for every prefix /0–/32 against `ipaddress`, non-contiguous masks, malformed addresses, host-sizing boundaries, 2,000 random network/broadcast checks |
| `test_media.py` | 100 m / 400 m / 10 km / 35 km / 80 km boundaries, copper and PoE distance violations, > 10 G copper, optical budget arithmetic, attenuator detection |
| `test_vlsm.py` | textbook allocation, order independence, 300-case randomised zero-overlap property test, exact fit, exhaustion (+ minimum prefix), /30, /31, /32, hierarchical summarisability |
| `test_validator_routing.py` | each validation rule, resiliency SPOF / dual-homing checks, OSPF area 0 vs multi-area vs ≥ 50-subnet switch-over, eBGP, BFD, latency budget incl. failover |
| `test_engine_configs.py` | all presets end to end; IOS lint (usable-host IPs, contiguous OSPF wildcards, constrained trunks, unique IPs, matching PSKs, no underlay in OSPF); exports |
| `test_cli_web.py` | CLI exit codes 0/1/2/3/4, the JSON API incl. 422 error payloads, bad JSON, path traversal |
| `test_ai_audit_regressions.py` | reproduces every flaw in [ai_audit_log.md](ai_audit_log.md) and proves the fix |

---

## Project layout

```
netarchitect/
  ipmath.py       bitwise IPv4 primitives (no ipaddress dependency)
  media.py        L1 engine: copper/MMF/SMF rules, optical budgets, PoE, latency
  vlsm.py         bitwise VLSM allocator, hierarchical per-site blocks, overlap verification
  routing.py      OSPF single/multi-area, ABR summaries, eBGP, BFD selection
  topology.py     access sizing, PoE budget, STP/trunk policy, topology tier, Dijkstra latency, QoS
  validator.py    parameter engine (collects every issue)
  configgen.py    Cisco IOS generator (DSW/ASW/router/simulators), structured ACLs
  packetflow.py   ACL evaluator + longest-prefix-match simulator
  rationale.py    architectural rationale log
  engine.py       pipeline orchestrator + verification
  cli.py          command-line interface
  presets/        campus_lan.json, metro_man.json, global_wan.json
  web/            stdlib HTTP server + static dashboard (HTML/CSS/JS, no build step)
tests/            pytest suite
examples/         custom JSON inputs (valid + one per error class)
exports/          verification exports for the three presets
ai_audit_log.md   AI code audit & defence log
```

## Assumptions & limitations

* IEEE 802.3 link-model attenuation (0.4 dB/km @1310 nm, 0.3 dB/km @1550 nm, 3.5 dB/km @850 nm), 0.75 dB per mated
  connector pair, and a 0.1 dB fusion splice every 4 km. These are conservative planning values. Real designs should
  use OTDR-measured plant loss.
* Internet path latency is estimated as cable distance × 1.4 at 204 km/ms. It is a planning figure, not a guarantee.
* Access-switch configs are **templates**, one per site; the rationale says how many to deploy.
* Single-vendor (Cisco IOS) output. Designs are IPv4 only.
