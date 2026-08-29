#!/usr/bin/env python3
"""Sum PoE allocation per switch and flag budgets over 80% utilization."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


HEADROOM_LIMIT = 0.80


@dataclass
class SwitchBudget:
    name: str
    budget_watts: float
    allocated_watts: float
    ports: int
    poe_ports: int
    fast_ethernet: int

    @property
    def reserved(self) -> float:
        return self.allocated_watts / self.budget_watts if self.budget_watts else 0.0

    @property
    def ok(self) -> bool:
        return self.reserved <= HEADROOM_LIMIT


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_inventory(path: Path) -> list[SwitchBudget]:
    grouped: dict[str, SwitchBudget] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            name = raw["switch"]
            if name not in grouped:
                grouped[name] = SwitchBudget(
                    name=name,
                    budget_watts=float(raw["budget_watts"]),
                    allocated_watts=0.0,
                    ports=0,
                    poe_ports=0,
                    fast_ethernet=0,
                )
            row = grouped[name]
            row.ports += 1
            draw = float(raw["allocated_watts"])
            row.allocated_watts += draw
            if draw > 0:
                row.poe_ports += 1
            if raw["link_speed"].upper().startswith("100"):
                row.fast_ethernet += 1
    if not grouped:
        raise ValueError(f"no inventory rows in {path}")
    return list(grouped.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=repo_root() / "docs" / "poe-budget.csv",
    )
    args = parser.parse_args(argv)
    switches = load_inventory(args.inventory)
    print(f"{'switch':<16} {'budget':>8} {'used':>8} {'pct':>7} {'poe':>5} {'100M':>5} status")
    failed = 0
    for sw in switches:
        status = "OK" if sw.ok else "OVER 80%"
        if not sw.ok:
            failed += 1
        print(
            f"{sw.name:<16} {sw.budget_watts:8.1f} {sw.allocated_watts:8.1f} "
            f"{sw.reserved * 100:6.1f}% {sw.poe_ports:5} {sw.fast_ethernet:5} {status}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
