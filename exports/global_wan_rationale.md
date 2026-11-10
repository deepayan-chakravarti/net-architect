# Global WAN - NetArchitect plan

* **Topology tier:** Hub-and-spoke IPsec overlay with regional site LANs
* **Routing:** Multi-area OSPF
* **Root prefix:** 10.64.0.0/16
* **Verification:** 38/38 checks passed

## Architectural rationale

1. **[Input] Global WAN - wan profile, 5 sites, 7 links, root 10.64.0.0/16**  
   Parameters validated: 2,564 hosts across 14 subnets, resiliency 'redundant'.
2. **[L1 Media] NYC <-> LONDON - Internet underlay with IPsec overlay**  
   Link spans 5570 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 38.2 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
3. **[L1 Media] NYC <-> SINGAPORE - Internet underlay with IPsec overlay**  
   Link spans 15340 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 105.3 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
4. **[L1 Media] NYC <-> MUMBAI - Internet underlay with IPsec overlay**  
   Link spans 12540 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 86.1 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
5. **[L1 Media] LONDON <-> MUMBAI - Internet underlay with IPsec overlay**  
   Link spans 7190 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 49.3 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
6. **[L1 Media] SINGAPORE <-> MUMBAI - Internet underlay with IPsec overlay**  
   Link spans 3900 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 26.8 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
7. **[L1 Media] NYC <-> CLOUD-VPC - Internet underlay with IPsec overlay**  
   Link spans 350 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 2.4 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
8. **[L1 Media] LONDON <-> CLOUD-VPC - Internet underlay with IPsec overlay**  
   Link spans 5600 km; owned fibre is uneconomic beyond metro reach and the longest unamplified 10G optic (10GBASE-ZR) stops at 80 km. A carrier Internet circuit is used and confidentiality is restored with an IPsec tunnel. Estimated one-way propagation 38.4 ms (cable distance x 1.4 path factor / 204 km per ms in glass).  _(RFC 4301 (IPsec), ITU-T G.652)_
9. **[L2 Switching] NYC access layer - 35 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (700), so only port-consuming endpoints are counted. ceil(700 x (1 + 20% growth) / 24) = 35.  _(IEEE 802.1Q (voice VLAN))_
10. **[L2 Switching] LONDON access layer - 28 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (560), so only port-consuming endpoints are counted. ceil(560 x (1 + 20% growth) / 24) = 28.  _(IEEE 802.1Q (voice VLAN))_
11. **[L2 Switching] SINGAPORE access layer - 25 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (490), so only port-consuming endpoints are counted. ceil(490 x (1 + 20% growth) / 24) = 25.  _(IEEE 802.1Q (voice VLAN))_
12. **[L2 Switching] MUMBAI access layer - 25 x 24-port access switch(es)**  
   Ports are consumed by wired data/IoT/server endpoints and APs (500), so only port-consuming endpoints are counted. ceil(500 x (1 + 20% growth) / 24) = 25.  _(IEEE 802.1Q (voice VLAN))_
13. **[L2 Switching] Spanning tree - Rapid PVST+ (802.1w per VLAN), root at distribution**  
   RSTP converges in under a second via proposal/agreement instead of 802.1D's 30-50 s listening/learning timers. The distribution switch is pinned as root (priority 4096) so the L2 forwarding path matches the L3 gateway, and PortFast + BPDU Guard on edge ports stop a rogue switch from triggering a topology change.  _(IEEE 802.1w, IEEE 802.1D-2004)_
14. **[L2 Switching] Trunk policy - 802.1Q trunks, explicit allowed list, native VLAN 999, DTP off**  
   Trunks carry only the VLANs that exist at that site (no 'allowed vlan all'), the native VLAN is moved to unused VLAN 999 and DTP is disabled with 'nonegotiate'. This blocks double-tagging VLAN hopping and switch-spoofing attacks; unused ports are shut down in black-hole VLAN 998.  _(IEEE 802.1Q, Cisco SAFE)_
15. **[Topology] Topology tier - Hub-and-spoke IPsec overlay with regional site LANs**  
   Chosen because sites are continents apart, so each has a collapsed site LAN and an edge router that builds encrypted GRE tunnels across the Internet to the hub (and backup peers); routing hierarchy follows the tunnel hierarchy.
16. **[L3 VLSM] NYC IOT-SCANNERS - 10.64.0.0/22 (gw 10.64.0.1, bcast 10.64.3.255)**  
   600 hosts + 1 gateway + network + broadcast = 603 addresses -> 2^10 = 1024 block (/22); /23 would offer only 510 usable < 601 required. Utilisation 58.8% of 1022 usable. Network address is a multiple of the 1024-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
17. **[L3 VLSM] NYC USERS - 10.64.4.0/25 (gw 10.64.4.1, bcast 10.64.4.127)**  
   100 hosts + 1 gateway + network + broadcast = 103 addresses -> 2^7 = 128 block (/25); /26 would offer only 62 usable < 101 required. Utilisation 80.2% of 126 usable. Network address is a multiple of the 128-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
18. **[L3 VLSM] NYC MGMT - 10.64.4.128/27 (gw 10.64.4.129, bcast 10.64.4.159)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
19. **[L3 VLSM] Site block NYC - 10.64.0.0/21**  
   Sum of NYC's subnet blocks = 1,184 addresses, rounded up to the next power of two (2,048) so the whole site is one bit-aligned prefix /21. This lets the site be advertised as a single summary route (wildcard 0.0.7.255).  _(RFC 4632 (CIDR aggregation))_
20. **[L3 VLSM] LONDON IOT-SCANNERS - 10.64.8.0/23 (gw 10.64.8.1, bcast 10.64.9.255)**  
   500 hosts + 1 gateway + network + broadcast = 503 addresses -> 2^9 = 512 block (/23); /24 would offer only 254 usable < 501 required. Utilisation 98.2% of 510 usable. Network address is a multiple of the 512-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
21. **[L3 VLSM] LONDON USERS - 10.64.10.0/26 (gw 10.64.10.1, bcast 10.64.10.63)**  
   60 hosts + 1 gateway + network + broadcast = 63 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 61 required. Utilisation 98.4% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
22. **[L3 VLSM] LONDON MGMT - 10.64.10.64/27 (gw 10.64.10.65, bcast 10.64.10.95)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
23. **[L3 VLSM] Site block LONDON - 10.64.8.0/22**  
   Sum of LONDON's subnet blocks = 608 addresses, rounded up to the next power of two (1,024) so the whole site is one bit-aligned prefix /22. This lets the site be advertised as a single summary route (wildcard 0.0.3.255).  _(RFC 4632 (CIDR aggregation))_
24. **[L3 VLSM] SINGAPORE IOT-SCANNERS - 10.64.12.0/23 (gw 10.64.12.1, bcast 10.64.13.255)**  
   450 hosts + 1 gateway + network + broadcast = 453 addresses -> 2^9 = 512 block (/23); /24 would offer only 254 usable < 451 required. Utilisation 88.4% of 510 usable. Network address is a multiple of the 512-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
25. **[L3 VLSM] SINGAPORE USERS - 10.64.14.0/26 (gw 10.64.14.1, bcast 10.64.14.63)**  
   40 hosts + 1 gateway + network + broadcast = 43 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 41 required. Utilisation 66.1% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
26. **[L3 VLSM] SINGAPORE MGMT - 10.64.14.64/27 (gw 10.64.14.65, bcast 10.64.14.95)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
27. **[L3 VLSM] Site block SINGAPORE - 10.64.12.0/22**  
   Sum of SINGAPORE's subnet blocks = 608 addresses, rounded up to the next power of two (1,024) so the whole site is one bit-aligned prefix /22. This lets the site be advertised as a single summary route (wildcard 0.0.3.255).  _(RFC 4632 (CIDR aggregation))_
28. **[L3 VLSM] MUMBAI IOT-SCANNERS - 10.64.16.0/23 (gw 10.64.16.1, bcast 10.64.17.255)**  
   450 hosts + 1 gateway + network + broadcast = 453 addresses -> 2^9 = 512 block (/23); /24 would offer only 254 usable < 451 required. Utilisation 88.4% of 510 usable. Network address is a multiple of the 512-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
29. **[L3 VLSM] MUMBAI USERS - 10.64.18.0/26 (gw 10.64.18.1, bcast 10.64.18.63)**  
   50 hosts + 1 gateway + network + broadcast = 53 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 51 required. Utilisation 82.3% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
30. **[L3 VLSM] MUMBAI MGMT - 10.64.18.64/27 (gw 10.64.18.65, bcast 10.64.18.95)**  
   16 hosts + 1 gateway + network + broadcast = 19 addresses -> 2^5 = 32 block (/27); /28 would offer only 14 usable < 17 required. Utilisation 56.7% of 30 usable. Network address is a multiple of the 32-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
31. **[L3 VLSM] Site block MUMBAI - 10.64.16.0/22**  
   Sum of MUMBAI's subnet blocks = 608 addresses, rounded up to the next power of two (1,024) so the whole site is one bit-aligned prefix /22. This lets the site be advertised as a single summary route (wildcard 0.0.3.255).  _(RFC 4632 (CIDR aggregation))_
32. **[L3 VLSM] Site block INFRA - 10.64.20.0/27**  
   Sum of INFRA's subnet blocks = 24 addresses, rounded up to the next power of two (32) so the whole site is one bit-aligned prefix /27. This lets the site be advertised as a single summary route (wildcard 0.0.0.31).  _(RFC 4632 (CIDR aggregation))_
33. **[L3 VLSM] CLOUD-VPC APP-TIER - 10.200.0.0/24 (gw 10.200.0.1, bcast 10.200.0.255)**  
   200 hosts + 1 gateway + network + broadcast = 203 addresses -> 2^8 = 256 block (/24); /25 would offer only 126 usable < 201 required. Utilisation 79.1% of 254 usable. Network address is a multiple of the 256-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
34. **[L3 VLSM] CLOUD-VPC DATA-TIER - 10.200.1.0/26 (gw 10.200.1.1, bcast 10.200.1.63)**  
   50 hosts + 1 gateway + network + broadcast = 53 addresses -> 2^6 = 64 block (/26); /27 would offer only 30 usable < 51 required. Utilisation 82.3% of 62 usable. Network address is a multiple of the 64-address block size, so it is bit-aligned (host bits all zero).  _(RFC 950, RFC 1878, RFC 4632)_
35. **[L3 VLSM] Site block CLOUD-VPC - 10.200.0.0/16**  
   CLOUD-VPC keeps its own provider-assigned prefix 10.200.0.0/16, allocated outside the enterprise root 10.64.0.0/16 so cloud and on-prem routes never overlap and each side can be summarised independently.  _(RFC 4632)_
36. **[L3 VLSM] Root utilisation - 7.86% of 10.64.0.0/16**  
   23 subnets packed largest-first with zero overlap (verified by sorting on network address and checking each broadcast < next network). Host demand fills 77.33% of allocated addresses. A fixed-length design using the largest LAN block everywhere would consume 14,360 addresses vs 3,352 with VLSM.  _(RFC 1878, RFC 4632)_
37. **[L3 VLSM] Cloud tunnel inside addresses - 169.254.10.0/24 carved into /30s**  
   Cloud VPN gateways number the BGP-over-IPsec inside interfaces from the IPv4 link-local range; using it keeps tunnel addressing out of both the enterprise root and the VPC CIDR.  _(RFC 3927)_
38. **[L3 VLSM] Internet underlay addresses - 203.0.113.0/24 /30 per site (lab)**  
   Public WAN addresses in the lab use the RFC 5737 documentation block so the configs never collide with real Internet space; replace with ISP-assigned addresses in production.  _(RFC 5737)_
39. **[L3 Routing] Interior gateway protocol - Multi-area OSPFv2 (area 0 backbone at NYC, one area per remote site)**  
   Selected multi-area OSPF because 4 geographically dispersed sites interconnect over an Internet/IPsec WAN whose tunnels can flap independently. Areas confine Type-1/2 LSA flooding and SPF recalculation to the site where a change happens; area 0 carries only inter-area summaries. OSPF remains vendor-neutral and converges in seconds as a link-state protocol.  _(RFC 2328 (OSPFv2) section 3, RFC 3509 (ABR behaviour))_
40. **[L3 Routing] Area 1 summary (LONDON) - area 1 range 10.64.8.0 255.255.252.0**  
   The ABR at LONDON advertises 3 intra-area subnets into area 0 as one Type-3 LSA 10.64.8.0/22. This works only because the VLSM engine allocated the site as one contiguous, bit-aligned block; it shrinks every other router's routing table and hides intra-site flaps from the backbone.  _(RFC 2328 section 12.4.3, RFC 4632)_
41. **[L3 Routing] Area 2 summary (SINGAPORE) - area 2 range 10.64.12.0 255.255.252.0**  
   The ABR at SINGAPORE advertises 3 intra-area subnets into area 0 as one Type-3 LSA 10.64.12.0/22. This works only because the VLSM engine allocated the site as one contiguous, bit-aligned block; it shrinks every other router's routing table and hides intra-site flaps from the backbone.  _(RFC 2328 section 12.4.3, RFC 4632)_
42. **[L3 Routing] Area 3 summary (MUMBAI) - area 3 range 10.64.16.0 255.255.252.0**  
   The ABR at MUMBAI advertises 3 intra-area subnets into area 0 as one Type-3 LSA 10.64.16.0/22. This works only because the VLSM engine allocated the site as one contiguous, bit-aligned block; it shrinks every other router's routing table and hides intra-site flaps from the backbone.  _(RFC 2328 section 12.4.3, RFC 4632)_
43. **[L3 Routing] OSPF reference bandwidth - auto-cost reference-bandwidth 100000**  
   The default 100 Mbps reference gives FastEthernet, 1G and 10G links the same cost (1). Raising it to 100 Gbps makes cost = 100000 / link Mbps, so 10G = 10, 1G = 100 and SPF prefers the faster path. Must be identical on every router.  _(RFC 2328 Appendix C.3)_
44. **[L3 Routing] Cloud boundary - eBGP AS65010 <-> AS64512 (CLOUD-VPC)**  
   The cloud VPC is a separate administrative and routing domain; cloud VPN gateways only exchange dynamic routes via BGP. eBGP isolates the domains: the enterprise advertises one aggregate (10.64.0.0/16) filtered by prefix-list, and accepts only the VPC CIDR, so a mistake on either side cannot leak or black-hole the other's routes. Private ASNs from 64512-65534 are used.  _(RFC 4271 (BGP-4), RFC 6996 (private ASNs), RFC 7454 (BGP filtering))_
45. **[L3 Routing] BGP -> OSPF - Redistribute VPC prefix into OSPF at NYC**  
   Spokes keep a local Internet default route (split tunnelling), so the VPC prefix must be injected into OSPF as an E2 route by the hub that terminates the eBGP session; a route-map limits redistribution to the VPC CIDR only.  _(RFC 2328 section 2.3 (AS-external routes))_
46. **[QoS & Latency] Path latency - Worst path SINGAPORE -> NYC -> CLOUD-VPC = 107.776 ms one-way**  
   Estimated from cable/route distance at ~4.9 us/km (Internet paths x1.4) plus 0.05 ms per hop. Intercontinental latency is dominated by physics, so chatty IoT protocols should batch telemetry and use MQTT/HTTPS keep-alives rather than synchronous request/response.  _(ITU-T G.114)_
47. **[Verification] Packet-flow simulation - 38/38 checks passed**  
   Every LAN's last usable address was resolved by longest-prefix match to exactly one subnet (proves zero overlap), and representative flows (DHCP, DNS, Internet, lateral SMB, cloud MQTT/SSH) were walked through each generated ACL entry-by-entry using the same wildcard arithmetic the router applies.

## Device configurations

### NYC-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - NYC-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, hub (area 0)
! Site block: 10.64.0.0/21
! ======================================================================
enable
configure terminal
!
hostname NYC-RTR1
no ip domain-lookup
ip domain-name wan.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- IPsec: IKEv1 AES-256/SHA-256/DH14 ---
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 28800
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
crypto ipsec profile IPSEC-GRE
 set transform-set TS-GRE
crypto ipsec transform-set TS-VTI esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC-VTI
 set transform-set TS-VTI
crypto isakmp key NA-b93a5b47676d4b47 address 203.0.113.10
crypto isakmp key NA-14d7968553cfd1a0 address 203.0.113.14
crypto isakmp key NA-9e6359a05b1f2ad3 address 203.0.113.18
crypto isakmp key NA-261fd155fc225fe4 address 203.0.113.22
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended IOT-IN-V100
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.64.0.0 0.0.3.255 host 1.1.1.1 eq domain
 remark HTTPS to cloud app
 permit tcp 10.64.0.0 0.0.3.255 10.200.0.0 0.0.0.255 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.0.0 0.0.3.255 10.200.0.0 0.0.0.255 eq 8883
 remark HTTPS to cloud app
 permit tcp 10.64.0.0 0.0.3.255 10.200.1.0 0.0.0.63 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.0.0 0.0.3.255 10.200.1.0 0.0.0.63 eq 8883
 remark IoT may not talk to anything else
 deny ip 10.64.0.0 0.0.3.255 any log
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 10.64.20.20 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to NYC-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 10.64.4.0/25 (100 hosts)
 encapsulation dot1Q 10
 ip address 10.64.4.1 255.255.255.128
interface GigabitEthernet0/0/0.99
 description MGMT gateway 10.64.4.128/27 (16 hosts)
 encapsulation dot1Q 99
 ip address 10.64.4.129 255.255.255.224
interface GigabitEthernet0/0/0.100
 description IOT-SCANNERS gateway 10.64.0.0/22 (600 hosts)
 encapsulation dot1Q 100
 ip address 10.64.0.1 255.255.252.0
 ip access-group IOT-IN-V100 in
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Internet underlay (RFC 5737 lab addressing) ---
interface GigabitEthernet0/0/1
 description INTERNET underlay
 ip address 203.0.113.6 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 203.0.113.5 name INTERNET
!
! --- Encrypted tunnels ---
interface Tunnel1
 description GRE/IPsec to LONDON (5,570 km)
 ip address 10.64.20.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.10
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel2
 description GRE/IPsec to SINGAPORE (15,340 km)
 ip address 10.64.20.5 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.14
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel3
 description GRE/IPsec to MUMBAI (12,540 km)
 ip address 10.64.20.9 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.18
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel6
 description IPsec VTI + eBGP to CLOUD-VPC VPC
 ip address 169.254.10.21 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0/1
 tunnel mode ipsec ipv4
 tunnel destination 203.0.113.22
 tunnel protection ipsec profile IPSEC-VTI
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.64.4.1
ip dhcp excluded-address 10.64.0.1
ip dhcp pool NYC-USERS
 network 10.64.4.0 255.255.255.128
 default-router 10.64.4.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
ip dhcp pool NYC-IOT-SCANNERS
 network 10.64.0.0 255.255.252.0
 default-router 10.64.0.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
!
! --- OSPF (Multi-area OSPF) ---
router ospf 1
 router-id 10.64.20.20
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface Tunnel1
 no passive-interface Tunnel2
 no passive-interface Tunnel3
 network 10.64.20.20 0.0.0.0 area 0
 network 10.64.20.0 0.0.0.3 area 0
 network 10.64.20.4 0.0.0.3 area 0
 network 10.64.20.8 0.0.0.3 area 0
 network 10.64.4.0 0.0.0.127 area 0
 network 10.64.4.128 0.0.0.31 area 0
 network 10.64.0.0 0.0.3.255 area 0
 redistribute bgp 65010 subnets route-map BGP-TO-OSPF
!
! --- eBGP to cloud VPC (aggregate out, VPC CIDR in) ---
ip route 10.64.0.0 255.255.0.0 Null0 254 name AGGREGATE-DISCARD
ip prefix-list TO-CLOUD seq 5 permit 10.64.0.0/16
ip prefix-list FROM-CLOUD seq 5 permit 10.200.0.0/16 le 24
route-map BGP-TO-OSPF permit 10
 match ip address prefix-list FROM-CLOUD
router bgp 65010
 bgp router-id 10.64.20.20
 bgp log-neighbor-changes
 neighbor 169.254.10.22 remote-as 64512
 neighbor 169.254.10.22 description CLOUD-VPC VGW
 neighbor 169.254.10.22 timers 10 30
 address-family ipv4
  network 10.64.0.0 mask 255.255.0.0
  neighbor 169.254.10.22 activate
  neighbor 169.254.10.22 prefix-list TO-CLOUD out
  neighbor 169.254.10.22 prefix-list FROM-CLOUD in
 exit-address-family
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### LONDON-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - LONDON-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, ABR area 0/1
! Site block: 10.64.8.0/22
! ======================================================================
enable
configure terminal
!
hostname LONDON-RTR1
no ip domain-lookup
ip domain-name wan.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- IPsec: IKEv1 AES-256/SHA-256/DH14 ---
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 28800
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
crypto ipsec profile IPSEC-GRE
 set transform-set TS-GRE
crypto ipsec transform-set TS-VTI esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC-VTI
 set transform-set TS-VTI
crypto isakmp key NA-b93a5b47676d4b47 address 203.0.113.6
crypto isakmp key NA-34ef1501908242c3 address 203.0.113.18
crypto isakmp key NA-11a9e9909014e40d address 203.0.113.22
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended IOT-IN-V100
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.64.8.0 0.0.1.255 host 1.1.1.1 eq domain
 remark HTTPS to cloud app
 permit tcp 10.64.8.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.8.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 8883
 remark HTTPS to cloud app
 permit tcp 10.64.8.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.8.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 8883
 remark IoT may not talk to anything else
 deny ip 10.64.8.0 0.0.1.255 any log
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 10.64.20.21 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to LONDON-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 10.64.10.0/26 (60 hosts)
 encapsulation dot1Q 10
 ip address 10.64.10.1 255.255.255.192
interface GigabitEthernet0/0/0.99
 description MGMT gateway 10.64.10.64/27 (16 hosts)
 encapsulation dot1Q 99
 ip address 10.64.10.65 255.255.255.224
interface GigabitEthernet0/0/0.100
 description IOT-SCANNERS gateway 10.64.8.0/23 (500 hosts)
 encapsulation dot1Q 100
 ip address 10.64.8.1 255.255.254.0
 ip access-group IOT-IN-V100 in
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Internet underlay (RFC 5737 lab addressing) ---
interface GigabitEthernet0/0/1
 description INTERNET underlay
 ip address 203.0.113.10 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 203.0.113.9 name INTERNET
!
! --- Encrypted tunnels ---
interface Tunnel1
 description GRE/IPsec to NYC (5,570 km)
 ip address 10.64.20.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.6
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel4
 description GRE/IPsec to MUMBAI (7,190 km)
 ip address 10.64.20.13 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.18
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel7
 description IPsec VTI + eBGP to CLOUD-VPC VPC
 ip address 169.254.10.25 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0/1
 tunnel mode ipsec ipv4
 tunnel destination 203.0.113.22
 tunnel protection ipsec profile IPSEC-VTI
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.64.10.1
ip dhcp excluded-address 10.64.8.1
ip dhcp pool LONDON-USERS
 network 10.64.10.0 255.255.255.192
 default-router 10.64.10.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
ip dhcp pool LONDON-IOT-SCANNERS
 network 10.64.8.0 255.255.254.0
 default-router 10.64.8.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
!
! --- OSPF (Multi-area OSPF) ---
router ospf 1
 router-id 10.64.20.21
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface Tunnel1
 no passive-interface Tunnel4
 network 10.64.20.21 0.0.0.0 area 0
 network 10.64.20.0 0.0.0.3 area 0
 network 10.64.20.12 0.0.0.3 area 0
 network 10.64.10.0 0.0.0.63 area 1
 network 10.64.10.64 0.0.0.31 area 1
 network 10.64.8.0 0.0.1.255 area 1
 area 1 range 10.64.8.0 255.255.252.0
 redistribute bgp 65010 subnets route-map BGP-TO-OSPF
!
! --- eBGP to cloud VPC (aggregate out, VPC CIDR in) ---
ip route 10.64.0.0 255.255.0.0 Null0 254 name AGGREGATE-DISCARD
ip prefix-list TO-CLOUD seq 5 permit 10.64.0.0/16
ip prefix-list FROM-CLOUD seq 5 permit 10.200.0.0/16 le 24
route-map BGP-TO-OSPF permit 10
 match ip address prefix-list FROM-CLOUD
router bgp 65010
 bgp router-id 10.64.20.21
 bgp log-neighbor-changes
 neighbor 169.254.10.26 remote-as 64512
 neighbor 169.254.10.26 description CLOUD-VPC VGW
 neighbor 169.254.10.26 timers 10 30
 address-family ipv4
  network 10.64.0.0 mask 255.255.0.0
  neighbor 169.254.10.26 activate
  neighbor 169.254.10.26 prefix-list TO-CLOUD out
  neighbor 169.254.10.26 prefix-list FROM-CLOUD in
 exit-address-family
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### SINGAPORE-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - SINGAPORE-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, ABR area 0/2
! Site block: 10.64.12.0/22
! ======================================================================
enable
configure terminal
!
hostname SINGAPORE-RTR1
no ip domain-lookup
ip domain-name wan.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- IPsec: IKEv1 AES-256/SHA-256/DH14 ---
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 28800
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
crypto ipsec profile IPSEC-GRE
 set transform-set TS-GRE
crypto isakmp key NA-14d7968553cfd1a0 address 203.0.113.6
crypto isakmp key NA-1a7616bfdc3f9c5e address 203.0.113.18
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended IOT-IN-V100
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.64.12.0 0.0.1.255 host 1.1.1.1 eq domain
 remark HTTPS to cloud app
 permit tcp 10.64.12.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.12.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 8883
 remark HTTPS to cloud app
 permit tcp 10.64.12.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.12.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 8883
 remark IoT may not talk to anything else
 deny ip 10.64.12.0 0.0.1.255 any log
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 10.64.20.22 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to SINGAPORE-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 10.64.14.0/26 (40 hosts)
 encapsulation dot1Q 10
 ip address 10.64.14.1 255.255.255.192
interface GigabitEthernet0/0/0.99
 description MGMT gateway 10.64.14.64/27 (16 hosts)
 encapsulation dot1Q 99
 ip address 10.64.14.65 255.255.255.224
interface GigabitEthernet0/0/0.100
 description IOT-SCANNERS gateway 10.64.12.0/23 (450 hosts)
 encapsulation dot1Q 100
 ip address 10.64.12.1 255.255.254.0
 ip access-group IOT-IN-V100 in
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Internet underlay (RFC 5737 lab addressing) ---
interface GigabitEthernet0/0/1
 description INTERNET underlay
 ip address 203.0.113.14 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 203.0.113.13 name INTERNET
!
! --- Encrypted tunnels ---
interface Tunnel2
 description GRE/IPsec to NYC (15,340 km)
 ip address 10.64.20.6 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.6
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel5
 description GRE/IPsec to MUMBAI (3,900 km)
 ip address 10.64.20.17 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.18
 tunnel protection ipsec profile IPSEC-GRE
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.64.14.1
ip dhcp excluded-address 10.64.12.1
ip dhcp pool SINGAPORE-USERS
 network 10.64.14.0 255.255.255.192
 default-router 10.64.14.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
ip dhcp pool SINGAPORE-IOT-SCANNERS
 network 10.64.12.0 255.255.254.0
 default-router 10.64.12.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
!
! --- OSPF (Multi-area OSPF) ---
router ospf 1
 router-id 10.64.20.22
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface Tunnel2
 no passive-interface Tunnel5
 network 10.64.20.22 0.0.0.0 area 0
 network 10.64.20.4 0.0.0.3 area 0
 network 10.64.20.16 0.0.0.3 area 0
 network 10.64.14.0 0.0.0.63 area 2
 network 10.64.14.64 0.0.0.31 area 2
 network 10.64.12.0 0.0.1.255 area 2
 area 2 range 10.64.12.0 255.255.252.0
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### MUMBAI-RTR1

```cisco
! ======================================================================
! NetArchitect generated configuration - MUMBAI-RTR1
! Platform : Cisco ISR4331 (IOS-XE) / IOSv
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Role: site edge router, ABR area 0/3
! Site block: 10.64.16.0/22
! ======================================================================
enable
configure terminal
!
hostname MUMBAI-RTR1
no ip domain-lookup
ip domain-name wan.netarch.lab
service password-encryption
service timestamps log datetime msec
enable secret NetArch-Lab-2026
username netadmin privilege 15 secret NetArch-Lab-2026
banner motd ^Authorized access only - NetArchitect lab^
!
! --- IPsec: IKEv1 AES-256/SHA-256/DH14 ---
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 28800
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
crypto ipsec profile IPSEC-GRE
 set transform-set TS-GRE
crypto isakmp key NA-9e6359a05b1f2ad3 address 203.0.113.6
crypto isakmp key NA-34ef1501908242c3 address 203.0.113.10
crypto isakmp key NA-1a7616bfdc3f9c5e address 203.0.113.14
!
! --- Security ACLs (wildcard masks computed bitwise) ---
ip access-list extended IOT-IN-V100
 remark DHCP to local gateway
 permit udp any eq bootpc any eq bootps
 remark DNS
 permit udp 10.64.16.0 0.0.1.255 host 1.1.1.1 eq domain
 remark HTTPS to cloud app
 permit tcp 10.64.16.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.16.0 0.0.1.255 10.200.0.0 0.0.0.255 eq 8883
 remark HTTPS to cloud app
 permit tcp 10.64.16.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 443
 remark MQTT/TLS telemetry
 permit tcp 10.64.16.0 0.0.1.255 10.200.1.0 0.0.0.63 eq 8883
 remark IoT may not talk to anything else
 deny ip 10.64.16.0 0.0.1.255 any log
!
! --- Loopback (router-id) ---
interface Loopback0
 ip address 10.64.20.23 255.255.255.255
!
! --- LAN: router-on-a-stick sub-interfaces (802.1Q) ---
interface GigabitEthernet0/0/0
 description LAN trunk to MUMBAI-ASW1
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.10
 description USERS gateway 10.64.18.0/26 (50 hosts)
 encapsulation dot1Q 10
 ip address 10.64.18.1 255.255.255.192
interface GigabitEthernet0/0/0.99
 description MGMT gateway 10.64.18.64/27 (16 hosts)
 encapsulation dot1Q 99
 ip address 10.64.18.65 255.255.255.224
interface GigabitEthernet0/0/0.100
 description IOT-SCANNERS gateway 10.64.16.0/23 (450 hosts)
 encapsulation dot1Q 100
 ip address 10.64.16.1 255.255.254.0
 ip access-group IOT-IN-V100 in
interface GigabitEthernet0/0/0.999
 description native VLAN (unused)
 encapsulation dot1Q 999 native
!
! --- Internet underlay (RFC 5737 lab addressing) ---
interface GigabitEthernet0/0/1
 description INTERNET underlay
 ip address 203.0.113.18 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 203.0.113.17 name INTERNET
!
! --- Encrypted tunnels ---
interface Tunnel3
 description GRE/IPsec to NYC (12,540 km)
 ip address 10.64.20.10 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.6
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel4
 description GRE/IPsec to LONDON (7,190 km)
 ip address 10.64.20.14 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.10
 tunnel protection ipsec profile IPSEC-GRE
interface Tunnel5
 description GRE/IPsec to SINGAPORE (3,900 km)
 ip address 10.64.20.18 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip ospf network point-to-point
 tunnel source GigabitEthernet0/0/1
 tunnel destination 203.0.113.14
 tunnel protection ipsec profile IPSEC-GRE
!
! --- DHCP (gateway excluded, one pool per VLAN) ---
ip dhcp excluded-address 10.64.18.1
ip dhcp excluded-address 10.64.16.1
ip dhcp pool MUMBAI-USERS
 network 10.64.18.0 255.255.255.192
 default-router 10.64.18.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
ip dhcp pool MUMBAI-IOT-SCANNERS
 network 10.64.16.0 255.255.254.0
 default-router 10.64.16.1
 dns-server 1.1.1.1
 domain-name wan.netarch.lab
!
! --- OSPF (Multi-area OSPF) ---
router ospf 1
 router-id 10.64.20.23
 auto-cost reference-bandwidth 100000
 passive-interface default
 no passive-interface Tunnel3
 no passive-interface Tunnel4
 no passive-interface Tunnel5
 network 10.64.20.23 0.0.0.0 area 0
 network 10.64.20.8 0.0.0.3 area 0
 network 10.64.20.12 0.0.0.3 area 0
 network 10.64.20.16 0.0.0.3 area 0
 network 10.64.18.0 0.0.0.63 area 3
 network 10.64.18.64 0.0.0.31 area 3
 network 10.64.16.0 0.0.1.255 area 3
 area 3 range 10.64.16.0 255.255.252.0
!
! --- Management plane (SSH only, ACL-restricted) ---
ip access-list standard VTY-MGMT
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### NYC-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - NYC-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 35 access switch(es) in NYC; increment the hostname and the Vlan99 address (next free host in 10.64.4.128/27).
! ======================================================================
enable
configure terminal
!
hostname NYC-ASW1
no ip domain-lookup
ip domain-name wan.netarch.lab
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
vlan 99
 name MGMT
vlan 100
 name IOT-SCANNERS
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 10.64.4.130 255.255.255.224
 no shutdown
ip default-gateway 10.64.4.129
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 18
 description IOT-SCANNERS endpoints
 switchport mode access
 switchport access vlan 100
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/19 - 22
 description USERS endpoints
 switchport mode access
 switchport access vlan 10
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
 description TRUNK to NYC-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,99,100,999
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
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### LONDON-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - LONDON-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 28 access switch(es) in LONDON; increment the hostname and the Vlan99 address (next free host in 10.64.10.64/27).
! ======================================================================
enable
configure terminal
!
hostname LONDON-ASW1
no ip domain-lookup
ip domain-name wan.netarch.lab
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
vlan 99
 name MGMT
vlan 100
 name IOT-SCANNERS
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 10.64.10.66 255.255.255.224
 no shutdown
ip default-gateway 10.64.10.65
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 19
 description IOT-SCANNERS endpoints
 switchport mode access
 switchport access vlan 100
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/20 - 22
 description USERS endpoints
 switchport mode access
 switchport access vlan 10
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
 description TRUNK to LONDON-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,99,100,999
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
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### SINGAPORE-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - SINGAPORE-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 25 access switch(es) in SINGAPORE; increment the hostname and the Vlan99 address (next free host in 10.64.14.64/27).
! ======================================================================
enable
configure terminal
!
hostname SINGAPORE-ASW1
no ip domain-lookup
ip domain-name wan.netarch.lab
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
vlan 99
 name MGMT
vlan 100
 name IOT-SCANNERS
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 10.64.14.66 255.255.255.224
 no shutdown
ip default-gateway 10.64.14.65
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 19
 description IOT-SCANNERS endpoints
 switchport mode access
 switchport access vlan 100
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/20 - 22
 description USERS endpoints
 switchport mode access
 switchport access vlan 10
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
 description TRUNK to SINGAPORE-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,99,100,999
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
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### MUMBAI-ASW1

```cisco
! ======================================================================
! NetArchitect generated configuration - MUMBAI-ASW1
! Platform : Cisco Catalyst 3650-24PS / 2960 (L2 access)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! TEMPLATE: replicate for 25 access switch(es) in MUMBAI; increment the hostname and the Vlan99 address (next free host in 10.64.18.64/27).
! ======================================================================
enable
configure terminal
!
hostname MUMBAI-ASW1
no ip domain-lookup
ip domain-name wan.netarch.lab
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
vlan 99
 name MGMT
vlan 100
 name IOT-SCANNERS
vlan 998
 name BLACKHOLE
vlan 999
 name NATIVE-UNUSED
!
! --- Management SVI ---
interface Vlan99
 description In-band management
 ip address 10.64.18.66 255.255.255.224
 no shutdown
ip default-gateway 10.64.18.65
!
! --- Edge ports (PortFast + BPDU Guard, DTP off) ---
interface range GigabitEthernet1/0/1 - 19
 description IOT-SCANNERS endpoints
 switchport mode access
 switchport access vlan 100
 switchport nonegotiate
 spanning-tree portfast
 spanning-tree bpduguard enable
 no shutdown
interface range GigabitEthernet1/0/20 - 22
 description USERS endpoints
 switchport mode access
 switchport access vlan 10
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
 description TRUNK to MUMBAI-RTR1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,99,100,999
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
 remark NYC MGMT
 permit 10.64.4.128 0.0.0.31
 remark LONDON MGMT
 permit 10.64.10.64 0.0.0.31
 remark SINGAPORE MGMT
 permit 10.64.14.64 0.0.0.31
 remark MUMBAI MGMT
 permit 10.64.18.64 0.0.0.31
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

### ISP-SIM

```cisco
! ======================================================================
! NetArchitect generated configuration - ISP-SIM
! Platform : Cisco ISR4331 (lab Internet simulator)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! Router-on-a-stick: one sub-interface per customer /30 (RFC 5737 TEST-NET-3).
! ======================================================================
enable
configure terminal
!
hostname ISP-SIM
no ip domain-lookup
interface GigabitEthernet0/0/0
 description trunk to ISP-SW
 no ip address
 no shutdown
interface GigabitEthernet0/0/0.11
 description NYC-RTR1
 encapsulation dot1Q 11
 ip address 203.0.113.5 255.255.255.252
interface GigabitEthernet0/0/0.12
 description LONDON-RTR1
 encapsulation dot1Q 12
 ip address 203.0.113.9 255.255.255.252
interface GigabitEthernet0/0/0.13
 description SINGAPORE-RTR1
 encapsulation dot1Q 13
 ip address 203.0.113.13 255.255.255.252
interface GigabitEthernet0/0/0.14
 description MUMBAI-RTR1
 encapsulation dot1Q 14
 ip address 203.0.113.17 255.255.255.252
interface GigabitEthernet0/0/0.15
 description CLOUD-VPC-VGW-SIM
 encapsulation dot1Q 15
 ip address 203.0.113.21 255.255.255.252
!
end
write memory
```

### ISP-SW

```cisco
! ======================================================================
! NetArchitect generated configuration - ISP-SW
! Platform : Cisco Catalyst 3650 (lab Internet access switch)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! ======================================================================
enable
configure terminal
!
hostname ISP-SW
no ip domain-lookup
vlan 11
 name NYC-RTR1
vlan 12
 name LONDON-RTR1
vlan 13
 name SINGAPORE-RTR1
vlan 14
 name MUMBAI-RTR1
vlan 15
 name CLOUD-VPC-VGW-SIM
interface GigabitEthernet1/0/1
 description NYC-RTR1 Gi0/0/1
 switchport mode access
 switchport access vlan 11
 spanning-tree portfast
 no shutdown
interface GigabitEthernet1/0/2
 description LONDON-RTR1 Gi0/0/1
 switchport mode access
 switchport access vlan 12
 spanning-tree portfast
 no shutdown
interface GigabitEthernet1/0/3
 description SINGAPORE-RTR1 Gi0/0/1
 switchport mode access
 switchport access vlan 13
 spanning-tree portfast
 no shutdown
interface GigabitEthernet1/0/4
 description MUMBAI-RTR1 Gi0/0/1
 switchport mode access
 switchport access vlan 14
 spanning-tree portfast
 no shutdown
interface GigabitEthernet1/0/5
 description CLOUD-VPC-VGW-SIM Gi0/0/1
 switchport mode access
 switchport access vlan 15
 spanning-tree portfast
 no shutdown
interface GigabitEthernet1/1/1
 description trunk to ISP-SIM
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 11,12,13,14,15
 switchport nonegotiate
 no shutdown
!
end
write memory
```

### CLOUD-VPC-VGW-SIM

```cisco
! ======================================================================
! NetArchitect generated configuration - CLOUD-VPC-VGW-SIM
! Platform : Cisco ISR4331 / CSR1000v (lab stand-in for the cloud VPN gateway)
! Scenario : Global WAN
! Paste into privileged EXEC mode. Lab credentials below - change before production.
! In production these values are entered in the cloud console (VPN connection + BGP ASN); this router lets the lab run end-to-end.
! ======================================================================
enable
configure terminal
!
hostname CLOUD-VPC-VGW-SIM
no ip domain-lookup
!
! --- IPsec: IKEv1 AES-256/SHA-256/DH14 ---
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
 lifetime 28800
crypto ipsec transform-set TS-VTI esp-aes 256 esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC-VTI
 set transform-set TS-VTI
crypto isakmp key NA-261fd155fc225fe4 address 203.0.113.6
crypto isakmp key NA-11a9e9909014e40d address 203.0.113.10
interface GigabitEthernet0/0/1
 description INTERNET underlay
 ip address 203.0.113.22 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 203.0.113.21
interface Loopback1
 description VPC subnet APP-TIER 10.200.0.0/24
 ip address 10.200.0.1 255.255.255.0
interface Loopback2
 description VPC subnet DATA-TIER 10.200.1.0/26
 ip address 10.200.1.1 255.255.255.192
interface Tunnel6
 description VTI to NYC-RTR1
 ip address 169.254.10.22 255.255.255.252
 tunnel source GigabitEthernet0/0/1
 tunnel mode ipsec ipv4
 tunnel destination 203.0.113.6
 tunnel protection ipsec profile IPSEC-VTI
interface Tunnel7
 description VTI to LONDON-RTR1
 ip address 169.254.10.26 255.255.255.252
 tunnel source GigabitEthernet0/0/1
 tunnel mode ipsec ipv4
 tunnel destination 203.0.113.10
 tunnel protection ipsec profile IPSEC-VTI
ip route 10.200.0.0 255.255.0.0 Null0 254
router bgp 64512
 bgp log-neighbor-changes
 neighbor 169.254.10.21 remote-as 65010
 neighbor 169.254.10.21 timers 10 30
 neighbor 169.254.10.25 remote-as 65010
 neighbor 169.254.10.25 timers 10 30
 address-family ipv4
  network 10.200.0.0 mask 255.255.0.0
  neighbor 169.254.10.21 activate
  neighbor 169.254.10.25 activate
 exit-address-family
!
end
write memory
```
