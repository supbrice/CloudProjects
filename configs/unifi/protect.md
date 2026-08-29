# UniFi Protect — port and power notes

Localized Protect deployment: console and cameras on VLAN 60, powered from the same PoE switches as the access layer. Analytics stay on the console (person/vehicle detections), not a cloud video platform.

## Addressing

| Role | Address | Port profile |
| --- | --- | --- |
| Protect console | 10.10.60.2 | VLAN 60 access, no PoE (wall / UPS) |
| Cameras | 10.10.60.10+ | VLAN 60 access + PoE |
| Controller / Network app | 10.10.99.2 | VLAN 99 (same UniFi OS host if combined) |

## Switchport example (per camera)

```
interface GigabitEthernet1/0/5
  description G4-Bullet-Entry
  switchport mode access
  switchport access vlan 60
  spanning-tree portfast
  spanning-tree bpduguard enable
  poe mode auto
```

UniFi UI equivalent: port **Profile = Protect-Camera** (native VLAN 60, PoE on, isolation off so the camera can reach `10.10.60.2`).

## Power

| Device class | Typical draw | Class |
| --- | --- | --- |
| G4 Bullet / Dome | 4–5 W | 0 / 802.3af |
| AC Lite AP | ~13.5 W | 4 / 802.3af |
| AC Pro AP | ~20 W | 4 / 802.3at |

Do not load a 195 W rear IDF the same way as a 370 W front switch. Recalculate with:

```bash
python3 scripts/poe_budget.py --inventory docs/poe-budget.csv
```

Headroom target used on this job: **keep reserved + allocated under 80% of switch budget** so negotiation spikes and a failed camera reboot do not brown out an AP.

## Fast Ethernet verification

Some camera drops only trained at **100 Mbps / full duplex**. That was accepted when:

1. `ethtool` / switch port stats showed 100/full, not 100/half.
2. Protect timeline stayed continuous (no repeated disconnects).
3. CRC / FCS counters on the port stayed flat after a soak.

If the port flapped or sat at half duplex: reterminate, shorter patch, or a media converter — do not “fix” it by forcing 1G on a bad pair.

## Isolation

Cameras do not get a default route to the internet (WAN OUT deny for VLAN 60). Staff VLANs cannot open the Protect UI; use the jump host on VLAN 99 or the console’s local display.
