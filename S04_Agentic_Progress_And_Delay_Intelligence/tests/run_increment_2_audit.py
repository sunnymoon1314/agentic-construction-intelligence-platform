#!/usr/bin/env python3
"""
ACIP S04: Increment 2 Verification & Empirical Audit Runner
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/run_increment_2_audit.py

Executes a complete, verifiable audit across all Increment 2 artefacts:
1. Computes SHA-256 cryptographic hashes and sizes of all engine, server, and test files.
2. Ingests and recalculates schedule data via TIAEvaluator and FastMCP tools.
3. Executes the full 8-test Increment 2 suite (tests/test_s04_increment_2.py).
4. Executes the full 12-test Increment 1B suite (tests/test_s04_increment_1b.py).
5. Executes the full 8-test Increment 1A suite (tests/test_s04_increment_1a.py).
6. Executes the full 8-test Gate 2 regression suite (tests/test_s04_verification_suite.py).
7. Emits a persisted audit log to tests/INCREMENT_2_VERIFICATION_AUDIT_REPORT.log.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
import os
import sys
import time
import unittest
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pq

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S04_ROOT)

from engine.cpm_recalculation_service import CPMRecalculationService
from engine.tia_evaluator import TIAEvaluator
from mcp_server.server import (
    s04_compare_schedule_baselines,
    s04_recalculate_cpm_schedule,
    s04_simulate_tia_fragnet,
    s04_analyze_float_erosion,
    s04_calculate_psscoc_notice_clock,
    s04_assess_liquidated_damages_exposure,
)


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_audit() -> tuple[str, bool]:
    lines = []
    lines.append("=" * 80)
    lines.append("ACIP S04: INCREMENT 2 AUTOMATED VERIFICATION & ARTEFACT AUDIT REPORT")
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
    # 1. FILE MANIFEST AND CRYPTOGRAPHIC DIGESTS
    # -------------------------------------------------------------------------
def check_manifest(root_dir: str = S04_ROOT, simulated_missing: str | None = None) -> tuple[bool, list[str], list[str]]:
    """
    Validates cryptographic file manifest and existence.
    Returns: (manifest_passed, log_lines, missing_files)
    """
    log_lines = []
    log_lines.append("\n[1] ARTEFACT CRYPTOGRAPHIC INTEGRITY MANIFEST (SHA-256)")
    log_lines.append("-" * 80)

    tracked_files = [
        "engine/cpm_engine.py",
        "engine/p6_parser.py",
        "engine/data_validator.py",
        "engine/xer_ingestion_pipeline.py",
        "engine/cpm_recalculation_service.py",
        "engine/tia_evaluator.py",
        "mcp_server/server.py",
        "tests/test_s04_verification_suite.py",
        "tests/test_s04_increment_1a.py",
        "tests/test_s04_increment_1b.py",
        "tests/test_s04_increment_2.py",
        "data/parquet/calendars.parquet",
        "data/parquet/contract_parameters.parquet",
        "data/parquet/delay_events.parquet",
        "data/parquet/delay_event_activities.parquet",
    ]

    manifest_passed = True
    missing_files = []

    for rel_path in tracked_files:
        full_path = os.path.join(root_dir, rel_path)
        if simulated_missing and rel_path == simulated_missing:
            log_lines.append(f"  {rel_path:<45} | MISSING (SIMULATED_NEGATIVE_CONTROL)")
            missing_files.append(rel_path)
            manifest_passed = False
        elif os.path.exists(full_path):
            digest = sha256_file(full_path)
            size = os.path.getsize(full_path)
            log_lines.append(f"  {rel_path:<45} | Size: {size:>7} bytes | SHA-256: {digest}")
        else:
            log_lines.append(f"  {rel_path:<45} | MISSING")
            missing_files.append(rel_path)
            manifest_passed = False

    if not manifest_passed:
        log_lines.append(f"\n[!] MANIFEST INTEGRITY FAILED: Missing required files: {missing_files}")

    return manifest_passed, log_lines, missing_files


def run_audit() -> tuple[str, bool]:
    lines = []
    lines.append("=" * 80)
    lines.append("ACIP S04: INCREMENT 2 AUTOMATED VERIFICATION & ARTEFACT AUDIT REPORT")
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
    # 1. FILE MANIFEST AND CRYPTOGRAPHIC DIGESTS
    # -------------------------------------------------------------------------
    simulated_missing = os.environ.get("SIMULATE_MISSING_ARTEFACT")
    manifest_passed, manifest_lines, missing_files = check_manifest(S04_ROOT, simulated_missing)
    lines.extend(manifest_lines)

    # -------------------------------------------------------------------------
    # 2. TIME IMPACT ANALYSIS EVALUATION EVIDENCE
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[2] TIME IMPACT ANALYSIS (TIA) LIVE LAKEHOUSE EVALUATION EVIDENCE")
    lines.append("=" * 80)

    parquet_dir = os.path.join(S04_ROOT, "data", "parquet")
    evaluator = TIAEvaluator()
    tia_result = evaluator.evaluate_parquet_delay_event(parquet_dir, "DLY-2026-001")

    lines.append(f"Event ID: {tia_result.event_id}")
    lines.append(f"Event Title: {tia_result.event_title}")
    lines.append(f"Risk Allocation: {tia_result.risk_allocation}")
    lines.append(f"Unimpacted Completion Date: {tia_result.unimpacted_completion_date.isoformat()}")
    lines.append(f"Impacted Completion Date: {tia_result.impacted_completion_date.isoformat()}")
    lines.append(f"Net Critical Delay: {tia_result.net_critical_delay_workdays} workdays")
    lines.append(f"Candidate EOT Relief: {tia_result.candidate_eot_relief_days} workdays")
    lines.append(f"Contractor Culpable Delay: {tia_result.contractor_culpable_days} workdays")
    lines.append(f"Liquidated Damages Exposure: S$ {tia_result.liquidated_damages_exposure_sgd:,.2f}")
    lines.append(f"Concurrency Attribution: {tia_result.concurrency_attribution}")
    lines.append(f"Notice Compliance Status: {tia_result.notice_compliance_status} (Elapsed: {tia_result.notice_elapsed_calendar_days} days)")

    # -------------------------------------------------------------------------
    # 3. INCREMENT 2 TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[3] INCREMENT 2 TEST SUITE EXECUTION (tests/test_s04_increment_2.py)")
    lines.append("=" * 80)

    from tests.test_s04_increment_2 import TestS04Increment2

    suite_2 = unittest.TestLoader().loadTestsFromTestCase(TestS04Increment2)
    stream_2 = io.StringIO()
    runner_2 = unittest.TextTestRunner(stream=stream_2, verbosity=2)

    t0 = time.time()
    result_2 = runner_2.run(suite_2)
    t_2 = time.time() - t0

    lines.append(stream_2.getvalue())
    lines.append(f"Increment 2 Tests Run: {result_2.testsRun}")
    lines.append(f"Increment 2 Failures: {len(result_2.failures)}")
    lines.append(f"Increment 2 Errors: {len(result_2.errors)}")
    lines.append(f"Increment 2 Duration: {t_2:.3f} seconds")
    lines.append(f"Increment 2 Status: {'PASSED' if result_2.wasSuccessful() else 'FAILED'}")

    # -------------------------------------------------------------------------
    # 4. INCREMENT 1B TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[4] INCREMENT 1B REGRESSION SUITE EXECUTION (tests/test_s04_increment_1b.py)")
    lines.append("=" * 80)

    from tests.test_s04_increment_1b import TestS04Increment1B

    suite_1b = unittest.TestLoader().loadTestsFromTestCase(TestS04Increment1B)
    stream_1b = io.StringIO()
    runner_1b = unittest.TextTestRunner(stream=stream_1b, verbosity=2)

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
    # 5. INCREMENT 1A TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[5] INCREMENT 1A REGRESSION SUITE EXECUTION (tests/test_s04_increment_1a.py)")
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
    # 6. GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[6] GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)")
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

    total_tests = result_2.testsRun + result_1b.testsRun + result_1a.testsRun + result_g2.testsRun
    total_time = t_2 + t_1b + t_1a + t_g2

    all_passed = (
        manifest_passed
        and result_2.wasSuccessful()
        and result_1b.wasSuccessful()
        and result_1a.wasSuccessful()
        and result_g2.wasSuccessful()
    )

    lines.append("\n" + "=" * 80)
    lines.append(
        f"COMBINED TEST SUITE TOTALS: {total_tests} Tests Run across 4 Suites | "
        f"{len(result_2.failures) + len(result_1b.failures) + len(result_1a.failures) + len(result_g2.failures)} Failures | "
        f"{len(result_2.errors) + len(result_1b.errors) + len(result_1a.errors) + len(result_g2.errors)} Errors | "
        f"{total_time:.3f}s"
    )
    if not manifest_passed:
        lines.append(f"MANIFEST AUDIT STATUS: FAILED (Required artefacts missing: {missing_files})")
    lines.append(f"FINAL AUDIT STATUS: {'PASSED (ALL 4 SUITES GREEN)' if all_passed else 'FAILED (REMEDIATION REQUIRED)'}")
    lines.append("END OF INCREMENT 2 AUDIT REPORT")
    lines.append("=" * 80)

    return "\n".join(lines) + "\n", all_passed


if __name__ == "__main__":
    report_text, all_passed = run_audit()
    print(report_text)

    log_path = os.path.join(S04_ROOT, "tests", "INCREMENT_2_VERIFICATION_AUDIT_REPORT.log")
    with open(log_path, "w") as f:
        f.write(report_text)
    print(f"\n[Audit Report written to {log_path}]")

    if not all_passed:
        sys.exit(1)
    sys.exit(0)
