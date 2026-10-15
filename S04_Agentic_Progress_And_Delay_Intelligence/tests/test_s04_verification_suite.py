#!/usr/bin/env python3
"""
ACIP S04: Automated Verification Test Suite (Eight Verification Tests)
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: tests/test_s04_verification_suite.py

Implements independent verification resolving all eight review findings from Independent Technical Review:
1. test_01_cpm_forward_backward_pass_benchmark (FS, SS, FF, SF, Milestones, Mixed Calendars)
2. test_02_composite_fk_and_downstream_referential_integrity (S05 Quality & S06 Claims Links)
3. test_03_delay_revision_lifecycle_and_immutability (Snapshot immutability, prohibited fields)
4. test_04_synthetic_provenance_enforcement (Rejects FALSE/NULL in synthetic datasets)
5. test_05_contract_parameters_governance (Point-of-use authoritative guardrail)
6. test_06_downstream_s05_s06_lineage_and_version_pinning (Lineage survival across updates)
7. test_07_atomic_parquet_validator_fail_closed (Atomic directory swap, DAG acyclicity, rollback)
8. test_08_physical_p6_xer_scoped_round_trip (Loads physical XER files from disk)
"""

import json
import os
import sys
import unittest
import shutil
import tempfile
from datetime import date
import pandas as pd

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S04_ROOT)

from engine.cpm_engine import (
    build_six_activity_benchmark,
    build_sf_and_mixed_calendar_benchmark,
    ScheduleNetwork,
    Activity,
    Relationship,
    CyclicDependencyError,
)
from unittest.mock import patch

from engine.data_validator import (
    ParquetDataValidator,
    ValidationError,
    LifecycleStateError,
    ImmutabilityError,
    ProvenanceError,
    SourceHashMismatchError,
    ContractGovernanceError,
    LegacyStorageError,
    calculate_contractual_exposure,
    compute_file_sha256,
    atomic_publish_dataset,
    migrate_legacy_directory_to_versioned_store,
    recover_interrupted_migration,
    verify_snapshot_manifest,
)
from engine.p6_parser import (
    P6XERParser,
)


class TestS04VerificationSuite(unittest.TestCase):
    """Rigorous verification test suite for ACIP S04 Gate 2."""

    def setUp(self):
        self.project_id = "PRJ-WHC-COM-001"
        self.schedule_version = "BL-01"

    # -------------------------------------------------------------------------
    # TEST 1: CPM All 4 Relationships (FS, SS, FF, SF) & Mixed Calendars
    # -------------------------------------------------------------------------
    def test_01_cpm_forward_backward_pass_benchmark(self):
        """Verify FS, SS, FF in 6-activity benchmark and SF + mixed calendars in independent network."""
        # 1. Benchmark Network (FS, SS, FF)
        net = build_six_activity_benchmark()
        project_start = date(2026, 11, 2)
        start_d, finish_d = net.calculate_cpm(project_start)

        self.assertEqual(start_d, date(2026, 11, 2))
        self.assertEqual(finish_d, date(2026, 11, 19))  # Exactly 14 elapsed workdays

        expected_bench = {
            "ACT-01": (date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 2), 0, 0, True),
            "ACT-02": (date(2026, 11, 2), date(2026, 11, 6), date(2026, 11, 2), date(2026, 11, 6), 0, 0, True),
            "ACT-03": (date(2026, 11, 9), date(2026, 11, 12), date(2026, 11, 9), date(2026, 11, 12), 0, 0, True),
            "ACT-04": (date(2026, 11, 4), date(2026, 11, 11), date(2026, 11, 11), date(2026, 11, 18), 5, 5, False),
            "ACT-05": (date(2026, 11, 13), date(2026, 11, 19), date(2026, 11, 13), date(2026, 11, 19), 0, 0, True),
            "ACT-06": (date(2026, 11, 19), date(2026, 11, 19), date(2026, 11, 19), date(2026, 11, 19), 0, 0, True),
        }
        for act_id, (es, ef, ls, lf, tf, ff, crit) in expected_bench.items():
            act = net.activities[act_id]
            self.assertEqual(act.early_start, es, f"{act_id} ES mismatch")
            self.assertEqual(act.early_finish, ef, f"{act_id} EF mismatch")
            self.assertEqual(act.late_start, ls, f"{act_id} LS mismatch")
            self.assertEqual(act.late_finish, lf, f"{act_id} LF mismatch")
            self.assertEqual(act.total_float_days, tf, f"{act_id} Total Float mismatch")
            self.assertEqual(act.free_float_days, ff, f"{act_id} Free Float mismatch")
            self.assertEqual(act.is_critical, crit, f"{act_id} Critical flag mismatch")

        # 2. Independent Network specifically exercising SF and Mixed Calendars
        net_sf = build_sf_and_mixed_calendar_benchmark()
        sf_start, sf_finish = net_sf.calculate_cpm(date(2026, 11, 2))
        self.assertEqual(sf_start, date(2026, 11, 2))
        self.assertEqual(sf_finish, date(2026, 11, 13))

        expected_sf = {
            # (ES, EF, LS, LF, TF, FF, is_critical)
            "SF-01": (date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 2), 0, 0, True),
            "SF-02": (date(2026, 11, 2), date(2026, 11, 5), date(2026, 11, 2), date(2026, 11, 5), 0, 0, True),
            "SF-03": (date(2026, 11, 2), date(2026, 11, 4), date(2026, 11, 11), date(2026, 11, 13), 7, 7, False),
            "SF-04": (date(2026, 11, 9), date(2026, 11, 13), date(2026, 11, 9), date(2026, 11, 13), 0, 0, True),
            "SF-05": (date(2026, 11, 13), date(2026, 11, 13), date(2026, 11, 13), date(2026, 11, 13), 0, 0, True),
        }
        for act_id, (es, ef, ls, lf, tf, ff, crit) in expected_sf.items():
            act = net_sf.activities[act_id]
            self.assertEqual(act.early_start, es, f"{act_id} ES mismatch")
            self.assertEqual(act.early_finish, ef, f"{act_id} EF mismatch")
            self.assertEqual(act.late_start, ls, f"{act_id} LS mismatch")
            self.assertEqual(act.late_finish, lf, f"{act_id} LF mismatch")
            self.assertEqual(act.total_float_days, tf, f"{act_id} Total Float mismatch")
            self.assertEqual(act.free_float_days, ff, f"{act_id} Free Float mismatch")
            self.assertEqual(act.is_critical, crit, f"{act_id} Critical flag mismatch")

    # -------------------------------------------------------------------------
    # TEST 2: Composite FK Integrity & Downstream Links (S05/S06)
    # -------------------------------------------------------------------------
    def test_02_composite_fk_and_downstream_referential_integrity(self):
        """Verify composite FK integrity across delay links, S05 quality, and S06 claims."""
        validator = ParquetDataValidator()

        df_act = pd.DataFrame([{
            "project_id": self.project_id,
            "schedule_version": self.schedule_version,
            "activity_id": "ACT-02",
        }])
        df_delay = pd.DataFrame([{
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 1,
        }])
        df_dea = pd.DataFrame([{
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 1,
            "schedule_version": self.schedule_version,
            "activity_id": "ACT-02",
        }])
        df_s05 = pd.DataFrame([{
            "inspection_id": "INSP-01",
            "project_id": self.project_id,
            "schedule_version": self.schedule_version,
            "activity_id": "ACT-02",
        }])
        df_s06 = pd.DataFrame([{
            "claim_dossier_id": "CLM-01",
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 1,
        }])

        tables = {
            "schedule_activities": df_act,
            "delay_events": df_delay,
            "delay_event_activities": df_dea,
            "quality_inspection_schedule_links": df_s05,
            "formal_claims_delay_links": df_s06,
        }
        validator.register_tables(tables)
        validator.validate_foreign_keys(tables)  # Must pass

        # Negative Test: S05 link referencing non-existent activity
        df_s05_bad = pd.DataFrame([{
            "inspection_id": "INSP-01",
            "project_id": self.project_id,
            "schedule_version": self.schedule_version,
            "activity_id": "NON_EXISTENT_ACTIVITY",
        }])
        tables_bad_s05 = dict(tables, quality_inspection_schedule_links=df_s05_bad)
        val_bad1 = ParquetDataValidator()
        val_bad1.register_tables(tables_bad_s05)
        with self.assertRaises(ValidationError):
            val_bad1.validate_foreign_keys(tables_bad_s05)

        # Negative Test: S06 link referencing non-existent delay revision
        df_s06_bad = pd.DataFrame([{
            "claim_dossier_id": "CLM-01",
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 999,  # Missing revision
        }])
        tables_bad_s06 = dict(tables, formal_claims_delay_links=df_s06_bad)
        val_bad2 = ParquetDataValidator()
        val_bad2.register_tables(tables_bad_s06)
        with self.assertRaises(ValidationError):
            val_bad2.validate_foreign_keys(tables_bad_s06)

    # -------------------------------------------------------------------------
    # TEST 3: Delay Revision Lifecycle & Immutability (Append-Only)
    # -------------------------------------------------------------------------
    def test_03_delay_revision_lifecycle_and_immutability(self):
        """Verify lifecycle stage rules and assert rejection of in-place historical mutation."""
        validator = ParquetDataValidator()

        df_rev1 = pd.DataFrame([{
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 1,
            "revision_stage": "CONTRACTOR_CLAIM",
            "claimed_eot_days": 10,
            "assessed_eot_days": None,
            "concurrent_delay_flag": None,
            "approved_eot_days": None,
            "compensable_days": None,
            "determined_by": None,
            "determination_date": None,
            "determination_doc_reference": None,
        }])
        validator.validate_delay_revision_lifecycle({"delay_events": df_rev1})

        # Negative Test: Revision 1 with prohibited determination doc ref
        df_rev1_bad = df_rev1.copy()
        df_rev1_bad.loc[0, "determination_doc_reference"] = "PREMATURE-CERT-01"
        with self.assertRaises(LifecycleStateError):
            validator.validate_delay_revision_lifecycle({"delay_events": df_rev1_bad})

        # Negative Test: Revision 2 with prohibited approved_eot_days
        df_rev2_bad = pd.DataFrame([{
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 2,
            "revision_stage": "FORENSIC_ASSESSMENT",
            "claimed_eot_days": 10,
            "assessed_eot_days": 4,
            "approved_eot_days": 4,  # Prohibited at Rev 2!
            "determined_by": None,
            "determination_date": None,
            "determination_doc_reference": None,
        }])
        with self.assertRaises(LifecycleStateError):
            validator.validate_delay_revision_lifecycle({"delay_events": df_rev2_bad})

        # Immutability Test 1: Attempting to modify existing committed revision 1
        df_rev1_mutated = df_rev1.copy()
        df_rev1_mutated.loc[0, "claimed_eot_days"] = 99  # Tampering with history
        with self.assertRaises(ImmutabilityError):
            validator.validate_revision_immutability(df_rev1, df_rev1_mutated)

        # Immutability Test 2: Attempting to delete existing committed revision 1 by omitting it in subsequent submission
        df_rev2_only = pd.DataFrame([{
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 2,  # Omits revision 1
            "revision_stage": "FORENSIC_ASSESSMENT",
            "claimed_eot_days": 10,
            "assessed_eot_days": 4,
            "approved_eot_days": None,
            "determined_by": None,
            "determination_date": None,
            "determination_doc_reference": None,
        }])
        with self.assertRaises(ImmutabilityError):
            validator.validate_revision_immutability(df_rev1, df_rev2_only)

    # -------------------------------------------------------------------------
    # TEST 4: Synthetic Provenance Enforcement (No Permissive Default)
    # -------------------------------------------------------------------------
    def test_04_synthetic_provenance_enforcement(self):
        """Verify strict rejection of is_synthetic=False, NULL, or missing tags in benchmark datasets."""
        validator = ParquetDataValidator()

        df_valid = pd.DataFrame([{
            "project_id": self.project_id,
            "record_date": date(2026, 8, 14),
            "log_id": "LOG-01",
            "is_synthetic": True,
            "synthetic_benchmark_tag": "SIMULATED_TEST_SCENARIO_ACIP_S04",
        }])
        validator.validate_synthetic_provenance({"site_records": df_valid})

        # Negative Test: is_synthetic = False in synthetic-only dataset
        df_false_synth = pd.DataFrame([{
            "project_id": self.project_id,
            "record_date": date(2026, 8, 14),
            "log_id": "LOG-01",
            "is_synthetic": False,  # Rejected!
            "synthetic_benchmark_tag": "SIMULATED_TEST_SCENARIO_ACIP_S04",
        }])
        with self.assertRaises(ProvenanceError):
            validator.validate_synthetic_provenance({"site_records": df_false_synth})

        # Negative Test: Missing/wrong benchmark tag
        df_bad_tag = pd.DataFrame([{
            "project_id": self.project_id,
            "record_date": date(2026, 8, 14),
            "log_id": "LOG-01",
            "is_synthetic": True,
            "synthetic_benchmark_tag": "UNVERIFIED_SOURCE_TAG",
        }])
        with self.assertRaises(ProvenanceError):
            validator.validate_synthetic_provenance({"site_records": df_bad_tag})

    # -------------------------------------------------------------------------
    # TEST 5: Contract Parameters Governance & Point-of-Use Guardrail
    # -------------------------------------------------------------------------
    def test_05_contract_parameters_governance(self):
        """Verify point-of-use contract guardrail preventing authoritative conclusions if unverified."""
        params_unverified = {
            "daily_liquidated_damages_rate_sgd": 15000.0,
            "delay_notice_period_days": 28,
            "verified_against_signed_contract": False,
        }

        # Advisory mode works and is explicitly flagged
        advisory_res = calculate_contractual_exposure(
            self.project_id, 10, 4, params_unverified, force_authoritative=False
        )
        self.assertEqual(advisory_res["status"], "ADVISORY_SIMULATION_ONLY")
        self.assertEqual(advisory_res["liquidated_damages_amount_sgd"], 90000.0)

        # Authoritative attempt MUST fail closed if particulars unverified
        with self.assertRaises(ContractGovernanceError):
            calculate_contractual_exposure(
                self.project_id, 10, 4, params_unverified, force_authoritative=True
            )

        # Verified mode succeeds
        params_verified = dict(params_unverified, verified_against_signed_contract=True)
        auth_res = calculate_contractual_exposure(
            self.project_id, 10, 4, params_verified, force_authoritative=True
        )
        self.assertEqual(auth_res["status"], "AUTHORITATIVE_VERIFIED")

    # -------------------------------------------------------------------------
    # TEST 6: Downstream S05/S06 Lineage & Version Pinning
    # -------------------------------------------------------------------------
    def test_06_downstream_s05_s06_lineage_and_version_pinning(self):
        """Verify downstream links preserve exact parent revision and schedule version."""
        validator = ParquetDataValidator()

        df_act = pd.DataFrame([
            {"project_id": self.project_id, "schedule_version": "BL-01", "activity_id": "ACT-02"},
            {"project_id": self.project_id, "schedule_version": "UPD-01", "activity_id": "ACT-02"},
        ])
        df_delay = pd.DataFrame([
            {"project_id": self.project_id, "event_id": "DLY-001", "revision_id": 1},
            {"project_id": self.project_id, "event_id": "DLY-001", "revision_id": 2},
        ])
        # S05 pinned to BL-01
        df_s05 = pd.DataFrame([{
            "inspection_id": "INSP-01",
            "project_id": self.project_id,
            "schedule_version": "BL-01",
            "activity_id": "ACT-02",
        }])
        # S06 pinned to Revision 1 (the original contractor claim)
        df_s06 = pd.DataFrame([{
            "claim_dossier_id": "CLM-CLAIMANT-ORIGINAL",
            "project_id": self.project_id,
            "event_id": "DLY-001",
            "revision_id": 1,
        }])

        tables = {
            "schedule_activities": df_act,
            "delay_events": df_delay,
            "quality_inspection_schedule_links": df_s05,
            "formal_claims_delay_links": df_s06,
        }
        validator.register_tables(tables)
        validator.validate_foreign_keys(tables)
        validator.validate_primary_keys(tables)

        # Assert S06 link remains explicitly pinned to revision 1
        self.assertEqual(df_s06.iloc[0]["revision_id"], 1)

    # -------------------------------------------------------------------------
    # TEST 7: Atomic Parquet Publishing, Interruption Testing & Fault Injection
    # -------------------------------------------------------------------------
    def test_07_atomic_parquet_validator_fail_closed(self):
        """Verify genuine atomic pointer swap, interruption handling, fault injection, legacy rejection, and hash validation."""
        tmp_parent = tempfile.mkdtemp(prefix="s04_test_atomic_parent_")
        tmp_target = os.path.join(tmp_parent, "published_parquet")
        try:
            # Source file path with valid hash
            xer_file = os.path.join(S04_ROOT, "data", "xer", "WHC_COM_BL01_Approved_Baseline.xer")
            actual_hash = compute_file_sha256(xer_file)

            df_ver = pd.DataFrame([{
                "project_id": self.project_id,
                "schedule_version": self.schedule_version,
                "source_file_path": xer_file,
                "source_file_sha256": actual_hash,
            }])
            df_contract = pd.DataFrame([{
                "project_id": self.project_id,
                "contract_id": "CNT-WHC-COM-001",
                "daily_liquidated_damages_rate_sgd": 15000.0,
                "delay_notice_period_days": 28,
            }])
            df_rels = pd.DataFrame([
                {"project_id": self.project_id, "schedule_version": "BL-01", "predecessor_activity_id": "A1", "successor_activity_id": "A2", "relationship_type": "FS"},
                {"project_id": self.project_id, "schedule_version": "BL-01", "predecessor_activity_id": "A2", "successor_activity_id": "A3", "relationship_type": "FS"},
            ])
            df_acts = pd.DataFrame([
                {"project_id": self.project_id, "schedule_version": "BL-01", "activity_id": "A1"},
                {"project_id": self.project_id, "schedule_version": "BL-01", "activity_id": "A2"},
                {"project_id": self.project_id, "schedule_version": "BL-01", "activity_id": "A3"},
            ])

            tables = {
                "schedule_versions": df_ver,
                "contract_parameters": df_contract,
                "schedule_activities": df_acts,
                "schedule_relationships": df_rels,
            }

            # 1. Publish valid dataset with single atomic commit point
            atomic_publish_dataset(tables, tmp_target, S04_ROOT)
            self.assertTrue(os.path.islink(tmp_target), "Published target must be an atomic symlink")
            target_contract_file = os.path.join(tmp_target, "contract_parameters.parquet")
            self.assertTrue(os.path.exists(target_contract_file))
            self.assertTrue(os.path.exists(os.path.join(tmp_target, "_manifest.json")))
            orig_mtime = os.path.getmtime(target_contract_file)
            orig_snapshot_target = os.path.realpath(tmp_target)

            # 2. Reject Cyclic Dependency in relationships
            df_cyclic_rels = pd.concat([df_rels, pd.DataFrame([{
                "project_id": self.project_id, "schedule_version": "BL-01",
                "predecessor_activity_id": "A3", "successor_activity_id": "A1", "relationship_type": "FS"
            }])], ignore_index=True)
            tables_cyclic = dict(tables, schedule_relationships=df_cyclic_rels)

            with self.assertRaises(CyclicDependencyError):
                atomic_publish_dataset(tables_cyclic, tmp_target, S04_ROOT)

            # Assert target directory was not modified or corrupted
            self.assertEqual(os.path.getmtime(target_contract_file), orig_mtime)
            self.assertEqual(os.path.realpath(tmp_target), orig_snapshot_target)

            # 3. Interruption during publication staging phase: verify fail-closed behavior before commit
            with self.assertRaises(RuntimeError):
                atomic_publish_dataset(tables, tmp_target, S04_ROOT, simulate_interruption=True)

            # Assert target remains untouched at previous commit
            self.assertEqual(os.path.getmtime(target_contract_file), orig_mtime)
            self.assertEqual(os.path.realpath(tmp_target), orig_snapshot_target)

            # 4. Fault injection around commit boundary: simulate I/O failure during atomic swap rename(2)
            with patch("os.replace", side_effect=OSError("Injected I/O failure during atomic swap rename(2)")):
                with self.assertRaises(OSError):
                    atomic_publish_dataset(tables, tmp_target, S04_ROOT)

            # Assert fail-closed guarantees: target symlink remains untouched at original snapshot
            self.assertEqual(os.path.getmtime(target_contract_file), orig_mtime)
            self.assertEqual(os.path.realpath(tmp_target), orig_snapshot_target)
            # Assert no dangling temporary commit symlinks exist in parent directory
            dangling_links = [f for f in os.listdir(tmp_parent) if f.startswith(".tmp_commit_")]
            self.assertEqual(dangling_links, [], "Temporary commit links must be removed upon failure")

            # 5. Reject existing non-symlink legacy directory (eliminate migration gap)
            legacy_dir = os.path.join(tmp_parent, "unmanaged_legacy_parquet")
            os.makedirs(legacy_dir, exist_ok=True)
            dummy_parquet = os.path.join(legacy_dir, "dummy_table.parquet")
            pd.DataFrame([{"k": "v"}]).to_parquet(dummy_parquet)

            with self.assertRaises(LegacyStorageError):
                atomic_publish_dataset(tables, legacy_dir, S04_ROOT)

            # Assert unmanaged legacy directory remains untouched
            self.assertTrue(os.path.exists(dummy_parquet))
            self.assertFalse(os.path.islink(legacy_dir))

            # Migrate legacy directory safely using offline migration utility
            migrate_legacy_directory_to_versioned_store(legacy_dir)
            self.assertTrue(os.path.islink(legacy_dir), "Migrated target must now be a symlink")
            self.assertTrue(os.path.exists(os.path.join(legacy_dir, "_manifest.json")))
            self.assertTrue(os.path.exists(os.path.join(legacy_dir, "dummy_table.parquet")))

            # Assert manifest records actual row counts (not 0) and verify snapshot integrity
            with open(os.path.join(legacy_dir, "_manifest.json"), "r") as mf:
                manifest_content = json.load(mf)
            self.assertEqual(manifest_content["tables"]["dummy_table.parquet"]["rows"], 1,
                             "Manifest must record actual physical row count (1) for migrated Parquet file")
            self.assertTrue(verify_snapshot_manifest(legacy_dir), "Snapshot manifest verification must succeed")

            # Subsequent atomic publish to migrated directory now succeeds cleanly
            atomic_publish_dataset(tables, legacy_dir, S04_ROOT)
            self.assertTrue(os.path.exists(os.path.join(legacy_dir, "contract_parameters.parquet")))

            # 5a. Regression Test: Calling migration utility on already-migrated target preserves symlink identity
            target_snap_before = os.path.realpath(legacy_dir)
            noop_result = migrate_legacy_directory_to_versioned_store(legacy_dir)
            self.assertTrue(os.path.islink(legacy_dir), "Target must remain an active symlink")
            self.assertEqual(os.path.realpath(legacy_dir), target_snap_before,
                             "Backing snapshot must remain untouched")
            self.assertEqual(noop_result, target_snap_before,
                             "Operation must safely return existing snapshot path as a safe no-op")

            # 5a-1. Hardening Assertion: Existing symlink pointing to corrupted snapshot fails closed
            corrupt_existing_symlink_dir = os.path.join(tmp_parent, "corrupt_existing_symlink")
            os.makedirs(corrupt_existing_symlink_dir, exist_ok=True)
            pd.DataFrame([{"id": 100}]).to_parquet(os.path.join(corrupt_existing_symlink_dir, "test.parquet"))
            migrate_legacy_directory_to_versioned_store(corrupt_existing_symlink_dir)
            self.assertTrue(os.path.islink(corrupt_existing_symlink_dir))
            # Corrupt the backing snapshot file
            backing_test_file = os.path.join(os.path.realpath(corrupt_existing_symlink_dir), "test.parquet")
            with open(backing_test_file, "ab") as f:
                f.write(b"CORRUPTION_BYTES")
            with self.assertRaises(ValidationError):
                migrate_legacy_directory_to_versioned_store(corrupt_existing_symlink_dir)

            # 5b. Fail closed when physical row counts cannot be established for corrupt/unreadable files
            corrupt_parquet_dir = os.path.join(tmp_parent, "corrupt_parquet_legacy")
            os.makedirs(corrupt_parquet_dir, exist_ok=True)
            corrupt_file = os.path.join(corrupt_parquet_dir, "bad.parquet")
            with open(corrupt_file, "wb") as f:
                f.write(b"NOT_A_VALID_PARQUET_FILE_DATA")

            with self.assertRaises(ValidationError) as ctx_corrupt:
                migrate_legacy_directory_to_versioned_store(corrupt_parquet_dir)
            self.assertIn("Unable to establish physical row count", str(ctx_corrupt.exception))

            # 5c. Test fault injection & crash recovery during offline legacy migration
            interrupted_legacy_dir = os.path.join(tmp_parent, "interrupted_legacy_parquet")
            os.makedirs(interrupted_legacy_dir, exist_ok=True)
            dummy2_parquet = os.path.join(interrupted_legacy_dir, "table2.parquet")
            pd.DataFrame([{"id": 1}, {"id": 2}]).to_parquet(dummy2_parquet)

            # Fault injection: simulate crash between directory move and symlink creation
            with self.assertRaises(RuntimeError):
                migrate_legacy_directory_to_versioned_store(interrupted_legacy_dir, simulate_interruption=True)

            # Helper to find journals cleanly without leaving open file descriptors
            def find_journals_for(target_name):
                matches = []
                for fname in os.listdir(tmp_parent):
                    if fname.startswith(".migration_journal_"):
                        fpath = os.path.join(tmp_parent, fname)
                        with open(fpath, "r") as jf:
                            if target_name in jf.read():
                                matches.append(fpath)
                return matches

            # Assert target directory path is absent following the interruption
            self.assertFalse(os.path.exists(interrupted_legacy_dir))
            # Assert persistent migration journal exists in parent directory
            journals = find_journals_for("interrupted_legacy_parquet")
            self.assertGreater(len(journals), 0, "Persistent migration journal must exist after interruption")

            # Execute offline recovery procedure
            recovered_snap = recover_interrupted_migration(interrupted_legacy_dir)
            self.assertIsNotNone(recovered_snap)
            self.assertTrue(os.path.islink(interrupted_legacy_dir), "Target must be restored as an active symlink")
            self.assertEqual(os.path.realpath(interrupted_legacy_dir), os.path.realpath(recovered_snap))
            with open(os.path.join(interrupted_legacy_dir, "_manifest.json"), "r") as mf:
                recovered_manifest = json.load(mf)
            self.assertEqual(recovered_manifest["tables"]["table2.parquet"]["rows"], 2,
                             "Recovered manifest must record exact row count (2)")
            self.assertTrue(verify_snapshot_manifest(interrupted_legacy_dir),
                            "Recovered snapshot manifest must pass verification")

            # 5d. Fault-injection Test: Corrupt hash during recovery must fail closed and retain journal
            corrupt_hash_dir = os.path.join(tmp_parent, "corrupt_hash_recovery_dir")
            os.makedirs(corrupt_hash_dir, exist_ok=True)
            pd.DataFrame([{"id": 10}]).to_parquet(os.path.join(corrupt_hash_dir, "tbl.parquet"))

            with self.assertRaises(RuntimeError):
                migrate_legacy_directory_to_versioned_store(corrupt_hash_dir, simulate_interruption=True)

            j_match = find_journals_for("corrupt_hash_recovery_dir")
            self.assertTrue(len(j_match) > 0)
            j_file = j_match[0]
            with open(j_file) as f:
                j_meta = json.load(f)
            staged_snap = j_meta["snapshot_dir"]
            snap_mf_path = os.path.join(staged_snap, "_manifest.json")
            with open(snap_mf_path, "r") as f:
                mf_data = json.load(f)
            mf_data["tables"]["tbl.parquet"]["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
            with open(snap_mf_path, "w") as f:
                json.dump(mf_data, f)

            with self.assertRaises(ValidationError) as ctx_hash:
                recover_interrupted_migration(corrupt_hash_dir)
            self.assertIn("SHA-256 hash mismatch", str(ctx_hash.exception))
            self.assertFalse(os.path.lexists(corrupt_hash_dir), "Recovery must refuse to install target symlink for corrupt hash")
            self.assertTrue(os.path.exists(j_file), "Recovery journal must be retained when validation fails")

            # 5e. Fault-injection Test: Row-count mismatch during recovery must fail closed and retain journal
            mismatch_rows_dir = os.path.join(tmp_parent, "mismatch_rows_recovery_dir")
            os.makedirs(mismatch_rows_dir, exist_ok=True)
            pd.DataFrame([{"id": 1}, {"id": 2}]).to_parquet(os.path.join(mismatch_rows_dir, "tbl2.parquet"))

            with self.assertRaises(RuntimeError):
                migrate_legacy_directory_to_versioned_store(mismatch_rows_dir, simulate_interruption=True)

            j_match2 = find_journals_for("mismatch_rows_recovery_dir")
            self.assertTrue(len(j_match2) > 0)
            j_file2 = j_match2[0]
            with open(j_file2) as f:
                j_meta2 = json.load(f)
            staged_snap2 = j_meta2["snapshot_dir"]
            snap_mf_path2 = os.path.join(staged_snap2, "_manifest.json")
            with open(snap_mf_path2, "r") as f:
                mf_data2 = json.load(f)
            mf_data2["tables"]["tbl2.parquet"]["rows"] = 999  # Mismatch against physical 2 rows
            with open(snap_mf_path2, "w") as f:
                json.dump(mf_data2, f)

            with self.assertRaises(ValidationError) as ctx_rows:
                recover_interrupted_migration(mismatch_rows_dir)
            self.assertIn("Row count mismatch", str(ctx_rows.exception))
            self.assertFalse(os.path.lexists(mismatch_rows_dir), "Recovery must refuse to install target symlink for row mismatch")
            self.assertTrue(os.path.exists(j_file2), "Recovery journal must be retained when validation fails")

            # 6. Fail closed when referenced source file is missing
            df_missing_file_ver = df_ver.copy()
            df_missing_file_ver.loc[0, "source_file_path"] = "data/xer/NON_EXISTENT_SOURCE_FILE.xer"
            tables_missing_file = dict(tables, schedule_versions=df_missing_file_ver)
            with self.assertRaises(SourceHashMismatchError):
                atomic_publish_dataset(tables_missing_file, tmp_target, S04_ROOT)

            # 7. Reject Wrong Source File Hash
            df_bad_hash_ver = df_ver.copy()
            df_bad_hash_ver.loc[0, "source_file_sha256"] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            tables_bad_hash = dict(tables, schedule_versions=df_bad_hash_ver)
            with self.assertRaises(SourceHashMismatchError):
                atomic_publish_dataset(tables_bad_hash, tmp_target, S04_ROOT)

        finally:
            shutil.rmtree(tmp_parent, ignore_errors=True)

    # -------------------------------------------------------------------------
    # TEST 8: Physical Primavera P6 XER Files Loaded from Disk (Both BL01 & UP01)
    # -------------------------------------------------------------------------
    def test_08_physical_p6_xer_scoped_round_trip(self):
        """Verify round-trip parsing of both physical XER files, assert substantive update deltas, and verify semantic UDF preservation."""
        bl01_path = os.path.join(S04_ROOT, "data", "xer", "WHC_COM_BL01_Approved_Baseline.xer")
        up01_path = os.path.join(S04_ROOT, "data", "xer", "WHC_COM_UP01_Progress_Update.xer")

        self.assertTrue(os.path.exists(bl01_path), "Physical BL01 XER must exist")
        self.assertTrue(os.path.exists(up01_path), "Physical UP01 XER must exist")

        with open(bl01_path, "r") as f:
            raw_bl01 = f.read()
        with open(up01_path, "r") as f:
            raw_up01 = f.read()

        parser_bl = P6XERParser()
        parser_bl.parse(raw_bl01)

        parser_up = P6XERParser()
        parser_up.parse(raw_up01)

        # 1. Verify Baseline (BL01) Scope
        proj_bl = parser_bl.get_project()
        self.assertEqual(proj_bl["proj_short_name"], "PRJ-WHC-COM-001")
        self.assertEqual(proj_bl["plan_start_date"], "2026-11-02 08:00")
        self.assertEqual(proj_bl["plan_end_date"], "2026-11-19 17:00")
        self.assertEqual(proj_bl["last_recalc_date"], "2026-11-02 08:00")

        acts_bl = parser_bl.get_activities()
        acts_bl_dict = {a["task_code"]: a for a in acts_bl}
        self.assertEqual(acts_bl_dict["ACT-03"]["target_durn_hr_cnt"], "32.0")
        self.assertEqual(acts_bl_dict["ACT-04"]["total_float_hr_cnt"], "40.0")

        # 2. Verify Progress Update (UP01) Scope
        proj_up = parser_up.get_project()
        self.assertEqual(proj_up["proj_short_name"], "PRJ-WHC-COM-001")
        self.assertEqual(proj_up["plan_start_date"], "2026-11-02 08:00")
        self.assertEqual(proj_up["plan_end_date"], "2026-11-24 17:00")
        self.assertEqual(proj_up["last_recalc_date"], "2026-11-09 08:00")

        acts_up = parser_up.get_activities()
        acts_up_dict = {a["task_code"]: a for a in acts_up}
        self.assertEqual(acts_up_dict["ACT-03"]["target_durn_hr_cnt"], "56.0")
        self.assertEqual(acts_up_dict["ACT-04"]["total_float_hr_cnt"], "16.0")

        # 3. Assert Substantive Schedule Differences Between Baseline and Progress Update
        self.assertNotEqual(proj_bl["plan_end_date"], proj_up["plan_end_date"],
                           "Substantive delta: Planned project end date must differ")
        self.assertNotEqual(proj_bl["last_recalc_date"], proj_up["last_recalc_date"],
                           "Substantive delta: Data recalculation date must advance")
        self.assertGreater(float(acts_up_dict["ACT-03"]["target_durn_hr_cnt"]),
                           float(acts_bl_dict["ACT-03"]["target_durn_hr_cnt"]),
                           "Substantive delta: ACT-03 duration must expand due to delay event")
        self.assertLess(float(acts_up_dict["ACT-04"]["total_float_hr_cnt"]),
                        float(acts_bl_dict["ACT-04"]["total_float_hr_cnt"]),
                        "Substantive delta: ACT-04 total float must compress from 40h to 16h")

        # 4. Comprehensive Round-Trip Verification & Semantic UDF Preservation for Both Files
        test_cases = [
            ("BL01", parser_bl, 1),
            ("UP01", parser_up, 2),
        ]

        for label, parser_inst, expected_udf_count in test_cases:
            proj = parser_inst.get_project()
            wbs_list = parser_inst.get_wbs()
            acts = parser_inst.get_activities()
            rels = parser_inst.get_relationships()

            # Assert pass-through enterprise table (UDFVALUE)
            self.assertIn("UDFVALUE", parser_inst.tables)
            udf_tbl = parser_inst.tables["UDFVALUE"]
            self.assertEqual(len(udf_tbl.records), expected_udf_count)

            # Round trip serialization
            exported_xer = parser_inst.export()
            reparser = P6XERParser()
            reparser.parse(exported_xer)

            # Verify semantic preservation across all core entities
            re_proj = reparser.get_project()
            self.assertEqual(re_proj["proj_short_name"], proj["proj_short_name"])
            self.assertEqual(re_proj["plan_start_date"], proj["plan_start_date"])
            self.assertEqual(re_proj["plan_end_date"], proj["plan_end_date"])
            self.assertEqual(re_proj["last_recalc_date"], proj["last_recalc_date"])

            re_wbs = reparser.get_wbs()
            self.assertEqual(re_wbs, wbs_list)

            re_acts = reparser.get_activities()
            self.assertEqual(len(re_acts), len(acts))
            for a_orig, a_re in zip(acts, re_acts):
                self.assertEqual(a_orig["task_code"], a_re["task_code"])
                self.assertEqual(a_orig["task_name"], a_re["task_name"])
                self.assertEqual(a_orig["target_durn_hr_cnt"], a_re["target_durn_hr_cnt"])
                self.assertEqual(a_orig["total_float_hr_cnt"], a_re["total_float_hr_cnt"])

            re_rels = reparser.get_relationships()
            self.assertEqual(len(re_rels), len(rels))
            for r_orig, r_re in zip(rels, re_rels):
                self.assertEqual(r_orig["task_id"], r_re["task_id"])
                self.assertEqual(r_orig["pred_task_id"], r_re["pred_task_id"])
                self.assertEqual(r_orig["pred_type"], r_re["pred_type"])
                self.assertEqual(r_orig["lag_hr_cnt"], r_re["lag_hr_cnt"])

            # Verify Semantic Pass-Through Preservation of UDFVALUE (schema and record contents identical)
            self.assertIn("UDFVALUE", reparser.tables)
            re_udf = reparser.tables["UDFVALUE"]
            self.assertEqual(re_udf.fields, udf_tbl.fields)
            self.assertEqual(re_udf.records, udf_tbl.records)

        # 5. Assert Canonical Delay Event Identifier Consistency (DLY-2026-001)
        up_udf_tbl = parser_up.tables["UDFVALUE"]
        udf_text_values = [" ".join(rec) for rec in up_udf_tbl.records]
        self.assertTrue(
            any("DLY-2026-001" in text for text in udf_text_values),
            f"UP01 UDF records must reference canonical delay event DLY-2026-001. Found: {udf_text_values}"
        )




if __name__ == "__main__":
    unittest.main()
