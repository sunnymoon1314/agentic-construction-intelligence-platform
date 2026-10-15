#!/usr/bin/env python3
"""
ACIP S04: Increment 3 Verification & Empirical Audit Runner
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/run_increment_3_audit.py

Executes a complete, verifiable audit across all S04 milestones through Increment 3:
1. Executes R5 Preflight Input Prerequisite Audit (ensuring zero side-effects on missing inputs).
2. Generates and validates Downstream Handshake tables for S05 and S06 with R4 package hash binding.
3. Executes Multi-Agent Adversarial Deliberation live on lakehouse delay events.
4. Performs R3 Cryptographic Artefact Digest Inventory & Baseline Tamper Verification.
5. Executes the expanded Increment 3 suite (tests/test_s04_increment_3.py).
6. Executes the full 11-test Increment 2 suite (tests/test_s04_increment_2.py).
7. Executes the full 12-test Increment 1B suite (tests/test_s04_increment_1b.py).
8. Executes the full 8-test Increment 1A suite (tests/test_s04_increment_1a.py).
9. Executes the full 8-test Gate 2 regression suite (tests/test_s04_verification_suite.py).
10. Emits a persisted audit log to tests/INCREMENT_3_VERIFICATION_AUDIT_REPORT.log.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
import os
import sys
import time
from typing import Optional, Dict, Any, Tuple
import unittest
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pq

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S04_ROOT)

from engine.handshake_emitters import HandshakeEmitterService
from agent_client.deliberation_pipeline import DeliberationPipeline


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


TRUSTED_INPUT_BASELINE = {
    "engine/cpm_engine.py": "22f35aed330992d7fa9a8a51ae7926b4b556a84971835361986fefa42943096f",
    "engine/p6_parser.py": "16409216ac052f527ea6ccc4b5172aec0d26555e2b1be51871bec0d42af37289",
    "engine/data_validator.py": "6358c2a4d30e8dc9b76a388e51854bc4e0010ad53c2faa66ad9b555b4b97d9b7",
    "engine/xer_ingestion_pipeline.py": "6c4982c90e0372d3417c6ee6e8f4e26b19c528d57f797fc084a259c85ff1c55b",
    "engine/cpm_recalculation_service.py": "24382548bc8bf1063df4448414309813d6fc2f94db77e9dd8962f9952e04ecff",
    "engine/tia_evaluator.py": "2d4c354465845a17e65efdb3442d1e681e262fe09d34074878e08d0b7031487c",
    "mcp_server/server.py": "388f7ec79315b8eca14f823c8d38e7be51f244e9bd10a886578f9b57e953a838",
    "data/parquet/calendars.parquet": "9d0a7d399e60d62710a7754568e10eb32b95e83f9ccccfd19e4ff46a2ff1a274",
    "data/parquet/contract_parameters.parquet": "b7ec043c1dd434d262882f8462124915dfe33e2160503de66515728ca7a8dddb",
    "data/parquet/delay_events.parquet": "0e45797dacc7a9b1a95ed96b37a13eaedeec9b42d622185ff870f8c381dd4417",
    "data/parquet/delay_event_activities.parquet": "2f04a2c968c5e52eb318fa9da7f35a62cf44c55f5b00b0d87abf87ccce53d12b",
    "data/parquet/schedule_activities.parquet": "d4c3b66d965785ed4e6675f1928399b74ccfabf6bf3091afb1732b32e8abfbd8",
    "data/parquet/schedule_versions.parquet": "cc03bf9b672475bdfb97b1a58c0a6ee1a26dcc6d2767934c9567946be55f0fc6",
}


def run_preflight_input_audit(root_dir: str = S04_ROOT) -> tuple[bool, list[str]]:
    """
    R5 Preflight Audit: Verifies prerequisite inputs exist before publishing handshakes.
    Ensures zero side-effects if preflight inputs are missing.
    """
    log_lines = []
    log_lines.append("\n[0] PREFLIGHT INPUT PREREQUISITE AUDIT")
    log_lines.append("-" * 80)
    
    prereqs = [
        "data/parquet/schedule_activities.parquet",
        "data/parquet/schedule_versions.parquet",
        "data/parquet/calendars.parquet",
        "data/parquet/contract_parameters.parquet",
        "data/parquet/delay_events.parquet",
        "data/parquet/delay_event_activities.parquet",
    ]
    
    simulated_missing = os.environ.get("SIMULATE_PREFLIGHT_FAILURE")
    passed = True
    for p in prereqs:
        full_p = os.path.join(root_dir, p)
        if simulated_missing and p == simulated_missing:
            log_lines.append(f"  {p:<50} | MISSING (SIMULATED PREFLIGHT FAILURE)")
            passed = False
        elif os.path.exists(full_p) and os.path.getsize(full_p) > 0:
            log_lines.append(f"  {p:<50} | VERIFIED ({os.path.getsize(full_p)} bytes)")
        else:
            log_lines.append(f"  {p:<50} | MISSING / CORRUPT")
            passed = False
            
    if not passed:
        log_lines.append("[!] PREFLIGHT AUDIT FAILED: Required lakehouse inputs missing. Aborting publication.")
    else:
        log_lines.append("  Preflight Input Audit PASSED: All prerequisite lakehouse tables verified.")
    return passed, log_lines


AUTHORITATIVE_INPUT_FILES = [
    "engine/cpm_engine.py",
    "engine/p6_parser.py",
    "engine/data_validator.py",
    "engine/xer_ingestion_pipeline.py",
    "engine/cpm_recalculation_service.py",
    "engine/tia_evaluator.py",
    "engine/handshake_emitters.py",
    "mcp_server/server.py",
    "agent_client/deliberation_pipeline.py",
    "tests/test_s04_verification_suite.py",
    "tests/test_s04_increment_1a.py",
    "tests/test_s04_increment_1b.py",
    "tests/test_s04_increment_2.py",
    "tests/test_s04_increment_3.py",
    "data/parquet/calendars.parquet",
    "data/parquet/contract_parameters.parquet",
    "data/parquet/delay_events.parquet",
    "data/parquet/delay_event_activities.parquet",
    "data/parquet/schedule_activities.parquet",
    "data/parquet/schedule_versions.parquet",
]

GENERATED_OUTPUT_INVENTORY = [
    "data/parquet/quality_inspection_schedule_links.parquet",
    "data/parquet/formal_claims_delay_links.parquet",
    "data/parquet/quality_inspection_schedule_links_manifest.json",
    "data/parquet/formal_claims_delay_links_manifest.json",
    "data/parquet/audit_deliberation_log.parquet",
]


def check_manifest(
    root_dir: str = S04_ROOT,
    simulated_tamper: str | None = None,
    include_generated_outputs: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """
    R3 Cryptographic Artefact Digest Inventory & Baseline Verification:
    Calculates SHA-256 digests and validates against trusted baseline anchors.
    Separates required authoritative-input baselines from generated-output inventory.
    Generated outputs are not required to exist before publication.
    Returns: (manifest_passed, log_lines, mismatched_or_missing_files)
    """
    log_lines = []
    if include_generated_outputs:
        log_lines.append("\n[2.1] GENERATED OUTPUT ARTEFACT INVENTORY (POST-PUBLICATION)")
        tracked_files = GENERATED_OUTPUT_INVENTORY
    else:
        log_lines.append("\n[1] AUTHORITATIVE INPUT BASELINE INTEGRITY & TAMPER AUDIT (PRE-PUBLICATION)")
        tracked_files = AUTHORITATIVE_INPUT_FILES

    log_lines.append("-" * 80)

    manifest_passed = True
    failed_files = []

    for rel_path in tracked_files:
        full_path = os.path.join(root_dir, rel_path)
        if not os.path.exists(full_path):
            fallback_code = os.path.join(S04_ROOT, rel_path)
            if not rel_path.startswith("data/") and os.path.exists(fallback_code):
                full_path = fallback_code
            else:
                log_lines.append(f"  {rel_path:<50} | MISSING")
                failed_files.append(rel_path)
                manifest_passed = False
                continue

        digest = sha256_file(full_path)
        size = os.path.getsize(full_path)

        # R3 Baseline comparison for anchored static inputs
        baseline_digest = TRUSTED_INPUT_BASELINE.get(rel_path)
        if simulated_tamper and rel_path == simulated_tamper:
            digest = "TAMPERED_HASH_00000000000000000000000000000000000000000000000000000000"
            log_lines.append(f"  {rel_path:<50} | Size: {size:>7} B | SHA-256: {digest} [TAMPER DETECTED]")
            failed_files.append(rel_path)
            manifest_passed = False
        elif baseline_digest:
            if digest == baseline_digest:
                log_lines.append(f"  {rel_path:<50} | Size: {size:>7} B | SHA-256: {digest} [BASELINE MATCH]")
            else:
                log_lines.append(f"  {rel_path:<50} | Size: {size:>7} B | SHA-256: {digest} [BASELINE MISMATCH]")
                failed_files.append(rel_path)
                manifest_passed = False
        else:
            log_lines.append(f"  {rel_path:<50} | Size: {size:>7} B | SHA-256: {digest} [INVENTORY]")

    if not manifest_passed:
        log_lines.append(f"\n[!] MANIFEST INTEGRITY FAILED: Mismatched/missing files: {failed_files}")

    return manifest_passed, log_lines, failed_files


def run_audit(root_dir: Optional[str] = None, run_tests: bool = True) -> tuple[str, bool]:
    if root_dir is None:
        root_dir = S04_ROOT

    lines = []
    lines.append("=" * 80)
    lines.append("ACIP S04: INCREMENT 3 AUTOMATED VERIFICATION & ARTEFACT AUDIT REPORT")
    lines.append("=" * 80)
    lines.append(f"Audit Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append("Execution Role: Automated CI/CD Execution (Verification Suite)")
    lines.append(f"Audit Host OS: {sys.platform} (macOS Darwin)")
    lines.append(f"Python Executable: {sys.executable}")
    lines.append(f"Python Version: {sys.version.split()[0]}")
    lines.append(f"Key Dependencies: duckdb={duckdb.__version__}, pyarrow={pq.__version__}, pandas={pd.__version__}, numpy={np.__version__}")
    lines.append(f"Module Root: {root_dir}")
    lines.append("-" * 80)

    # -------------------------------------------------------------------------
    # 0. R5 PREFLIGHT PREREQUISITE AUDIT (ZERO SIDE EFFECTS ON FAILURE)
    # -------------------------------------------------------------------------
    preflight_ok, preflight_lines = run_preflight_input_audit(root_dir)
    lines.extend(preflight_lines)
    if not preflight_ok:
        lines.append("\n[!] AUDIT ABORTED AT PREFLIGHT: Prerequisite tables missing; zero outputs published.")
        return "\n".join(lines) + "\n", False

    # -------------------------------------------------------------------------
    # 1. R3 INPUT BASELINE INTEGRITY & TAMPER AUDIT (BEFORE PUBLICATION/PERSISTENCE)
    # -------------------------------------------------------------------------
    simulated_tamper = os.environ.get("SIMULATE_TAMPER_ARTEFACT")
    manifest_passed, manifest_lines, failed_files = check_manifest(root_dir, simulated_tamper, include_generated_outputs=False)
    lines.extend(manifest_lines)
    if not manifest_passed:
        lines.append(f"\n[!] AUDIT ABORTED: Input baseline integrity failure ({failed_files}); zero publication/deliberation executed.")
        return "\n".join(lines) + "\n", False

    # -------------------------------------------------------------------------
    # 2. PUBLISH HANDSHAKES & DELIBERATION TRANSACTIONS
    # -------------------------------------------------------------------------
    parquet_dir = os.path.join(root_dir, "data", "parquet")
    handshake_service = HandshakeEmitterService(parquet_dir=parquet_dir)
    df_s05, df_s06, handshake_res = handshake_service.publish_all_handshake_links()

    pipeline = DeliberationPipeline(parquet_dir=parquet_dir)
    delib_consensus = pipeline.run_deliberation(
        project_id="PRJ-WHC-COM-001",
        event_id="DLY-2026-001",
        event_data={
            "event_title": "Groundwater Ingress & Pumping Stoppage",
            "affected_activity_id": "ACT-03",
            "claimed_delay_days": 3.0,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE",
            "event_start_date": "2026-11-09",
            "notice_served_date": "2026-11-10",
            "is_contract_verified": True,
        },
        persist_log=True,
    )

    # Inventory post-publication generated outputs
    out_ok, out_lines, out_failed = check_manifest(root_dir, include_generated_outputs=True)
    lines.extend(out_lines)

    # -------------------------------------------------------------------------
    # 3. DOWNSTREAM HANDSHAKES & DELIBERATION EVIDENCE
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[2] INCREMENT 3 DOWNSTREAM HANDSHAKES & MULTI-AGENT DELIBERATION EVIDENCE")
    lines.append("=" * 80)
    lines.append(f"S05 Quality Inspection Links Emitted: {len(df_s05)} records (Status: {handshake_res['s05_validation_status']})")
    lines.append(f"S06 Adjudication Claims Links Emitted: {len(df_s06)} records (Status: {handshake_res['s06_validation_status']})")
    lines.append(f"Downstream Package Receipt Status: {handshake_res.get('lifecycle_status', 'N/A')}")
    lines.append(f"Downstream Composite Referential Integrity: {'PASSED (Zero Dangling Keys)' if handshake_res['overall_integrity_passed'] else 'FAILED'}")
    lines.append("-" * 80)
    lines.append(f"Live Multi-Agent Deliberation Session: {delib_consensus.session_id}")
    lines.append(f"Event Evaluated: {delib_consensus.event_id} ({delib_consensus.event_title})")
    lines.append(f"Determination Tier: {delib_consensus.determination_tier}")
    lines.append(f"Contract Verification Guardrail: {delib_consensus.contract_verification_status}")
    lines.append(f"Certified EOT Relief: {delib_consensus.candidate_eot_relief_days} workdays")
    lines.append(f"Contractor Culpable Delay: {delib_consensus.contractor_culpable_days} workdays")
    lines.append(f"Liquidated Damages Assessment: S$ {delib_consensus.liquidated_damages_exposure_sgd:,.2f}")
    lines.append(f"Concurrency Attribution: {delib_consensus.concurrency_attribution}")
    lines.append(f"Notice Compliance Status: {delib_consensus.notice_compliance_status}")

    if not run_tests:
        return "\n".join(lines) + "\n", manifest_passed and handshake_res["overall_integrity_passed"]

    # -------------------------------------------------------------------------
    # 3. INCREMENT 3 TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[3] INCREMENT 3 TEST SUITE EXECUTION (tests/test_s04_increment_3.py)")
    lines.append("=" * 80)

    from tests.test_s04_increment_3 import TestS04Increment3

    suite_3 = unittest.TestLoader().loadTestsFromTestCase(TestS04Increment3)
    stream_3 = io.StringIO()
    runner_3 = unittest.TextTestRunner(stream=stream_3, verbosity=2)

    t0 = time.time()
    result_3 = runner_3.run(suite_3)
    t_3 = time.time() - t0

    lines.append(stream_3.getvalue())
    lines.append(f"Increment 3 Tests Run: {result_3.testsRun}")
    lines.append(f"Increment 3 Failures: {len(result_3.failures)}")
    lines.append(f"Increment 3 Errors: {len(result_3.errors)}")
    lines.append(f"Increment 3 Duration: {t_3:.3f} seconds")
    lines.append(f"Increment 3 Status: {'PASSED' if result_3.wasSuccessful() else 'FAILED'}")

    # -------------------------------------------------------------------------
    # 4. INCREMENT 2 TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[4] INCREMENT 2 TEST SUITE EXECUTION (tests/test_s04_increment_2.py)")
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
    # 5. INCREMENT 1B TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[5] INCREMENT 1B REGRESSION SUITE EXECUTION (tests/test_s04_increment_1b.py)")
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
    # 6. INCREMENT 1A TEST SUITE EXECUTION
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[6] INCREMENT 1A REGRESSION SUITE EXECUTION (tests/test_s04_increment_1a.py)")
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
    # 7. GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[7] GATE 2 CERTIFIED REGRESSION SUITE EXECUTION (ZERO REGRESSIONS)")
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

    total_tests = result_3.testsRun + result_2.testsRun + result_1b.testsRun + result_1a.testsRun + result_g2.testsRun
    total_time = t_3 + t_2 + t_1b + t_1a + t_g2

    all_passed = (
        manifest_passed
        and result_3.wasSuccessful()
        and result_2.wasSuccessful()
        and result_1b.wasSuccessful()
        and result_1a.wasSuccessful()
        and result_g2.wasSuccessful()
    )

    lines.append("\n" + "=" * 80)
    lines.append(
        f"COMBINED TEST SUITE TOTALS: {total_tests} Tests Run across 5 Suites | "
        f"{len(result_3.failures) + len(result_2.failures) + len(result_1b.failures) + len(result_1a.failures) + len(result_g2.failures)} Failures | "
        f"{len(result_3.errors) + len(result_2.errors) + len(result_1b.errors) + len(result_1a.errors) + len(result_g2.errors)} Errors | "
        f"{total_time:.3f}s"
    )
    if not manifest_passed:
        lines.append(f"MANIFEST AUDIT STATUS: FAILED (Required artefacts mismatched or missing: {failed_files})")
    lines.append(f"FINAL AUDIT STATUS: {'PASSED (ALL 5 SUITES GREEN)' if all_passed else 'FAILED (REMEDIATION REQUIRED)'}")
    lines.append("END OF INCREMENT 3 AUDIT REPORT")
    lines.append("=" * 80)

    return "\n".join(lines) + "\n", all_passed


if __name__ == "__main__":
    report_text, all_passed = run_audit()
    print(report_text)

    log_path = os.path.join(S04_ROOT, "tests", "INCREMENT_3_VERIFICATION_AUDIT_REPORT.log")
    with open(log_path, "w") as f:
        f.write(report_text)
    print(f"\n[Audit Report written to {log_path}]")

    if not all_passed:
        sys.exit(1)
    sys.exit(0)
