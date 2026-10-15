#!/usr/bin/env python3
"""
ACIP S04: Increment 2 Automated Verification & Regression Suite
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/test_s04_increment_2.py

Verification Targets for Increment 2:
1. TEST-01: Time Impact Analysis (TIA) fragnet insertion benchmark on ACT-03 (+3 workdays net delay).
2. TEST-02: Float absorption on non-critical path activity ACT-04 (0 project delay, float erosion from 5d to 3d).
3. TEST-03: SCL Delay Protocol Core Principle 10 concurrency attribution (CONCURRENT_SPLIT).
4. TEST-04: Singapore PSSCOC 2020 Clause 23.1 statutory 28-day notice window verification.
5. TEST-05: Point-of-use contract verification guardrail (unverified deed yields UNASSESSED / ADVISORY).
6. TEST-06: FastMCP baseline comparison tool (s04_compare_schedule_baselines).
7. TEST-07: FastMCP dynamic CPM recalculation tool with what-if overrides (s04_recalculate_cpm_schedule).
8. TEST-08: FastMCP liquidated damages exposure assessment tool (s04_assess_liquidated_damages_exposure).
"""

from datetime import date, datetime, timedelta
import os
import sys
import unittest
import pandas as pd

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S04_ROOT = MODULE_ROOT
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from engine.cpm_engine import ScheduleNetwork, Activity, Relationship
from engine.cpm_recalculation_service import CPMRecalculationService, DynamicCalendarRegistry
from engine.tia_evaluator import (
    TIAEvaluator,
    DelayEventDefinition,
    FragnetActivity,
    TIAResult,
)
from mcp_server.server import (
    s04_compare_schedule_baselines,
    s04_recalculate_cpm_schedule,
    s04_simulate_tia_fragnet,
    s04_analyze_float_erosion,
    s04_calculate_psscoc_notice_clock,
    s04_assess_liquidated_damages_exposure,
)

DATA_DIR = os.path.join(MODULE_ROOT, "data")
PARQUET_DIR = os.path.join(DATA_DIR, "parquet")


class TestS04Increment2(unittest.TestCase):
    """Increment 2 Automated Verification Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.cpm_service = CPMRecalculationService(default_calendar_id="CAL-STD-5D")
        cls.evaluator = TIAEvaluator(cpm_service=cls.cpm_service)
        cls.base_network, cls.project_start, cls.tables, cls.registry = cls.cpm_service.load_network_from_parquet(
            PARQUET_DIR
        )

    def test_01_tia_fragnet_injection_benchmark(self):
        """
        TEST-01: Verifies controlled fragnet insertion on ACT-03 (Basement Excavation).
        Unimpacted finish: 2026-11-19 (Thursday)
        Fragnet: 3 workdays delay
        Expected Impacted finish: 2026-11-24 (Tuesday)
        Net Critical Delay: 3.0 workdays
        Candidate EOT: 3.0 workdays
        """
        frag = FragnetActivity(
            activity_id="FRAG-TEST-01",
            activity_name="Unforeseen Ground Hard Rock Fragnet",
            duration_days=3.0,
            calendar_id="CAL-STD-5D",
            predecessor_id="ACT-03",
            predecessor_rel="FS",
            predecessor_lag=0.0,
            successor_id="ACT-05",
            successor_rel="FS",
            successor_lag=0.0,
        )

        event = DelayEventDefinition(
            event_id="DLY-TEST-001",
            event_title="Unforeseen Ground Hard Rock",
            cause_category="PHYSICAL_CONDITIONS",
            risk_allocation="EMPLOYER_RISK",
            event_start_date=date(2026, 11, 9),
            event_end_date=date(2026, 11, 13),
            notice_served_date=date(2026, 11, 12),
            fragnets=[frag],
        )

        result = self.evaluator.evaluate_fragnet_impact(
            base_network=self.base_network,
            project_start=self.project_start,
            registry=self.registry,
            event=event,
            daily_ld_rate_sgd=15000.0,
            notice_window_days=28,
            is_contract_verified=True,
        )

        self.assertEqual(result.unimpacted_completion_date, date(2026, 11, 19))
        self.assertEqual(result.impacted_completion_date, date(2026, 11, 24))
        self.assertEqual(result.net_critical_delay_workdays, 3.0)
        self.assertEqual(result.candidate_eot_relief_days, 3.0)
        self.assertEqual(result.contractor_culpable_days, 0.0)
        self.assertEqual(result.liquidated_damages_exposure_sgd, 0.0)
        self.assertEqual(result.notice_compliance_status, "COMPLIANT")

    def test_02_tia_float_absorption_non_critical(self):
        """
        TEST-02: Verifies float absorption on non-critical activity ACT-04 (Ground Anchors).
        ACT-04 has 5 workdays of total float. Inserting a 2-day fragnet should:
        1. Result in 0 workdays of project completion delay.
        2. Erode total float on ACT-04 from 5d to 3d.
        """
        frag = FragnetActivity(
            activity_id="FRAG-TEST-02",
            activity_name="Anchor Drilling Subcontractor Rescheduling",
            duration_days=2.0,
            calendar_id="CAL-STD-5D",
            predecessor_id="ACT-04",
            predecessor_rel="FS",
            predecessor_lag=0.0,
            successor_id="ACT-05",
            successor_rel="FF",
            successor_lag=1.0,
        )

        event = DelayEventDefinition(
            event_id="DLY-TEST-002",
            event_title="Subcontractor Rescheduling",
            cause_category="CONTRACTOR_DEFAULT",
            risk_allocation="CONTRACTOR_RISK",
            event_start_date=date(2026, 11, 5),
            event_end_date=date(2026, 11, 7),
            notice_served_date=date(2026, 11, 6),
            fragnets=[frag],
        )

        result = self.evaluator.evaluate_fragnet_impact(
            base_network=self.base_network,
            project_start=self.project_start,
            registry=self.registry,
            event=event,
            daily_ld_rate_sgd=15000.0,
            notice_window_days=28,
            is_contract_verified=True,
        )

        # Zero project completion delay because float absorbed the impact
        self.assertEqual(result.unimpacted_completion_date, date(2026, 11, 19))
        self.assertEqual(result.impacted_completion_date, date(2026, 11, 19))
        self.assertEqual(result.net_critical_delay_workdays, 0.0)
        self.assertEqual(result.liquidated_damages_exposure_sgd, 0.0)

        # Float erosion on ACT-04 consumed 2 workdays
        act04_erosion = result.float_erosion.get("ACT-04")
        self.assertIsNotNone(act04_erosion)
        self.assertEqual(act04_erosion["total_float_before"], 5.0)
        self.assertEqual(act04_erosion["total_float_after"], 3.0)
        self.assertEqual(act04_erosion["float_consumed"], 2.0)

    def test_03_scl_concurrency_split_attribution(self):
        """
        TEST-03: Verifies SCL Delay Protocol Core Principle 10 concurrency attribution.
        When an event is designated as CONCURRENT_SPLIT:
        - Candidate EOT relief is granted against liquidated damages (relief from LD).
        - Prolongation costs are flagged as REQUIRES_SO_DETERMINATION.
        """
        frag = FragnetActivity(
            activity_id="FRAG-TEST-03",
            activity_name="Concurrent Design Variation and Equipment Failure",
            duration_days=4.0,
            calendar_id="CAL-STD-5D",
            predecessor_id="ACT-03",
            predecessor_rel="FS",
            successor_id="ACT-05",
            successor_rel="FS",
        )

        event = DelayEventDefinition(
            event_id="DLY-TEST-003",
            event_title="Concurrent Architectural Drawing and Rig Breakdown",
            cause_category="CONCURRENT_EVENT",
            risk_allocation="CONCURRENT_SPLIT",
            event_start_date=date(2026, 11, 9),
            event_end_date=date(2026, 11, 15),
            notice_served_date=date(2026, 11, 10),
            fragnets=[frag],
        )

        result = self.evaluator.evaluate_fragnet_impact(
            base_network=self.base_network,
            project_start=self.project_start,
            registry=self.registry,
            event=event,
            daily_ld_rate_sgd=15000.0,
            notice_window_days=28,
            is_contract_verified=True,
        )

        self.assertEqual(result.concurrency_attribution, "CONCURRENT_SPLIT")
        self.assertEqual(result.candidate_eot_relief_days, result.net_critical_delay_workdays)
        self.assertEqual(result.contractor_culpable_days, 0.0)
        self.assertEqual(result.liquidated_damages_exposure_sgd, 0.0)
        self.assertEqual(result.candidate_prolongation_cost_status, "REQUIRES_SO_DETERMINATION")

    def test_04_psscoc_notice_clock_28_day_boundary(self):
        """
        TEST-04: Verifies Singapore PSSCOC 2020 Clause 23.1 28-day notice clock boundary:
        - Notice served on day 28 (inclusive): COMPLIANT
        - Notice served on day 29: POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION
        - Notice served on day 10: COMPLIANT
        """
        start_d = date(2026, 11, 1)

        # Exactly 28 days
        notice_28 = start_d + timedelta(days=28)
        status_28, elapsed_28 = self.evaluator.evaluate_psscoc_notice(start_d, notice_28, notice_window_days=28, is_contract_verified=True)
        self.assertEqual(status_28, "COMPLIANT")
        self.assertEqual(elapsed_28, 28)

        # 29 days (Late notice)
        notice_29 = start_d + timedelta(days=29)
        status_29, elapsed_29 = self.evaluator.evaluate_psscoc_notice(start_d, notice_29, notice_window_days=28, is_contract_verified=True)
        self.assertEqual(status_29, "POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION")
        self.assertEqual(elapsed_29, 29)

        # Early notice
        notice_10 = start_d + timedelta(days=10)
        status_10, elapsed_10 = self.evaluator.evaluate_psscoc_notice(start_d, notice_10, notice_window_days=28, is_contract_verified=True)
        self.assertEqual(status_10, "COMPLIANT")
        self.assertEqual(elapsed_10, 10)

    def test_05_unverified_contract_guardrail(self):
        """
        TEST-05: Verifies that unverified contract deeds (is_contract_verified=False)
        fail-closed to advisory status, preventing binding legal conclusions.
        """
        status, elapsed = self.evaluator.evaluate_psscoc_notice(
            event_start_date=date(2026, 11, 1),
            notice_served_date=date(2026, 11, 5),
            is_contract_verified=False,
        )
        self.assertEqual(status, "UNASSESSED")

        ld_res = s04_assess_liquidated_damages_exposure(
            contractor_culpable_days=5.0,
            daily_rate_sgd=15000.0,
            is_contract_verified=False,
        )
        self.assertEqual(ld_res["assurance_tier"], "ADVISORY_SIMULATION_ONLY")
        self.assertFalse(ld_res["is_contract_verified"])

    def test_06_fastmcp_tool_baseline_comparison(self):
        """
        TEST-06: Verifies FastMCP tool s04_compare_schedule_baselines returns
        6 activities, 6 relationships, and correct critical path activities.
        """
        res = s04_compare_schedule_baselines()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_activities"], 6)
        self.assertEqual(res["total_relationships"], 6)
        self.assertIn("ACT-01", res["critical_path_activities"])
        self.assertIn("ACT-02", res["critical_path_activities"])
        self.assertIn("ACT-03", res["critical_path_activities"])
        self.assertIn("ACT-05", res["critical_path_activities"])
        self.assertIn("ACT-06", res["critical_path_activities"])
        self.assertNotIn("ACT-04", res["critical_path_activities"])

    def test_07_fastmcp_tool_dynamic_recalculation(self):
        """
        TEST-07: Verifies FastMCP tool s04_recalculate_cpm_schedule executes
        what-if overrides without mutating disk files.
        """
        # Baseline finish is 2026-11-19. Adding 2 workdays to ACT-03 (from 4d to 6d) shifts completion to 2026-11-23.
        res = s04_recalculate_cpm_schedule(duration_overrides={"ACT-03": 6.0})
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["recalculated_completion_date"], "2026-11-23")
        self.assertIn("ACT-03", res["critical_path"])

    def test_08_fastmcp_tool_liquidated_damages_exposure(self):
        """
        TEST-08: Verifies FastMCP tool s04_assess_liquidated_damages_exposure
        correctly computes exposure under Singapore PSSCOC 2020 Clause 24.1.
        """
        res = s04_assess_liquidated_damages_exposure(
            contractor_culpable_days=3.0,
            daily_rate_sgd=15000.0,
            is_contract_verified=True,
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_liquidated_damages_exposure_sgd"], 45000.0)
        self.assertEqual(res["assurance_tier"], "CERTIFIED_ASSESSMENT")
        self.assertTrue(res["is_contract_verified"])

    def test_09_fail_closed_contract_verification_scenarios(self):
        """
        TEST-09 (Contract Verification Assurance):
        Directly exercises evaluate_parquet_delay_event() loading path against controlled fixtures:
        (a) contract_parameters.parquet table absent entirely from directory
        (b) empty contract_parameters.parquet table (0 rows)
        (c) missing verified_against_signed_contract column in table
        (d) null / NaN verification value in table
        (e) verified_against_signed_contract = True (positive control)
        All cases (a)-(d) must fail-closed to UNASSESSED, and case (e) must yield COMPLIANT.
        """
        import shutil
        import tempfile

        base_parquet = os.path.join(S04_ROOT, "data", "parquet")
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Copy all base tables EXCEPT contract_parameters.parquet
            for tbl in [
                "schedule_activities.parquet",
                "schedule_relationships.parquet",
                "schedule_versions.parquet",
                "calendars.parquet",
                "delay_events.parquet",
                "delay_event_activities.parquet",
            ]:
                src = os.path.join(base_parquet, tbl)
                if os.path.exists(src):
                    shutil.copy(src, os.path.join(tmp_dir, tbl))

            cp_file = os.path.join(tmp_dir, "contract_parameters.parquet")

            # Case (a): contract_parameters.parquet completely absent
            res_a = self.evaluator.evaluate_parquet_delay_event(tmp_dir, "DLY-2026-001")
            self.assertEqual(res_a.notice_compliance_status, "UNASSESSED")

            # Case (b): empty contract DataFrame (0 rows)
            pd.DataFrame().to_parquet(cp_file)
            res_b = self.evaluator.evaluate_parquet_delay_event(tmp_dir, "DLY-2026-001")
            self.assertEqual(res_b.notice_compliance_status, "UNASSESSED")

            # Case (c): missing verified_against_signed_contract column
            df_c = pd.DataFrame([{"daily_liquidated_damages_rate_sgd": 15000.0, "delay_notice_period_days": 28}])
            df_c.to_parquet(cp_file)
            res_c = self.evaluator.evaluate_parquet_delay_event(tmp_dir, "DLY-2026-001")
            self.assertEqual(res_c.notice_compliance_status, "UNASSESSED")

            # Case (d): null/NaN verification value
            df_d = pd.DataFrame([{"daily_liquidated_damages_rate_sgd": 15000.0, "delay_notice_period_days": 28, "verified_against_signed_contract": None}])
            df_d.to_parquet(cp_file)
            res_d = self.evaluator.evaluate_parquet_delay_event(tmp_dir, "DLY-2026-001")
            self.assertEqual(res_d.notice_compliance_status, "UNASSESSED")

            # Case (e): Positive control with verified_against_signed_contract = True
            df_e = pd.DataFrame([{"daily_liquidated_damages_rate_sgd": 15000.0, "delay_notice_period_days": 28, "verified_against_signed_contract": True}])
            df_e.to_parquet(cp_file)
            res_e = self.evaluator.evaluate_parquet_delay_event(tmp_dir, "DLY-2026-001")
            self.assertEqual(res_e.notice_compliance_status, "COMPLIANT")

    def test_10_sql_parameterization_and_injection_defense(self):
        """
        TEST-10 (Finding 3 Remediation): Verifies SQL parameterization in mcp_server/server.py.
        Unusual user input containing SQL injection syntax (' OR '1'='1) must be safely treated
        as a literal string value rather than SQL tokens, producing zero matches and zero syntax errors.
        """
        malicious_input = "' OR '1'='1"

        # Baseline comparison parameterized query
        res_comp = s04_compare_schedule_baselines(project_id=malicious_input)
        self.assertEqual(res_comp["status"], "SUCCESS")
        self.assertEqual(res_comp["total_activities"], 0)
        self.assertEqual(res_comp["total_relationships"], 0)

        # Float erosion parameterized query
        res_erosion = s04_analyze_float_erosion(project_id=malicious_input)
        self.assertEqual(res_erosion["status"], "SUCCESS")
        self.assertEqual(res_erosion["total_activities_evaluated"], 0)

    def test_11_audit_manifest_missing_artefact_negative_control(self):
        """
        TEST-11 (Audit Manifest Verification Assurance):
        Subprocess-level negative control proving that a missing required tracked file
        causes run_increment_2_audit.py CLI to fail with non-zero exit code (code 1)
        and emit explicit failure statuses.
        """
        import subprocess
        from tests.run_increment_2_audit import check_manifest

        # 1. Direct manifest checker verification
        manifest_passed, log_lines, missing_files = check_manifest(simulated_missing="engine/tia_evaluator.py")
        self.assertFalse(manifest_passed)
        self.assertIn("engine/tia_evaluator.py", missing_files)

        # 2. Subprocess execution verification (with recursion guard)
        if os.environ.get("SIMULATE_MISSING_ARTEFACT"):
            return

        env = os.environ.copy()
        env["SIMULATE_MISSING_ARTEFACT"] = "engine/tia_evaluator.py"
        audit_runner_path = os.path.join(S04_ROOT, "tests", "run_increment_2_audit.py")
        proc = subprocess.run(
            [sys.executable, audit_runner_path],
            env=env,
            capture_output=True,
            text=True,
            cwd=S04_ROOT,
        )
        self.assertEqual(proc.returncode, 1, f"Audit runner must exit with code 1. Output:\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("MANIFEST AUDIT STATUS: FAILED", proc.stdout)
        self.assertIn("FINAL AUDIT STATUS: FAILED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
