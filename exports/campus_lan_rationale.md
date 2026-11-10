# Campus LAN - NetArchitect plan

* **Topology tier:** Three-tier hierarchical (core / distribution / access)
* **Routing:** Single-area OSPF
* **Root prefix:** 10.10.0.0/16
* **Verification:** 30/30 checks passed

## Architectural rationale

1. **[Input] Campus LAN - campus profile, 3 sites, 3 links, root 10.10.0.0/16**  
   Parameters validated: 1,751 hosts across 18 subnets, resiliency 'redundant'.
2. **[L1 Media] BLDG-A <-> BLDG-B - OM4 MMF + 10GBASE-SR**  
   Selected OM4 multimode because 250 m exceeds the 100 m copper channel limit of IEEE 802.3an, while staying within the 400 m reach of 10GBASE-SR at 850 nm. Reach on multimode is bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), not attenuation. Loss check: 0.25 km x 3.5 dB/km + 1.5 dB connectors = 2.38 dB <= 2.9 dB channel budget (headroom 0.52 dB). VCSEL-based SR optics are cheaper than single-mode lasers.  _(IEEE 802.3ae Clause 52, TIA-492AAAD (OM4))_
3. **[L1 Media] BLDG-A <-> BLDG-C - OM4 MMF + 10GBASE-SR**  
   Selected OM4 multimode because 380 m exceeds the 100 m copper channel limit of IEEE 802.3an, while staying within the 400 m reach of 10GBASE-SR at 850 nm. Reach on multimode is bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), not attenuation. Loss check: 0.38 km x 3.5 dB/km + 1.5 dB connectors = 2.83 dB <= 2.9 dB channel budget (headroom 0.07 dB). VCSEL-based SR optics are cheaper than single-mode lasers.  _(IEEE 802.3ae Clause 52, TIA-492AAAD (OM4))_
4. **[L1 Media] BLDG-A <-> BLDG-C - WARNING**  
   Optical headroom only 0.07 dB on 10GBASE-SR; clean/inspect connectors or reduce patch points.
5. **[L1 Media] BLDG-B <-> BLDG-C - OM4 MMF + 10GBASE-SR**  
   Selected OM4 multimode because 320 m exceeds the 100 m copper channel limit of IEEE 802.3an, while staying within the 400 m reach of 10GBASE-SR at 850 nm. Reach on multimode is bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), not attenuation. Loss check: 0.32 km x 3.5 dB/km + 1.5 dB connectors = 2.62 dB <= 2.9 dB channel budget (headroom 0.28 dB). VCSEL-based SR optics are cheaper than single-mode lasers.  _(IEEE 802.3ae Clause 52, TIA-492AAAD (OM4))_
6. **[L1 Media] BLDG-B <-> BLDG-C - WARNING**  
   Optical headroom only 0.28 dB on 10GBASE-SR; clean/inspect connectors or reduce patch points.
7. **[L1 Media] BLDG-A IDF to desk (horizontal) - Cat6a UTP + 10GBASE-T**  
   Run length 85 m is within the 100 m channel limit of IEEE 802.3an (90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports 10GBASE-T at full reach and costs far less than optics.  _(IEEE 802.3an, TIA-568.2-D)_
8. **[L1 Media] BLDG-A Ceiling AP drop - Cat6a UTP + 10GBASE-T**  
   Run length 90 m is within the 100 m channel limit of IEEE 802.3an (90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports 10GBASE-T at full reach and costs far less than optics. The run also carries PoE (IEEE 802.3bt Type 4, up to 90 W PSE), which is only possible on copper and is specified to the same 100 m channel.  _(IEEE 802.3an, TIA-568.2-D, IEEE 802.3bt)_
9. **[L1 Media] BLDG-A MDF to floor-4 IDF riser - OM4 MMF + 10GBASE-SR**  
   Selected OM4 multimode because 140 m exceeds the 100 m copper channel limit of IEEE 802.3an, while staying within the 400 m reach of 10GBASE-SR at 850 nm. Reach on multimode is bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), not attenuation. Loss check: 0.14 km x 3.5 dB/km + 1.5 dB connectors = 1.99 dB <= 2.9 dB channel budget (headroom 0.91 dB). VCSEL-based SR optics are cheaper than single-mode lasers.  _(IEEE 802.3ae Clause 52, TIA-492AAAD (OM4))_
10. **[L1 Media] BLDG-B IDF to desk (horizontal) - Cat6a UTP + 10GBASE-T**  
   Run length 72 m is within the 100 m channel limit of IEEE 802.3an (90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports 10GBASE-T at full reach and costs far less than optics.  _(IEEE 802.3an, TIA-568.2-D)_
11. **[L1 Media] BLDG-B Ceiling AP drop - Cat6a UTP + 10GBASE-T**  
   Run length 64 m is within the 100 m channel limit of IEEE 802.3an (90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports 10GBASE-T at full reach and costs far less than optics. The run also carries PoE (IEEE 802.3bt Type 4, up to 90 W PSE), which is only possible on copper and is specified to the same 100 m channel.  _(IEEE 802.3an, TIA-568.2-D, IEEE 802.3bt)_
12. **[L1 Media] BLDG-C IDF to desk (horizontal) - Cat6a UTP + 10GBASE-T**  
   Run length 95 m is within the 100 m channel limit of IEEE 802.3an (90 m permanent link + 10 m patch cords). Cat6a (Class EA, 500 MHz) supports 10GBASE-T at full reach and costs far less than optics.  _(IEEE 802.3an, TIA-568.2-D)_
13. **[L1 Media] BLDG-C Lab bench (fibre requested) - OM4 MMF + 10GBASE-SR**  
   Selected OM4 multimode because the requester explicitly asked for fibre, while staying within the 400 m reach of 10GBASE-SR at 850 nm. Reach on multimode is bounded by modal dispersion (OM4 effective modal bandwidth 4700 MHz*km), not attenuation. Loss check: 0.04 km x 3.5 dB/km + 1.5 dB connectors = 1.64 dB <= 2.9 dB channel budget (headroom 1.26 dB). VCSEL-based SR optics are cheaper than single-mode lasers.  _(IEEE 802.3ae Clause 52, TIA-492AAAD (OM4))_
14. **[L2 Switching] BLDG-A access layer - 17 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (340); 150 IP phones share the PC's port via the voice VLAN; 250 wireless clients attach through 40 APs, so only port-consuming endpoints are counted. ceil(340 x (1 + 20% growth) / 24) = 17.  _(IEEE 802.1Q (voice VLAN))_
15. **[L2 Switching] BLDG-A PoE budget - 3,510 W total, ~206 W per switch**  
   40 APs x 30 W (802.3at Class 4 at the PSE) + 150 phones x 15.4 W (802.3af) = 3,510 W. Specify PoE+ access switches with at least 250 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
16. **[L2 Switching] BLDG-B access layer - 13 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (250); 100 IP phones share the PC's port via the voice VLAN; 180 wireless clients attach through 30 APs, so only port-consuming endpoints are counted. ceil(250 x (1 + 20% growth) / 24) = 13.  _(IEEE 802.1Q (voice VLAN))_
17. **[L2 Switching] BLDG-B PoE budget - 2,440 W total, ~188 W per switch**  
   30 APs x 30 W (802.3at Class 4 at the PSE) + 100 phones x 15.4 W (802.3af) = 2,440 W. Specify PoE+ access switches with at least 200 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
18. **[L2 Switching] BLDG-C access layer - 11 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (205); 80 IP phones share the PC's port via the voice VLAN; 140 wireless clients attach through 25 APs, so only port-consuming endpoints are counted. ceil(205 x (1 + 20% growth) / 24) = 11.  _(IEEE 802.1Q (voice VLAN))_
19. **[L2 Switching] BLDG-C PoE budget - 1,982 W total, ~180 W per switch**  
   25 APs x 30 W (802.3at Class 4 at the PSE) + 80 phones x 15.4 W (802.3af) = 1,982 W. Specify PoE+ access switches with at least 200 W PoE budget each (rounded up to the next 50 W PSU tier).  _(IEEE 802.3at, IEEE 802.3af)_
20. **[L2 Switching] Spanning tree - Rapid PVST+ (802.1w per VLAN), root at distribution**  
   RSTP converges in under a second via proposal/agreement instead of 802.1D's 30-50 s listening/learning timers. The distribution switch is pinned as root (priority 4096) so the L2 forwarding path matches the L3 gateway, and PortFast + BPDU Guard on edge ports stop a rogue switch from triggering a topology change.  _(IEEE 802.1w, IEEE 802.1D-2004)_
21. **[L2 Switching] Trunk policy - 802.1Q trunks, explicit allowed list, native VLAN 999, DTP off**  
   Trunks carry only the VLANs that exist at that site (no 'allowed vlan all'), the native VLAN is moved to unused VLAN 999 and DTP is disabled with 'nonegotiate'. This blocks double-tagging VLAN hopping and switch-spoofing attacks; unused ports are shut down in black-hole VLAN 998.  _(IEEE 802.1Q, Cisco SAFE)_
22. **[Topology] Topology tier - Three-tier hierarchical (core / distribution / access)**  
   Chosen because 3 buildings and 41 access switches: each building gets an L3 distribution switch (failure-domain + STP boundary), and inter-building fibre terminates on a routed core, so no VLAN spans buildings.  _(Cisco Enterprise Campus design guide)_
23. **[L3 VLSM] BLDG-A STAFF - 10.10.0.0/23 (gw 10.10.0.1, bcast 10.10.1.255)**  
   300 hosts + 1 gateway + network + broadcast = 303 addresses -> 2^9 = 512 block (/23); /24 would offer only 254 usable < 301 required. Utilisation 59.0% of 510 usable. Network address is a multiple of the 512-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
24. **[L3 VLSM] BLDG-A VOICE - 10.10.2.0/24 (gw 10.10.2.1, bcast 10.10.2.255)**  
   150 hosts + 1 gateway + network + broadcast = 153 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 151 required. Utilisation 59.4% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
25. **[L3 VLSM] BLDG-A WIFI - 10.10.3.0/24 (gw 10.10.3.1, bcast 10.10.3.255)**  
   200 hosts + 1 gateway + network + broadcast = 203 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 201 required. Utilisation 79.1% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
26. **[L3 VLSM] BLDG-A GUEST - 10.10.4.0/26 (gw 10.10.4.1, bcast 10.10.4.63)**  
   50 hosts + 1 gateway + network + broadcast = 53 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 51 required. Utilisation 82.3% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
27. **[L3 VLSM] BLDG-A AP-MGMT - 10.10.4.64/26 (gw 10.10.4.65, bcast 10.10.4.127)**  
   40 hosts + 1 gateway + network + broadcast = 43 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 41 required. Utilisation 66.1% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
28. **[L3 VLSM] BLDG-A MGMT - 10.10.4.128/27 (gw 10.10.4.129, bcast 10.10.4.159)**  
   24 hosts + 1 gateway + network + broadcast = 27 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 25 required. Utilisation 83.3% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
29. **[L3 VLSM] Site block BLDG-A - 10.10.0.0/21**  
   Sum of BLDG-A's subnet blocks = 1,184 addresses, rounded up to the next power of two (2,048) so the whole site is one bit-aligned prefix /21. This lets the site be advertised as a single summary route (wildcard 0.0.7.255).  _(RFC 4632 (CIDR aggregation))_
30. **[L3 VLSM] BLDG-B STAFF - 10.10.8.0/24 (gw 10.10.8.1, bcast 10.10.8.255)**  
   220 hosts + 1 gateway + network + broadcast = 223 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 221 required. Utilisation 87.0% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
31. **[L3 VLSM] BLDG-B WIFI - 10.10.9.0/24 (gw 10.10.9.1, bcast 10.10.9.255)**  
   140 hosts + 1 gateway + network + broadcast = 143 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 141 required. Utilisation 55.5% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
32. **[L3 VLSM] BLDG-B VOICE - 10.10.10.0/25 (gw 10.10.10.1, bcast 10.10.10.127)**  
   100 hosts + 1 gateway + network + broadcast = 103 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 101 required. Utilisation 80.2% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
33. **[L3 VLSM] BLDG-B GUEST - 10.10.10.128/26 (gw 10.10.10.129, bcast 10.10.10.191)**  
   40 hosts + 1 gateway + network + broadcast = 43 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 41 required. Utilisation 66.1% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
34. **[L3 VLSM] BLDG-B AP-MGMT - 10.10.10.192/26 (gw 10.10.10.193, bcast 10.10.10.255)**  
   30 hosts + 1 gateway + network + broadcast = 33 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 31 required. Utilisation 50.0% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
35. **[L3 VLSM] BLDG-B MGMT - 10.10.11.0/27 (gw 10.10.11.1, bcast 10.10.11.31)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
36. **[L3 VLSM] Site block BLDG-B - 10.10.8.0/22**  
   Sum of BLDG-B's subnet blocks = 800 addresses, rounded up to the next power of two (1,024) so the whole site is one bit-aligned prefix /22. This lets the site be advertised as a single summary route (wildcard 0.0.3.255).  _(RFC 4632 (CIDR aggregation))_
37. **[L3 VLSM] BLDG-C STAFF - 10.10.12.0/24 (gw 10.10.12.1, bcast 10.10.12.255)**  
   180 hosts + 1 gateway + network + broadcast = 183 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 181 required. Utilisation 71.3% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
38. **[L3 VLSM] BLDG-C VOICE - 10.10.13.0/25 (gw 10.10.13.1, bcast 10.10.13.127)**  
   80 hosts + 1 gateway + network + broadcast = 83 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 81 required. Utilisation 64.3% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
39. **[L3 VLSM] BLDG-C WIFI - 10.10.13.128/25 (gw 10.10.13.129, bcast 10.10.13.255)**  
   110 hosts + 1 gateway + network + broadcast = 113 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 111 required. Utilisation 88.1% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
40. **[L3 VLSM] BLDG-C GUEST - 10.10.14.0/26 (gw 10.10.14.1, bcast 10.10.14.63)**  
   30 hosts + 1 gateway + network + broadcast = 33 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 31 required. Utilisation 50.0% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
41. **[L3 VLSM] BLDG-C AP-MGMT - 10.10.14.64/27 (gw 10.10.14.65, bcast 10.10.14.95)**  
   25 hosts + 1 gateway + network + broadcast = 28 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 26 required. Utilisation 86.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
42. **[L3 VLSM] BLDG-C MGMT - 10.10.14.96/27 (gw 10.10.14.97, bcast 10.10.14.127)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
43. **[L3 VLSM] Site block BLDG-C - 10.10.12.0/22**  
   Sum of BLDG-C's subnet blocks = 640 addresses, rounded up to the next power of two (1,024) so the whole site is one bit-aligned prefix /22. This lets the site be advertised as a single summary route (wildcard 0.0.3.255).  _(RFC 4632 (CIDR aggregation))_
44. **[L3 VLSM] Site block INFRA - 10.10.16.0/28**  
   Sum of INFRA's subnet blocks = 15 addresses, rounded up to the next power of two (16) so the whole site is one bit-aligned prefix /28. This lets the site be advertised as a single summary route (wildcard 0.0.0.15).  _(RFC 4632 (CIDR aggregation))_
45. **[L3 VLSM] Root utilisation - 6.27% of 10.10.0.0/16**  
   24 subnets packed largest-first with zero overlap (verified by sorting on network address and checking each broadcast < next network). Host demand fills 67.37% of allocated addresses. A fixed-length design using the largest LAN block everywhere would consume 9,231 addresses vs 2,639 with VLSM.  _(RFC 1878, RFC 4632)_
46. **[L3 Routing] Interior gateway protocol - OSPFv2 single area 0**  
   The design is a single autonomous system with 24 subnets (< 50), so one LSDB stays small and SPF runs in milliseconds. A link-state protocol gives sub-second-to-seconds convergence without the hop-count limits and slow count-to-infinity behaviour of distance-vector RIP, and avoids the ABR/summarisation complexity that multi-area would add with no scaling benefit.  _(RFC 2328 (OSPFv2))_
47. **[L3 Routing] OSPF reference bandwidth - auto-cost reference-bandwidth 100000**  
   The default 100 Mbps reference gives FastEthernet, 1G and 10G links the same cost (1). Raising it to 100 Gbps makes cost = 100000 / link Mbps, so 10G = 10, 1G = 100 and SPF prefers the faster path. Must be identical on every router.  _(RFC 2328 Appendix C.3)_
48. **[QoS & Latency] Path latency - Worst path BLDG-A -> BLDG-C = 0.052 ms one-way**  
   Estimated from cable/route distance at ~4.9 us/km (Internet paths x1.4) plus 0.05 ms per hop. Intercontinental latency is dominated by physics, so chatty IoT protocols should batch telemetry and use MQTT/HTTPS keep-alives rather than synchronous request/response.  _(ITU-T G.114)_
49. **[Verification] Packet-flow simulation - 30/30 checks passed**  
   Every LAN's last usable address was resolved by longest-prefix match to exactly one subnet (proves zero overlap), and representative flows (DHCP, DNS, Internet, lateral SMB, cloud MQTT/SSH) were walked through each generated ACL entry-by-entry using the same wildcard arithmetic the router applies.

## Device configurations

### BLDG-A-DSW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-A-DSW1
! Platform : Cisco Catalyst 3650-24PS (L3) / IOSvL2
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: building distribution (L3 gateway for 6 VLANs, OSPF area 0)
! Site block: 10.10.0.0/21
! ======================================================================
enable
configure terminal
!
hostname BLDG-A-DSW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
ip routing
!
! --- Spanning tree: Rapid PVST+, this switch is root ---
spanning-tree mode rapid-pvst
spanning-tree vlan 110,120,130,140,150,199 priority 4096
!
! --- VLAN database ---
vlan 110
 name STAFF
vlan 120
 name VOICE
vlan 130
 name WIFI
vlan 140
 name GUEST
vlan 150
 name AP-MGMT
vlan 199
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended GUEST-IN-V140
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.10.4.0 0.0.0.63 host 1.1.1.1 eq domain
 remark block guest -> internal RFC 1918
 deny ip 10.10.4.0 0.0.0.63 10.0.0.0 0.255.255.255 log
 deny ip 10.10.4.0 0.0.0.63 172.16.0.0 0.15.255.255 log
 deny ip 10.10.4.0 0.0.0.63 192.168.0.0 0.0.255.255 log
 remark Internet only
 permit ip 10.10.4.0 0.0.0.63 any
!
! --- Loopback (OSPF router-id) ---
interface Loopback0
 ip address 10.10.16.12 255.255.255.255
!
! --- SVIs (default gateways) ---
interface Vlan110
 description STAFF gateway 10.10.0.0/23 (300 hosts)
 ip address 10.10.0.1 255.255.254.0
 no shutdown
interface Vlan120
 description VOICE gateway 10.10.2.0/24 (150 hosts)
 ip address 10.10.2.1 255.255.255.0
 no shutdown
interface Vlan130
 description WIFI gateway 10.10.3.0/24 (200 hosts)
 ip address 10.10.3.1 255.255.255.0
 no shutdown
interface Vlan140
 description GUEST gateway 10.10.4.0/26 (50 hosts)
 ip address 10.10.4.1 255.255.255.192
 ip access-group GUEST-IN-V140 in
 no shutdown
interface Vlan150
 description AP-MGMT gateway 10.10.4.64/26 (40 hosts)
 ip address 10.10.4.65 255.255.255.192
 no shutdown
interface Vlan199
 description MGMT gateway 10.10.4.128/27 (24 hosts)
 ip address 10.10.4.129 255.255.255.224
 no shutdown
!
! --- Downlink trunks to 17 access switch(es) ---
interface range GigabitEthernet1/0/1 - 17
 description TRUNK to access layer
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 110,120,130,140,150,199,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/0/18 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Routed inter-building links ---
interface GigabitEthernet1/1/1
 description P2P to BLDG-B-DSW1 (OM4 MMF 10GBASE-SR 250m)
 no switchport
 ip address 10.10.16.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
interface GigabitEthernet1/1/2
 description P2P to BLDG-C-DSW1 (OM4 MMF 10GBASE-SR 380m)
 no switchport
 ip address 10.10.16.5 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.10.0.1
ip dhcp excluded-address 10.10.2.1
ip dhcp excluded-address 10.10.3.1
ip dhcp excluded-address 10.10.4.1
ip dhcp excluded-address 10.10.4.65
ip dhcp pool BLDG-A-STAFF
 network 10.10.0.0 255.255.254.0
 default-router 10.10.0.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-A-VOICE
 network 10.10.2.0 255.255.255.0
 default-router 10.10.2.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-A-WIFI
 network 10.10.3.0 255.255.255.0
 default-router 10.10.3.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-A-GUEST
 network 10.10.4.0 255.255.255.192
 default-router 10.10.4.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-A-AP-MGMT
 network 10.10.4.64 255.255.255.192
 default-router 10.10.4.65
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 10.10.16.12
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet1/1/1
 no passive-interface GigabitEthernet1/1/2
 network 10.10.16.12 0.0.0.0 area 0
 network 10.10.16.0 0.0.0.3 area 0
 network 10.10.16.4 0.0.0.3 area 0
 network 10.10.0.0 0.0.1.255 area 0
 network 10.10.2.0 0.0.0.255 area 0
 network 10.10.3.0 0.0.0.255 area 0
 network 10.10.4.0 0.0.0.63 area 0
 network 10.10.4.64 0.0.0.63 area 0
 network 10.10.4.128 0.0.0.31 area 0
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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

### BLDG-B-DSW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-B-DSW1
! Platform : Cisco Catalyst 3650-24PS (L3) / IOSvL2
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: building distribution (L3 gateway for 6 VLANs, OSPF area 0)
! Site block: 10.10.8.0/22
! ======================================================================
enable
configure terminal
!
hostname BLDG-B-DSW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
ip routing
!
! --- Spanning tree: Rapid PVST+, this switch is root ---
spanning-tree mode rapid-pvst
spanning-tree vlan 210,220,230,240,250,299 priority 4096
!
! --- VLAN database ---
vlan 210
 name STAFF
vlan 220
 name VOICE
vlan 230
 name WIFI
vlan 240
 name GUEST
vlan 250
 name AP-MGMT
vlan 299
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended GUEST-IN-V240
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.10.10.128 0.0.0.63 host 1.1.1.1 eq domain
 remark block guest -> internal RFC 1918
 deny ip 10.10.10.128 0.0.0.63 10.0.0.0 0.255.255.255 log
 deny ip 10.10.10.128 0.0.0.63 172.16.0.0 0.15.255.255 log
 deny ip 10.10.10.128 0.0.0.63 192.168.0.0 0.0.255.255 log
 remark Internet only
 permit ip 10.10.10.128 0.0.0.63 any
!
! --- Loopback (OSPF router-id) ---
interface Loopback0
 ip address 10.10.16.13 255.255.255.255
!
! --- SVIs (default gateways) ---
interface Vlan210
 description STAFF gateway 10.10.8.0/24 (220 hosts)
 ip address 10.10.8.1 255.255.255.0
 no shutdown
interface Vlan220
 description VOICE gateway 10.10.10.0/25 (100 hosts)
 ip address 10.10.10.1 255.255.255.128
 no shutdown
interface Vlan230
 description WIFI gateway 10.10.9.0/24 (140 hosts)
 ip address 10.10.9.1 255.255.255.0
 no shutdown
interface Vlan240
 description GUEST gateway 10.10.10.128/26 (40 hosts)
 ip address 10.10.10.129 255.255.255.192
 ip access-group GUEST-IN-V240 in
 no shutdown
interface Vlan250
 description AP-MGMT gateway 10.10.10.192/26 (30 hosts)
 ip address 10.10.10.193 255.255.255.192
 no shutdown
interface Vlan299
 description MGMT gateway 10.10.11.0/27 (16 hosts)
 ip address 10.10.11.1 255.255.255.224
 no shutdown
!
! --- Downlink trunks to 13 access switch(es) ---
interface range GigabitEthernet1/0/1 - 13
 description TRUNK to access layer
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 210,220,230,240,250,299,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/0/14 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Routed inter-building links ---
interface GigabitEthernet1/1/1
 description P2P to BLDG-A-DSW1 (OM4 MMF 10GBASE-SR 250m)
 no switchport
 ip address 10.10.16.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
interface GigabitEthernet1/1/2
 description P2P to BLDG-C-DSW1 (OM4 MMF 10GBASE-SR 320m)
 no switchport
 ip address 10.10.16.9 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.10.8.1
ip dhcp excluded-address 10.10.9.1
ip dhcp excluded-address 10.10.10.1
ip dhcp excluded-address 10.10.10.129
ip dhcp excluded-address 10.10.10.193
ip dhcp pool BLDG-B-STAFF
 network 10.10.8.0 255.255.255.0
 default-router 10.10.8.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-B-WIFI
 network 10.10.9.0 255.255.255.0
 default-router 10.10.9.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-B-VOICE
 network 10.10.10.0 255.255.255.128
 default-router 10.10.10.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-B-GUEST
 network 10.10.10.128 255.255.255.192
 default-router 10.10.10.129
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-B-AP-MGMT
 network 10.10.10.192 255.255.255.192
 default-router 10.10.10.193
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 10.10.16.13
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet1/1/1
 no passive-interface GigabitEthernet1/1/2
 network 10.10.16.13 0.0.0.0 area 0
 network 10.10.16.0 0.0.0.3 area 0
 network 10.10.16.8 0.0.0.3 area 0
 network 10.10.8.0 0.0.0.255 area 0
 network 10.10.9.0 0.0.0.255 area 0
 network 10.10.10.0 0.0.0.127 area 0
 network 10.10.10.128 0.0.0.63 area 0
 network 10.10.10.192 0.0.0.63 area 0
 network 10.10.11.0 0.0.0.31 area 0
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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

### BLDG-C-DSW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-C-DSW1
! Platform : Cisco Catalyst 3650-24PS (L3) / IOSvL2
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: building distribution (L3 gateway for 6 VLANs, OSPF area 0)
! Site block: 10.10.12.0/22
! ======================================================================
enable
configure terminal
!
hostname BLDG-C-DSW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
ip routing
!
! --- Spanning tree: Rapid PVST+, this switch is root ---
spanning-tree mode rapid-pvst
spanning-tree vlan 310,320,330,340,350,399 priority 4096
!
! --- VLAN database ---
vlan 310
 name STAFF
vlan 320
 name VOICE
vlan 330
 name WIFI
vlan 340
 name GUEST
vlan 350
 name AP-MGMT
vlan 399
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended GUEST-IN-V340
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.10.14.0 0.0.0.63 host 1.1.1.1 eq domain
 remark block guest -> internal RFC 1918
 deny ip 10.10.14.0 0.0.0.63 10.0.0.0 0.255.255.255 log
 deny ip 10.10.14.0 0.0.0.63 172.16.0.0 0.15.255.255 log
 deny ip 10.10.14.0 0.0.0.63 192.168.0.0 0.0.255.255 log
 remark Internet only
 permit ip 10.10.14.0 0.0.0.63 any
!
! --- Loopback (OSPF router-id) ---
interface Loopback0
 ip address 10.10.16.14 255.255.255.255
!
! --- SVIs (default gateways) ---
interface Vlan310
 description STAFF gateway 10.10.12.0/24 (180 hosts)
 ip address 10.10.12.1 255.255.255.0
 no shutdown
interface Vlan320
 description VOICE gateway 10.10.13.0/25 (80 hosts)
 ip address 10.10.13.1 255.255.255.128
 no shutdown
interface Vlan330
 description WIFI gateway 10.10.13.128/25 (110 hosts)
 ip address 10.10.13.129 255.255.255.128
 no shutdown
interface Vlan340
 description GUEST gateway 10.10.14.0/26 (30 hosts)
 ip address 10.10.14.1 255.255.255.192
 ip access-group GUEST-IN-V340 in
 no shutdown
interface Vlan350
 description AP-MGMT gateway 10.10.14.64/27 (25 hosts)
 ip address 10.10.14.65 255.255.255.224
 no shutdown
interface Vlan399
 description MGMT gateway 10.10.14.96/27 (16 hosts)
 ip address 10.10.14.97 255.255.255.224
 no shutdown
!
! --- Downlink trunks to 11 access switch(es) ---
interface range GigabitEthernet1/0/1 - 11
 description TRUNK to access layer
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 310,320,330,340,350,399,999
 switchport nonegotiate
 no shutdown
interface range GigabitEthernet1/0/12 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Routed inter-building links ---
interface GigabitEthernet1/1/1
 description P2P to BLDG-A-DSW1 (OM4 MMF 10GBASE-SR 380m)
 no switchport
 ip address 10.10.16.6 255.255.255.252
 ip ospf network point-to-point
 no shutdown
interface GigabitEthernet1/1/2
 description P2P to BLDG-B-DSW1 (OM4 MMF 10GBASE-SR 320m)
 no switchport
 ip address 10.10.16.10 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.10.12.1
ip dhcp excluded-address 10.10.13.1
ip dhcp excluded-address 10.10.13.129
ip dhcp excluded-address 10.10.14.1
ip dhcp excluded-address 10.10.14.65
ip dhcp pool BLDG-C-STAFF
 network 10.10.12.0 255.255.255.0
 default-router 10.10.12.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-C-VOICE
 network 10.10.13.0 255.255.255.128
 default-router 10.10.13.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-C-WIFI
 network 10.10.13.128 255.255.255.128
 default-router 10.10.13.129
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-C-GUEST
 network 10.10.14.0 255.255.255.192
 default-router 10.10.14.1
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
ip dhcp pool BLDG-C-AP-MGMT
 network 10.10.14.64 255.255.255.224
 default-router 10.10.14.65
 dns-server 1.1.1.1
 domain-name campus.netarch.lab
!
! --- OSPF (Single-area OSPF) ---
router ospf 1
 router-id 10.10.16.14
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface GigabitEthernet1/1/1
 no passive-interface GigabitEthernet1/1/2
 network 10.10.16.14 0.0.0.0 area 0
 network 10.10.16.4 0.0.0.3 area 0
 network 10.10.16.8 0.0.0.3 area 0
 network 10.10.12.0 0.0.0.255 area 0
 network 10.10.13.0 0.0.0.127 area 0
 network 10.10.13.128 0.0.0.127 area 0
 network 10.10.14.0 0.0.0.63 area 0
 network 10.10.14.64 0.0.0.31 area 0
 network 10.10.14.96 0.0.0.31 area 0
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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

### BLDG-A-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-A-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 17 access switch(es) in BLDG-A; increment the hostname and the Vlan199 address (next free host in 10.10.4.128/27).
! ======================================================================
enable
configure terminal
!
hostname BLDG-A-ASW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 110
 name STAFF
vlan 120
 name VOICE
vlan 130
 name WIFI
vlan 140
 name GUEST
vlan 150
 name AP-MGMT
vlan 199
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan199
 description In-band management
 ip address 10.10.4.130 255.255.255.224
 no shutdown
ip default-gateway 10.10.4.129
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 18
 description STAFF endpoints + IP phone
 switchport mode access
 switchport access vlan 110
 switchport voice vlan 120
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/19 - 22
 description PoE access points (FlexConnect local switching)
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 150
 switchport trunk allowed vlan 130,140,150
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 power inline auto
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to BLDG-A-DSW1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 110,120,130,140,150,199,999
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
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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

### BLDG-B-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-B-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 13 access switch(es) in BLDG-B; increment the hostname and the Vlan299 address (next free host in 10.10.11.0/27).
! ======================================================================
enable
configure terminal
!
hostname BLDG-B-ASW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 210
 name STAFF
vlan 220
 name VOICE
vlan 230
 name WIFI
vlan 240
 name GUEST
vlan 250
 name AP-MGMT
vlan 299
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan299
 description In-band management
 ip address 10.10.11.2 255.255.255.224
 no shutdown
ip default-gateway 10.10.11.1
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 18
 description STAFF endpoints + IP phone
 switchport mode access
 switchport access vlan 210
 switchport voice vlan 220
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/19 - 22
 description PoE access points (FlexConnect local switching)
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 250
 switchport trunk allowed vlan 230,240,250
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 power inline auto
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to BLDG-B-DSW1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 210,220,230,240,250,299,999
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
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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

### BLDG-C-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - BLDG-C-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Campus LAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 11 access switch(es) in BLDG-C; increment the hostname and the Vlan399 address (next free host in 10.10.14.96/27).
! ======================================================================
enable
configure terminal
!
hostname BLDG-C-ASW1
no ip domain-lookup
ip domain-name campus.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
spanning-tree mode rapid-pvst
spanning-tree portfast bpduguard default
!
! --- VLAN database ---
vlan 310
 name STAFF
vlan 320
 name VOICE
vlan 330
 name WIFI
vlan 340
 name GUEST
vlan 350
 name AP-MGMT
vlan 399
 name MGMT
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan399
 description In-band management
 ip address 10.10.14.98 255.255.255.224
 no shutdown
ip default-gateway 10.10.14.97
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 18
 description STAFF endpoints + IP phone
 switchport mode access
 switchport access vlan 310
 switchport voice vlan 320
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/19 - 22
 description PoE access points (FlexConnect local switching)
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 350
 switchport trunk allowed vlan 330,340,350
 switchport nonegotiate
 spanning-tree portfast trunk
 spanning-tree bpduguard enable
 power inline auto
 no shutdown
interface range GigabitEthernet1/0/23 - 24
 description UNUSED
 switchport mode access
 switchport access vlan 998
 shutdown
!
! --- Uplink trunk ---
interface GigabitEthernet1/1/1
 description TRUNK to BLDG-C-DSW1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 310,320,330,340,350,399,999
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
 remark BLDG-A MGMT
 permit 10.10.4.128 0.0.0.31
 remark BLDG-B MGMT
 permit 10.10.11.0 0.0.0.31
 remark BLDG-C MGMT
 permit 10.10.14.96 0.0.0.31
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
