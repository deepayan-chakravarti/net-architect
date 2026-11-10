# Metro MAN - NetArchitect plan

* **Topology tier:** Dual-homed hub-and-spoke over carrier EVPL
* **Routing:** Single-area OSPF
* **Root prefix:** 172.16.0.0/16
* **Verification:** 12/12 checks passed

## Architectural rationale

1. **[Input] Metro MAN - metro profile, 4 sites, 5 links, root 172.16.0.0/16**  
   Parameters validated: 800 hosts across 12 subnets, resiliency 'dual_homed', latency budget 5 ms.
2. **[L1 Media] HQ <-> REMOTE-1 - OS2 SMF + 10GBASE-ER (Carrier EVPL (MEF E-Line) over provider OS2)**  
   Selected OS2 Single-Mode Fiber because link distance (22 km) exceeds the 400 m attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for 10GBASE-ER at 1550 nm: 22.0 km x 0.3 dB/km = 6.6 dB fibre + 1.5 dB connectors + 5 splices x 0.1 dB = 8.6 dB, + 1.0 dB safety margin = 9.6 dB <= 11.0 dB maximum channel insertion loss (headroom 1.4 dB). Rejected: 10GBASE-LR: reach 10 km < 22 km. The 10G optic is the UNI port speed; the purchased EVC CIR of 1 Gbps is enforced by an egress shaper on the router.  _(IEEE 802.3ae Clause 52, ITU-T G.652.D, TIA-568.3-D)_
3. **[L1 Media] HQ <-> REMOTE-2 - OS2 SMF + 10GBASE-ZR (Carrier EVPL (MEF E-Line) over provider OS2)**  
   Selected OS2 Single-Mode Fiber because link distance (35 km) exceeds the 400 m attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for 10GBASE-ZR at 1550 nm: 35.0 km x 0.3 dB/km = 10.5 dB fibre + 1.5 dB connectors + 8 splices x 0.1 dB = 12.8 dB, + 1.0 dB safety margin = 13.8 dB <= 23.0 dB maximum channel insertion loss (headroom 9.2 dB). Rejected: 10GBASE-LR: reach 10 km < 35 km; 10GBASE-ER: needs 13.8 dB > 11.0 dB budget. The 10G optic is the UNI port speed; the purchased EVC CIR of 1 Gbps is enforced by an egress shaper on the router.  _(SFF MSA (non-IEEE), ITU-T G.652.D, TIA-568.3-D)_
4. **[L1 Media] HQ <-> COLO - OS2 SMF + 10GBASE-ER (Carrier EVPL (MEF E-Line) over provider OS2)**  
   Selected OS2 Single-Mode Fiber because link distance (15 km) exceeds the 400 m attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for 10GBASE-ER at 1550 nm: 15.0 km x 0.3 dB/km = 4.5 dB fibre + 1.5 dB connectors + 3 splices x 0.1 dB = 6.3 dB, + 1.0 dB safety margin = 7.3 dB <= 11.0 dB maximum channel insertion loss (headroom 3.7 dB). Rejected: 10GBASE-LR: reach 10 km < 15 km. The 10G optic is the UNI port speed; the purchased EVC CIR of 1 Gbps is enforced by an egress shaper on the router.  _(IEEE 802.3ae Clause 52, ITU-T G.652.D, TIA-568.3-D)_
5. **[L1 Media] REMOTE-1 <-> COLO - OS2 SMF + 10GBASE-ZR (Carrier EVPL (MEF E-Line) over provider OS2)**  
   Selected OS2 Single-Mode Fiber because link distance (28 km) exceeds the 400 m attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for 10GBASE-ZR at 1550 nm: 28.0 km x 0.3 dB/km = 8.4 dB fibre + 1.5 dB connectors + 6 splices x 0.1 dB = 10.5 dB, + 1.0 dB safety margin = 11.5 dB <= 23.0 dB maximum channel insertion loss (headroom 11.5 dB). Rejected: 10GBASE-LR: reach 10 km < 28 km; 10GBASE-ER: needs 11.5 dB > 11.0 dB budget. The 10G optic is the UNI port speed; the purchased EVC CIR of 1 Gbps is enforced by an egress shaper on the router.  _(SFF MSA (non-IEEE), ITU-T G.652.D, TIA-568.3-D)_
6. **[L1 Media] REMOTE-1 <-> COLO - WARNING**  
   10GBASE-ZR link loss 10.5 dB is below the 11.0 dB minimum; fit a 1 dB inline attenuator to avoid receiver overload.  _(SFF MSA (non-IEEE))_
7. **[L1 Media] REMOTE-2 <-> COLO - OS2 SMF + 10GBASE-ZR (Carrier EVPL (MEF E-Line) over provider OS2)**  
   Selected OS2 Single-Mode Fiber because link distance (30 km) exceeds the 400 m attenuation/dispersion limit of OM4 Multimode Fiber. Optical budget for 10GBASE-ZR at 1550 nm: 30.0 km x 0.3 dB/km = 9.0 dB fibre + 1.5 dB connectors + 7 splices x 0.1 dB = 11.2 dB, + 1.0 dB safety margin = 12.2 dB <= 23.0 dB maximum channel insertion loss (headroom 10.8 dB). Rejected: 10GBASE-LR: reach 10 km < 30 km; 10GBASE-ER: needs 12.2 dB > 11.0 dB budget. The 10G optic is the UNI port speed; the purchased EVC CIR of 1 Gbps is enforced by an egress shaper on the router.  _(SFF MSA (non-IEEE), ITU-T G.652.D, TIA-568.3-D)_
8. **[L2 Switching] HQ access layer - 13 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (250); 120 IP phones share the PC's port via the voice VLAN, so only port-consuming endpoints are counted. ceil(250 x (1 + 20% growth) / 24) = 13.  _(IEEE 802.1Q (voice VLAN))_
9. **[L2 Switching] HQ PoE budget - 1,848 W total, ~142 W per switch**  
   0 APs x 30 W (802.3at Class 4 at the PSE) + 120 phones x 15.4 W (802.3af) = 1,848 W. Specify PoE+ access switches with at least 150 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
10. **[L2 Switching] REMOTE-1 access layer - 6 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (120); 60 IP phones share the PC's port via the voice VLAN, so only port-consuming endpoints are counted. ceil(120 x (1 + 20% growth) / 24) = 6.  _(IEEE 802.1Q (voice VLAN))_
11. **[L2 Switching] REMOTE-1 PoE budget - 924 W total, ~154 W per switch**  
   0 APs x 30 W (802.3at Class 4 at the PSE) + 60 phones x 15.4 W (802.3af) = 924 W. Specify PoE+ access switches with at least 200 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
12. **[L2 Switching] REMOTE-2 access layer - 4 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (80); 40 IP phones share the PC's port via the voice VLAN, so only port-consuming endpoints are counted. ceil(80 x (1 + 20% growth) / 24) = 4.  _(IEEE 802.1Q (voice VLAN))_
13. **[L2 Switching] REMOTE-2 PoE budget - 616 W total, ~154 W per switch**  
   0 APs x 30 W (802.3at Class 4 at the PSE) + 40 phones x 15.4 W (802.3af) = 616 W. Specify PoE+ access switches with at least 200 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
14. **[L2 Switching] COLO access layer - 5 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (90), so only port-consuming endpoints are counted. ceil(90 x (1 + 20% growth) / 24) = 5.  _(IEEE 802.1Q (voice VLAN))_
15. **[L2 Switching] Spanning tree - Rapid PVST+ (802.1w per VLAN), root at distribution**  
   RSTP converges in under a second via proposal/agreement instead of 802.1D's 30-50 s listening/learning timers. The distribution switch is pinned as root (priority 4096) so the L2 forwarding path matches the L3 gateway, and PortFast + BPDU Guard on edge ports stop a rogue switch from triggering a topology change.  _(IEEE 802.1w, IEEE 802.1D-2004)_
16. **[L2 Switching] Trunk policy - 802.1Q trunks, explicit allowed list, native VLAN 999, DTP off**  
   Trunks carry only the VLANs that exist at that site (no 'allowed vlan all'), the native VLAN is moved to unused VLAN 999 and DTP is disabled with 'nonegotiate'. This blocks double-tagging VLAN hopping and switch-spoofing attacks; unused ports are shut down in black-hole VLAN 998.  _(IEEE 802.1Q, Cisco SAFE)_
17. **[Topology] Topology tier - Dual-homed hub-and-spoke over carrier EVPL**  
   Chosen because every remote site has diverse circuits to two hubs so the loss of one circuit or one hub never isolates a site.
18. **[L3 VLSM] HQ USERS - 172.16.0.0/24 (gw 172.16.0.1, bcast 172.16.0.255)**  
   250 hosts + 1 gateway + network + broadcast = 253 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 251 required. Utilisation 98.8% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
19. **[L3 VLSM] HQ VOICE - 172.16.1.0/25 (gw 172.16.1.1, bcast 172.16.1.127)**  
   120 hosts + 1 gateway + network + broadcast = 123 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 121 required. Utilisation 96.0% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
20. **[L3 VLSM] HQ MGMT - 172.16.1.128/27 (gw 172.16.1.129, bcast 172.16.1.159)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
21. **[L3 VLSM] Site block HQ - 172.16.0.0/23**  
   Sum of HQ's subnet blocks = 416 addresses, rounded up to the next power of two (512) so the whole site is one bit-aligned prefix /23. This lets the site be advertised as a single summary route (wildcard 0.0.1.255).  _(RFC 4632 (CIDR aggregation))_
22. **[L3 VLSM] REMOTE-1 USERS - 172.16.2.0/25 (gw 172.16.2.1, bcast 172.16.2.127)**  
   120 hosts + 1 gateway + network + broadcast = 123 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 121 required. Utilisation 96.0% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
23. **[L3 VLSM] REMOTE-1 VOICE - 172.16.2.128/26 (gw 172.16.2.129, bcast 172.16.2.191)**  
   60 hosts + 1 gateway + network + broadcast = 63 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 61 required. Utilisation 98.4% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
24. **[L3 VLSM] REMOTE-1 MGMT - 172.16.2.192/28 (gw 172.16.2.193, bcast 172.16.2.207)**  
   8 hosts + 1 gateway + network + broadcast = 11 addresses -> 2^4 = 16 block (/28); /29 would offer only 6 usable < 9 required. Utilisation 64.3% of 14 usable. Network address is a multiple of the 16-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
25. **[L3 VLSM] Site block REMOTE-1 - 172.16.2.0/24**  
   Sum of REMOTE-1's subnet blocks = 208 addresses, rounded up to the next power of two (256) so the whole site is one bit-aligned prefix /24. This lets the site be advertised as a single summary route (wildcard 0.0.0.255).  _(RFC 4632 (CIDR aggregation))_
26. **[L3 VLSM] REMOTE-2 USERS - 172.16.3.0/25 (gw 172.16.3.1, bcast 172.16.3.127)**  
   80 hosts + 1 gateway + network + broadcast = 83 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 81 required. Utilisation 64.3% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
27. **[L3 VLSM] REMOTE-2 VOICE - 172.16.3.128/26 (gw 172.16.3.129, bcast 172.16.3.191)**  
   40 hosts + 1 gateway + network + broadcast = 43 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 41 required. Utilisation 66.1% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
28. **[L3 VLSM] REMOTE-2 MGMT - 172.16.3.192/28 (gw 172.16.3.193, bcast 172.16.3.207)**  
   8 hosts + 1 gateway + network + broadcast = 11 addresses -> 2^4 = 16 block (/28); /29 would offer only 6 usable < 9 required. Utilisation 64.3% of 14 usable. Network address is a multiple of the 16-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
29. **[L3 VLSM] Site block REMOTE-2 - 172.16.3.0/24**  
   Sum of REMOTE-2's subnet blocks = 208 addresses, rounded up to the next power of two (256) so the whole site is one bit-aligned prefix /24. This lets the site be advertised as a single summary route (wildcard 0.0.0.255).  _(RFC 4632 (CIDR aggregation))_
30. **[L3 VLSM] COLO TRADING-SRV - 172.16.4.0/26 (gw 172.16.4.1, bcast 172.16.4.63)**  
   60 hosts + 1 gateway + network + broadcast = 63 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 61 required. Utilisation 98.4% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
31. **[L3 VLSM] COLO MKT-DATA - 172.16.4.64/26 (gw 172.16.4.65, bcast 172.16.4.127)**  
   30 hosts + 1 gateway + network + broadcast = 33 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 31 required. Utilisation 50.0% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
32. **[L3 VLSM] COLO MGMT - 172.16.4.128/28 (gw 172.16.4.129, bcast 172.16.4.143)**  
   8 hosts + 1 gateway + network + broadcast = 11 addresses -> 2^4 = 16 block (/28); /29 would offer only 6 usable < 9 required. Utilisation 64.3% of 14 usable. Network address is a multiple of the 16-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
33. **[L3 VLSM] Site block COLO - 172.16.4.0/24**  
   Sum of COLO's subnet blocks = 144 addresses, rounded up to the next power of two (256) so the whole site is one bit-aligned prefix /24. This lets the site be advertised as a single summary route (wildcard 0.0.0.255).  _(RFC 4632 (CIDR aggregation))_
34. **[L3 VLSM] Site block INFRA - 172.16.5.0/27**  
   Sum of INFRA's subnet blocks = 24 addresses, rounded up to the next power of two (32) so the whole site is one bit-aligned prefix /27. This lets the site be advertised as a single summary route (wildcard 0.0.0.31).  _(RFC 4632 (CIDR aggregation))_
35. **[L3 VLSM] Root utilisation - 2.0% of 172.16.0.0/16**  
   21 subnets packed largest-first with zero overlap (verified by sorting on network address and checking each broadcast < next network). Host demand fills 82.6% of allocated addresses. A fixed-length design using the largest LAN block everywhere would consume 3,096 addresses vs 1,000 with VLSM.  _(RFC 1878, RFC 4632)_
36. **[L3 Routing] Interior gateway protocol - OSPFv2 single area 0**  
   Although there are 4 sites, the carrier EVPL circuits are Layer-2 point-to-point Ethernet, so all routers form direct OSPF adjacencies as if on one campus. The design is a single autonomous system with 21 subnets (< 50), so one LSDB stays small and SPF runs in milliseconds. A link-state protocol gives sub-second-to-seconds convergence without the hop-count limits and slow count-to-infinity behaviour of distance-vector RIP, and avoids the ABR/summarisation complexity that multi-area would add with no scaling benefit.  _(RFC 2328 (OSPFv2))_
37. **[L3 Routing] OSPF reference bandwidth - auto-cost reference-bandwidth 100000**  
   The default 100 Mbps reference gives FastEthernet, 1G and 10G links the same cost (1). Raising it to 100 Gbps makes cost = 100000 / link Mbps, so 10G = 10, 1G = 100 and SPF prefers the faster path. Must be identical on every router.  _(RFC 2328 Appendix C.3)_
38. **[L3 Routing] Failure detection - BFD 50 ms x 3 on WAN links + cost-based primary**  
   Dual-homed failover requires detecting a carrier fault faster than OSPF's 40 s dead interval. BFD (50 ms interval, multiplier 3) declares the neighbour down in 150 ms and triggers immediate SPF; primary circuits use OSPF cost 10 and secondary circuits cost 100 so traffic only shifts on failure.  _(RFC 5880 (BFD), RFC 5882 (BFD for OSPF))_
39. **[QoS & Latency] Latency budget - Worst path REMOTE-1 -> HQ -> REMOTE-2 = 0.379 ms one-way (within 5 ms)**  
   Propagation in fibre is ~4.9 us/km (c / n with n ~ 1.47) plus a 0.05 ms forwarding allowance per hop. The worst site pair uses 7.6% of the 5 ms budget, so the remainder is reserved for queuing delay - which is why latency-sensitive classes get a strict-priority (LLQ) queue rather than relying on raw link speed.  _(ITU-T G.114, RFC 4594)_
40. **[QoS & Latency] Failover latency - Worst failover path HQ -> REMOTE-1 -> COLO = 0.345 ms (within 5 ms)**  
   Each primary circuit was removed in turn and the shortest surviving path recomputed (Dijkstra on latency). The worst case after a single failure still meets the budget, so dual-homing preserves the latency SLA, not just reachability.  _(RFC 2328 (SPF), ITU-T G.114)_
41. **[QoS & Latency] WAN edge QoS - Hierarchical shaper + LLQ: REALTIME (DSCP EF, priority 30%), TRADING (DSCP AF41, 30%), MGMT (DSCP CS6, 5%)**  
   An EVPL is sold at a committed information rate, so the router first shapes to the CIR (otherwise the carrier polices excess and drops indiscriminately) and then queues inside the shaper: REALTIME uses the strict-priority LLQ to bound jitter and delay for sub-5 ms trading/voice flows, assured-forwarding classes get guaranteed minimum bandwidth, and class-default uses fair-queue. Traffic is marked by source subnet at the LAN ingress (wildcard-mask ACLs) so the classification is enforced at the trust boundary. IOS requires the shaper parent because CBWFQ cannot attach directly to a sub-interface.  _(RFC 4594 (DiffServ classes), RFC 3246 (EF PHB), RFC 2597 (AF PHB), MEF 10.3)_
42. **[Verification] Packet-flow simulation - 12/12 checks passed**  
   Every LAN's last usable address was resolved by longest-prefix match to exactly one subnet (proves zero overlap), and representative flows (DHCP, DNS, Internet, lateral SMB, cloud MQTT/SSH) were walked through each generated ACL entry-by-entry using the same wildcard arithmetic the router applies.

## Device configurations

### HQ-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - HQ-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, OSPF area 0
! Site block: 172.16.0.0/23
! ======================================================================
enable
configure terminal
!
hostname HQ-RTR1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- QoS: LAN ingress marking + hierarchical WAN egress (shaper -> LLQ) ---
ip access-list extended QOS-REALTIME
 remark HQ VOICE
 permit ip 172.16.1.0 0.0.0.127 any
class-map match-any MARK-REALTIME
 match access-group name QOS-REALTIME
policy-map LAN-MARKING
 class MARK-REALTIME
  set dscp ef
class-map match-any REALTIME
 match dscp ef
class-map match-any TRADING
 match dscp af41
class-map match-any MGMT
 match dscp cs6
policy-map WAN-QUEUING
 class REALTIME
  priority percent 30
 class TRADING
  bandwidth percent 30
 class MGMT
  bandwidth percent 5
 class class-default
  fair-queue
policy-map WAN-SHAPE-1000M
 class class-default
  shape average 1000000000
  service-policy WAN-QUEUING
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 172.16.5.20 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to HQ-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 172.16.0.0/24 (250 hosts)
 encapsulation dot1Q 10
 ip address 172.16.0.1 255.255.255.0
interface GigabitEthernet0/0/0.20
 description VOICE gateway 172.16.1.0/25 (120 hosts)
 encapsulation dot1Q 20
 ip address 172.16.1.1 255.255.255.128
 service-policy input LAN-MARKING
interface GigabitEthernet0/0/0.99
 description MGMT gateway 172.16.1.128/27 (16 hosts)
 encapsulation dot1Q 99
 ip address 172.16.1.129 255.255.255.224
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Carrier EVPL circuits (one dot1Q EVC per sub-interface) ---
interface GigabitEthernet0/0/1
 description EVPL UNI - primary
 no ip address
 no shutdown
interface GigabitEthernet0/0/1.3001
 description EVC 3001 to REMOTE-1-RTR1 - primary (OS2 SMF 10GBASE-ER 22km)
 encapsulation dot1Q 3001
 ip address 172.16.5.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/1.3002
 description EVC 3002 to REMOTE-2-RTR1 - primary (OS2 SMF 10GBASE-ZR 35km)
 encapsulation dot1Q 3002
 ip address 172.16.5.5 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/1.3003
 description EVC 3003 to COLO-RTR1 - primary (OS2 SMF 10GBASE-ER 15km)
 encapsulation dot1Q 3003
 ip address 172.16.5.9 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 172.16.0.1
ip dhcp excluded-address 172.16.1.1
ip dhcp pool HQ-USERS
 network 172.16.0.0 255.255.255.0
 default-router 172.16.0.1
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
ip dhcp pool HQ-VOICE
 network 172.16.1.0 255.255.255.128
 default-router 172.16.1.1
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 172.16.5.20
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet0/0/1.3001
 no passive-interface GigabitEthernet0/0/1.3002
 no passive-interface GigabitEthernet0/0/1.3003
 network 172.16.5.20 0.0.0.0 area 0
 network 172.16.5.0 0.0.0.3 area 0
 network 172.16.5.4 0.0.0.3 area 0
 network 172.16.5.8 0.0.0.3 area 0
 network 172.16.0.0 0.0.0.255 area 0
 network 172.16.1.0 0.0.0.127 area 0
 network 172.16.1.128 0.0.0.31 area 0
 bfd all-interfaces
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 4
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### REMOTE-1-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - REMOTE-1-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, OSPF area 0
! Site block: 172.16.2.0/24
! ======================================================================
enable
configure terminal
!
hostname REMOTE-1-RTR1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- QoS: LAN ingress marking + hierarchical WAN egress (shaper -> LLQ) ---
ip access-list extended QOS-REALTIME
 remark REMOTE-1 VOICE
 permit ip 172.16.2.128 0.0.0.63 any
class-map match-any MARK-REALTIME
 match access-group name QOS-REALTIME
policy-map LAN-MARKING
 class MARK-REALTIME
  set dscp ef
class-map match-any REALTIME
 match dscp ef
class-map match-any TRADING
 match dscp af41
class-map match-any MGMT
 match dscp cs6
policy-map WAN-QUEUING
 class REALTIME
  priority percent 30
 class TRADING
  bandwidth percent 30
 class MGMT
  bandwidth percent 5
 class class-default
  fair-queue
policy-map WAN-SHAPE-1000M
 class class-default
  shape average 1000000000
  service-policy WAN-QUEUING
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 172.16.5.21 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to REMOTE-1-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 172.16.2.0/25 (120 hosts)
 encapsulation dot1Q 10
 ip address 172.16.2.1 255.255.255.128
interface GigabitEthernet0/0/0.20
 description VOICE gateway 172.16.2.128/26 (60 hosts)
 encapsulation dot1Q 20
 ip address 172.16.2.129 255.255.255.192
 service-policy input LAN-MARKING
interface GigabitEthernet0/0/0.99
 description MGMT gateway 172.16.2.192/28 (8 hosts)
 encapsulation dot1Q 99
 ip address 172.16.2.193 255.255.255.240
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Carrier EVPL circuits (one dot1Q EVC per sub-interface) ---
interface GigabitEthernet0/0/1
 description EVPL UNI - primary
 no ip address
 no shutdown
interface GigabitEthernet0/0/2
 description EVPL UNI - secondary (diverse path)
 no ip address
 no shutdown
interface GigabitEthernet0/0/1.3001
 description EVC 3001 to HQ-RTR1 - primary (OS2 SMF 10GBASE-ER 22km)
 encapsulation dot1Q 3001
 ip address 172.16.5.2 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/2.3004
 description EVC 3004 to COLO-RTR1 - secondary (OS2 SMF 10GBASE-ZR 28km)
 encapsulation dot1Q 3004
 ip address 172.16.5.13 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 100
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 172.16.2.1
ip dhcp excluded-address 172.16.2.129
ip dhcp pool REMOTE-1-USERS
 network 172.16.2.0 255.255.255.128
 default-router 172.16.2.1
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
ip dhcp pool REMOTE-1-VOICE
 network 172.16.2.128 255.255.255.192
 default-router 172.16.2.129
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 172.16.5.21
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet0/0/1.3001
 no passive-interface GigabitEthernet0/0/2.3004
 network 172.16.5.21 0.0.0.0 area 0
 network 172.16.5.0 0.0.0.3 area 0
 network 172.16.5.12 0.0.0.3 area 0
 network 172.16.2.0 0.0.0.127 area 0
 network 172.16.2.128 0.0.0.63 area 0
 network 172.16.2.192 0.0.0.15 area 0
 bfd all-interfaces
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 4
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### REMOTE-2-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - REMOTE-2-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, OSPF area 0
! Site block: 172.16.3.0/24
! ======================================================================
enable
configure terminal
!
hostname REMOTE-2-RTR1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- QoS: LAN ingress marking + hierarchical WAN egress (shaper -> LLQ) ---
ip access-list extended QOS-REALTIME
 remark REMOTE-2 VOICE
 permit ip 172.16.3.128 0.0.0.63 any
class-map match-any MARK-REALTIME
 match access-group name QOS-REALTIME
policy-map LAN-MARKING
 class MARK-REALTIME
  set dscp ef
class-map match-any REALTIME
 match dscp ef
class-map match-any TRADING
 match dscp af41
class-map match-any MGMT
 match dscp cs6
policy-map WAN-QUEUING
 class REALTIME
  priority percent 30
 class TRADING
  bandwidth percent 30
 class MGMT
  bandwidth percent 5
 class class-default
  fair-queue
policy-map WAN-SHAPE-1000M
 class class-default
  shape average 1000000000
  service-policy WAN-QUEUING
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 172.16.5.22 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to REMOTE-2-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 172.16.3.0/25 (80 hosts)
 encapsulation dot1Q 10
 ip address 172.16.3.1 255.255.255.128
interface GigabitEthernet0/0/0.20
 description VOICE gateway 172.16.3.128/26 (40 hosts)
 encapsulation dot1Q 20
 ip address 172.16.3.129 255.255.255.192
 service-policy input LAN-MARKING
interface GigabitEthernet0/0/0.99
 description MGMT gateway 172.16.3.192/28 (8 hosts)
 encapsulation dot1Q 99
 ip address 172.16.3.193 255.255.255.240
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Carrier EVPL circuits (one dot1Q EVC per sub-interface) ---
interface GigabitEthernet0/0/1
 description EVPL UNI - primary
 no ip address
 no shutdown
interface GigabitEthernet0/0/2
 description EVPL UNI - secondary (diverse path)
 no ip address
 no shutdown
interface GigabitEthernet0/0/1.3002
 description EVC 3002 to HQ-RTR1 - primary (OS2 SMF 10GBASE-ZR 35km)
 encapsulation dot1Q 3002
 ip address 172.16.5.6 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/2.3005
 description EVC 3005 to COLO-RTR1 - secondary (OS2 SMF 10GBASE-ZR 30km)
 encapsulation dot1Q 3005
 ip address 172.16.5.17 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 100
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 172.16.3.1
ip dhcp excluded-address 172.16.3.129
ip dhcp pool REMOTE-2-USERS
 network 172.16.3.0 255.255.255.128
 default-router 172.16.3.1
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
ip dhcp pool REMOTE-2-VOICE
 network 172.16.3.128 255.255.255.192
 default-router 172.16.3.129
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 172.16.5.22
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet0/0/1.3002
 no passive-interface GigabitEthernet0/0/2.3005
 network 172.16.5.22 0.0.0.0 area 0
 network 172.16.5.4 0.0.0.3 area 0
 network 172.16.5.16 0.0.0.3 area 0
 network 172.16.3.0 0.0.0.127 area 0
 network 172.16.3.128 0.0.0.63 area 0
 network 172.16.3.192 0.0.0.15 area 0
 bfd all-interfaces
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 4
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### COLO-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - COLO-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, OSPF area 0
! Site block: 172.16.4.0/24
! ======================================================================
enable
configure terminal
!
hostname COLO-RTR1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- QoS: LAN ingress marking + hierarchical WAN egress (shaper -> LLQ) ---
ip access-list extended QOS-REALTIME
 remark COLO MKT-DATA
 permit ip 172.16.4.64 0.0.0.63 any
ip access-list extended QOS-TRADING
 remark COLO TRADING-SRV
 permit ip 172.16.4.0 0.0.0.63 any
class-map match-any MARK-REALTIME
 match access-group name QOS-REALTIME
class-map match-any MARK-TRADING
 match access-group name QOS-TRADING
policy-map LAN-MARKING
 class MARK-REALTIME
  set dscp ef
 class MARK-TRADING
  set dscp af41
class-map match-any REALTIME
 match dscp ef
class-map match-any TRADING
 match dscp af41
class-map match-any MGMT
 match dscp cs6
policy-map WAN-QUEUING
 class REALTIME
  priority percent 30
 class TRADING
  bandwidth percent 30
 class MGMT
  bandwidth percent 5
 class class-default
  fair-queue
policy-map WAN-SHAPE-1000M
 class class-default
  shape average 1000000000
  service-policy WAN-QUEUING
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 172.16.5.23 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to COLO-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.30
 description TRADING-SRV gateway 172.16.4.0/26 (60 hosts)
 encapsulation dot1Q 30
 ip address 172.16.4.1 255.255.255.192
 service-policy input LAN-MARKING
interface GigabitEthernet0/0/0.40
 description MKT-DATA gateway 172.16.4.64/26 (30 hosts)
 encapsulation dot1Q 40
 ip address 172.16.4.65 255.255.255.192
 service-policy input LAN-MARKING
interface GigabitEthernet0/0/0.99
 description MGMT gateway 172.16.4.128/28 (8 hosts)
 encapsulation dot1Q 99
 ip address 172.16.4.129 255.255.255.240
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Carrier EVPL circuits (one dot1Q EVC per sub-interface) ---
interface GigabitEthernet0/0/1
 description EVPL UNI - primary
 no ip address
 no shutdown
interface GigabitEthernet0/0/2
 description EVPL UNI - secondary (diverse path)
 no ip address
 no shutdown
interface GigabitEthernet0/0/1.3003
 description EVC 3003 to HQ-RTR1 - primary (OS2 SMF 10GBASE-ER 15km)
 encapsulation dot1Q 3003
 ip address 172.16.5.10 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 10
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/2.3004
 description EVC 3004 to REMOTE-1-RTR1 - secondary (OS2 SMF 10GBASE-ZR 28km)
 encapsulation dot1Q 3004
 ip address 172.16.5.14 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 100
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
interface GigabitEthernet0/0/2.3005
 description EVC 3005 to REMOTE-2-RTR1 - secondary (OS2 SMF 10GBASE-ZR 30km)
 encapsulation dot1Q 3005
 ip address 172.16.5.18 255.255.255.252
 ip ospf network point-to-point
 ip ospf cost 100
 bfd interval 50 min_rx 50 multiplier 3
 service-policy output WAN-SHAPE-1000M
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 172.16.4.1
ip dhcp excluded-address 172.16.4.65
ip dhcp pool COLO-TRADING-SRV
 network 172.16.4.0 255.255.255.192
 default-router 172.16.4.1
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
ip dhcp pool COLO-MKT-DATA
 network 172.16.4.64 255.255.255.192
 default-router 172.16.4.65
 dns-server 1.1.1.1
 domain-name metro.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 172.16.5.23
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet0/0/1.3003
 no passive-interface GigabitEthernet0/0/2.3004
 no passive-interface GigabitEthernet0/0/2.3005
 network 172.16.5.23 0.0.0.0 area 0
 network 172.16.5.8 0.0.0.3 area 0
 network 172.16.5.12 0.0.0.3 area 0
 network 172.16.5.16 0.0.0.3 area 0
 network 172.16.4.0 0.0.0.63 area 0
 network 172.16.4.64 0.0.0.63 area 0
 network 172.16.4.128 0.0.0.15 area 0
 bfd all-interfaces
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 4
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### HQ-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - HQ-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 13 access switch(es) in HQ; increment the hostname and the Vlan99 address (next free host in 172.16.1.128/27).
! ======================================================================
enable
configure terminal
!
hostname HQ-ASW1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 10
 name USERS
vlan 20
 name VOICE
vlan 99
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 172.16.1.130 255.255.255.224
 no shutdown
ip default-gateway 172.16.1.129
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 22
 description USERS endpoints + IP phone
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 20
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to HQ-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20,99,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/1/2 - 4
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 15
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### REMOTE-1-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - REMOTE-1-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 6 access switch(es) in REMOTE-1; increment the hostname and the Vlan99 address (next free host in 172.16.2.192/28).
! ======================================================================
enable
configure terminal
!
hostname REMOTE-1-ASW1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 10
 name USERS
vlan 20
 name VOICE
vlan 99
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 172.16.2.194 255.255.255.240
 no shutdown
ip default-gateway 172.16.2.193
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 22
 description USERS endpoints + IP phone
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 20
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to REMOTE-1-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20,99,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/1/2 - 4
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 15
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### REMOTE-2-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - REMOTE-2-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 4 access switch(es) in REMOTE-2; increment the hostname and the Vlan99 address (next free host in 172.16.3.192/28).
! ======================================================================
enable
configure terminal
!
hostname REMOTE-2-ASW1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 10
 name USERS
vlan 20
 name VOICE
vlan 99
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 172.16.3.194 255.255.255.240
 no shutdown
ip default-gateway 172.16.3.193
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 22
 description USERS endpoints + IP phone
 switchport mode access
 switchport access vlan 10
 switchport voice vlan 20
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to REMOTE-2-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20,99,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/1/2 - 4
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 15
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### COLO-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - COLO-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 5 access switch(es) in COLO; increment the hostname and the Vlan99 address (next free host in 172.16.4.128/28).
! ======================================================================
enable
configure terminal
!
hostname COLO-ASW1
no ip domain-lookup
ip domain-name metro.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 30
 name TRADING-SRV
vlan 40
 name MKT-DATA
vlan 99
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 172.16.4.130 255.255.255.240
 no shutdown
ip default-gateway 172.16.4.129
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 14
 description TRADING-SRV endpoints
 switchport mode access
 switchport access vlan 30
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/15 - 22
 description MKT-DATA endpoints
 switchport mode access
 switchport access vlan 40
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to COLO-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 30,40,99,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/1/2 - 4
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark HQ MGMT
 permit 172.16.1.128 0.0.0.31
 remark REMOTE-1 MGMT
 permit 172.16.2.192 0.0.0.15
 remark REMOTE-2 MGMT
 permit 172.16.3.192 0.0.0.15
 remark COLO MGMT
 permit 172.16.4.128 0.0.0.15
 deny any log
crypto key generate rsa modulus 2048
ip ssh version 2
line con 0
 logging synchronous
 exec-timeout 15 0
 login local
line vty 0 15
 access-class VTY-MGMT in
 exec-timeout 15 0
 login local
 transport input ssh
!
end
write memory
```

### CARRIER-EVPL-SIM

```cisco
! ======================================================================
! NetArchitect generated configuration - CARRIER-EVPL-SIM
! Platform : Cisco Catalyst 3650 (lab carrier EVPL simulator)
! Scenario : Metro MAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Emulates the provider metro-Ethernet network: one VLAN per EVC, UNI ports trunk only the EVCs ordered for that site.
! ======================================================================
enable
configure terminal
!
hostname CARRIER-EVPL-SIM
no ip domain-lookup
spanning-tree mode rapid-pvst
vlan 3001
 name EVC-3001
vlan 3002
 name EVC-3002
vlan 3003
 name EVC-3003
vlan 3004
 name EVC-3004
vlan 3005
 name EVC-3005
interface GigabitEthernet1/0/1
 description UNI COLO-RTR1 GigabitEthernet0/0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3003
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/2
 description UNI COLO-RTR1 GigabitEthernet0/0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3004,3005
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/3
 description UNI HQ-RTR1 GigabitEthernet0/0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3001,3002,3003
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/4
 description UNI REMOTE-1-RTR1 GigabitEthernet0/0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3001
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/5
 description UNI REMOTE-1-RTR1 GigabitEthernet0/0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3004
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/6
 description UNI REMOTE-2-RTR1 GigabitEthernet0/0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3002
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
interface GigabitEthernet1/0/7
 description UNI REMOTE-2-RTR1 GigabitEthernet0/0/2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 3005
 switchport nonegotiate
 spanning-tree portfast trunk
 no shutdown
!
end
write memory
```
