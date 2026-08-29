# Adoption loops and post-cutover checks

## Layer 2 device adoption loops

Symptoms on this build: a switch or camera sat in **Adopting / Getting Ready / Offline**, then came back on the old inform host or on a Layer 2 discovery address that was not the current controller.

Usual cause: the device still had a previous `inform` URL in NVRAM, and L2 discovery plus the new gateway DHCP option were both trying to own it.

### Reset

1. If the device has a reset button, hold until LEDs cycle (typically 10+ seconds).
2. If it still has SSH (`ubnt` / device password from the old site):

```bash
# UniFi device shell — factory NVRAM / default
syswrapper.sh restore-default
```

3. Wait for reboot. Confirm it is on VLAN 99 (switches/APs) or VLAN 60 (cameras) with a DHCP or static address you expect.

### SSH adoption

From a jump host on VLAN 99:

```bash
ssh ubnt@10.10.99.40
set-inform http://10.10.99.2:8080/inform
```

Then adopt **once** in the current controller. Do not point a second controller at the same device. If adoption flaps again, reset NVRAM — do not stack inform URLs.

### What I checked after each device

- Controller shows **Connected**, not a second site’s MAC.
- Switch uplink is a trunk with the VLAN set in [`vlan-plan.md`](vlan-plan.md).
- Camera is access VLAN 60 and drawing PoE (see [`poe-budget.csv`](poe-budget.csv)).
- `info` on the device shell shows the new inform URL only.

---

## Performance and monitoring

Resume work here: validate switch/routing performance, then leave continuous monitoring for staff systems and vendor-hosted OT.

### After each IDF

Run from a laptop on the zone you just stood up:

```bash
python3 scripts/validate_network.py --plan docs/vlan-plan.csv --profile live
```

On a Windows staff PC:

```powershell
.\scripts\Test-NetworkHealth.ps1 -Plan docs\vlan-plan.csv -Profile live
```

Checks encoded in those scripts:

| Check | Pass |
| --- | --- |
| Zone gateway reachable | ICMP or TCP to `gateway` in the plan |
| Latency | RTT under the per-zone threshold (defaults in the scripts) |
| DNS | Resolves the zone’s `vendor_check_host` or demo names |
| DHCP (informational) | Interface has a lease; gateway/DNS match the VLAN |
| Isolation sample | Public/OT client cannot open TCP to `10.10.10.1:53` |

### Continuous

- UniFi controller: device offline, PoE fault, adopt-state change, WAN drop.
- Scheduled script run (Task Scheduler or cron) against corporate DNS and the OT vendor hostnames.
- Ticket if a vendor-hosted signage/fleet/signal URL fails from its VLAN but the WAN is up — routing/NAT/QoS, not “the internet is down.”

This project did not use Prometheus or Grafana.
