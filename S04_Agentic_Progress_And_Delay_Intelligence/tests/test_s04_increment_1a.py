"""
ACIP S04: Increment 1A Comprehensive Automated Acceptance Test Suite
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/test_s04_increment_1a.py

Automated acceptance suite validating Increment 1A commitments:
1. Pre-parse cryptographic assertions on authoritative XER fixtures.
2. Canonical 6-activity golden benchmark topology and unmapped table preservation.
3. Fractional relationship lag fidelity (positive lag, negative lead, zero lag).
4. Strict Decimal duration modulo rejection (FractionalWorkdayConversionError).
5. Unconditional fail-closed calendar resolution (UnresolvedCalendarError).
6. Multi-source full-table row-level provenance enforcement (ProvenanceViolationError).
7. Negative malformed XER tests (missing tables, row width mismatch, duplicate codes, invalid links).
8. Genuinely atomic publication commit and fail-closed rollback.
"""

from decimal import Decimal
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, date
import pandas as pd

from engine.data_validator import compute_file_sha256
from engine.xer_ingestion_pipeline import (
    XERIngestionPipeline,
    MissingRequiredXERTableError,
    MalformedXERRowWidthError,
    DuplicateActivityCodeError,
    UnsupportedRelationshipTypeError,
    UnresolvedRelationshipKeyError,
    UnresolvedCalendarError,
    MissingDefaultCalendarError,
    FractionalWorkdayConversionError,
    InvalidNumericDataError,
    ProvenanceViolationError,
)


class TestS04Increment1A(unittest.TestCase):
    """Increment 1A Automated Acceptance Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="acip_s04_inc1a_")
        cls.module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.bl01_xer_path = os.path.join(
            cls.module_root, "data", "xer", "WHC_COM_BL01_Approved_Baseline.xer"
        )
        cls.up01_xer_path = os.path.join(
            cls.module_root, "data", "xer", "WHC_COM_UP01_Progress_Update.xer"
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_pre_parse_cryptographic_and_size_assertions(self):
        """Assert exact physical disk size and SHA-256 for authoritative fixtures."""
        self.assertTrue(os.path.exists(self.bl01_xer_path))
        self.assertTrue(os.path.exists(self.up01_xer_path))

        # 1. Baseline XER
        with open(self.bl01_xer_path, "rb") as f:
            bl_bytes = f.read()
        bl_hash = hashlib.sha256(bl_bytes).hexdigest()
        self.assertEqual(
            len(bl_bytes), 1077, "WHC_COM_BL01_Approved_Baseline.xer must be exactly 1077 bytes"
        )
        self.assertEqual(
            bl_hash,
            "a22ddedd35b7aee75089a1141c71b685fb46ae1939966c6816ff3ac4078e18f1",
            "WHC_COM_BL01_Approved_Baseline.xer SHA-256 mismatch",
        )

        # 2. Progress Update XER
        with open(self.up01_xer_path, "rb") as f:
            up_bytes = f.read()
        up_hash = hashlib.sha256(up_bytes).hexdigest()
        self.assertEqual(
            len(up_bytes), 1155, "WHC_COM_UP01_Progress_Update.xer must be exactly 1155 bytes"
        )
        self.assertEqual(
            up_hash,
            "76e118d7c0efd0e20efa52110f03d3f0f9b289efd97b8d56b96530451f3ef43e",
            "WHC_COM_UP01_Progress_Update.xer SHA-256 mismatch",
        )

    def test_02_golden_benchmark_ingestion_and_topology(self):
        """Verify baseline XER ingestion produces 6 activities, 6 relationships, and preserves UDFs."""
        target_store = os.path.join(self.test_dir, "published_bl01")
        pipeline = XERIngestionPipeline()

        tables = pipeline.ingest_and_publish(
            xer_path=self.bl01_xer_path,
            target_parquet_dir=target_store,
            source_provenance_type="SYNTHETIC_BENCHMARK_FIXTURE",
        )

        # Activities assertion
        df_act = tables["schedule_activities"]
        self.assertEqual(len(df_act), 6, "Expected 6 activities")
        act_ids = set(df_act["activity_id"])
        self.assertEqual(act_ids, {"ACT-01", "ACT-02", "ACT-03", "ACT-04", "ACT-05", "ACT-06"})

        # ACT-04 duration and float assertions
        act_04 = df_act[df_act["activity_id"] == "ACT-04"].iloc[0]
        self.assertEqual(act_04["original_duration_days"], 6)
        self.assertEqual(act_04["total_float_days"], 5)
        self.assertEqual(act_04["free_float_days"], 5)
        self.assertFalse(act_04["is_critical"])

        # Relationships assertion
        df_rel = tables["schedule_relationships"]
        self.assertEqual(len(df_rel), 6, "Expected 6 relationships")

        # schedule_versions assertions
        df_ver = tables["schedule_versions"]
        self.assertEqual(len(df_ver), 1)
        ver_row = df_ver.iloc[0]
        self.assertEqual(
            ver_row["source_file_sha256"],
            "a22ddedd35b7aee75089a1141c71b685fb46ae1939966c6816ff3ac4078e18f1",
        )
        self.assertEqual(ver_row["schedule_timezone"], "Asia/Singapore")

        # Unmapped tables preservation assertion
        extended_json = ver_row["source_extended_tables_json"]
        unmapped = json.loads(extended_json)
        self.assertIn("UDFVALUE", unmapped)
        self.assertEqual(len(unmapped["UDFVALUE"]), 1)
        self.assertEqual(
            unmapped["UDFVALUE"][0]["udf_text"],
            "Preserved Pass-Through Enterprise Field Value",
        )

    def test_03_fractional_lag_fidelity_positive_negative_and_zero(self):
        """Verify positive lag, negative lead, and zero lag are preserved with full precision."""
        custom_xer = [
            "ERMHDR\t8.3\t2026-10-10\tTEST_FIXTURE",
            "%T\tPROJECT",
            "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date",
            "%R\t1001\tPRJ-LAG-TEST\t2026-11-02 08:00\t2026-11-19 17:00",
            "%T\tPROJWBS",
            "%F\twbs_id\tproj_id\twbs_short_name",
            "%R\t2001\t1001\tWHC.SUB",
            "%T\tTASK",
            "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_durn_hr_cnt\ttotal_float_hr_cnt",
            "%R\t3001\t1001\t2001\tACT-A\tTask A\t16.0\t0.0",
            "%R\t3002\t1001\t2001\tACT-B\tTask B\t16.0\t0.0",
            "%R\t3003\t1001\t2001\tACT-C\tTask C\t16.0\t0.0",
            "%T\tTASKPRED",
            "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
            "%R\t4001\t3002\t3001\tPR_FS\t4.0",    # +4.0h lag = +0.5 workdays
            "%R\t4002\t3003\t3002\tPR_SS\t-4.0",   # -4.0h lead = -0.5 workdays
            "%R\t4003\t3003\t3001\tPR_FF\t0.0",    # 0.0h lag = 0.0 workdays
        ]
        xer_path = os.path.join(self.test_dir, "test_fractional_lag.xer")
        with open(xer_path, "w") as f:
            f.write("\n".join(custom_xer) + "\n")

        pipeline = XERIngestionPipeline()
        target_store = os.path.join(self.test_dir, "published_fractional_lag")
        tables = pipeline.ingest_and_publish(
            xer_path=xer_path,
            target_parquet_dir=target_store,
        )

        df_rel = tables["schedule_relationships"]
        self.assertEqual(len(df_rel), 3)

        # 1. Positive fractional lag (+4.0h / 8.0 = 0.5d)
        rel_pos = df_rel[(df_rel["predecessor_activity_id"] == "ACT-A") & (df_rel["successor_activity_id"] == "ACT-B")].iloc[0]
        self.assertEqual(rel_pos["lag_days"], 0.5)
        self.assertEqual(rel_pos["lag_hours"], 4.0)

        # 2. Negative fractional lead (-4.0h / 8.0 = -0.5d)
        rel_neg = df_rel[(df_rel["predecessor_activity_id"] == "ACT-B") & (df_rel["successor_activity_id"] == "ACT-C")].iloc[0]
        self.assertEqual(rel_neg["lag_days"], -0.5)
        self.assertEqual(rel_neg["lag_hours"], -4.0)

        # 3. Zero lag (0.0h / 8.0 = 0.0d)
        rel_zero = df_rel[(df_rel["predecessor_activity_id"] == "ACT-A") & (df_rel["successor_activity_id"] == "ACT-C")].iloc[0]
        self.assertEqual(rel_zero["lag_days"], 0)
        self.assertEqual(rel_zero["lag_hours"], 0.0)

    def test_04_duration_modulo_rejection_fail_closed(self):
        """Verify non-integral activity duration raises FractionalWorkdayConversionError."""
        custom_xer = [
            "ERMHDR\t8.3\t2026-10-10\tTEST_FIXTURE",
            "%T\tPROJECT",
            "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date",
            "%R\t1001\tPRJ-FAIL\t2026-11-02 08:00\t2026-11-19 17:00",
            "%T\tPROJWBS",
            "%F\twbs_id\tproj_id\twbs_short_name",
            "%R\t2001\t1001\tWHC.SUB",
            "%T\tTASK",
            "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_durn_hr_cnt\ttotal_float_hr_cnt",
            "%R\t3001\t1001\t2001\tACT-FAIL\tNon-Integral Task\t41.0\t0.0",  # 41.0h % 8.0 != 0
            "%T\tTASKPRED",
            "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        ]
        xer_path = os.path.join(self.test_dir, "test_fractional_duration.xer")
        with open(xer_path, "w") as f:
            f.write("\n".join(custom_xer) + "\n")

        pipeline = XERIngestionPipeline()
        target_store = os.path.join(self.test_dir, "should_not_publish")
        with self.assertRaises(FractionalWorkdayConversionError):
            pipeline.ingest_and_publish(
                xer_path=xer_path,
                target_parquet_dir=target_store,
            )

    def test_05_calendar_hierarchy_and_fail_closed_validation(self):
        """Verify nonblank invalid calendar raises UnresolvedCalendarError and omitted calendar resolves to default."""
        # 1. Invalid nonblank calendar must fail closed
        xer_bad_cal = [
            "ERMHDR\t8.3\t2026-10-10\tTEST_FIXTURE",
            "%T\tPROJECT",
            "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date",
            "%R\t1001\tPRJ-CAL\t2026-11-02 08:00\t2026-11-19 17:00",
            "%T\tPROJWBS",
            "%F\twbs_id\tproj_id\twbs_short_name",
            "%R\t2001\t1001\tWHC.SUB",
            "%T\tTASK",
            "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_durn_hr_cnt\ttotal_float_hr_cnt\tclndr_id",
            "%R\t3001\t1001\t2001\tACT-01\tTask 1\t16.0\t0.0\tNON_EXISTENT_CALENDAR",
            "%T\tTASKPRED",
            "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        ]
        bad_cal_path = os.path.join(self.test_dir, "test_bad_cal.xer")
        with open(bad_cal_path, "w") as f:
            f.write("\n".join(xer_bad_cal) + "\n")

        pipeline = XERIngestionPipeline()
        with self.assertRaises(UnresolvedCalendarError):
            pipeline.ingest_and_publish(
                xer_path=bad_cal_path,
                target_parquet_dir=os.path.join(self.test_dir, "bad_cal_out"),
            )

        # 2. Omitted calendar resolves to CAL-STD-5D with reason
        xer_omit_cal = [
            "ERMHDR\t8.3\t2026-10-10\tTEST_FIXTURE",
            "%T\tPROJECT",
            "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date",
            "%R\t1001\tPRJ-CAL-OK\t2026-11-02 08:00\t2026-11-19 17:00",
            "%T\tPROJWBS",
            "%F\twbs_id\tproj_id\twbs_short_name",
            "%R\t2001\t1001\tWHC.SUB",
            "%T\tTASK",
            "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttarget_durn_hr_cnt\ttotal_float_hr_cnt",
            "%R\t3001\t1001\t2001\tACT-01\tTask 1\t16.0\t0.0",
            "%T\tTASKPRED",
            "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        ]
        omit_cal_path = os.path.join(self.test_dir, "test_omit_cal.xer")
        with open(omit_cal_path, "w") as f:
            f.write("\n".join(xer_omit_cal) + "\n")

        tables_ok = pipeline.ingest_and_publish(
            xer_path=omit_cal_path,
            target_parquet_dir=os.path.join(self.test_dir, "omit_cal_out"),
        )
        act_row = tables_ok["schedule_activities"].iloc[0]
        self.assertEqual(act_row["calendar_id"], "CAL-STD-5D")
        self.assertEqual(act_row["calendar_resolution_reason"], "SOURCE_OMITTED_DEFAULT_APPLIED")

    def test_06_full_scope_provenance_enforcement(self):
        """Verify row-level provenance is enforced across all 5 canonical tables."""
        pipeline = XERIngestionPipeline()
        target_store = os.path.join(self.test_dir, "published_provenance_test")

        tables = pipeline.ingest_and_publish(
            xer_path=self.bl01_xer_path,
            target_parquet_dir=target_store,
            source_provenance_type="SYNTHETIC_BENCHMARK_FIXTURE",
        )

        for tname in ["schedule_versions", "schedule_activities", "schedule_relationships", "calendars", "contract_parameters"]:
            self.assertIn(tname, tables)
            df = tables[tname]
            self.assertTrue((df["is_synthetic"] == True).all(), f"All rows in {tname} must have is_synthetic=True")
            self.assertTrue(
                (df["synthetic_benchmark_tag"] == "SIMULATED_TEST_SCENARIO_ACIP_S04").all(),
                f"All rows in {tname} must have valid synthetic benchmark tag",
            )

    def test_07_malformed_xer_negative_tests(self):
        """Verify negative tests: missing tables, row width mismatch, duplicate task codes, and bad link keys."""
        pipeline = XERIngestionPipeline()

        # 1. Missing required table (%T TASK)
        xer_missing_task = "ERMHDR\t8.3\t2026-10-10\tTEST\n%T\tPROJECT\n%F\tproj_id\n%R\t1\n%T\tPROJWBS\n%F\twbs_id\n%R\t1\n%T\tTASKPRED\n%F\tid\n"
        p_missing = os.path.join(self.test_dir, "missing_task.xer")
        with open(p_missing, "w") as f:
            f.write(xer_missing_task)
        with self.assertRaises(MissingRequiredXERTableError):
            pipeline.ingest_and_publish(p_missing, os.path.join(self.test_dir, "out1"))

        # 2. Row width mismatch
        xer_bad_width = (
            "ERMHDR\t8.3\t2026-10-10\tTEST\n"
            "%T\tPROJECT\n%F\tproj_id\tproj_short_name\n%R\t1\tPRJ-1\n"
            "%T\tPROJWBS\n%F\twbs_id\tproj_id\n%R\t1\t1\n"
            "%T\tTASK\n%F\ttask_id\ttask_code\ttarget_durn_hr_cnt\n%R\t1\tACT-1\n"  # Only 2 cols, expected 3
            "%T\tTASKPRED\n%F\tid\n"
        )
        p_width = os.path.join(self.test_dir, "bad_width.xer")
        with open(p_width, "w") as f:
            f.write(xer_bad_width)
        with self.assertRaises(MalformedXERRowWidthError):
            pipeline.ingest_and_publish(p_width, os.path.join(self.test_dir, "out2"))

        # 3. Duplicate activity code
        xer_dup = (
            "ERMHDR\t8.3\t2026-10-10\tTEST\n"
            "%T\tPROJECT\n%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\n%R\t1\tPRJ-1\t2026-11-02 08:00\t2026-11-19 17:00\n"
            "%T\tPROJWBS\n%F\twbs_id\tproj_id\twbs_short_name\n%R\t1\t1\tWHC.SUB\n"
            "%T\tTASK\n%F\ttask_id\ttask_code\ttarget_durn_hr_cnt\n"
            "%R\t1\tACT-01\t8.0\n"
            "%R\t2\tACT-01\t8.0\n"  # Duplicate ACT-01
            "%T\tTASKPRED\n%F\tid\n"
        )
        p_dup = os.path.join(self.test_dir, "dup.xer")
        with open(p_dup, "w") as f:
            f.write(xer_dup)
        with self.assertRaises(DuplicateActivityCodeError):
            pipeline.ingest_and_publish(p_dup, os.path.join(self.test_dir, "out3"))

        # 4. Unresolved relationship foreign key
        xer_bad_rel = (
            "ERMHDR\t8.3\t2026-10-10\tTEST\n"
            "%T\tPROJECT\n%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\n%R\t1\tPRJ-1\t2026-11-02 08:00\t2026-11-19 17:00\n"
            "%T\tPROJWBS\n%F\twbs_id\tproj_id\twbs_short_name\n%R\t1\t1\tWHC.SUB\n"
            "%T\tTASK\n%F\ttask_id\ttask_code\ttarget_durn_hr_cnt\n"
            "%R\t1\tACT-01\t8.0\n"
            "%T\tTASKPRED\n%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n"
            "%R\t99\t1\t9999\tPR_FS\t0.0\n"  # pred_task_id 9999 does not exist
        )
        p_rel = os.path.join(self.test_dir, "bad_rel.xer")
        with open(p_rel, "w") as f:
            f.write(xer_bad_rel)
        with self.assertRaises(UnresolvedRelationshipKeyError):
            pipeline.ingest_and_publish(p_rel, os.path.join(self.test_dir, "out4"))

    def test_08_atomic_swap_and_rollback_integrity(self):
        """Verify simulated interruption rollback leaves target untouched, and valid publish writes manifest."""
        target_store = os.path.join(self.test_dir, "atomic_lakehouse_store")
        pipeline = XERIngestionPipeline()

        # Phase 1: Successful initial publication
        tables = pipeline.ingest_and_publish(
            xer_path=self.bl01_xer_path,
            target_parquet_dir=target_store,
        )
        self.assertTrue(os.path.islink(target_store), "Target directory must be a symlink")
        manifest_path = os.path.join(target_store, "_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "_manifest.json must exist in published store")

        with open(manifest_path) as f:
            manifest = json.load(f)
        self.assertIn("tables", manifest)
        self.assertIn("schedule_activities.parquet", manifest["tables"])
        self.assertEqual(manifest["tables"]["schedule_activities.parquet"]["rows"], 6)

        # Record active symlink target path
        initial_target_link = os.readlink(target_store)

        # Phase 2: Injected fault during second publication
        with self.assertRaises(RuntimeError):
            pipeline.ingest_and_publish(
                xer_path=self.bl01_xer_path,
                target_parquet_dir=target_store,
                simulate_interruption=True,
            )

        # Assert active symlink was 100% untouched
        self.assertTrue(os.path.islink(target_store))
        self.assertEqual(
            os.readlink(target_store),
            initial_target_link,
            "Target symlink pointer must remain completely unchanged after interrupted publication",
        )


if __name__ == "__main__":
    unittest.main()
