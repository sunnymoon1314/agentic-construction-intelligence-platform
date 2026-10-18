#!/usr/bin/env python3
"""
ACIP S04: Dashboard EXP-01 Candidate Integration Test Suite
Validates dual-version schedule querying, candidate status, fail-closed validation,
reconciliation to deterministic CPM results, and baseline preservation.
"""

import os
import sys
import json
import unittest
import urllib.request
import urllib.error

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

BASE_URL = "http://localhost:8087"


class TestDashboardEXP01Integration(unittest.TestCase):
    """Integration test suite for S04 dashboard multi-version schedule support."""

    def _get_json(self, path):
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "ACIP-EXP01-Test"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                data = json.loads(response.read().decode("utf-8"))
                return status, data
        except urllib.error.HTTPError as e:
            data = json.loads(e.read().decode("utf-8"))
            return e.code, data

    def test_01_bl01_certified_baseline_preserved(self):
        """Verify BL-01 returns certified baseline with exactly 6 activities and APPROVED status."""
        status, data = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001&version=BL-01")
        self.assertEqual(status, 200)
        self.assertEqual(data["schedule_version"], "BL-01")
        self.assertEqual(data["version_status"], "APPROVED")
        self.assertFalse(data.get("is_candidate", False))
        self.assertEqual(len(data["activities"]), 6)
        self.assertEqual(len(data["relationships"]), 6)
        self.assertEqual(data["completion_milestone_id"], "ACT-06")
        self.assertEqual(data["baseline_completion_date"], "2026-11-19")
        self.assertEqual(data["activities_lineage"], "data/parquet/schedule_activities.parquet")

    def test_02_default_version_defaults_to_bl01(self):
        """Verify omitting version parameter continues to serve BL-01 for backward compatibility."""
        status, data = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status, 200)
        self.assertEqual(data["schedule_version"], "BL-01")
        self.assertEqual(data["version_status"], "APPROVED")
        self.assertEqual(len(data["activities"]), 6)

    def test_03_exp01_candidate_reconciles_to_deterministic_cpm(self):
        """Verify EXP-01 candidate serves 26 activities, 107 workdays, 20 critical path nodes, and PROPOSED status."""
        status, data = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001&version=EXP-01")
        self.assertEqual(status, 200)
        self.assertEqual(data["schedule_version"], "EXP-01")
        self.assertEqual(data["version_status"], "PROPOSED")
        self.assertTrue(data["is_candidate"])
        self.assertEqual(data["total_workdays"], 107)
        self.assertEqual(data["activity_count"], 26)
        self.assertEqual(data["relationship_count"], 34)
        self.assertEqual(data["critical_activity_count"], 20)
        self.assertEqual(data["non_critical_activity_count"], 6)
        self.assertEqual(data["project_early_start"], "2026-11-02")
        self.assertEqual(data["project_early_finish"], "2027-03-30")
        self.assertEqual(data["completion_milestone_id"], "ACT-26")
        self.assertEqual(data["erss_milestone_id"], "ACT-18")
        self.assertEqual(data["erss_milestone_date"], "2027-02-11")

        # Reconcile positive total float values
        act_map = {a["activity_id"]: a for a in data["activities"]}
        self.assertEqual(len(act_map), 26)
        expected_floats = {
            "ACT-02": 1,
            "ACT-12": 3,
            "ACT-09": 6,
            "ACT-21": 6,
            "ACT-16": 13,
            "ACT-11": 24,
        }
        for aid, exp_tf in expected_floats.items():
            self.assertIn(aid, act_map)
            self.assertEqual(act_map[aid]["total_float"], exp_tf, f"Float mismatch on {aid}")
            self.assertFalse(act_map[aid]["is_critical"], f"{aid} must be non-critical")

    def test_04_fail_closed_on_invalid_version(self):
        """Verify requesting an unknown schedule version fails safely with HTTP 404."""
        status, data = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001&version=UNKNOWN-VER")
        self.assertEqual(status, 404)
        self.assertIn("error", data)
        self.assertIn("UNKNOWN-VER", data["error"])

    def test_05_cross_project_isolation(self):
        """Verify non-WHC projects do not leak EXP-01 candidate data."""
        status, data = self._get_json("/api/schedule?project_id=PRJ-T5-003&version=EXP-01")
        self.assertEqual(status, 200)
        self.assertEqual(data["project_id"], "PRJ-T5-003")
        self.assertNotEqual(data.get("schedule_version"), "EXP-01")

    def test_06_physical_parquet_baseline_unmutated(self):
        """Verify certified baseline parquet on disk was not modified or overwritten."""
        baseline_path = os.path.join(MODULE_ROOT, "data", "parquet", "schedule_activities.parquet")
        self.assertTrue(os.path.exists(baseline_path))
        import pyarrow.parquet as pq
        tbl = pq.read_table(baseline_path)
        self.assertEqual(tbl.num_rows, 6, "Certified baseline must remain strictly 6 rows")


if __name__ == "__main__":
    unittest.main()
