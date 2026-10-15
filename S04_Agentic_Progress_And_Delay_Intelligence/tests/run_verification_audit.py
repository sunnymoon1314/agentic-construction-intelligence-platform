#!/usr/bin/env python3
"""
ACIP S04: Automated Verification & Empirical Audit Runner
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: tests/run_verification_audit.py

Executes a complete, verifiable audit across all S04 artefacts:
1. Computes SHA-256 cryptographic hashes of all engine source files, Parquet datasets, and XER files.
2. Dumps schemas, record counts, and actual row contents from all 8 Parquet tables using DuckDB.
3. Dumps raw content of the Primavera P6 XER files.
4. Executes the complete 8-test verification suite (tests/test_s04_verification_suite.py) in verbose mode.
5. Saves a timestamped audit log to tests/VERIFICATION_AUDIT_REPORT.log for auditor inspection.
"""

import hashlib
import os
import sys
import time
import unittest
from datetime import datetime, timezone
import duckdb

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S04_ROOT)


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


import pandas as pd
import numpy as np
import pyarrow as pq

def run_audit() -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("ACIP S04: AUTOMATED VERIFICATION & ARTEFACT AUDIT REPORT")
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
    # 1. SHA-256 CRYPTOGRAPHIC HASHES & FILE SIZES
    # -------------------------------------------------------------------------
    lines.append("\n[1] CRYPTOGRAPHIC CHECKSUMS & FILE MANIFEST")
    lines.append("-" * 80)

    audit_files = [
        "engine/cpm_engine.py",
        "engine/data_validator.py",
        "engine/p6_parser.py",
        "tests/test_s04_verification_suite.py",
        "data/parquet/contract_parameters.parquet",
        "data/parquet/schedule_versions.parquet",
        "data/parquet/schedule_activities.parquet",
        "data/parquet/schedule_relationships.parquet",
        "data/parquet/site_records.parquet",
        "data/parquet/site_record_activities.parquet",
        "data/parquet/delay_events.parquet",
        "data/parquet/delay_event_activities.parquet",
        "data/xer/WHC_COM_BL01_Approved_Baseline.xer",
        "data/xer/WHC_COM_UP01_Progress_Update.xer",
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
            lines.append(f"FILE: {rel_path:<45} | MISSING!")

    # -------------------------------------------------------------------------
    # 2. PARQUET LAKEHOUSE DATASET INSPECTION (DUCKDB ROW DUMPS)
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[2] PARQUET LAKEHOUSE RECORD INSPECTION (EMPIRICAL DATA DUMPS)")
    lines.append("=" * 80)

    con = duckdb.connect(database=":memory:")
    parquet_dir = os.path.join(S04_ROOT, "data", "parquet")
    parquet_tables = [
        "contract_parameters",
        "schedule_versions",
        "schedule_activities",
        "schedule_relationships",
        "site_records",
        "site_record_activities",
        "delay_events",
        "delay_event_activities",
    ]

    for tbl in parquet_tables:
        p_path = os.path.join(parquet_dir, f"{tbl}.parquet")
        lines.append(f"\n--- TABLE: {tbl} ({p_path}) ---")
        if os.path.exists(p_path):
            count_res = con.execute(f"SELECT count(*) FROM read_parquet('{p_path}')").fetchone()[0]
            lines.append(f"Total Rows: {count_res}")
            
            # Describe columns
            schema_info = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p_path}')").fetchall()
            col_desc = ", ".join([f"{col[0]}:{col[1]}" for col in schema_info])
            lines.append(f"Columns: {col_desc}")
            
            # Dump all records
            rows = con.execute(f"SELECT * FROM read_parquet('{p_path}')").fetchall()
            col_names = [col[0] for col in schema_info]
            for i, r in enumerate(rows, 1):
                row_str = " | ".join([f"{col_names[j]}={val}" for j, val in enumerate(r)])
                lines.append(f"  Row {i}: {row_str}")
        else:
            lines.append("  TABLE FILE DOES NOT EXIST")

    # -------------------------------------------------------------------------
    # 3. PRIMAVERA P6 XER CONTENT INSPECTION (BASELINE & PROGRESS UPDATE)
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[3] PRIMAVERA P6 XER SCHEDULE FILE INSPECTION (EMPIRICAL DUMPS)")
    lines.append("=" * 80)

    xer_files_to_inspect = [
        "data/xer/WHC_COM_BL01_Approved_Baseline.xer",
        "data/xer/WHC_COM_UP01_Progress_Update.xer",
    ]

    for rel_xer in xer_files_to_inspect:
        xer_path = os.path.join(S04_ROOT, rel_xer)
        lines.append(f"\n--- FILE: {rel_xer} ({xer_path}) ---")
        if os.path.exists(xer_path):
            with open(xer_path, "r") as f:
                content = f.read()
            lines.append(content.strip())
        else:
            lines.append("XER FILE DOES NOT EXIST")

    # -------------------------------------------------------------------------
    # 4. TEST EXECUTION CAPTURE
    # -------------------------------------------------------------------------
    lines.append("\n" + "=" * 80)
    lines.append("[4] AUTOMATED VERIFICATION TEST EXECUTION CAPTURE")
    lines.append("=" * 80)

    from tests.test_s04_verification_suite import TestS04VerificationSuite

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestS04VerificationSuite)
    
    # Run tests capturing output
    import io
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    test_output = stream.getvalue()
    lines.append(test_output.strip())
    lines.append("-" * 80)
    lines.append(f"Tests Run: {result.testsRun}")
    lines.append(f"Failures: {len(result.failures)}")
    lines.append(f"Errors: {len(result.errors)}")
    lines.append(f"Skipped: {len(result.skipped)}")
    lines.append(f"Duration: {duration:.3f} seconds")
    lines.append(f"Test Suite Status: {'ALL TESTS PASSED (OK)' if result.wasSuccessful() else 'TEST FAILURES DETECTED'}")
    lines.append("=" * 80)
    lines.append("END OF AUDIT REPORT")
    lines.append("=" * 80)

    report_content = "\n".join(lines) + "\n"

    # Write report to log file
    report_file = os.path.join(S04_ROOT, "tests", "VERIFICATION_AUDIT_REPORT.log")
    with open(report_file, "w") as f:
        f.write(report_content)

    return report_content


if __name__ == "__main__":
    report = run_audit()
    print(report)
