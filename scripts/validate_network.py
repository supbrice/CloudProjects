#!/usr/bin/env python3
"""Validate DNS, DHCP, reachability, and zone isolation against the VLAN plan.

Profiles
  demo  Public DNS/HTTPS targets so the script runs off-site.
  live  VLAN gateways and vendor hostnames from docs/vlan-plan.csv.
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_LATENCY_MS = 80.0
# Corporate gateway DNS — not 443, which intercepting proxies often answer for any IP.
ISOLATION_TARGET = ("10.10.10.1", 53)
DEMO_DNS = ("cloudflare.com", "quad9.net")
DEMO_TCP = (("1.1.1.1", 443), ("9.9.9.9", 443))


@dataclass
class VlanRow:
    vlan_id: int
    name: str
    zone: str
    cidr: str
    gateway: str
    dhcp_start: str
    dhcp_end: str
    dns: list[str]
    qos_class: str
    allow_internet: str
    inter_vlan: str
    vendor_check_host: str
    notes: str


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    skipped: bool = False


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_plan(path: Path) -> list[VlanRow]:
    rows: list[VlanRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            dns = [part.strip() for part in raw["dns"].split(";") if part.strip()]
            rows.append(
                VlanRow(
                    vlan_id=int(raw["vlan_id"]),
                    name=raw["name"],
                    zone=raw["zone"],
                    cidr=raw["cidr"],
                    gateway=raw["gateway"].strip(),
                    dhcp_start=raw["dhcp_start"].strip(),
                    dhcp_end=raw["dhcp_end"].strip(),
                    dns=dns,
                    qos_class=raw["qos_class"],
                    allow_internet=raw["allow_internet"],
                    inter_vlan=raw["inter_vlan"],
                    vendor_check_host=raw["vendor_check_host"].strip(),
                    notes=raw["notes"],
                )
            )
    if not rows:
        raise ValueError(f"no VLAN rows in {path}")
    return rows


def resolve_name(hostname: str, timeout: float = 3.0) -> tuple[bool, str]:
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        addrs = sorted({info[4][0] for info in infos})
        return True, ", ".join(addrs)
    except OSError as exc:
        return False, str(exc)


def tcp_rtt(host: str, port: int, timeout: float = 3.0) -> tuple[bool, float | None, str]:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            rtt_ms = (time.perf_counter() - start) * 1000.0
            return True, rtt_ms, f"tcp/{port} {rtt_ms:.1f} ms"
    except OSError as exc:
        return False, None, str(exc)


def ping_rtt(host: str, timeout: float = 2.0) -> tuple[bool, float | None, str]:
    if os.name == "nt":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, None, str(exc)
    if proc.returncode != 0:
        err = (proc.stdout or proc.stderr or "ping failed").strip().splitlines()
        return False, None, err[-1] if err else "ping failed"
    text = proc.stdout or ""
    marker = "time="
    lower = text.lower()
    if marker in lower:
        chunk = text[lower.index(marker) + len(marker) :]
        value = chunk.split()[0].rstrip("ms")
        try:
            return True, float(value), f"icmp {value} ms"
        except ValueError:
            pass
    return True, None, "icmp ok"


def _is_private_host(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def reachability(host: str, latency_ms: float) -> CheckResult:
    ok_ping, rtt, detail = ping_rtt(host)
    if ok_ping:
        if rtt is not None and rtt > latency_ms:
            return CheckResult(f"reach {host}", False, f"{detail} (limit {latency_ms:.0f} ms)")
        return CheckResult(f"reach {host}", True, detail)
    # Private gateways: ICMP then DNS/53. Skip 80/443 — proxies often accept those for any IP.
    ports = (53,) if _is_private_host(host) else (443, 53)
    last_tcp = "no tcp fallback"
    for port in ports:
        ok_tcp, rtt, tcp_detail = tcp_rtt(host, port)
        last_tcp = tcp_detail
        if not ok_tcp:
            continue
        if rtt is not None and rtt > latency_ms:
            return CheckResult(f"reach {host}", False, f"{tcp_detail} (limit {latency_ms:.0f} ms)")
        return CheckResult(f"reach {host}", True, f"{tcp_detail} (icmp blocked)")
    return CheckResult(f"reach {host}", False, f"icmp failed ({detail}); tcp failed ({last_tcp})")


def _linux_ipv4_ioctl() -> list[str]:
    import fcntl
    import struct

    sysfs = Path("/sys/class/net")
    if not sysfs.is_dir():
        return []
    found: list[str] = []
    for iface in sysfs.iterdir():
        name = iface.name
        if name == "lo":
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            packed = struct.pack("256s", name.encode()[:15])
            addr = socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915, packed)[20:24])
            found.append(f"{name} {addr}")
        except OSError:
            continue
        finally:
            sock.close()
    return found


def dhcp_info() -> CheckResult:
    if os.name == "nt":
        return CheckResult("dhcp", True, "use Test-NetworkHealth.ps1 on Windows for lease details", skipped=True)
    try:
        proc = subprocess.run(
            ["ip", "-j", "addr"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    if proc is not None and proc.returncode == 0:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            leases: list[str] = []
            for iface in payload:
                ifname = iface.get("ifname", "?")
                for addr in iface.get("addr_info", []):
                    if addr.get("family") != "inet" or addr.get("scope") != "global":
                        continue
                    dyn = "dynamic" if addr.get("dynamic") else "static"
                    leases.append(f"{ifname} {addr.get('local')}/{addr.get('prefixlen')} {dyn}")
            if leases:
                return CheckResult("dhcp", True, "; ".join(leases), skipped=True)
    ioctl_addrs = _linux_ipv4_ioctl()
    if ioctl_addrs:
        return CheckResult("dhcp", True, "; ".join(ioctl_addrs), skipped=True)
    return CheckResult("dhcp", True, "no global IPv4 visible on this host (informational)", skipped=True)


def isolation_check(enabled: bool) -> CheckResult:
    if not enabled:
        return CheckResult(
            "isolation sample",
            True,
            "skipped in demo (would probe 10.10.10.1:53 from public/OT)",
            skipped=True,
        )
    ok, _, detail = tcp_rtt(*ISOLATION_TARGET, timeout=2.0)
    if ok:
        return CheckResult(
            "isolation sample",
            False,
            f"unexpected connect to {ISOLATION_TARGET[0]}:{ISOLATION_TARGET[1]} ({detail})",
        )
    return CheckResult("isolation sample", True, f"no connect to corporate gw ({detail})")


def run_demo(latency_ms: float) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name in DEMO_DNS:
        ok, detail = resolve_name(name)
        results.append(CheckResult(f"dns {name}", ok, detail))
    for host, port in DEMO_TCP:
        ok, rtt, detail = tcp_rtt(host, port)
        if ok and rtt is not None and rtt > latency_ms:
            results.append(CheckResult(f"tcp {host}:{port}", False, f"{detail} (limit {latency_ms:.0f} ms)"))
        else:
            results.append(CheckResult(f"tcp {host}:{port}", ok, detail))
    results.append(dhcp_info())
    results.append(isolation_check(enabled=False))
    return results


def run_live(plan: Iterable[VlanRow], latency_ms: float) -> list[CheckResult]:
    results: list[CheckResult] = []
    for row in plan:
        if row.gateway:
            results.append(reachability(row.gateway, latency_ms))
        host = row.vendor_check_host
        if host and not host.endswith(".test"):
            ok, detail = resolve_name(host)
            results.append(CheckResult(f"dns vlan{row.vlan_id} {host}", ok, detail))
        elif host.endswith(".test"):
            results.append(
                CheckResult(
                    f"dns vlan{row.vlan_id} {host}",
                    True,
                    "placeholder vendor hostname — replace before live cutover",
                    skipped=True,
                )
            )
    results.append(dhcp_info())
    results.append(isolation_check(enabled=True))
    return results


def print_table(results: list[CheckResult]) -> None:
    width = max(len(item.name) for item in results)
    for item in results:
        if item.skipped:
            flag = "SKIP"
        elif item.ok:
            flag = "PASS"
        else:
            flag = "FAIL"
        print(f"{flag:4}  {item.name:<{width}}  {item.detail}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--plan",
        type=Path,
        default=repo_root() / "docs" / "vlan-plan.csv",
        help="VLAN plan CSV",
    )
    parser.add_argument("--profile", choices=("demo", "live"), default="demo")
    parser.add_argument("--latency-ms", type=float, default=DEFAULT_LATENCY_MS)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = load_plan(args.plan)
    if args.profile == "demo":
        results = run_demo(args.latency_ms)
    else:
        results = run_live(plan, args.latency_ms)
    if args.json:
        print(json.dumps([asdict(item) for item in results], indent=2))
    else:
        print(f"profile={args.profile}  vlans={len(plan)}  plan={args.plan}")
        print_table(results)
    failed = [item for item in results if not item.ok and not item.skipped]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
