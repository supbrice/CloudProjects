#!/usr/bin/env python3
"""Offline checks for the VLAN plan, PoE inventory, and UniFi example config."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import poe_budget  # noqa: E402
import validate_network  # noqa: E402


class ArtifactTests(unittest.TestCase):
    def test_vlan_plan_zones(self) -> None:
        plan = validate_network.load_plan(ROOT / "docs" / "vlan-plan.csv")
        names = {row.name for row in plan}
        self.assertEqual(
            names,
            {
                "Corporate",
                "Public",
                "OT-Signage",
                "OT-Signals",
                "OT-Fleet",
                "Protect",
                "Management",
            },
        )
        zones = {row.zone for row in plan}
        self.assertEqual(zones, {"corporate", "public", "ot", "protect", "management"})
        public = next(row for row in plan if row.vlan_id == 20)
        self.assertEqual(public.inter_vlan, "deny")
        protect = next(row for row in plan if row.vlan_id == 60)
        self.assertEqual(protect.allow_internet, "no")
        self.assertEqual(protect.dhcp_start, "")

    def test_poe_headroom(self) -> None:
        switches = poe_budget.load_inventory(ROOT / "docs" / "poe-budget.csv")
        by_name = {sw.name: sw for sw in switches}
        self.assertIn("SW-IDF-FRONT", by_name)
        self.assertIn("SW-IDF-REAR", by_name)
        for sw in switches:
            self.assertTrue(sw.ok, f"{sw.name} over 80% PoE budget")
        self.assertGreater(by_name["SW-IDF-FRONT"].fast_ethernet, 0)

    def test_unifi_networks_match_plan(self) -> None:
        plan = validate_network.load_plan(ROOT / "docs" / "vlan-plan.csv")
        payload = json.loads((ROOT / "configs" / "unifi" / "networks.json").read_text())
        by_vlan = {net["vlan"]: net for net in payload["networks"]}
        self.assertEqual(len(by_vlan), len(plan))
        for row in plan:
            net = by_vlan[row.vlan_id]
            self.assertEqual(net["ip_subnet"], row.cidr)
            self.assertEqual(net["name"], row.name)

    def test_poe_csv_vlans_exist(self) -> None:
        plan_vlans = {
            int(raw["vlan_id"])
            for raw in csv.DictReader((ROOT / "docs" / "vlan-plan.csv").open())
        }
        with (ROOT / "docs" / "poe-budget.csv").open() as handle:
            for raw in csv.DictReader(handle):
                self.assertIn(int(raw["vlan"]), plan_vlans)


if __name__ == "__main__":
    unittest.main(verbosity=2)
