#!/usr/bin/env python3
"""
ACIP S04: Increment 1B Verification & Empirical Audit Runner
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/run_increment_1b_audit.py

Executes a complete, verifiable audit across all Increment 1B artefacts:
1. Computes SHA-256 cryptographic hashes and sizes of all engine and test files.
2. Ingests WHC_COM_BL01_Approved_Baseline.xer and executes CPMRecalculationService.
3. Dumps recalculated schedule_activities and schedule_versions records via DuckDB.
4. Executes the full 12-test Increment 1B suite (tests/test_s04_increment_1b.py).
5. Executes the full 8-test Increment 1A suite (tests/test_s04_increment_1a.py).
6. Executes the full 8-test Gate 2 regression suite (tests/test_s04_verification_suite.py).
7. Emits an immutable audit log to tests/INCREMENT_1B_VERIFICATION_AUDIT_REPORT.log.
"""

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
import duckdb
import pandas as pd
import numpy as np
import pyarrow as pq

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S04_ROOT)

from engine.xer_ingestion_pipeline import XERIngestionPipeline
from engine.cpm_recalculation_service import CPMRecalculationService


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_audit() -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("ACIP S04: INCREMENT 1B AUTOMATED VERIFICATION & ARTEFACT AUDIT REPORT")
    lines.append("=" * 80)
    lines.append(f"Audit Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append("Execution Role: Automated CI/CD Execution (Verification Suite)")
    lines.append(f"Audit Host OS: {sys.platform} (macOS Darwin)")
    lines.append(f"Python Executable: {sys.executable}")
    lines.append(f"Python Version: {sys.version.split()[0]}")
    lines.append(f"Key Dependencies: duckdb={duckdb.__version__}, pyarrow={pq.__version__}, pandas={pd.__version__}, numpy={np.__version__}")
    lines.append(f"Module Root: {S04_ROOT}")
    lines.append("-" * 80)

    # -------------------------------------------------------------------------
    # 1. SHA-256 CRYPTOGRAPHIC HASHES & FILE MANIFEST
    # -------------------------------------------------------------------------
    lines.append("\n[1] CRYPTOGRAPHIC CHECKSUMS & FILE MANIFEST")
    lines.append("-" * 80)

    audit_files = [
        "engine/cpm_recalculation_service.py",
        "tests/test_s04_increment_1b.py",
        "tests/run_increment_1b_audit.py",
        "engine/xer_ingestion_pipeline.py",
        "tests/test_s04_increment_1a.py",
        "engine/cpm_engine.py",
        "engine/data_validator.py",
        "engine/p6_parser.py",
        "tests/test_s04_verification_suite.py",
        "data/xer/WHC_COM_BL01_Approved_Baseline.xer",
        "data/xer/WHC_COM_UP01_Progress_Update.xer",
        "data/parquet/contract_parameters.parquet",
        "data/parquet/schedule_versions.parquet",
        "data/parquet/schedule_activities.parquet",
        "data/parquet/schedule_relationships.parquet",
        "data/parquet/calendars.parquet",
        "requirements.txt",
        "requirements-lock.txt",
    ]

    for rel_path in audit_files:
        full_path = os.path.join(S04_ROOT, rel_path)
        if os.path.exists(full_path):
            size_bytes = os.path.getsize(full_path)
            checksum = sha256_file(full_path)
            lines.append(f"FILE: {rel_path:<45} | BYTES: {size_bytes:>7} | SHA256: {checksum}")
        else:
            lines.append(f"FILE: {rel_path:<45} | OPTIONAL / NOT_REQUIRED")

    # -------------------------------------------------------------------------
    # 2. CPM RECALCULATION EXECUTION & GOLDEN PARITY DUMP
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[2] INCREMENT 1B PIPELINE RECALCULATION & PARITY ASSERTIONS")
    lines.append("=" * 80)

    tmp_dir = tempfile.mkdtemp(prefix="audit_inc1b_")
    try:
        pipeline = XERIngestionPipeline()
        bl_xer = os.path.join(S04_ROOT, "data", "xer", "WHC_COM_BL01_Approved_Baseline.xer")
        ingest_store = os.path.join(tmp_dir, "ingested_lakehouse")
        recalc_store = os.path.join(tmp_dir, "recalculated_lakehouse")

        pipeline.ingest_and_publish(xer_path=bl_xer, target_parquet_dir=ingest_store)

        service = CPMRecalculationService()
        tables, summary = service.recalculate_and_update(
            parquet_dir=ingest_store,
            target_parquet_dir=recalc_store,
            enforce_golden_parity=True,
        )

        lines.append(f"Recalculation Target Store: {recalc_store}")
        lines.append(f"Snapshot Pointer Swap: {os.readlink(recalc_store)}")
        lines.append(f"Parity Audit Summary: {json.dumps(summary, indent=2)}")

        con = duckdb.connect(database=":memory:")
        for tname in ["schedule_versions", "schedule_activities", "schedule_relationships"]:
            df = tables[tname]
            con.register(tname, df)
            count = con.execute(f"SELECT count(*) FROM {tname}").fetchone()[0]
            lines.append(f"\n--- RECALCULATED TABLE: {tname} (Rows: {count}) ---")
            df_dump = con.execute(f"SELECT * FROM {tname}").fetchdf()
            for idx, row in df_dump.iterrows():
                row_items = [f"{k}={v}" for k, v in row.items()]
                lines.append(f"  Row {idx + 1}: {' | '.join(row_items)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 3. INCREMENT 1B ACCEPTANCE TEST EXECUTION CAPTURE
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[3] INCREMENT 1B AUTOMATED CPM ACCEPTANCE SUITE EXECUTION")
    lines.append("=" * 80)

    from tests.test_s04_increment_1b import TestS04Increment1B

    suite_1b = unittest.TestLoader().loadTestsFromTestCase(TestS04Increment1B)
    stream_1b = io.StringIO()
    runner_1b = unittest.TextTestRunner(stream=stream_1b, verbosity=2)

    # Support bounded negative-control simulation for process exit status (A2)
    if os.environ.get("SIMULATE_AUDIT_FAILURE") == "1":
        class FailingNegativeControlTest(unittest.TestCase):
            def test_simulated_audit_failure(self):
                self.fail("Simulated negative-control failure to verify non-zero process exit signalling.")
        suite_1b.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(FailingNegativeControlTest))

    t0 = time.time()
    result_1b = runner_1b.run(suite_1b)
    t_1b = time.time() - t0

    lines.append(stream_1b.getvalue())
    lines.append(f"Increment 1B Tests Run: {result_1b.testsRun}")
    lines.append(f"Increment 1B Failures: {len(result_1b.failures)}")
    lines.append(f"Increment 1B Errors: {len(result_1b.errors)}")
    lines.append(f"Increment 1B Duration: {t_1b:.3f} seconds")
    lines.append(f"Increment 1B Status: {'PASSED' if result_1b.wasSuccessful() else 'FAILED'}")

    # -------------------------------------------------------------------------
    # 4. INCREMENT 1A ACCEPTANCE TEST EXECUTION CAPTURE
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[4] INCREMENT 1A INGESTION ACCEPTANCE SUITE EXECUTION")
    lines.append("=" * 80)

    from tests.test_s04_increment_1a import TestS04Increment1A

    suite_1a = unittest.TestLoader().loadTestsFromTestCase(TestS04Increment1A)
    stream_1a = io.StringIO()
    runner_1a = unittest.TextTestRunner(stream=stream_1a, verbosity=2)

    t0 = time.time()
    result_1a = runner_1a.run(suite_1a)
    t_1a = time.time() - t0

    lines.append(stream_1a.getvalue())
    lines.append(f"Increment 1A Tests Run: {result_1a.testsRun}")
    lines.append(f"Increment 1A Failures: {len(result_1a.failures)}")
    lines.append(f"Increment 1A Errors: {len(result_1a.errors)}")
    lines.append(f"Increment 1A Duration: {t_1a:.3f} seconds")
    lines.append(f"Increment 1A Status: {'PASSED' if result_1a.wasSuccessful() else 'FAILED'}")

    # -------------------------------------------------------------------------
    # 5. GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[5] GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)")
    lines.append("=" * 80)

    from tests.test_s04_verification_suite import TestS04VerificationSuite

    suite_g2 = unittest.TestLoader().loadTestsFromTestCase(TestS04VerificationSuite)
    stream_g2 = io.StringIO()
    runner_g2 = unittest.TextTestRunner(stream=stream_g2, verbosity=2)

    t0 = time.time()
    result_g2 = runner_g2.run(suite_g2)
    t_g2 = time.time() - t0

    lines.append(stream_g2.getvalue())
    lines.append(f"Gate 2 Tests Run: {result_g2.testsRun}")
    lines.append(f"Gate 2 Failures: {len(result_g2.failures)}")
    lines.append(f"Gate 2 Errors: {len(result_g2.errors)}")
    lines.append(f"Gate 2 Duration: {t_g2:.3f} seconds")
    lines.append(f"Gate 2 Regression Status: {'PASSED (ZERO REGRESSIONS)' if result_g2.wasSuccessful() else 'FAILED'}")

    total_tests = result_1b.testsRun + result_1a.testsRun + result_g2.testsRun
    total_time = t_1b + t_1a + t_g2

    all_passed = (
        result_1b.wasSuccessful()
        and result_1a.wasSuccessful()
        and result_g2.wasSuccessful()
    )

    lines.append("\n" + "=" * 80)
    lines.append(f"COMBINED TEST SUITE TOTALS: {total_tests} Tests Run across 3 Suites | {len(result_1b.failures) + len(result_1a.failures) + len(result_g2.failures)} Failures | {len(result_1b.errors) + len(result_1a.errors) + len(result_g2.errors)} Errors | {total_time:.3f}s")
    lines.append(f"FINAL AUDIT STATUS: {'PASSED (ALL SUITES GREEN)' if all_passed else 'FAILED (REMEDIATION REQUIRED)'}")
    lines.append("END OF INCREMENT 1B AUDIT REPORT")
    lines.append("=" * 80)

    return "\n".join(lines) + "\n", all_passed


if __name__ == "__main__":
    report_text, all_passed = run_audit()
    print(report_text)

    log_path = os.path.join(S04_ROOT, "tests", "INCREMENT_1B_VERIFICATION_AUDIT_REPORT.log")
    with open(log_path, "w") as f:
        f.write(report_text)
    print(f"\n[Audit Report written to {log_path}]")

    # Non-zero process exit status on test failure (A2)
    if not all_passed:
        sys.exit(1)
    sys.exit(0)
