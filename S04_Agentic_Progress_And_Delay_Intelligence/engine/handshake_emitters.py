#!/usr/bin/env python3
"""
ACIP S04: Downstream Handshake Emitters & Referential Lineage Service
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: engine/handshake_emitters.py

Generates and validates version-pinned composite foreign-key links between S04 schedule intelligence
and downstream platform modules:
1. S05 (Quality & Defect Intelligence):
   - Maps schedule activities to quality inspection hold points (quality_inspection_schedule_links.parquet).
   - Composite Foreign Key: (project_id, schedule_version, activity_id) -> schedule_activities.parquet.
2. S06 (Contract & Claims Intelligence):
   - Maps delay events and revisions to formal SOPA adjudication claims dossiers (formal_claims_delay_links.parquet).
   - Composite Foreign Key: (project_id, event_id, revision_id) -> delay_events.parquet.

Enforces strict referential integrity, fail-closed validation on dangling links, and version pinning.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Dict, Any, List, Optional, Tuple
import duckdb
import numpy as np
import pandas as pd


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class DownstreamHandshakeError(Exception):
    """Raised when downstream referential integrity or version pinning fails."""
    pass


def validate_and_parse_revision_id(raw_rev: Any, context: str = "emission") -> int:
    """
    R2 Strict Revision ID Integrality Validation:
    - Rejects None, NaN, and booleans (True/False).
    - Rejects fractional numbers (1.5, 1.7, etc.).
    - Rejects non-positive numbers (<= 0).
    - Accepts whole integers or exact integer floats (1, 1.0, 2).
    - Accepts string representations of whole numbers ('1', '2').
    """
    if raw_rev is None or pd.isna(raw_rev):
        raise DownstreamHandshakeError(f"R2 Violation ({context}): revision_id cannot be null or NaN.")

    # Guard against Python bool being a subclass of int
    if isinstance(raw_rev, bool):
        raise DownstreamHandshakeError(f"R2 Violation ({context}): revision_id cannot be a boolean ({raw_rev}).")

    if isinstance(raw_rev, (int, np.integer)):
        rev_int = int(raw_rev)
    elif isinstance(raw_rev, (float, np.floating)):
        if not float(raw_rev).is_integer():
            raise DownstreamHandshakeError(
                f"R2 Violation ({context}): revision_id cannot be fractional ({raw_rev}); must be exact integer."
            )
        rev_int = int(raw_rev)
    elif isinstance(raw_rev, str):
        s = raw_rev.strip()
        try:
            f_val = float(s)
            if not f_val.is_integer():
                raise DownstreamHandshakeError(
                    f"R2 Violation ({context}): revision_id string '{raw_rev}' is fractional; must be exact integer."
                )
            rev_int = int(f_val)
        except ValueError:
            raise DownstreamHandshakeError(
                f"R2 Violation ({context}): revision_id string '{raw_rev}' is not a valid integer."
            )
    else:
        raise DownstreamHandshakeError(
            f"R2 Violation ({context}): unsupported type {type(raw_rev).__name__} for revision_id."
        )

    if rev_int < 1:
        raise DownstreamHandshakeError(
            f"R2 Violation ({context}): revision_id must be >= 1; received {rev_int}."
        )

    return rev_int


class HandshakeEmitterService:
    """
    Engine service for generating, validating, and publishing downstream handshake links
    from S04 Lakehouse tables to S05 Quality and S06 Claims.
    """

    def __init__(self, parquet_dir: Optional[str] = None):
        if parquet_dir is None:
            s04_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parquet_dir = os.path.join(s04_root, "data", "parquet")
        self.parquet_dir = parquet_dir

    def emit_s05_quality_inspection_links(
        self,
        output_path: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Extracts structural and critical-path activities from schedule_activities.parquet
        and generates version-pinned quality inspection hold points for S05.
        
        Composite FK: (project_id, schedule_version, activity_id) referencing schedule_activities.
        Returns: (DataFrame of links, Manifest Envelope Dictionary)
        """
        act_path = os.path.join(self.parquet_dir, "schedule_activities.parquet")
        if not os.path.exists(act_path):
            raise DownstreamHandshakeError(f"Missing schedule_activities.parquet in {self.parquet_dir}")

        source_hash = sha256_file(act_path)

        con = duckdb.connect()
        try:
            df_act = con.execute(f"SELECT * FROM read_parquet('{act_path}')").fetch_df()
        finally:
            con.close()

        if df_act.empty:
            raise DownstreamHandshakeError("schedule_activities table is empty; cannot emit S05 links.")

        links = []
        for idx, row in df_act.iterrows():
            proj_id = str(row["project_id"])
            sched_ver = str(row["schedule_version"])
            act_id = str(row["activity_id"])
            act_name = str(row.get("activity_name", ""))
            is_crit = bool(row.get("is_critical", False))

            # Determine inspection hold point tier based on critical path and activity nature
            if is_crit:
                risk_tier = "CRITICAL_STRUCTURAL_HOLD_POINT"
                lead_days = 3
                hold_status = "MANDATORY_QP_INSPECTION_REQUIRED"
            elif any(k in act_name.lower() for k in ["rebar", "concrete", "anchor", "excavation"]):
                risk_tier = "HIGH_RISK_SURVEILLANCE"
                lead_days = 2
                hold_status = "SURVEILLANCE_NOTICE_REQUIRED"
            else:
                risk_tier = "STANDARD_QUALITY_AUDIT"
                lead_days = 1
                hold_status = "NOTIFICATION_OPTIONAL"

            insp_id = f"INSP-S05-{proj_id}-{sched_ver}-{act_id}"
            links.append({
                "inspection_id": insp_id,
                "project_id": proj_id,
                "schedule_version": sched_ver,
                "activity_id": act_id,
                "activity_name": act_name,
                "defect_risk_tier": risk_tier,
                "hold_point_status": hold_status,
                "inspection_lead_time_days": lead_days,
                "is_critical_path_activity": is_crit,
                "source_module": "ACIP_S04",
                "target_module": "ACIP_S05",
                "handshake_version": "1.0",
                "source_file_sha256": source_hash,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            })

        df_links = pd.DataFrame(links)

        # F4: Handshake Package Manifest Envelope
        package_id = f"PKG-S05-HANDSHAKE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        manifest_envelope = {
            "package_id": package_id,
            "handshake_target": "ACIP_S05_QUALITY",
            "schema_version": "1.0",
            "source_table": "schedule_activities.parquet",
            "source_content_sha256": source_hash,
            "record_count": len(df_links),
            "records_emitted": len(df_links),
            "producer_module": "ACIP_S04",
            "producer_service_version": "1.0.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "validation_status": "PRE_FLIGHT_EMITTED",
        }

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            df_links.to_parquet(output_path, index=False)
            pkg_hash = sha256_file(output_path)
            manifest_envelope["package_sha256"] = pkg_hash
            manifest_envelope["output_package_sha256"] = pkg_hash
            manifest_envelope["package_file"] = os.path.basename(output_path)
            manifest_envelope["lifecycle_status"] = "EMITTED"
            manifest_path = output_path.replace(".parquet", "_manifest.json")
            with open(manifest_path, "w") as mf:
                json.dump(manifest_envelope, mf, indent=2)

        return df_links, manifest_envelope

    def emit_s06_adjudication_claim_links(
        self,
        output_path: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Extracts delay events and revision records from delay_events.parquet
        and generates revision-pinned dispute review triage links for S06 SOPA intelligence.
        
        Composite FK: (project_id, event_id, revision_id) referencing delay_events.
        Enforces strict non-null revision_id (F5).
        Returns: (DataFrame of links, Manifest Envelope Dictionary)
        """
        dly_path = os.path.join(self.parquet_dir, "delay_events.parquet")
        if not os.path.exists(dly_path):
            raise DownstreamHandshakeError(f"Missing delay_events.parquet in {self.parquet_dir}")

        source_hash = sha256_file(dly_path)

        con = duckdb.connect()
        try:
            df_dly = con.execute(f"SELECT * FROM read_parquet('{dly_path}')").fetch_df()
        finally:
            con.close()

        if df_dly.empty:
            raise DownstreamHandshakeError("delay_events table is empty; cannot emit S06 links.")

        # F5: Strict check on revision_id column
        if "revision_id" not in df_dly.columns:
            raise DownstreamHandshakeError("delay_events table is missing required 'revision_id' column.")

        links = []
        for idx, row in df_dly.iterrows():
            proj_id = str(row["project_id"])
            event_id = str(row["event_id"])
            rev_raw = row["revision_id"]

            # F5/R2: Strict revision_id validation (rejects fractional, negative, boolean, non-integral)
            rev_id = validate_and_parse_revision_id(rev_raw, context=f"S06 link row {idx}")

            event_title = str(row.get("event_title", "Unspecified Delay Event"))
            risk_alloc = str(row.get("risk_allocation", "EMPLOYER_RISK"))
            claimed_eot = float(row.get("claimed_eot_days", 0.0))

            # F6: Qualified triage indicator and illustrative quantum estimate (not statutory conclusion)
            if risk_alloc in ["EMPLOYER_RISK", "CONCURRENT_SPLIT", "NEUTRAL_FORCE_MAJEURE"] and claimed_eot > 0:
                sopa_candidate = True
                triage_status = "INTERNAL_TRIAGE_CANDIDATE_FOR_CLAIM_REVIEW"
                illustrative_quantum_sgd = claimed_eot * 15000.0  # Illustrative baseline formula
            else:
                sopa_candidate = False
                triage_status = "NOT_IDENTIFIED_FOR_SOPA_TRIAGE"
                illustrative_quantum_sgd = 0.0

            dossier_id = f"CLM-S06-{proj_id}-{event_id}-R{rev_id}"
            links.append({
                "claim_dossier_id": dossier_id,
                "project_id": proj_id,
                "event_id": event_id,
                "revision_id": rev_id,
                "event_title": event_title,
                "risk_allocation": risk_alloc,
                "claimed_eot_days": claimed_eot,
                "candidate_for_sopa_claim_review": sopa_candidate,
                "triage_assessment_status": triage_status,
                "illustrative_baseline_estimate_sgd": illustrative_quantum_sgd,
                "source_module": "ACIP_S04",
                "target_module": "ACIP_S06",
                "handshake_version": "1.0",
                "source_file_sha256": source_hash,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            })

        df_links = pd.DataFrame(links)

        # F4: Handshake Package Manifest Envelope
        package_id = f"PKG-S06-HANDSHAKE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        manifest_envelope = {
            "package_id": package_id,
            "handshake_target": "ACIP_S06_CLAIMS",
            "schema_version": "1.0",
            "source_table": "delay_events.parquet",
            "source_content_sha256": source_hash,
            "record_count": len(df_links),
            "records_emitted": len(df_links),
            "producer_module": "ACIP_S04",
            "producer_service_version": "1.0.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "validation_status": "PRE_FLIGHT_EMITTED",
        }

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            df_links.to_parquet(output_path, index=False)
            pkg_hash = sha256_file(output_path)
            manifest_envelope["package_sha256"] = pkg_hash
            manifest_envelope["output_package_sha256"] = pkg_hash
            manifest_envelope["package_file"] = os.path.basename(output_path)
            manifest_envelope["lifecycle_status"] = "EMITTED"
            manifest_path = output_path.replace(".parquet", "_manifest.json")
            with open(manifest_path, "w") as mf:
                json.dump(manifest_envelope, mf, indent=2)

        return df_links, manifest_envelope

    def validate_downstream_handshake_integrity(
        self,
        df_s05: Optional[pd.DataFrame] = None,
        df_s06: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Validates composite foreign-key referential integrity and version pinning:
        1. S05 links: every (project_id, schedule_version, activity_id) MUST exist in schedule_activities.parquet.
        2. S06 links: every (project_id, event_id, revision_id) MUST exist in delay_events.parquet.
        
        Raises DownstreamHandshakeError if any dangling key or version mismatch is found.
        """
        act_path = os.path.join(self.parquet_dir, "schedule_activities.parquet")
        dly_path = os.path.join(self.parquet_dir, "delay_events.parquet")

        if not os.path.exists(act_path):
            raise DownstreamHandshakeError(f"R4 Fail-Closed: Required activity table missing: '{act_path}'.")
        if not os.path.exists(dly_path):
            raise DownstreamHandshakeError(f"R4 Fail-Closed: Required delay event table missing: '{dly_path}'.")

        con = duckdb.connect()
        try:
            df_act = con.execute(f"SELECT project_id, schedule_version, activity_id FROM read_parquet('{act_path}')").fetch_df()
            df_dly = con.execute(f"SELECT project_id, event_id, revision_id FROM read_parquet('{dly_path}')").fetch_df()
        finally:
            con.close()

        # Build valid composite key sets
        valid_s05_keys = set(zip(
            df_act["project_id"].astype(str),
            df_act["schedule_version"].astype(str),
            df_act["activity_id"].astype(str),
        ))

        # F5: Strict revision_id in delay_events (no fillna(1) fallback)
        if df_dly["revision_id"].isna().any():
            raise DownstreamHandshakeError("F5 Violation: delay_events table contains null revision_id.")

        valid_s06_keys = set()
        for idx, r in df_dly.iterrows():
            rev_val = validate_and_parse_revision_id(r["revision_id"], context=f"delay_events source row {idx}")
            valid_s06_keys.add((str(r["project_id"]), str(r["event_id"]), rev_val))

        results = {
            "s05_validation_status": "SKIPPED",
            "s05_links_validated": 0,
            "s05_dangling_keys": [],
            "s06_validation_status": "SKIPPED",
            "s06_links_validated": 0,
            "s06_dangling_keys": [],
            "overall_integrity_passed": True,
            "lifecycle_status": "PRE_FLIGHT_EMITTED",
        }

        # R4 Package Hash Verification: S05 Quality Inspection
        s05_parquet_path = os.path.join(self.parquet_dir, "quality_inspection_schedule_links.parquet")
        s05_manifest_path = os.path.join(self.parquet_dir, "quality_inspection_schedule_links_manifest.json")
        if df_s05 is not None:
            if not os.path.exists(s05_manifest_path):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError("R4 Fail-Closed: S05 manifest file is missing.")
            if not os.path.exists(s05_parquet_path):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError("R4 Fail-Closed: S05 package file is missing.")
            with open(s05_manifest_path, "r") as mf:
                try:
                    m5 = json.load(mf)
                except Exception as e:
                    results["overall_integrity_passed"] = False
                    raise DownstreamHandshakeError(f"R4 Fail-Closed: S05 manifest is malformed JSON: {e}")
            expected_hash = m5.get("package_sha256")
            if not expected_hash or not isinstance(expected_hash, str) or len(expected_hash.strip()) != 64:
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Fail-Closed: S05 manifest has missing, empty, or malformed 'package_sha256' reference ({expected_hash!r})."
                )
            actual_hash = sha256_file(s05_parquet_path)
            if actual_hash != expected_hash:
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Violation: S05 package SHA-256 mismatch! Manifest expected {expected_hash}, got {actual_hash}. Emitted package has been tampered with."
                )
            if m5.get("record_count") != len(df_s05):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Violation: S05 record count mismatch with manifest ({m5.get('record_count')} vs {len(df_s05)})."
                )

        # R4 Package Hash Verification: S06 Claims Handshake
        s06_parquet_path = os.path.join(self.parquet_dir, "formal_claims_delay_links.parquet")
        s06_manifest_path = os.path.join(self.parquet_dir, "formal_claims_delay_links_manifest.json")
        if df_s06 is not None:
            if not os.path.exists(s06_manifest_path):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError("R4 Fail-Closed: S06 manifest file is missing.")
            if not os.path.exists(s06_parquet_path):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError("R4 Fail-Closed: S06 package file is missing.")
            with open(s06_manifest_path, "r") as mf:
                try:
                    m6 = json.load(mf)
                except Exception as e:
                    results["overall_integrity_passed"] = False
                    raise DownstreamHandshakeError(f"R4 Fail-Closed: S06 manifest is malformed JSON: {e}")
            expected_hash = m6.get("package_sha256")
            if not expected_hash or not isinstance(expected_hash, str) or len(expected_hash.strip()) != 64:
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Fail-Closed: S06 manifest has missing, empty, or malformed 'package_sha256' reference ({expected_hash!r})."
                )
            actual_hash = sha256_file(s06_parquet_path)
            if actual_hash != expected_hash:
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Violation: S06 package SHA-256 mismatch! Manifest expected {expected_hash}, got {actual_hash}. Emitted package has been tampered with."
                )
            if m6.get("record_count") != len(df_s06):
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"R4 Violation: S06 record count mismatch with manifest ({m6.get('record_count')} vs {len(df_s06)})."
                )

        # Validate S05 links
        if df_s05 is not None and not df_s05.empty:
            dangling_s05 = []
            for _, r in df_s05.iterrows():
                key = (str(r["project_id"]), str(r["schedule_version"]), str(r["activity_id"]))
                if key not in valid_s05_keys:
                    dangling_s05.append(key)

            results["s05_links_validated"] = len(df_s05)
            if dangling_s05:
                results["s05_validation_status"] = "FAILED"
                results["s05_dangling_keys"] = dangling_s05
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"S05 Quality Handshake integrity failed: {len(dangling_s05)} dangling composite keys found: {dangling_s05[:3]}"
                )
            else:
                results["s05_validation_status"] = "PASSED"

        # Validate S06 links
        if df_s06 is not None and not df_s06.empty:
            if "revision_id" not in df_s06.columns:
                raise DownstreamHandshakeError(
                    "F5 Violation: S06 link table missing mandatory 'revision_id' column; silent fallback rejected."
                )
            dangling_s06 = []
            for idx, r in df_s06.iterrows():
                # F5/R2: Strict revision_id integrality validation
                rev_val = validate_and_parse_revision_id(r["revision_id"], context=f"S06 validation row {idx}")
                key = (str(r["project_id"]), str(r["event_id"]), rev_val)
                if key not in valid_s06_keys:
                    dangling_s06.append(key)

            results["s06_links_validated"] = len(df_s06)
            if dangling_s06:
                results["s06_validation_status"] = "FAILED"
                results["s06_dangling_keys"] = dangling_s06
                results["overall_integrity_passed"] = False
                raise DownstreamHandshakeError(
                    f"S06 Claims Handshake integrity failed: {len(dangling_s06)} dangling composite keys found: {dangling_s06[:3]}"
                )
            else:
                results["s06_validation_status"] = "PASSED"

        # R4: Transition lifecycle status to POST_VALIDATION_CERTIFIED and record receipt
        if results["overall_integrity_passed"]:
            receipt_time = datetime.now(timezone.utc).isoformat()
            results["lifecycle_status"] = "POST_VALIDATION_CERTIFIED"
            results["receipt_timestamp_utc"] = receipt_time

            if os.path.exists(s05_manifest_path):
                with open(s05_manifest_path, "r") as mf:
                    m5_data = json.load(mf)
                m5_data["lifecycle_status"] = "POST_VALIDATION_CERTIFIED"
                m5_data["receipt_timestamp_utc"] = receipt_time
                with open(s05_manifest_path, "w") as mf:
                    json.dump(m5_data, mf, indent=2)

            if os.path.exists(s06_manifest_path):
                with open(s06_manifest_path, "r") as mf:
                    m6_data = json.load(mf)
                m6_data["lifecycle_status"] = "POST_VALIDATION_CERTIFIED"
                m6_data["receipt_timestamp_utc"] = receipt_time
                with open(s06_manifest_path, "w") as mf:
                    json.dump(m6_data, mf, indent=2)

        return results

    def publish_all_handshake_links(self) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Emits and persists both S05 and S06 handshake tables into data/parquet/,
        verifying 100% composite referential integrity and generating package manifest envelopes.
        """
        s05_out = os.path.join(self.parquet_dir, "quality_inspection_schedule_links.parquet")
        s06_out = os.path.join(self.parquet_dir, "formal_claims_delay_links.parquet")

        df_s05, manifest_s05 = self.emit_s05_quality_inspection_links(output_path=s05_out)
        df_s06, manifest_s06 = self.emit_s06_adjudication_claim_links(output_path=s06_out)

        integrity_res = self.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_s06)
        integrity_res["manifest_s05"] = manifest_s05
        integrity_res["manifest_s06"] = manifest_s06
        return df_s05, df_s06, integrity_res


if __name__ == "__main__":
    service = HandshakeEmitterService()
    df5, df6, res = service.publish_all_handshake_links()
    print(f"Emitted {len(df5)} S05 links -> {res['s05_validation_status']}")
    print(f"Emitted {len(df6)} S06 links -> {res['s06_validation_status']}")
    print("Handshake publish successful!")
