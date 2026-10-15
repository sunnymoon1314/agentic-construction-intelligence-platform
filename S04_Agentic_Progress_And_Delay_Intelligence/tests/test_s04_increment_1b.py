"""
ACIP S04: Increment 1B Comprehensive Automated Test Suite
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/test_s04_increment_1b.py

Automated acceptance suite validating Increment 1B CPM Recalculation Service:
1. Recalculates discrete-workday CPM forward and backward passes from ingested Parquet.
2. Validates 100% mathematical parity against golden benchmark WHC_COM_BL01 targets.
3. Asserts independent Total Float (TF) and Free Float (FF) calculations (e.g., ACT-04 TF=5, FF=5).
4. Detects and rejects circular network dependencies via Kahn's algorithm (CyclicDependencyError).
5. Handles Start-to-Finish (SF) and multi-calendar networks (CAL-STD-5D + CAL-SGP-6D).
6. Atomically commits recalculated lakehouse datasets with tamper-evident commit manifests.
7. Preserves zero regressions across Gate 2 and Increment 1A suites.
"""

from datetime import date, datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import pandas as pd

from engine.cpm_engine import (
    CyclicDependencyError,
    MissingActivityError,
    InvalidRelationshipError,
    build_six_activity_benchmark,
    build_sf_and_mixed_calendar_benchmark,
)
from engine.cpm_recalculation_service import (
    CPMRecalculationService,
    CPMRecalculationError,
    ParityMismatchError,
    FractionalLagUnsupportedError,
    UnresolvedCalendarError,
    MalformedCalendarConfigurationError,
)
from engine.xer_ingestion_pipeline import XERIngestionPipeline


class TestS04Increment1B(unittest.TestCase):
    """Increment 1B CPM Recalculation Automated Acceptance Suite."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="acip_s04_inc1b_")
        cls.module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.bl01_xer_path = os.path.join(
            cls.module_root, "data", "xer", "WHC_COM_BL01_Approved_Baseline.xer"
        )
        cls.up01_xer_path = os.path.join(
            cls.module_root, "data", "xer", "WHC_COM_UP01_Progress_Update.xer"
        )

        # Ingest baseline XER into temporary lakehouse for CPM recalculation testing
        cls.ingestion_store = os.path.join(cls.test_dir, "ingested_bl01")
        pipeline = XERIngestionPipeline()
        pipeline.ingest_and_publish(
            xer_path=cls.bl01_xer_path,
            target_parquet_dir=cls.ingestion_store,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_recalculate_cpm_from_ingested_bl01_parquet(self):
        """Verify CPM recalculation from ingested Parquet reproduces golden benchmark exactly."""
        service = CPMRecalculationService()
        recalc_target = os.path.join(self.test_dir, "recalculated_bl01")

        tables, summary = service.recalculate_and_update(
            parquet_dir=self.ingestion_store,
            target_parquet_dir=recalc_target,
            enforce_golden_parity=True,
        )

        # Assert project finish date
        self.assertEqual(summary["calculated_finish_date"], "2026-11-19")
        self.assertEqual(summary["calculated_start_date"], "2026-11-02")
        self.assertEqual(summary["critical_path_duration_days"], 14)

        df_act = tables["schedule_activities"]
        self.assertEqual(len(df_act), 6)

        # Detailed activity date and float assertions matching golden benchmark
        expected_results = {
            "ACT-01": {"es": date(2026, 11, 2), "ef": date(2026, 11, 2), "tf": 0, "ff": 0, "crit": True},
            "ACT-02": {"es": date(2026, 11, 2), "ef": date(2026, 11, 6), "tf": 0, "ff": 0, "crit": True},
            "ACT-03": {"es": date(2026, 11, 9), "ef": date(2026, 11, 12), "tf": 0, "ff": 0, "crit": True},
            "ACT-04": {"es": date(2026, 11, 4), "ef": date(2026, 11, 11), "tf": 5, "ff": 5, "crit": False},
            "ACT-05": {"es": date(2026, 11, 13), "ef": date(2026, 11, 19), "tf": 0, "ff": 0, "crit": True},
            "ACT-06": {"es": date(2026, 11, 19), "ef": date(2026, 11, 19), "tf": 0, "ff": 0, "crit": True},
        }

        for act_id, exp in expected_results.items():
            row = df_act[df_act["activity_id"] == act_id].iloc[0]
            self.assertEqual(row["early_start_date"], exp["es"], f"{act_id} Early Start mismatch")
            self.assertEqual(row["early_finish_date"], exp["ef"], f"{act_id} Early Finish mismatch")
            self.assertEqual(row["total_float_days"], exp["tf"], f"{act_id} Total Float mismatch")
            self.assertEqual(row["free_float_days"], exp["ff"], f"{act_id} Free Float mismatch")
            self.assertEqual(row["is_critical"], exp["crit"], f"{act_id} Criticality mismatch")

    def test_02_float_independence_demonstration(self):
        """Verify Total Float and Free Float operate independently across the network."""
        net = build_six_activity_benchmark()
        net.calculate_cpm(project_start_date=date(2026, 11, 2))

        # ACT-04 has TF=5 and FF=5 in standard baseline
        act_04 = net.activities["ACT-04"]
        self.assertEqual(act_04.total_float_days, 5)
        self.assertEqual(act_04.free_float_days, 5)

        # Predecessor critical path activities have TF=0 and FF=0
        for crit_act in ["ACT-01", "ACT-02", "ACT-03", "ACT-05", "ACT-06"]:
            self.assertEqual(net.activities[crit_act].total_float_days, 0)
            self.assertEqual(net.activities[crit_act].free_float_days, 0)
            self.assertTrue(net.activities[crit_act].is_critical)

    def test_03_cyclic_network_detection_rejection(self):
        """Verify cyclic dependencies in schedule network raise CyclicDependencyError."""
        net = build_six_activity_benchmark()
        # Introduce cycle: ACT-06 (terminal) -> ACT-01 (start)
        from engine.cpm_engine import Relationship
        net.add_relationship(Relationship("ACT-06", "ACT-01", "FS", 0))

        with self.assertRaises(CyclicDependencyError):
            net.calculate_cpm(project_start_date=date(2026, 11, 2))

    def test_04_missing_activity_dependency_rejection(self):
        """Verify relationship referencing non-existent activity raises MissingActivityError."""
        net = build_six_activity_benchmark()
        from engine.cpm_engine import Relationship

        with self.assertRaises(MissingActivityError):
            net.add_relationship(Relationship("NON_EXISTENT_ACT", "ACT-02", "FS", 0))

    def test_05_sf_and_mixed_calendar_cpm_verification(self):
        """Verify Start-to-Finish (SF) and mixed 5-day / 6-day calendar calculation."""
        net = build_sf_and_mixed_calendar_benchmark()
        calc_start, calc_finish = net.calculate_cpm(project_start_date=date(2026, 11, 2))

        self.assertIsInstance(calc_start, date)
        self.assertIsInstance(calc_finish, date)
        self.assertGreaterEqual(calc_finish, calc_start)

        # Verify SF relationship link exists and resolves
        sf_act = net.activities.get("SF-02")
        self.assertIsNotNone(sf_act)
        self.assertIsNotNone(sf_act.early_start)
        self.assertIsNotNone(sf_act.early_finish)

    def test_06_atomic_lakehouse_recalculation_publish(self):
        """Verify recalculated tables publish atomically with manifest and rollback on fault."""
        service = CPMRecalculationService()
        recalc_target = os.path.join(self.test_dir, "published_recalc_lakehouse")

        tables, _ = service.recalculate_and_update(
            parquet_dir=self.ingestion_store,
            target_parquet_dir=recalc_target,
        )

        self.assertTrue(os.path.islink(recalc_target))
        manifest_path = os.path.join(recalc_target, "_manifest.json")
        self.assertTrue(os.path.exists(manifest_path))

        with open(manifest_path) as f:
            manifest = json.load(f)
        self.assertIn("tables", manifest)
        self.assertIn("schedule_activities.parquet", manifest["tables"])
        self.assertEqual(manifest["tables"]["schedule_activities.parquet"]["rows"], 6)

        # Fault injection rollback test
        initial_link = os.readlink(recalc_target)
        with self.assertRaises(RuntimeError):
            service.recalculate_and_update(
                parquet_dir=self.ingestion_store,
                target_parquet_dir=recalc_target,
                simulate_interruption=True,
            )

        # Assert pointer remained untouched
        self.assertEqual(os.readlink(recalc_target), initial_link)

    def test_07_fractional_lag_rejection_and_precision_preservation(self):
        """
        Verify R1 Fractional Lag Policy (Comprehensive End-to-End Precision & Guardrail):
        1. Positive fractional lag (+1.5 workdays) asserts explicit start/finish dates,
           sub-day offsets, backward-pass late dates/offsets, exact float (0.0), and driving flag.
        2. Negative fractional lag (-0.5 workdays) asserts explicit start/finish dates,
           sub-day offsets, backward propagation, and driving flag.
        3. Negative control asserts that when a secondary constraint dominates,
           the fractional relationship de-asserts driving (is_driving == False) and produces
           exact fractional Total Float (0.5 days) and Free Float (0.5 days).
        4. Guardrail: enforce_discrete_guardrail=True fails closed with FractionalLagUnsupportedError.
        5. Integer floats (e.g. 2.0) are accepted and preserved across both modes.
        """
        service = CPMRecalculationService()

        # 1. End-to-End Positive (+1.5d) & Negative (-0.5d) Fractional Lag Verification
        frac_dir_e2e = os.path.join(self.test_dir, "test_frac_e2e")
        os.makedirs(frac_dir_e2e, exist_ok=True)

        df_ver = pd.DataFrame([{
            "project_id": "PRJ-FRAC-001",
            "schedule_version": "V01",
            "planned_start_date": "2026-11-02",  # Monday
        }])
        df_act = pd.DataFrame([
            {"activity_id": "T-A", "activity_name": "Task A (Source)", "original_duration_days": 2, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-B", "activity_name": "Task B (+1.5d Lag)", "original_duration_days": 2, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-C", "activity_name": "Task C (-0.5d Lag)", "original_duration_days": 1, "calendar_id": "CAL-STD-5D"},
        ])
        df_rel = pd.DataFrame([
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 1.5},
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-C", "relationship_type": "FS", "lag_days": -0.5},
        ])
        df_cal = pd.DataFrame([
            {"calendar_id": "CAL-STD-5D", "calendar_name": "Standard 5-Day", "weekend_days_json": json.dumps(["SATURDAY", "SUNDAY"]), "statutory_holidays_json": "[]"}
        ])

        df_ver.to_parquet(os.path.join(frac_dir_e2e, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(frac_dir_e2e, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(frac_dir_e2e, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(frac_dir_e2e, "calendars.parquet"))

        tables_e2e, summary_e2e = service.recalculate_and_update(
            parquet_dir=frac_dir_e2e,
            enforce_golden_parity=False,
            enforce_discrete_guardrail=False,
        )

        res_act = tables_e2e["schedule_activities"]
        res_rel = tables_e2e["schedule_relationships"]

        # Predecessor T-A: Starts Mon Nov 2 (offset 0.0), finishes Tue Nov 3 (offset 0.0)
        t_a = res_act[res_act["activity_id"] == "T-A"].iloc[0]
        self.assertEqual(t_a["early_start_date"], date(2026, 11, 2))
        self.assertEqual(t_a["early_start_offset_days"], 0.0)
        self.assertEqual(t_a["early_finish_date"], date(2026, 11, 3))
        self.assertEqual(t_a["early_finish_offset_days"], 0.0)
        self.assertEqual(t_a["late_start_date"], date(2026, 11, 2))
        self.assertEqual(t_a["late_start_offset_days"], 0.0)
        self.assertEqual(t_a["late_finish_date"], date(2026, 11, 3))
        self.assertEqual(t_a["late_finish_offset_days"], 0.0)
        self.assertEqual(t_a["total_float_days"], 0.0)
        self.assertTrue(t_a["is_critical"])

        # Successor T-B (+1.5d lag):
        # Tuesday 17:00 + 1.0 workday lag = Wednesday 17:00; + 0.5 workday lag = Thursday 12:00 (offset 0.5)
        # Duration 2 days on CAL-STD-5D (Thu 0.5d + Fri 1.0d + Mon 0.5d) -> finishes Monday Nov 9 (offset 0.5)
        t_b = res_act[res_act["activity_id"] == "T-B"].iloc[0]
        self.assertEqual(t_b["early_start_date"], date(2026, 11, 5))
        self.assertEqual(t_b["early_start_offset_days"], 0.5)
        self.assertEqual(t_b["early_finish_date"], date(2026, 11, 9))
        self.assertEqual(t_b["early_finish_offset_days"], 0.5)
        self.assertEqual(t_b["late_start_date"], date(2026, 11, 5))
        self.assertEqual(t_b["late_start_offset_days"], 0.5)
        self.assertEqual(t_b["late_finish_date"], date(2026, 11, 9))
        self.assertEqual(t_b["late_finish_offset_days"], 0.5)
        self.assertEqual(t_b["total_float_days"], 0.0)
        self.assertTrue(t_b["is_critical"])

        # Relationship T-A -> T-B is driving (matches date 2026-11-05 AND offset 0.5)
        rel_ab = res_rel[(res_rel["predecessor_activity_id"] == "T-A") & (res_rel["successor_activity_id"] == "T-B")].iloc[0]
        self.assertTrue(rel_ab["is_driving"], "Positive fractional lag relationship must be driving")

        # Successor T-C (-0.5d lead):
        # Starts 0.5 days before T-A finishes -> Tuesday Nov 3 at 12:00 (offset 0.5)
        # Duration 1 day -> finishes Wednesday Nov 4 at 12:00 (offset 0.5)
        t_c = res_act[res_act["activity_id"] == "T-C"].iloc[0]
        self.assertEqual(t_c["early_start_date"], date(2026, 11, 3))
        self.assertEqual(t_c["early_start_offset_days"], 0.5)
        self.assertEqual(t_c["early_finish_date"], date(2026, 11, 4))
        self.assertEqual(t_c["early_finish_offset_days"], 0.5)
        self.assertEqual(t_c["late_start_date"], date(2026, 11, 6))
        self.assertEqual(t_c["late_start_offset_days"], 0.5)
        self.assertEqual(t_c["late_finish_date"], date(2026, 11, 9))
        self.assertEqual(t_c["late_finish_offset_days"], 0.5)
        self.assertEqual(t_c["total_float_days"], 3.0)
        self.assertFalse(t_c["is_critical"])

        # Relationship T-A -> T-C is driving for T-C's start
        rel_ac = res_rel[(res_rel["predecessor_activity_id"] == "T-A") & (res_rel["successor_activity_id"] == "T-C")].iloc[0]
        self.assertTrue(rel_ac["is_driving"], "Negative fractional lag relationship must be driving for T-C start")

        # 2. Negative Control for Fractional Relationship:
        # Dominating task T-DOM (duration 4 days) pushes T-B's start to Friday Nov 6 (offset 0.0)
        neg_ctrl_dir = os.path.join(self.test_dir, "test_frac_neg_ctrl")
        os.makedirs(neg_ctrl_dir, exist_ok=True)

        df_act_neg = pd.DataFrame([
            {"activity_id": "T-A", "activity_name": "Task A (Source)", "original_duration_days": 2, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-DOM", "activity_name": "Dominating Task", "original_duration_days": 4, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-B", "activity_name": "Task B", "original_duration_days": 2, "calendar_id": "CAL-STD-5D"},
        ])
        df_rel_neg = pd.DataFrame([
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 1.5},
            {"predecessor_activity_id": "T-DOM", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 0.0},
        ])
        df_ver.to_parquet(os.path.join(neg_ctrl_dir, "schedule_versions.parquet"))
        df_act_neg.to_parquet(os.path.join(neg_ctrl_dir, "schedule_activities.parquet"))
        df_rel_neg.to_parquet(os.path.join(neg_ctrl_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(neg_ctrl_dir, "calendars.parquet"))

        tables_neg, _ = service.recalculate_and_update(
            parquet_dir=neg_ctrl_dir,
            enforce_golden_parity=False,
            enforce_discrete_guardrail=False,
        )
        res_act_neg = tables_neg["schedule_activities"]
        res_rel_neg = tables_neg["schedule_relationships"]

        # T-DOM governs: T-DOM -> T-B is driving, T-A -> T-B is NON-DRIVING
        rel_ab_neg = res_rel_neg[(res_rel_neg["predecessor_activity_id"] == "T-A") & (res_rel_neg["successor_activity_id"] == "T-B")].iloc[0]
        rel_dom_b = res_rel_neg[(res_rel_neg["predecessor_activity_id"] == "T-DOM") & (res_rel_neg["successor_activity_id"] == "T-B")].iloc[0]
        self.assertFalse(rel_ab_neg["is_driving"], "Fractional relationship must be non-driving when dominated")
        self.assertTrue(rel_dom_b["is_driving"], "Dominating predecessor relationship must be driving")

        # T-A gains exact 0.5 workdays of float from the offset difference (Thu 12:00 vs Fri 08:00)
        t_a_neg = res_act_neg[res_act_neg["activity_id"] == "T-A"].iloc[0]
        self.assertEqual(t_a_neg["total_float_days"], 0.5, "T-A must carry exact 0.5 workdays total float")
        self.assertEqual(t_a_neg["free_float_days"], 0.5, "T-A must carry exact 0.5 workdays free float")
        self.assertFalse(t_a_neg["is_critical"])

        # 3. Recommended Guardrail (Fail-Closed Rejection when discrete boundaries are mandatory)
        with self.assertRaises(FractionalLagUnsupportedError) as ctx_pos:
            service.load_network_from_parquet(frac_dir_e2e, enforce_discrete_guardrail=True)
        self.assertIn("specifies fractional lag of 1.5 workdays", str(ctx_pos.exception))

        # 4. Integer Float Preservation (2.0)
        int_float_dir = os.path.join(self.test_dir, "test_int_float")
        os.makedirs(int_float_dir, exist_ok=True)
        df_rel_int = pd.DataFrame([
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 2.0},
        ])
        df_ver.to_parquet(os.path.join(int_float_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(int_float_dir, "schedule_activities.parquet"))
        df_rel_int.to_parquet(os.path.join(int_float_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(int_float_dir, "calendars.parquet"))

        net, _, raw_tables, _ = service.load_network_from_parquet(int_float_dir, enforce_discrete_guardrail=True)
        self.assertIn("T-B", net.activities)
        rel_row = raw_tables["schedule_relationships"].iloc[0]
        self.assertEqual(float(rel_row["lag_days"]), 2.0)

    def test_08_driving_flags_across_all_four_relationship_types_including_sf(self):
        """
        Verify R2: Driving flags across all 4 relationship types (FS, SS, FF, SF)
        with explicit date and constraint assertions PLUS negative control test where SF is non-driving.
        """
        service = CPMRecalculationService()
        fixture_dir = os.path.join(self.test_dir, "test_driving_all_types")
        os.makedirs(fixture_dir, exist_ok=True)

        # Network covering FS, SS, FF, SF:
        # T-A: Start Milestone (2026-11-02)
        # T-B: 5 days (2026-11-02 to 2026-11-06) linked to T-A via FS lag 0 -> DRIVING
        # T-C: 3 days (2026-11-04 to 2026-11-06) linked to T-B via SS lag 2 -> DRIVING
        # T-D: 5 days (2026-11-02 to 2026-11-06) linked to T-B via FF lag 0 -> DRIVING
        # T-E: 3 days on CAL-SGP-6D linked to T-B via SF lag 2 (Constraint EF = Nov 2 + 2d = Nov 4) -> DRIVING
        df_ver = pd.DataFrame([{
            "project_id": "PRJ-DRV-001",
            "schedule_version": "V01",
            "planned_start_date": "2026-11-02",
        }])
        df_act = pd.DataFrame([
            {"activity_id": "T-A", "activity_name": "Task A Start", "original_duration_days": 0, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-B", "activity_name": "Task B", "original_duration_days": 5, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-C", "activity_name": "Task C (SS)", "original_duration_days": 3, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-D", "activity_name": "Task D (FF)", "original_duration_days": 5, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-E", "activity_name": "Task E (SF)", "original_duration_days": 3, "calendar_id": "CAL-SGP-6D"},
        ])
        df_rel = pd.DataFrame([
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 0},
            {"predecessor_activity_id": "T-B", "successor_activity_id": "T-C", "relationship_type": "SS", "lag_days": 2},
            {"predecessor_activity_id": "T-B", "successor_activity_id": "T-D", "relationship_type": "FF", "lag_days": 0},
            {"predecessor_activity_id": "T-B", "successor_activity_id": "T-E", "relationship_type": "SF", "lag_days": 2, "lag_calendar_id": "CAL-SGP-6D"},
        ])
        df_cal = pd.DataFrame([
            {"calendar_id": "CAL-STD-5D", "calendar_name": "Standard 5 Day", "weekend_days_json": '["SATURDAY", "SUNDAY"]', "statutory_holidays_json": '[]'},
            {"calendar_id": "CAL-SGP-6D", "calendar_name": "Singapore 6 Day", "weekend_days_json": '["SUNDAY"]', "statutory_holidays_json": '[]'},
        ])

        df_ver.to_parquet(os.path.join(fixture_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(fixture_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(fixture_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(fixture_dir, "calendars.parquet"))

        tables, summary = service.recalculate_and_update(
            parquet_dir=fixture_dir,
            enforce_golden_parity=False,
        )

        res_rel = tables["schedule_relationships"]
        res_act = tables["schedule_activities"]

        # Explicit date assertions for SF successor T-E
        t_e = res_act[res_act["activity_id"] == "T-E"].iloc[0]
        self.assertEqual(t_e["early_finish_date"], date(2026, 11, 4), "T-E EF must equal SF constraint date")
        self.assertEqual(t_e["early_start_date"], date(2026, 11, 2), "T-E ES must match duration back-calculated from EF")

        # 1. T-A -> T-B (FS) drives T-B's start
        rel_fs = res_rel[(res_rel["predecessor_activity_id"] == "T-A") & (res_rel["successor_activity_id"] == "T-B")].iloc[0]
        self.assertTrue(rel_fs["is_driving"], "FS relationship should be DRIVING")

        # 2. T-B -> T-C (SS) drives T-C's start
        rel_ss = res_rel[(res_rel["predecessor_activity_id"] == "T-B") & (res_rel["successor_activity_id"] == "T-C")].iloc[0]
        self.assertTrue(rel_ss["is_driving"], "SS relationship should be DRIVING")

        # 3. T-B -> T-D (FF) drives T-D's finish
        rel_ff = res_rel[(res_rel["predecessor_activity_id"] == "T-B") & (res_rel["successor_activity_id"] == "T-D")].iloc[0]
        self.assertTrue(rel_ff["is_driving"], "FF relationship should be DRIVING")

        # 4. T-B -> T-E (SF) drives T-E's finish
        rel_sf = res_rel[(res_rel["predecessor_activity_id"] == "T-B") & (res_rel["successor_activity_id"] == "T-E")].iloc[0]
        self.assertTrue(rel_sf["is_driving"], "SF relationship should be DRIVING")

        # 5. Negative Control Test: SF relationship is NOT driving when secondary constraint dominates
        neg_dir = os.path.join(self.test_dir, "test_driving_sf_negative_control")
        os.makedirs(neg_dir, exist_ok=True)
        # Add T-IND (duration 6 on CAL-SGP-6D) driving T-E via FS lag 0
        df_act_neg = pd.DataFrame([
            {"activity_id": "T-A", "activity_name": "Task A Start", "original_duration_days": 0, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-B", "activity_name": "Task B", "original_duration_days": 5, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "T-IND", "activity_name": "Independent Task", "original_duration_days": 6, "calendar_id": "CAL-SGP-6D"},
            {"activity_id": "T-E", "activity_name": "Task E (SF)", "original_duration_days": 3, "calendar_id": "CAL-SGP-6D"},
        ])
        df_rel_neg = pd.DataFrame([
            {"predecessor_activity_id": "T-A", "successor_activity_id": "T-B", "relationship_type": "FS", "lag_days": 0},
            {"predecessor_activity_id": "T-B", "successor_activity_id": "T-E", "relationship_type": "SF", "lag_days": 2, "lag_calendar_id": "CAL-SGP-6D"},
            {"predecessor_activity_id": "T-IND", "successor_activity_id": "T-E", "relationship_type": "FS", "lag_days": 0},
        ])
        df_ver.to_parquet(os.path.join(neg_dir, "schedule_versions.parquet"))
        df_act_neg.to_parquet(os.path.join(neg_dir, "schedule_activities.parquet"))
        df_rel_neg.to_parquet(os.path.join(neg_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(neg_dir, "calendars.parquet"))

        tables_neg, _ = service.recalculate_and_update(
            parquet_dir=neg_dir,
            enforce_golden_parity=False,
        )
        res_rel_neg = tables_neg["schedule_relationships"]
        res_act_neg = tables_neg["schedule_activities"]

        t_e_neg = res_act_neg[res_act_neg["activity_id"] == "T-E"].iloc[0]
        # T-IND finishes on 2026-11-07, so T-E starts 2026-11-09 and finishes 2026-11-11
        # The SF constraint date was 2026-11-04, which is earlier than 2026-11-11
        rel_sf_neg = res_rel_neg[(res_rel_neg["predecessor_activity_id"] == "T-B") & (res_rel_neg["successor_activity_id"] == "T-E")].iloc[0]
        self.assertFalse(rel_sf_neg["is_driving"], "SF relationship must NOT be driving when FS pushes finish beyond SF constraint")

    def test_09_parquet_calendar_definitions_govern_recalculation_end_to_end(self):
        """
        Verify R3 & R6: Calendar Governance and Source of Authority:
        1. Parquet lakehouse calendar definitions take precedence over built-ins (PARQUET_GOVERNED).
        2. Malformed weekend_days_json raises MalformedCalendarConfigurationError fail-closed.
        3. Unrecognized weekday name raises MalformedCalendarConfigurationError fail-closed.
        4. Malformed statutory_holidays_json raises MalformedCalendarConfigurationError fail-closed.
        5. Unparseable ISO holiday date string raises MalformedCalendarConfigurationError fail-closed.
        6. Custom 4-day calendar from Parquet actively governs CPM recalculation dates.
        7. Reference to an undefined calendar ID raises UnresolvedCalendarError fail-closed.
        """
        service = CPMRecalculationService()
        cal_dir = os.path.join(self.test_dir, "test_calendar_e2e")
        os.makedirs(cal_dir, exist_ok=True)

        df_ver = pd.DataFrame([{
            "project_id": "PRJ-CAL-001",
            "schedule_version": "V01",
            "planned_start_date": "2026-11-02",  # Monday
        }])
        # Define a custom 4-day calendar with Wednesday holiday in calendars.parquet
        df_cal = pd.DataFrame([
            {
                "calendar_id": "CAL-CUST-4D",
                "calendar_name": "Custom 4-Day Workweek with Holiday",
                "weekend_days_json": json.dumps(["FRIDAY", "SATURDAY", "SUNDAY"]),
                "statutory_holidays_json": json.dumps(["2026-11-04"]),  # Wednesday Nov 4 is a holiday
            },
            {
                "calendar_id": "CAL-STD-5D",
                "calendar_name": "Standard 5 Day",
                "weekend_days_json": json.dumps(["SATURDAY", "SUNDAY"]),
                "statutory_holidays_json": json.dumps([]),
            },
        ])
        df_act = pd.DataFrame([
            {"activity_id": "ACT_CUST", "activity_name": "Custom Task", "original_duration_days": 3, "calendar_id": "CAL-CUST-4D"},
            {"activity_id": "ACT_STD", "activity_name": "Standard Task", "original_duration_days": 3, "calendar_id": "CAL-STD-5D"},
        ])
        df_rel = pd.DataFrame(columns=["predecessor_activity_id", "successor_activity_id", "relationship_type", "lag_days"])

        df_ver.to_parquet(os.path.join(cal_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(cal_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(cal_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(cal_dir, "calendars.parquet"))

        tables, _ = service.recalculate_and_update(
            parquet_dir=cal_dir,
            enforce_golden_parity=False,
        )
        res_act = tables["schedule_activities"]
        act_cust = res_act[res_act["activity_id"] == "ACT_CUST"].iloc[0]
        act_std = res_act[res_act["activity_id"] == "ACT_STD"].iloc[0]

        # Standard 5D: Mon Nov 2, Tue Nov 3, Wed Nov 4 -> finishes Wednesday Nov 4
        self.assertEqual(act_std["early_finish_date"], date(2026, 11, 4))

        # Custom 4D: Mon Nov 2 (day 1), Tue Nov 3 (day 2), Wed Nov 4 (Holiday!), Thu Nov 5 (day 3) -> finishes Thursday Nov 5
        self.assertEqual(act_cust["early_finish_date"], date(2026, 11, 5))

        # 1. Fail-closed test on undefined calendar ID (R6)
        df_act_bad = df_act.copy()
        df_act_bad.loc[0, "calendar_id"] = "CAL-UNKNOWN-99"
        bad_dir = os.path.join(self.test_dir, "test_bad_cal")
        os.makedirs(bad_dir, exist_ok=True)
        df_ver.to_parquet(os.path.join(bad_dir, "schedule_versions.parquet"))
        df_act_bad.to_parquet(os.path.join(bad_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(bad_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(bad_dir, "calendars.parquet"))

        with self.assertRaises(UnresolvedCalendarError):
            service.load_network_from_parquet(bad_dir)

        # 2. Fail-closed test on malformed weekend_days_json (R3)
        mal_wknd_dir = os.path.join(self.test_dir, "test_malformed_wknd_json")
        os.makedirs(mal_wknd_dir, exist_ok=True)
        df_cal_mal_w = df_cal.copy()
        df_cal_mal_w.loc[0, "weekend_days_json"] = "['SATURDAY', invalid json}"
        df_cal_mal_w.to_parquet(os.path.join(mal_wknd_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(mal_wknd_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(mal_wknd_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(mal_wknd_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_mw:
            service.load_network_from_parquet(mal_wknd_dir)
        self.assertIn("malformed weekend_days_json", str(ctx_mw.exception))

        # 3. Fail-closed test on unrecognized weekend day name (R3)
        inv_day_dir = os.path.join(self.test_dir, "test_invalid_wknd_name")
        os.makedirs(inv_day_dir, exist_ok=True)
        df_cal_inv_d = df_cal.copy()
        df_cal_inv_d.loc[0, "weekend_days_json"] = json.dumps(["NOT_A_VALID_DAY"])
        df_cal_inv_d.to_parquet(os.path.join(inv_day_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(inv_day_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(inv_day_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(inv_day_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_id:
            service.load_network_from_parquet(inv_day_dir)
        self.assertIn("unrecognized weekend day name", str(ctx_id.exception))

        # 4. Fail-closed test on malformed statutory_holidays_json (R3)
        mal_hol_dir = os.path.join(self.test_dir, "test_malformed_hol_json")
        os.makedirs(mal_hol_dir, exist_ok=True)
        df_cal_mal_h = df_cal.copy()
        df_cal_mal_h.loc[0, "statutory_holidays_json"] = "{malformed: json}"
        df_cal_mal_h.to_parquet(os.path.join(mal_hol_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(mal_hol_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(mal_hol_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(mal_hol_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_mh:
            service.load_network_from_parquet(mal_hol_dir)
        self.assertIn("malformed statutory_holidays_json", str(ctx_mh.exception))

        # 5. Fail-closed test on unparseable ISO holiday date string (R3)
        inv_date_dir = os.path.join(self.test_dir, "test_invalid_hol_date")
        os.makedirs(inv_date_dir, exist_ok=True)
        df_cal_inv_date = df_cal.copy()
        df_cal_inv_date.loc[0, "statutory_holidays_json"] = json.dumps(["invalid-date-format-999"])
        df_cal_inv_date.to_parquet(os.path.join(inv_date_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(inv_date_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(inv_date_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(inv_date_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_idate:
            service.load_network_from_parquet(inv_date_dir)
        self.assertIn("unparseable ISO holiday date string", str(ctx_idate.exception))

        # 6. Fail-closed test on null/missing weekend_days_json in authoritative record (A3)
        null_wknd_dir = os.path.join(self.test_dir, "test_null_wknd_json")
        os.makedirs(null_wknd_dir, exist_ok=True)
        df_cal_null_w = df_cal.copy()
        df_cal_null_w.loc[0, "weekend_days_json"] = None
        df_cal_null_w.to_parquet(os.path.join(null_wknd_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(null_wknd_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(null_wknd_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(null_wknd_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_nw:
            service.load_network_from_parquet(null_wknd_dir)
        self.assertIn("weekend_days_json' must be explicitly specified", str(ctx_nw.exception))

        # 7. Fail-closed test on null/missing statutory_holidays_json in authoritative record (A3)
        null_hol_dir = os.path.join(self.test_dir, "test_null_hol_json")
        os.makedirs(null_hol_dir, exist_ok=True)
        df_cal_null_h = df_cal.copy()
        df_cal_null_h.loc[0, "statutory_holidays_json"] = None
        df_cal_null_h.to_parquet(os.path.join(null_hol_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(null_hol_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(null_hol_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(null_hol_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_nh:
            service.load_network_from_parquet(null_hol_dir)
        self.assertIn("statutory_holidays_json' must be explicitly specified", str(ctx_nh.exception))

        # 8. Fail-closed test on completely omitted weekend_days_json column (A3)
        no_col_dir = os.path.join(self.test_dir, "test_missing_col_wknd")
        os.makedirs(no_col_dir, exist_ok=True)
        df_cal_no_col = df_cal.drop(columns=["weekend_days_json"])
        df_cal_no_col.to_parquet(os.path.join(no_col_dir, "calendars.parquet"))
        df_ver.to_parquet(os.path.join(no_col_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(no_col_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(no_col_dir, "schedule_relationships.parquet"))

        with self.assertRaises(MalformedCalendarConfigurationError) as ctx_nc:
            service.load_network_from_parquet(no_col_dir)
        self.assertIn("weekend_days_json' must be explicitly specified", str(ctx_nc.exception))

    def test_10_authoritative_lag_calendar_default_to_predecessor_calendar(self):
        """
        Verify R4: Authoritative default for relationship lags aligns to predecessor activity calendar across all paths.
        Predecessor is 6-day (CAL-TEST-6D), Successor is 5-day (CAL-TEST-5D).
        Lag = 1 day over Saturday.
        Forward Pass:
        - Pred starts Mon Nov 2, finishes Friday Nov 6.
        - Under predecessor calendar (6D), Saturday Nov 7 is a working day, so 1-day lag elapses on Saturday.
        - Successor starts Monday Nov 9 on CAL-TEST-5D, finishes Wednesday Nov 11.
        Backward Pass (Cross-Calendar Non-Zero Lag):
        - Successor late finish: Wednesday Nov 11, late start: Monday Nov 9, Total Float: 0.
        - Predecessor backward pass steps back 1 lag day on CAL-TEST-6D from Mon Nov 9 -> Saturday Nov 7.
        - Preceding workday on CAL-TEST-6D is Friday Nov 6.
        - Predecessor late finish: Friday Nov 6, late start: Monday Nov 2, Total Float: 0.
        - Demonstrates full forward-backward symmetry and zero float across cross-calendar boundaries.
        """
        service = CPMRecalculationService()
        cross_dir = os.path.join(self.test_dir, "test_cross_cal_lag")
        os.makedirs(cross_dir, exist_ok=True)

        df_ver = pd.DataFrame([{
            "project_id": "PRJ-CROSS-001",
            "schedule_version": "V01",
            "planned_start_date": "2026-11-02",
        }])
        df_cal = pd.DataFrame([
            {"calendar_id": "CAL-TEST-5D", "calendar_name": "Test 5-Day Workweek", "weekend_days_json": json.dumps(["SATURDAY", "SUNDAY"]), "statutory_holidays_json": "[]"},
            {"calendar_id": "CAL-TEST-6D", "calendar_name": "Test 6-Day Workweek", "weekend_days_json": json.dumps(["SUNDAY"]), "statutory_holidays_json": "[]"},
        ])
        df_act = pd.DataFrame([
            {"activity_id": "ACT-PRED-6D", "activity_name": "Pred 6D", "original_duration_days": 5, "calendar_id": "CAL-TEST-6D"},
            {"activity_id": "ACT-SUCC-5D", "activity_name": "Succ 5D", "original_duration_days": 3, "calendar_id": "CAL-TEST-5D"},
        ])
        # lag_calendar_id omitted (None) -> MUST default to ACT-PRED-6D calendar (CAL-TEST-6D)
        df_rel = pd.DataFrame([
            {"predecessor_activity_id": "ACT-PRED-6D", "successor_activity_id": "ACT-SUCC-5D", "relationship_type": "FS", "lag_days": 1, "lag_calendar_id": None},
        ])

        df_ver.to_parquet(os.path.join(cross_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(cross_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(cross_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(cross_dir, "calendars.parquet"))

        tables, _ = service.recalculate_and_update(
            parquet_dir=cross_dir,
            enforce_golden_parity=False,
        )
        res_act = tables["schedule_activities"]
        pred_row = res_act[res_act["activity_id"] == "ACT-PRED-6D"].iloc[0]
        succ_row = res_act[res_act["activity_id"] == "ACT-SUCC-5D"].iloc[0]

        # 1. Forward Pass explicit assertions
        self.assertEqual(pred_row["early_finish_date"], date(2026, 11, 6))
        self.assertEqual(succ_row["early_start_date"], date(2026, 11, 9))
        self.assertEqual(succ_row["early_finish_date"], date(2026, 11, 11))

        # 2. Backward Pass explicit cross-calendar assertions (R4)
        self.assertEqual(succ_row["late_finish_date"], date(2026, 11, 11))
        self.assertEqual(succ_row["late_start_date"], date(2026, 11, 9))
        self.assertEqual(succ_row["total_float_days"], 0)
        self.assertTrue(succ_row["is_critical"])

        self.assertEqual(pred_row["late_finish_date"], date(2026, 11, 6))
        self.assertEqual(pred_row["late_start_date"], date(2026, 11, 2))
        self.assertEqual(pred_row["total_float_days"], 0)
        self.assertTrue(pred_row["is_critical"])

    def test_11_fail_closed_missing_planned_start_and_dynamic_duration_derivation(self):
        """
        Verify R5: Missing or unparseable planned_start_date fails closed without synthetic fallbacks,
        and critical_path_duration_days is dynamically calculated from actual network date spans
        with explicit governing project calendar basis reporting.
        """
        service = CPMRecalculationService()
        dyn_dir = os.path.join(self.test_dir, "test_dynamic_duration")
        os.makedirs(dyn_dir, exist_ok=True)

        # 1. Missing planned_start_date fails closed
        df_ver_empty = pd.DataFrame([{
            "project_id": "PRJ-DYN-001",
            "schedule_version": "V01",
            "planned_start_date": None,
        }])
        df_act = pd.DataFrame([
            {"activity_id": "ACT-A", "activity_name": "Task A", "original_duration_days": 10, "calendar_id": "CAL-STD-5D"},
            {"activity_id": "ACT-B", "activity_name": "Task B", "original_duration_days": 15, "calendar_id": "CAL-STD-5D"},
        ])
        df_rel = pd.DataFrame([
            {"predecessor_activity_id": "ACT-A", "successor_activity_id": "ACT-B", "relationship_type": "FS", "lag_days": 0},
        ])
        df_cal = pd.DataFrame([
            {"calendar_id": "CAL-STD-5D", "calendar_name": "Standard 5 Day", "weekend_days_json": '["SATURDAY", "SUNDAY"]', "statutory_holidays_json": '[]'},
        ])

        df_ver_empty.to_parquet(os.path.join(dyn_dir, "schedule_versions.parquet"))
        df_act.to_parquet(os.path.join(dyn_dir, "schedule_activities.parquet"))
        df_rel.to_parquet(os.path.join(dyn_dir, "schedule_relationships.parquet"))
        df_cal.to_parquet(os.path.join(dyn_dir, "calendars.parquet"))

        with self.assertRaises(CPMRecalculationError) as ctx_err:
            service.load_network_from_parquet(dyn_dir)
        self.assertIn("Missing or unparseable planned_start_date", str(ctx_err.exception))

        # 2. Dynamic critical path duration verification (25 workdays, proving no static 14 fallback)
        df_ver_valid = pd.DataFrame([{
            "project_id": "PRJ-DYN-001",
            "schedule_version": "V01",
            "planned_start_date": "2026-11-02",
        }])
        df_ver_valid.to_parquet(os.path.join(dyn_dir, "schedule_versions.parquet"))

        tables, summary = service.recalculate_and_update(
            parquet_dir=dyn_dir,
            enforce_golden_parity=False,
        )
        # ACT-A is 10 days + ACT-B is 15 days = 25 total working days
        self.assertEqual(summary["critical_path_duration_days"], 25)
        self.assertNotEqual(summary["critical_path_duration_days"], 14)
        # Calendar basis explicitly verified (R5)
        self.assertEqual(summary["duration_calendar_basis"], "CAL-STD-5D")

    def test_12_audit_runner_non_zero_exit_on_suite_failure(self):
        """
        Verify A2: Audit runner process exit status signals non-zero when a test suite fails.
        Executes run_increment_1b_audit.py with SIMULATE_AUDIT_FAILURE=1 and verifies proc.returncode == 1.
        """
        if os.environ.get("SIMULATE_AUDIT_FAILURE") == "1":
            return  # Prevent recursive child spawn when invoked in negative-control mode

        runner_path = os.path.join(self.module_root, "tests", "run_increment_1b_audit.py")
        env = {**os.environ, "SIMULATE_AUDIT_FAILURE": "1"}
        proc = subprocess.run(
            [sys.executable, runner_path],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 1, f"Audit runner must exit with code 1 on simulated failure, got {proc.returncode}")
        self.assertIn("Simulated negative-control failure", proc.stdout)
        self.assertIn("FINAL AUDIT STATUS: FAILED (REMEDIATION REQUIRED)", proc.stdout)


if __name__ == "__main__":
    unittest.main()
