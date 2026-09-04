# Firewall, NAT, and QoS (example)

UniFi gateway LAN-in / WAN-out style rules. Order matters: first match wins. These are the policies from the README, written so a reviewer can compare them to a controller.

## Address / port groups

| Group | Members |
| --- | --- |
| RFC1918 | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 |
| CORP_NET | 10.10.10.0/24 |
| PUBLIC_NET | 10.10.20.0/24 |
| OT_NETS | 10.10.30.0/24, 10.10.40.0/24, 10.10.50.0/24 |
| PROTECT_NET | 10.10.60.0/24 |
| MGMT_NET | 10.10.99.0/24 |
| JUMP_HOST | 10.10.99.10 |
| VENDOR_SIGNAGE | destination FQDNs or IPs for the signage CMS |
| VENDOR_SIGNALS | destination FQDNs or IPs for signal vendors |
| VENDOR_FLEET | destination FQDNs or IPs for fleet tracking |

Production vendor IPs are not published here.

## LAN IN (inter-VLAN)

| # | Name | Action | Source | Dest | Service | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | Jump-admin | Accept | JUMP_HOST | RFC1918 | any | Ops only |
| 20 | Protect-local | Accept | PROTECT_NET | 10.10.60.2 | any | Cameras → console |
| 30 | Block-public-east-west | Drop | PUBLIC_NET | RFC1918 | any | Guest cannot see LAN |
| 40 | Block-corp-to-ot | Drop | CORP_NET | OT_NETS | any | Staff ≠ OT |
| 50 | Block-corp-to-protect | Drop | CORP_NET | PROTECT_NET | any | Cameras not on staff LAN |
| 60 | Block-ot-to-corp | Drop | OT_NETS | CORP_NET | any | |
| 70 | Block-ot-to-public | Drop | OT_NETS | PUBLIC_NET | any | |
| 80 | Block-ot-cross | Drop | OT_NETS | OT_NETS | any | Signage ≠ signals ≠ fleet |
| 90 | Block-protect-egress-lan | Drop | PROTECT_NET | RFC1918 | any | After rule 20 |
| 100 | Established | Accept | any | any | established/related | |

WAN-bound traffic is not matched here; it hits NAT + WAN OUT.

## WAN OUT (what may leave the site)

| # | Name | Action | Source | Dest | Service |
| --- | --- | --- | --- | --- | --- |
| 10 | Corp-web | Accept | CORP_NET | any | 80, 443, 53 |
| 20 | Public-web | Accept | PUBLIC_NET | !RFC1918 | 80, 443, 53 |
| 30 | Signage-vendor | Accept | 10.10.30.0/24 | VENDOR_SIGNAGE | 443 |
| 40 | Signals-vendor | Accept | 10.10.40.0/24 | VENDOR_SIGNALS | 443 |
| 50 | Fleet-vendor | Accept | 10.10.50.0/24 | VENDOR_FLEET | 443, vendor UDP if required |
| 60 | Mgmt-updates | Accept | MGMT_NET | any | 80, 443, 123 |
| 70 | Deny-protect-wan | Drop | PROTECT_NET | any | any |
| 80 | Default-drop | Drop | any | any | any |

DNS for public clients is already 1.1.1.1 / 9.9.9.9 via DHCP so they do not use the corporate resolver.

## NAT

| Name | Type | Source | Translated | Comment |
| --- | --- | --- | --- | --- |
| MASQ-CORP | masquerade | 10.10.10.0/24 | WAN address | Staff internet |
| MASQ-PUBLIC | masquerade | 10.10.20.0/24 | WAN address | Guest internet |
| MASQ-OT | masquerade | 10.10.30.0/24, 10.10.40.0/24, 10.10.50.0/24 | WAN address | Vendor-hosted OT only (WAN OUT still filters) |
| No-NAT-Protect | exclude | 10.10.60.0/24 | — | Cameras stay local |

No inbound port forwards in this design. Vendor systems are outbound-initiated.

## QoS queues

| Queue | Class | Match | Intent |
| --- | --- | --- | --- |
| 1 | EF | VLAN 40 | Signals — lowest latency |
| 2 | AF41 | VLAN 50 | Fleet tracking |
| 3 | AF31 | VLAN 60 | Protect video cap so it cannot burst |
| 4 | AF21 | VLAN 30 | Signage updates |
| 5 | CS1 | VLAN 10 | Corporate default |
| 6 | CS0 | VLAN 20 | Public scavenger |

On UniFi this is Smart Queues / traffic rules tagged by source network, not DSCP trust from endpoints (OT devices were inconsistent).
