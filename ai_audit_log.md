# AI Code Audit Log — NetArchitect (CIC-307)

This log records places where AI-generated code or AI assumptions were **wrong in networking terms**, how each
fault was diagnosed, what the packet / signal path looks like when the fault is live, and the fix that ships.
Every instance has a regression test that fails against the buggy version.

| # | Category | Origin | Caught by | Regression test |
|---|---|---|---|---|
| 1 | Incorrect optical budget (nominal reach mistaken for a working link) | **Observed in this project** | media-engine boundary test | `tests/test_media.py::test_distance_rules`, `tests/test_ai_audit_regressions.py::test_instance4_*` |
| 2 | Trunk left negotiable (DTP on), plus the wider "unconstrained trunk" pattern | **Observed in this project** | config-lint test | `tests/test_engine_configs.py::test_trunks_are_constrained`, `test_instance5_*` |
| 3 | Bitwise wildcard errors: Python `~mask` sign, and a `0.0.0.0` wildcard read as a netmask | **Observed in this project** | IP-math test / config test | `test_instance1_*`, `tests/test_engine_configs.py::test_ospf_network_wildcards_are_inverse_masks` |
| 4 | Host count to prefix ignores network, broadcast and gateway | Common AI pattern, reproduced | IP-math test | `test_instance2_*`, `tests/test_ipmath.py::test_prefix_for_hosts_*` |
| 5 | VLSM without sorting or alignment, giving networks with host bits set | Common AI pattern, reproduced | VLSM oracle test | `test_instance3_*`, `tests/test_vlsm.py::test_randomised_property_zero_overlap` |

> **"Observed in this project"** means the flaw was actually produced by the AI assistant while this codebase was
> being generated and was caught by the test suite or by review before shipping. **"Common AI pattern,
> reproduced"** entries keep the typical buggy suggestion verbatim inside the regression tests, so the failure can be
> re-run on demand. *Student validator: re-run each test yourself, and feel free to add any instances from your own
> AI sessions in the same format.*

---

## Instance 1: Optical budget: "10 km is LR's reach, so a 10 km link uses 10GBASE-LR"

**Prompt to the AI assistant**
> Write pytest boundary tests for the L1 media engine: ≤100 m Cat6a, 101–400 m OM4, >400 m OS2, and check the
> SMF transceiver chosen at the reach limits.

**AI-generated code (buggy assumption)**
```python
@pytest.mark.parametrize("distance,medium,optic", [
    ...
    (10_000, "OS2 SMF", "10GBASE-LR"),     # "LR is rated for 10 km, so 10 km -> LR"
    (10_001, "OS2 SMF", "10GBASE-ER"),
])
```
The same reasoning shows up in the common "reach-only / fibre-only" budget helper that AI tools tend to suggest
(kept verbatim in `test_ai_audit_regressions.py`):
```python
def ai_er_ok(km):                 # fibre attenuation only, no connectors/splices/margin
    return km * 0.3 <= 11.0 and km <= 40
```

**What happened.** The engine picked **10GBASE-ER** for the 10 km case, so the test failed:
`AssertionError: assert '10GBASE-ER' == '10GBASE-LR'`. The engine was right. The AI's test was wrong.

**Technical analysis (optical power walk, IEEE 802.3 Clause 52 link model)**

| Element | 10 km on 10GBASE-LR (1310 nm) |
|---|---|
| Fibre: 10 km × 0.4 dB/km | 4.0 dB |
| 2 mated connector pairs × 0.75 dB (TIA-568 max) | 1.5 dB |
| Fusion splices: ⌈10/4⌉−1 = 2 × 0.1 dB | 0.2 dB |
| **Link loss** | **5.7 dB** |
| Safety margin (ageing, repair splices) | 1.0 dB |
| **Required budget** | **6.7 dB** |
| 10GBASE-LR max channel insertion loss | 6.2 dB → **FAIL (−0.5 dB)** |

Signal path: worst-case Tx launch power −8.2 dBm − 5.7 dB = −13.9 dBm at the receiver, against a −14.4 dBm
sensitivity. That leaves only 0.5 dB of headroom before a single repair splice or one dirty connector. At that point
the BER climbs past 10⁻¹², FCS errors appear on every frame, OSPF hellos start dropping, and the adjacency flaps.
*Nominal reach* assumes a perfect fibre plant. A *budget* is what a real plant actually allows.

The same mistake at 35 km: `ai_er_ok(35)` returns `True` (10.5 dB ≤ 11.0). The real loss is 10.5 + 1.5 + 0.8 =
12.8 dB, plus 1 dB of margin, giving 13.8 dB against an 11.0 dB budget. That link would never come up reliably. The
engine therefore selects **10GBASE-ZR**. It also checks the *minimum* loss: at 28 km the ZR link loses only 10.5 dB,
under ZR's 11 dB receiver-overload floor, so the engine warns that a 1 dB attenuator is needed.

**Fix.** `media.optical_budget()` sums fibre + connectors + splices + margin and checks *both* the maximum and
minimum channel loss. `select_media()` walks LR → ER → ZR → carrier and logs why each optic was rejected. The test
now expects ER at 10 km and LR at 5 km, with a comment giving the arithmetic.

---

## Instance 2: Trunk left with DTP enabled (and the "unconstrained trunk" pattern)

**Prompt to the AI assistant**
> Generate a lab "ISP switch" config: one access port per customer router in its own VLAN, and a trunk to the
> ISP router-on-a-stick.

**AI-generated code (as first emitted for `ISP-SW`)**
```
interface GigabitEthernet1/1/1
 description trunk to ISP-SIM
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 11,12,13,14,15
 no shutdown
```
The allowed list was pruned, but `switchport nonegotiate` was missing. The config-lint test caught it:
`AssertionError: ISP-SW: DTP left on`.

The more dangerous version of this flaw, which AI assistants commonly produce for access-to-distribution trunks:
```
interface GigabitEthernet0/1
 switchport mode trunk          ! native VLAN 1, all VLANs allowed, DTP on
```

**Packet-flow analysis**

*DTP left on.* The port keeps sending DTP frames (dst `01:00:0C:CC:CC:CC`, SNAP PID `0x2004`) every 30 s. Any
device that answers "desirable" negotiates a trunk. On a port that should not trunk, that is the classic
**switch-spoofing** attack: the attacker's NIC receives every VLAN. On this ISP link the risk is low because the far
end is a router, but it breaks the project's own trunk policy and, cloned to an edge port, it becomes an exploit.

*Unconstrained trunk + native VLAN 1.* A **double-tagging VLAN hop** works like this:
1. The attacker sits on an access port in VLAN 1, which is also the trunk's native VLAN, and sends
   `[802.1Q VID 1][802.1Q VID 140][IP to victim]`.
2. Access switch: the frame arrives in VLAN 1. On egress to the trunk, the native VLAN is sent **untagged**, so the
   switch strips only the outer tag.
3. Distribution switch: it receives a frame tagged VID 140 and switches it into the **GUEST/victim VLAN**. One-way
   traffic has crossed a Layer-2 boundary with no router or ACL in the path.
4. With `allowed vlan all`, every VLAN (including management) is reachable this way and every broadcast floods
   down every trunk.

**Fix.** Every trunk the generator emits now has an explicit allowed list (only that site's VLANs), native VLAN
**999** (unused, no SVI, no access ports), `switchport nonegotiate`, and unused ports shut in black-hole VLAN 998.
`test_trunks_are_constrained` parses every generated config, splits it into interface blocks, and fails if any
`switchport mode trunk` block lacks an allowed list or `nonegotiate`.

---

## Instance 3: Bitwise wildcard errors (two real slips)

### 3a: Python `~` on a netmask

**Prompt to the AI assistant**
> Add a regression test showing why `~mask` is wrong for wildcard masks in Python.

**AI-generated code**
```python
def ai_wildcard(prefix):
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return ~mask

assert ai_wildcard(24) == -4294967040      # AI's expected value: itself wrong
```
The test failed with `assert -4294967041 == -4294967040`. In Python, `~x == -(x + 1)`, so
`~0xFFFFFF00 = -4294967041`. The AI got the two's-complement arithmetic wrong in the very test meant to demonstrate
the bug.

**Why it matters.** Python integers are signed and unbounded, so `~mask` is never the 32-bit wildcard `0.0.0.255`.
The bug hides well. An octet formatter that uses `(n >> s) & 0xFF` still prints `0.0.0.255`, because the low 32
bits happen to be right, so the text looks correct. Arithmetic built on top of it breaks silently, though:
`broadcast = net | ~mask` comes out **negative**, and a standard overlap test `a_net <= b_bcast and b_net <= a_bcast`
then returns `False` for *every* pair. The VLSM overlap guard passes even when two subnets collide. Range-checked
converters, sorting and JSON/DB storage of the value break too.

### 3b: A `0.0.0.0` wildcard read as a netmask

**AI-generated test code**
```python
for net, wc in re.findall(r"^ network (IP) (IP) area \d+$", cfg, re.M):
    n = ipaddress.ip_network(f"{net}/{wc}")    # "ipaddress accepts host-mask form"
```
This crashed on `network 10.10.16.12 0.0.0.0 area 0` (a loopback /32):
`ValueError: 10.10.16.12/0 has host bits set`. The library is ambiguous for `0.0.0.0`. It treats it as **netmask /0**
(match everything), not as **wildcard /32** (match one host).

**Packet-flow analysis.** For `access-list 10 permit 10.10.16.12 0.0.0.0`, IOS compares
`(src & ~wc) == (net & ~wc)`. With wc = 0 every bit is compared, so only 10.10.16.12 matches. A tool that reads the
same text as a *netmask* gets mask = 0, so `src & 0 == net & 0` holds for **every** source. Walk a packet from
192.0.2.50: wildcard semantics give *no match → implicit deny*, while the misreading gives *permit*. A management-plane
ACL generated or audited this way silently opens SSH to the Internet.

**Fix.**
* `ipmath.wildcard()` is `~prefix_to_mask(p) & 0xFFFFFFFF`, never bare `~`. It is tested for every prefix /0–/32
  against `ipaddress.hostmask` and asserted non-negative.
* The config test now converts a wildcard to a prefix with explicit bit arithmetic
  (`prefix = 32 − wc.bit_length()`, and asserts `wc == 2^(32−prefix) − 1` so it is contiguous) before handing it to
  the oracle.
* `packetflow.Match.matches()` implements the router's comparison exactly. The engine walks DHCP, DNS, Internet,
  lateral-SMB and cloud-MQTT/SSH packets through every generated ACL; see the **Verification** tab or
  `plan["verification"]`.

---

## Instance 4: Host count to prefix: `32 − ceil(log2(hosts))` (common pattern, reproduced)

**Prompt**
> Write a Python function that returns the subnet prefix needed for N hosts.

**Typical AI answer**
```python
def prefix_for_hosts(hosts):
    return 32 - math.ceil(math.log2(hosts))
```

**Analysis.**

| Hosts | AI prefix | Usable | Problem |
|---|---|---|---|
| 1 | /32 | 1 (host route) | No room for a gateway; the LAN cannot exist |
| 64 | /26 | 62 | 2 hosts stranded, plus the gateway |
| 256 | /24 | 254 | Hosts 255 and 256 land on the broadcast address |

Packet walk for host #255 in 10.0.0.0/24: it would hold 10.0.0.255. An ARP request from the gateway for
10.0.0.255 is never sent, because the router treats .255 as directed broadcast. Return traffic to that "host" is
either dropped (`no ip directed-broadcast`) or flooded to every host in the VLAN. A ping to it from another subnet
becomes a smurf-style amplification vector.

**Fix.** `ipmath.prefix_for_hosts()` computes `needed = hosts + 1 gateway + 2 (network, broadcast)`, rounds up to
`2^k`, and returns `32 − k`. Tests check every power-of-two boundary (61/62, 125/126, 253/254, 509/510) and
assert that the next-smaller prefix would not fit.

---

## Instance 5: VLSM without sort or alignment (common pattern, reproduced)

**Prompt**
> Allocate subnets for 50 and 100 hosts from 192.168.1.0/24.

**Typical AI answer**
```python
cursor = int(net.network_address)
for h in hosts_list:                       # input order, no alignment
    prefix = 32 - math.ceil(math.log2(h + 2))
    out.append(f"{ipaddress.ip_address(cursor)}/{prefix}")
    cursor += 2 ** (32 - prefix)
# -> ['192.168.1.0/26', '192.168.1.64/25']
```

**Analysis.** `192.168.1.64/25` has host bits set. A /25 can only start at .0 or .128. IOS rejects
`ip address 192.168.1.65 255.255.255.128` on the second SVI with *"overlaps with Vlan10"*, because it normalises to
192.168.1.0/25, which contains the first /26. If the misaligned value is instead normalised silently by a tool,
packet walks show **two connected routes covering 192.168.1.10** (/26 and /25). Longest-prefix match sends the /26
range to the first VLAN, and the "/25 VLAN" hosts in .0–.63 become unreachable: their replies route to the wrong SVI.

**Fix.** `vlsm._pack()` sorts requests largest-first and aligns each block with
`(cursor + size − 1) & ~(size − 1)`. Because every block is a power of two, the descending order means zero gaps and
zero overlap. `verify_no_overlap()` sorts by network and asserts `broadcast < next.network` and
`network & wildcard == 0`. A 300-iteration randomised test checks every allocation against `ipaddress` (strict
networks, `subnet_of(root)`, pairwise `overlaps()`), and the engine proves zero overlap at runtime with an LPM
probe of every LAN.

---

## Validation method summary

1. **Independent oracle:** bitwise results are cross-checked against Python's `ipaddress`, never against the
   module under test.
2. **Packet walks:** `packetflow.py` evaluates generated ACLs entry by entry and resolves LPM over the allocated
   routes, so a wrong wildcard or overlapping subnet shows up as a wrong forwarding or permit decision.
3. **Config lint:** every generated config is parsed for usable-host interface addresses, contiguous OSPF
   wildcards, constrained trunks, unique IPs across devices, matching IPsec PSKs on both tunnel ends, and the WAN
   underlay never being advertised into OSPF (which would cause recursive tunnel routing).
4. **Physics checks:** optical budgets include connectors, splices, margin and receiver overload, not just nominal
   reach.
