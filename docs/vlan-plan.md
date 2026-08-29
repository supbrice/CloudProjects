# VLAN and IP plan

Sanitized addressing for the Computer Plus Solutions site. Replace `10.10.0.0/16` if this is reused as a template.

## Zones

| VLAN | Name | Zone | Subnet | Gateway | DHCP | DNS | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | Corporate | corporate | 10.10.10.0/24 | 10.10.10.1 | 10.10.10.50–199 | 10.10.10.1 | Staff LAN; internet via NAT |
| 20 | Public | public | 10.10.20.0/24 | 10.10.20.1 | 10.10.20.50–220 | 1.1.1.1, 9.9.9.9 | Guest SSID; no RFC1918 except gw |
| 30 | OT-Signage | ot | 10.10.30.0/24 | 10.10.30.1 | 10.10.30.200–220 | 10.10.30.1 | Players mostly static `.10–.49` |
| 40 | OT-Signals | ot | 10.10.40.0/24 | 10.10.40.1 | none (static) | 10.10.40.1 | Control endpoints; QoS EF |
| 50 | OT-Fleet | ot | 10.10.50.0/24 | 10.10.50.1 | 10.10.50.200–220 | 10.10.50.1 | Tracking gateways; QoS AF41 |
| 60 | Protect | protect | 10.10.60.0/24 | 10.10.60.1 | none (static) | 10.10.60.1 | Console `.2`; cameras `.10+` |
| 99 | Management | management | 10.10.99.0/24 | 10.10.99.1 | 10.10.99.200–220 | 10.10.99.1 | Switches, controller, jump host |

Machine-readable copy: [`vlan-plan.csv`](vlan-plan.csv).

## Switchport roles

| Role | Mode | Allowed VLANs | Typical use |
| --- | --- | --- | --- |
| Access-Corp | access | 10 | Staff drops, printers |
| Access-Public | access | 20 | Public-area wired kiosks (rare) |
| Access-Signage | access | 30 | Display players |
| Access-Signals | access | 40 | Signal controllers |
| Access-Fleet | access | 50 | Tracking radios / gateways |
| Access-Protect | access + PoE | 60 | Cameras |
| AP-trunk | trunk | 10,20,99 | Corporate + guest SSIDs; AP mgmt on 99 |
| IDF-uplink | trunk | 10,20,30,40,50,60,99 | Switch-to-switch / switch-to-gateway |
| Mgmt | access | 99 | Spare for console or laptop |

## SSID mapping

| SSID (example) | VLAN | Isolation |
| --- | --- | --- |
| CPS-Staff | 10 | Client isolation off; LAN allowed |
| CPS-Guest | 20 | Client isolation on; guest portal optional |
| CPS-OT | 30 or 50 | Hidden; PSK rotated; no guest portal |

Signals stay wired. Cameras stay wired on VLAN 60.

## DHCP options (corporate / public)

| Option | Corporate | Public |
| --- | --- | --- |
| 003 Router | 10.10.10.1 | 10.10.20.1 |
| 006 DNS | 10.10.10.1 | 1.1.1.1, 9.9.9.9 |
| 015 Domain | cps.internal | (none) |
| 051 Lease | 8 hours | 2 hours |

OT and Protect use static addresses so a DHCP outage does not take down cameras or signals. Small commissioning pools exist on 30/50/99 only.

## Demo vs live targets for scripts

| Check | `demo` profile | `live` profile |
| --- | --- | --- |
| DNS | `cloudflare.com`, `quad9.net` | `cps.internal` + vendor hostnames in the CSV |
| Reachability | TCP/443 to `1.1.1.1` and `9.9.9.9` | ICMP/TCP to each VLAN gateway |
| DHCP | Local interface has a lease (informational) | Client on VLAN 10 or 20 gets the scope above |
