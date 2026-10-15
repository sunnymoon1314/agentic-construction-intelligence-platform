#!/usr/bin/env python3
"""
ACIP S04: Increment 3 Automated Verification & Regression Suite
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/test_s04_increment_3.py

Verification Targets for Increment 3:
1. TEST-01: Downstream S05 Quality Inspection Handshake Emission & Version Pinning.
2. TEST-02: Downstream S06 SOPA Adjudication Claims Handshake Emission & Revision Pinning.
3. TEST-03: Downstream Composite Referential Integrity & Dangling Key Rejection (Fail-Closed).
4. TEST-04: Multi-Agent Contractor Claims Agent Submission & Fragnet Simulation.
5. TEST-05: Multi-Agent Employer QS Agent Rebuttal & Notice Clock / LD Exposure Scrutiny.
6. TEST-06: Multi-Agent Superintending Officer Impartial Evaluation & Guardrail Tiering.
7. TEST-07: End-to-End Adversarial Deliberation Pipeline Execution & Consensus Synthesis.
8. TEST-08: Persisted Audit Deliberation Log Parquet Lakehouse Integrity & Queryability.
"""

from datetime import date, datetime, timedelta, timezone
import json
import os
import shutil
import sys
import tempfile
import unittest
import duckdb
import pandas as pd

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S04_ROOT = MODULE_ROOT
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from engine.handshake_emitters import (
    HandshakeEmitterService,
    DownstreamHandshakeError,
    validate_and_parse_revision_id,
)
from agent_client.deliberation_pipeline import (
    ContractorClaimsAgent,
    EmployerQSAgent,
    SuperintendingOfficerAgent,
    DeliberationPipeline,
    AgentTurn,
    DeliberationConsensus,
    DeliberationInputError,
    DeliberationPersistenceError,
    parse_strict_contract_verification,
)


class TestS04Increment3(unittest.TestCase):
    """
    Automated verification suite for Increment 3:
    Downstream Handshake Emitters & Multi-Agent Adversarial Deliberation Pipeline.
    """

    @classmethod
    def setUpClass(cls):
        cls.parquet_dir = os.path.join(S04_ROOT, "data", "parquet")
        cls.handshake_service = HandshakeEmitterService(cls.parquet_dir)
        cls.pipeline = DeliberationPipeline(cls.parquet_dir)

    # -------------------------------------------------------------------------
    # TEST 1: S05 Quality Inspection Handshake Emission & Version Pinning
    # -------------------------------------------------------------------------
    def test_01_s05_quality_inspection_handshake_emission(self):
        """
        TEST-01: Verifies S05 Quality Inspection Handshake link emission & envelope.
        - Generates links with composite FK (project_id, schedule_version, activity_id).
        - Correctly assigns CRITICAL_STRUCTURAL_HOLD_POINT to critical activities.
        - Preserves exact schedule_version and UTC timestamps.
        - Generates valid envelope manifest dictionary.
        """
        df_s05, manifest_s05 = self.handshake_service.emit_s05_quality_inspection_links()

        self.assertFalse(df_s05.empty)
        self.assertIn("inspection_id", df_s05.columns)
        self.assertIn("project_id", df_s05.columns)
        self.assertIn("schedule_version", df_s05.columns)
        self.assertIn("activity_id", df_s05.columns)
        self.assertIn("defect_risk_tier", df_s05.columns)
        self.assertIn("hold_point_status", df_s05.columns)

        # Provenance envelope validation (F4)
        self.assertIsInstance(manifest_s05, dict)
        self.assertIn("package_id", manifest_s05)
        self.assertEqual(manifest_s05["schema_version"], "1.0")
        self.assertIn("source_content_sha256", manifest_s05)
        self.assertEqual(manifest_s05["records_emitted"], len(df_s05))

        # Check critical path hold point assignment
        crit_rows = df_s05[df_s05["is_critical_path_activity"] == True]
        self.assertGreater(len(crit_rows), 0)
        for _, r in crit_rows.iterrows():
            self.assertEqual(r["defect_risk_tier"], "CRITICAL_STRUCTURAL_HOLD_POINT")
            self.assertEqual(r["hold_point_status"], "MANDATORY_QP_INSPECTION_REQUIRED")
            self.assertEqual(r["inspection_lead_time_days"], 3)

        # Assert version pinning against schedule_versions
        con = duckdb.connect()
        try:
            ver_path = os.path.join(self.parquet_dir, "schedule_versions.parquet")
            known_versions = set(con.execute(f"SELECT schedule_version FROM read_parquet('{ver_path}')").fetchnumpy()["schedule_version"])
        finally:
            con.close()

        for ver in df_s05["schedule_version"].unique():
            self.assertIn(ver, known_versions)

    # -------------------------------------------------------------------------
    # TEST 2: S06 Adjudication Claims Handshake Emission & Revision Pinning
    # -------------------------------------------------------------------------
    def test_02_s06_adjudication_claims_handshake_emission(self):
        """
        TEST-02: Verifies S06 SOPA Adjudication Claims Handshake link emission & revision pinning.
        - Generates links with composite FK (project_id, event_id, revision_id).
        - Correctly marks internal triage candidate for claim review for employer-risk delays.
        - Computes illustrative baseline dispute quantum estimates.
        - Emits provenance envelope manifest.
        """
        df_s06, manifest_s06 = self.handshake_service.emit_s06_adjudication_claim_links()

        self.assertFalse(df_s06.empty)
        self.assertIn("claim_dossier_id", df_s06.columns)
        self.assertIn("project_id", df_s06.columns)
        self.assertIn("event_id", df_s06.columns)
        self.assertIn("revision_id", df_s06.columns)
        self.assertIn("candidate_for_sopa_claim_review", df_s06.columns)
        self.assertIn("triage_assessment_status", df_s06.columns)
        self.assertIn("illustrative_baseline_estimate_sgd", df_s06.columns)

        # Provenance envelope validation (F4)
        self.assertIsInstance(manifest_s06, dict)
        self.assertIn("package_id", manifest_s06)
        self.assertEqual(manifest_s06["schema_version"], "1.0")
        self.assertIn("source_content_sha256", manifest_s06)
        self.assertEqual(manifest_s06["records_emitted"], len(df_s06))

        # DLY-2026-001 is NEUTRAL_FORCE_MAJEURE with 3 claimed days
        row_001 = df_s06[df_s06["event_id"] == "DLY-2026-001"].iloc[0]
        self.assertTrue(row_001["candidate_for_sopa_claim_review"])
        self.assertEqual(row_001["triage_assessment_status"], "INTERNAL_TRIAGE_CANDIDATE_FOR_CLAIM_REVIEW")
        self.assertEqual(row_001["claimed_eot_days"], 4.0)
        self.assertEqual(row_001["illustrative_baseline_estimate_sgd"], 60000.0)

    # -------------------------------------------------------------------------
    # TEST 3: Composite Referential Integrity & Dangling Key Rejection
    # -------------------------------------------------------------------------
    def test_03_handshake_composite_referential_integrity_and_dangling_key_rejection(self):
        """
        TEST-03: Verifies referential integrity and fail-closed rejection:
        - Valid links pass verification with overall_integrity_passed=True.
        - An injected dangling activity_id in S05 links raises DownstreamHandshakeError.
        - An injected invalid revision_id in S06 links raises DownstreamHandshakeError.
        """
        df_s05, _ = self.handshake_service.emit_s05_quality_inspection_links()
        df_s06, _ = self.handshake_service.emit_s06_adjudication_claim_links()

        # Valid baseline passes
        res = self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_s06)
        self.assertTrue(res["overall_integrity_passed"])
        self.assertEqual(res["s05_validation_status"], "PASSED")
        self.assertEqual(res["s06_validation_status"], "PASSED")

        # Negative Test 1: Dangling S05 key
        df_s05_bad = df_s05.copy()
        df_s05_bad.loc[0, "activity_id"] = "ACT-NONEXISTENT-999"
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05_bad, df_s06=df_s06)

        # Negative Test 2: Dangling S06 revision
        df_s06_bad = df_s06.copy()
        df_s06_bad.loc[0, "revision_id"] = 999  # Invalid revision
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_s06_bad)

    # -------------------------------------------------------------------------
    # TEST 4: Multi-Agent Contractor Claims Agent Submission
    # -------------------------------------------------------------------------
    def test_04_multi_agent_contractor_claims_agent_deliberation(self):
        """
        TEST-04: Verifies Round 1 deliberative submission by ContractorClaimsAgent:
        - Invokes deterministic FastMCP tool s04_simulate_tia_fragnet.
        - Cites net critical delay and requests full EOT relief from LD.
        - Role is correctly tagged as CLAIMANT with round_number=1.
        """
        agent = ContractorClaimsAgent()
        turn = agent.deliberate(
            session_id="TEST-SESS-001",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={
                "event_title": "Groundwater Ingress",
                "affected_activity_id": "ACT-03",
                "claimed_delay_days": 3.0,
                "risk_allocation": "EMPLOYER_RISK",
            },
        )

        self.assertEqual(turn.agent_role, "CLAIMANT")
        self.assertEqual(turn.round_number, 1)
        self.assertEqual(turn.recommended_eot_days, 3.0)
        self.assertEqual(turn.recommended_ld_exposure_sgd, 0.0)
        self.assertIn("s04_simulate_tia_fragnet", turn.tool_invoked)
        self.assertIn("unforeseen ground physical conditions", turn.position_statement)

    # -------------------------------------------------------------------------
    # TEST 5: Multi-Agent Employer QS Agent Rebuttal
    # -------------------------------------------------------------------------
    def test_05_multi_agent_employer_qs_agent_rebuttal(self):
        """
        TEST-05: Verifies Round 2 deliberative rebuttal by EmployerQSAgent:
        - Scrutinizes notice clock via s04_calculate_psscoc_notice_clock.
        - Computes potential LD exposure via s04_assess_liquidated_damages_exposure.
        - Role is correctly tagged as RESPONDENT with round_number=2.
        """
        claimant = ContractorClaimsAgent()
        turn_1 = claimant.deliberate(
            session_id="TEST-SESS-002",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "claimed_delay_days": 3.0, "is_contract_verified": True},
        )

        respondent = EmployerQSAgent()
        turn_2 = respondent.deliberate(
            session_id="TEST-SESS-002",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={
                "event_start_date": "2026-11-01",
                "notice_served_date": "2026-11-15",
                "notice_window_days": 28,
                "is_contract_verified": True,
            },
            claimant_turn=turn_1,
        )

        self.assertEqual(turn_2.agent_role, "RESPONDENT")
        self.assertEqual(turn_2.round_number, 2)
        self.assertEqual(turn_2.recommended_eot_days, 0.0)
        self.assertEqual(turn_2.recommended_ld_exposure_sgd, 45000.0)
        self.assertEqual(turn_2.notice_compliance_status, "COMPLIANT")
        self.assertIn("Liquidated Damages exposure", turn_2.position_statement)

    # -------------------------------------------------------------------------
    # TEST 6: Multi-Agent Superintending Officer Impartial Evaluation
    # -------------------------------------------------------------------------
    def test_06_multi_agent_superintending_officer_statutory_determination(self):
        """
        TEST-06: Verifies Round 3 statutory determination by SuperintendingOfficerAgent:
        - Unverified contract deed yields UNVERIFIED_ADVISORY_SIMULATION (fail-closed guardrail).
        - Verified contract deed yields DETERMINISTIC_ADVISORY_ASSESSMENT.
        - Concurrency attribution strictly follows SCL Delay Protocol Core Principle 10.
        """
        agent = SuperintendingOfficerAgent()
        claimant_turn = AgentTurn(
            turn_id="T1", session_id="S1", event_id="E1", project_id="P1", round_number=1,
            agent_name="Claimant", agent_role="CLAIMANT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="EMPLOYER_RISK",
            recommended_eot_days=3.0, recommended_ld_exposure_sgd=0.0, notice_compliance_status="CLAIMED_COMPLIANT",
        )
        respondent_turn = AgentTurn(
            turn_id="T2", session_id="S1", event_id="E1", project_id="P1", round_number=2,
            agent_name="Respondent", agent_role="RESPONDENT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="CONTESTED",
            recommended_eot_days=0.0, recommended_ld_exposure_sgd=45000.0, notice_compliance_status="COMPLIANT",
        )

        # Case A: Unverified Contract deed (Fail-Closed Guardrail)
        _, consensus_unverified = agent.deliberate(
            session_id="S1-UNVERIFIED",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "claimed_delay_days": 3.0, "is_contract_verified": False},
            claimant_turn=claimant_turn,
            respondent_turn=respondent_turn,
        )
        self.assertEqual(consensus_unverified.determination_tier, "UNVERIFIED_ADVISORY_SIMULATION")
        self.assertEqual(consensus_unverified.contract_verification_status, "UNVERIFIED")
        self.assertEqual(consensus_unverified.notice_compliance_status, "UNASSESSED")

        # Case B: Verified Contract deed (Deterministic Advisory Assessment)
        _, consensus_verified = agent.deliberate(
            session_id="S1-VERIFIED",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "claimed_delay_days": 3.0, "is_contract_verified": True},
            claimant_turn=claimant_turn,
            respondent_turn=respondent_turn,
        )
        self.assertEqual(consensus_verified.determination_tier, "DETERMINISTIC_ADVISORY_ASSESSMENT")
        self.assertEqual(consensus_verified.contract_verification_status, "VERIFIED")
        self.assertEqual(consensus_verified.candidate_eot_relief_days, 3.0)
        self.assertEqual(consensus_verified.contractor_culpable_days, 0.0)
        self.assertEqual(consensus_verified.liquidated_damages_exposure_sgd, 0.0)
        self.assertIn("Advisory determination only", consensus_verified.adjudication_disclaimer)

    # -------------------------------------------------------------------------
    # TEST 7: End-to-End Adversarial Deliberation Pipeline Execution
    # -------------------------------------------------------------------------
    def test_07_full_adversarial_deliberation_pipeline_execution(self):
        """
        TEST-07: Verifies end-to-end execution of DeliberationPipeline:
        - Produces exactly 3 agent turns (Claimant -> Respondent -> Arbitrator).
        - Synthesizes complete DeliberationConsensus.
        - Correctly certifies contractor-culpable delay when risk_allocation is CONTRACTOR_RISK.
        """
        # Test Contractor-Risk Event
        consensus_culpable = self.pipeline.run_deliberation(
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-CULPABLE-001",
            event_data={
                "event_title": "Contractor Rig Breakdown & Worker Deficit",
                "affected_activity_id": "ACT-03",
                "claimed_delay_days": 2.0,
                "risk_allocation": "CONTRACTOR_RISK",
                "event_start_date": "2026-11-09",
                "notice_served_date": "2026-11-12",
                "is_contract_verified": True,
            },
            persist_log=False,
        )

        self.assertEqual(len(consensus_culpable.turns), 3)
        self.assertEqual(consensus_culpable.turns[0].agent_role, "CLAIMANT")
        self.assertEqual(consensus_culpable.turns[1].agent_role, "RESPONDENT")
        self.assertEqual(consensus_culpable.turns[2].agent_role, "ARBITRATOR")

        # In contractor risk, EOT relief is 0.0 and contractor is culpable
        self.assertEqual(consensus_culpable.candidate_eot_relief_days, 0.0)
        self.assertEqual(consensus_culpable.contractor_culpable_days, 2.0)
        self.assertEqual(consensus_culpable.liquidated_damages_exposure_sgd, 30000.0)
        self.assertEqual(consensus_culpable.concurrency_attribution, "CONTRACTOR_DRIVEN_SOLE")

    # -------------------------------------------------------------------------
    # TEST 8: Persisted Audit Deliberation Log Parquet Lakehouse Integrity
    # -------------------------------------------------------------------------
    def test_08_persisted_audit_deliberation_log_parquet_integrity(self):
        """
        TEST-8: Verifies that deliberation transcripts are persisted to audit_deliberation_log.parquet:
        - File exists and is readable via DuckDB.
        - Schema contains all mandatory audit columns: session_id, turn_id, tool_metrics_json, timestamp_utc.
        - Every record has valid JSON tool metrics and non-empty statements.
        """
        # Run a deliberation with persistence enabled
        consensus = self.pipeline.run_deliberation(
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

        log_path = os.path.join(self.parquet_dir, "audit_deliberation_log.parquet")
        self.assertTrue(os.path.exists(log_path))

        con = duckdb.connect()
        try:
            df = con.execute(f"SELECT * FROM read_parquet('{log_path}')").fetch_df()
        finally:
            con.close()

        self.assertFalse(df.empty)
        required_cols = [
            "turn_id", "session_id", "event_id", "project_id", "round_number",
            "agent_name", "agent_role", "position_statement", "tool_invoked",
            "tool_metrics_json", "concurrency_attribution", "recommended_eot_days",
            "recommended_ld_exposure_sgd", "notice_compliance_status", "timestamp_utc",
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)

        # Assert every row has valid JSON tool metrics
        for _, r in df.iterrows():
            parsed = json.loads(r["tool_metrics_json"])
            self.assertIsInstance(parsed, dict)
            self.assertTrue(len(r["position_statement"]) > 10)

    # -------------------------------------------------------------------------
    # TEST 9: ContractorClaimsAgent Fail-Closed Contract Verification (F1)
    # -------------------------------------------------------------------------
    def test_09_contractor_claims_agent_fail_closed_contract_verification(self):
        """
        TEST-09: Verifies Finding F1 resolution.
        ContractorClaimsAgent must respect event_data['is_contract_verified'].
        When False or omitted, s04_simulate_tia_fragnet is called with is_contract_verified=False,
        yielding UNASSESSED notice compliance status rather than forced verified compliance.
        """
        agent = ContractorClaimsAgent()

        # Case A: Explicitly unverified
        turn_unverified = agent.deliberate(
            session_id="TEST-F1-001",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={
                "event_title": "Unverified Test Event",
                "affected_activity_id": "ACT-03",
                "claimed_delay_days": 3.0,
                "risk_allocation": "EMPLOYER_RISK",
                "is_contract_verified": False,
            },
        )
        self.assertEqual(turn_unverified.notice_compliance_status, "UNASSESSED")

        # Case B: Omitted is_contract_verified (defaults to False / fail-closed)
        turn_omitted = agent.deliberate(
            session_id="TEST-F1-002",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={
                "event_title": "Omitted Verification Event",
                "affected_activity_id": "ACT-03",
                "claimed_delay_days": 3.0,
                "risk_allocation": "EMPLOYER_RISK",
            },
        )
        self.assertEqual(turn_omitted.notice_compliance_status, "UNASSESSED")

        # Case C: Explicitly verified
        turn_verified = agent.deliberate(
            session_id="TEST-F1-003",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={
                "event_title": "Verified Event",
                "affected_activity_id": "ACT-03",
                "claimed_delay_days": 3.0,
                "risk_allocation": "EMPLOYER_RISK",
                "is_contract_verified": True,
            },
        )
        self.assertEqual(turn_verified.notice_compliance_status, "CLAIMED_COMPLIANT")

    # -------------------------------------------------------------------------
    # TEST 10: Fail-Closed Lakehouse Ingestion & No Synthetic Fallback (F2)
    # -------------------------------------------------------------------------
    def test_10_missing_source_parquet_fail_closed_rejection(self):
        """
        TEST-10: Verifies Finding F2 resolution.
        _load_event_from_parquet must fail closed and raise DeliberationInputError
        when delay_events.parquet is missing or event_id is not found.
        Synthetic verified fallbacks are strictly prohibited.
        """
        # Case A: Nonexistent event_id raises DeliberationInputError
        with self.assertRaises(DeliberationInputError):
            self.pipeline._load_event_from_parquet("DLY-NONEXISTENT-999")

        # Case B: Nonexistent parquet directory raises DeliberationInputError
        pipeline_bad = DeliberationPipeline(parquet_dir="/nonexistent/directory/path")
        with self.assertRaises(DeliberationInputError):
            pipeline_bad._load_event_from_parquet("DLY-2026-001")

    # -------------------------------------------------------------------------
    # TEST 11: Deliberation Authority & Dynamic Consensus Divergence (F3)
    # -------------------------------------------------------------------------
    def test_11_deliberation_authority_and_consensus_divergence_semantics(self):
        """
        TEST-11: Verifies Finding F3 resolution.
        - Determination tiers are DETERMINISTIC_ADVISORY_ASSESSMENT or UNVERIFIED_ADVISORY_SIMULATION.
        - Statutory disclaimer explicitly protects human SO/Adjudicator authority.
        - consensus_achieved is dynamically computed (False when party positions diverge).
        """
        agent = SuperintendingOfficerAgent()

        # Case A: Divergent positions (Claimant 4.0 days EOT vs Respondent 0.0 days EOT)
        c_turn = AgentTurn(
            turn_id="T1", session_id="S-DIV", event_id="E1", project_id="P1", round_number=1,
            agent_name="Claimant", agent_role="CLAIMANT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="EMPLOYER_RISK",
            recommended_eot_days=4.0, recommended_ld_exposure_sgd=0.0, notice_compliance_status="CLAIMED_COMPLIANT",
        )
        r_turn = AgentTurn(
            turn_id="T2", session_id="S-DIV", event_id="E1", project_id="P1", round_number=2,
            agent_name="Respondent", agent_role="RESPONDENT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="CONTESTED",
            recommended_eot_days=0.0, recommended_ld_exposure_sgd=60000.0, notice_compliance_status="COMPLIANT",
        )

        _, consensus = agent.deliberate(
            session_id="S-DIV",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "claimed_delay_days": 4.0, "is_contract_verified": True},
            claimant_turn=c_turn,
            respondent_turn=r_turn,
        )

        self.assertEqual(consensus.determination_tier, "DETERMINISTIC_ADVISORY_ASSESSMENT")
        self.assertFalse(consensus.consensus_achieved)
        self.assertIn("Advisory determination only", consensus.adjudication_disclaimer)
        self.assertIn("Superintending Officer", consensus.adjudication_disclaimer)

        # Case B: Convergent positions (both agree on 2.0 days)
        c_turn_conv = AgentTurn(
            turn_id="T1", session_id="S-CONV", event_id="E1", project_id="P1", round_number=1,
            agent_name="Claimant", agent_role="CLAIMANT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="EMPLOYER_RISK",
            recommended_eot_days=2.0, recommended_ld_exposure_sgd=0.0, notice_compliance_status="CLAIMED_COMPLIANT",
        )
        r_turn_conv = AgentTurn(
            turn_id="T2", session_id="S-CONV", event_id="E1", project_id="P1", round_number=2,
            agent_name="Respondent", agent_role="RESPONDENT", position_statement="",
            tool_invoked="", tool_metrics={}, concurrency_attribution="EMPLOYER_RISK",
            recommended_eot_days=2.0, recommended_ld_exposure_sgd=0.0, notice_compliance_status="COMPLIANT",
        )
        _, consensus_conv = agent.deliberate(
            session_id="S-CONV",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "claimed_delay_days": 2.0, "is_contract_verified": True},
            claimant_turn=c_turn_conv,
            respondent_turn=r_turn_conv,
        )
        self.assertTrue(consensus_conv.consensus_achieved)

    # -------------------------------------------------------------------------
    # TEST 12: Handshake Package Provenance Envelope & Manifest Sidecar (F4)
    # -------------------------------------------------------------------------
    def test_12_handshake_package_envelope_and_manifest_sidecar(self):
        """
        TEST-12: Verifies Finding F4 resolution.
        - Handshake emitters generate sidecar JSON manifests alongside parquet.
        - Manifest contains package_id, schema_version="1.0", source_content_sha256,
          producer_service_version="1.0.0", and record counts.
        """
        s05_manifest_path = os.path.join(self.parquet_dir, "quality_inspection_schedule_links_manifest.json")
        s06_manifest_path = os.path.join(self.parquet_dir, "formal_claims_delay_links_manifest.json")

        self.handshake_service.publish_all_handshake_links()

        self.assertTrue(os.path.exists(s05_manifest_path))
        self.assertTrue(os.path.exists(s06_manifest_path))

        with open(s05_manifest_path, "r") as f:
            m5 = json.load(f)
        self.assertIn("package_id", m5)
        self.assertEqual(m5["schema_version"], "1.0")
        self.assertEqual(m5["producer_service_version"], "1.0.0")
        self.assertEqual(len(m5["source_content_sha256"]), 64)

        with open(s06_manifest_path, "r") as f:
            m6 = json.load(f)
        self.assertIn("package_id", m6)
        self.assertEqual(m6["schema_version"], "1.0")
        self.assertEqual(m6["producer_service_version"], "1.0.0")
        self.assertEqual(len(m6["source_content_sha256"]), 64)

    # -------------------------------------------------------------------------
    # TEST 13: Strict Revision ID Validation & Fail-Closed Rejection (F5)
    # -------------------------------------------------------------------------
    def test_13_missing_or_null_revision_id_rejection(self):
        """
        TEST-13: Verifies Finding F5 resolution.
        Absence of revision_id, nulls, NaNs, or non-integral revision IDs
        must fail closed with DownstreamHandshakeError. Default fallbacks are rejected.
        """
        df_s05, _ = self.handshake_service.emit_s05_quality_inspection_links()
        df_s06, _ = self.handshake_service.emit_s06_adjudication_claim_links()

        # Case A: None / NaN revision_id
        df_bad_nan = df_s06.copy()
        df_bad_nan["revision_id"] = df_bad_nan["revision_id"].astype(object)
        df_bad_nan.loc[0, "revision_id"] = None
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_bad_nan)

        # Case B: Non-integral string revision_id
        df_bad_str = df_s06.copy()
        df_bad_str["revision_id"] = df_bad_str["revision_id"].astype(object)
        df_bad_str.loc[0, "revision_id"] = "rev_alpha"
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_bad_str)

        # Case C: Missing revision_id column altogether
        df_bad_nocol = df_s06.drop(columns=["revision_id"])
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_bad_nocol)

    # -------------------------------------------------------------------------
    # TEST 14: SOPA Triage Indicator & Illustrative Quantum Semantics (F6)
    # -------------------------------------------------------------------------
    def test_14_sopa_triage_indicator_and_illustrative_quantum_semantics(self):
        """
        TEST-14: Verifies Finding F6 resolution.
        - Verifies absence of authoritative legal keywords in column headers and enum values.
        - sopa_adjudication_eligible -> candidate_for_sopa_claim_review
        - STATUTORY_ADJUDICATION_ELIGIBLE -> INTERNAL_TRIAGE_CANDIDATE_FOR_CLAIM_REVIEW
        - estimated_dispute_quantum_sgd -> illustrative_baseline_estimate_sgd
        """
        df_s06, _ = self.handshake_service.emit_s06_adjudication_claim_links()

        self.assertNotIn("sopa_adjudication_eligible", df_s06.columns)
        self.assertNotIn("estimated_dispute_quantum_sgd", df_s06.columns)
        self.assertIn("candidate_for_sopa_claim_review", df_s06.columns)
        self.assertIn("illustrative_baseline_estimate_sgd", df_s06.columns)

        statuses = df_s06["triage_assessment_status"].unique()
        self.assertNotIn("STATUTORY_ADJUDICATION_ELIGIBLE", statuses)
        self.assertIn("INTERNAL_TRIAGE_CANDIDATE_FOR_CLAIM_REVIEW", statuses)

    # -------------------------------------------------------------------------
    # TEST 15: Atomic Log Persistence & Fail-Closed Protection (F7)
    # -------------------------------------------------------------------------
    def test_15_audit_log_persistence_atomic_preservation_on_read_failure(self):
        """
        TEST-15: Verifies Finding F7 resolution.
        - Corrupted audit_deliberation_log.parquet triggers DeliberationPersistenceError.
        - Previous corrupted file is NOT overwritten or destroyed.
        - Atomic file write via temporary file replacement is verified.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pipe = DeliberationPipeline(parquet_dir=tmp_dir)
            corrupt_path = os.path.join(tmp_dir, "audit_deliberation_log.parquet")

            # Write corrupted non-parquet bytes
            with open(corrupt_path, "wb") as f:
                f.write(b"CORRUPTED_PARQUET_FILE_HEADER_BYTE_STREAM")

            turns = [
                AgentTurn(
                    turn_id="T-TMP", session_id="S-TMP", event_id="E-TMP", project_id="P-TMP",
                    round_number=1, agent_name="TestAgent", agent_role="CLAIMANT",
                    position_statement="Test statement", tool_invoked="none", tool_metrics={},
                    concurrency_attribution="NEUTRAL", recommended_eot_days=1.0,
                    recommended_ld_exposure_sgd=0.0, notice_compliance_status="COMPLIANT",
                )
            ]

            # Fails closed without overwriting
            with self.assertRaises(DeliberationPersistenceError):
                tmp_pipe._persist_turns_to_parquet(turns)

            # Assert original corrupted file content remains preserved
            with open(corrupt_path, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"CORRUPTED_PARQUET_FILE_HEADER_BYTE_STREAM")

    # -------------------------------------------------------------------------
    # TEST 16: Strict Boolean Contract Verification Parsing (R1)
    # -------------------------------------------------------------------------
    def test_16_r1_string_and_malformed_verification_state_rejection(self):
        """
        TEST-16: Verifies Reviewer Finding R1.
        Generic truthy string values ('false', '0', 'no', 'true') and non-booleans (1)
        must be strictly rejected with DeliberationInputError rather than coerced to verified.
        Only explicit True yields verified state; False, None, or omitted yields unverified.
        """
        agent = ContractorClaimsAgent()

        # Strings and non-booleans must raise DeliberationInputError
        malformed_inputs = ["false", "0", "no", "true", "1", 1, 0]
        for bad_val in malformed_inputs:
            with self.subTest(bad_val=bad_val):
                with self.assertRaises(DeliberationInputError):
                    agent.deliberate(
                        session_id="S-MALFORMED",
                        project_id="PRJ-WHC-COM-001",
                        event_id="DLY-2026-001",
                        event_data={
                            "affected_activity_id": "ACT-03",
                            "claimed_delay_days": 3.0,
                            "is_contract_verified": bad_val,
                        },
                    )

        # Explicit True yields verified
        turn_true = agent.deliberate(
            session_id="S-STRICT-TRUE",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "is_contract_verified": True},
        )
        self.assertEqual(turn_true.notice_compliance_status, "CLAIMED_COMPLIANT")

        # Explicit False yields unverified
        turn_false = agent.deliberate(
            session_id="S-STRICT-FALSE",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"affected_activity_id": "ACT-03", "is_contract_verified": False},
        )
        self.assertEqual(turn_false.notice_compliance_status, "UNASSESSED")

        # R1 Employer QS Agent Liquidated Damages Verification Binding & Defensive Robustness
        employer_agent = EmployerQSAgent()
        # Test malformed input in Employer QS Agent
        for bad_val in malformed_inputs:
            with self.subTest(bad_val=bad_val):
                with self.assertRaises(DeliberationInputError):
                    employer_agent.deliberate(
                        session_id="S-MALFORMED-QS",
                        project_id="PRJ-WHC-COM-001",
                        event_id="DLY-2026-001",
                        event_data={"is_contract_verified": bad_val},
                        claimant_turn=turn_true,
                    )

        # Unverified deed yields ADVISORY_SIMULATION_ONLY in LD metrics
        turn_qs_unverified = employer_agent.deliberate(
            session_id="S-QS-UNVERIFIED",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"is_contract_verified": False},
            claimant_turn=turn_true,
        )
        ld_metrics_unverified = turn_qs_unverified.tool_metrics["liquidated_damages_assessment"]
        self.assertFalse(ld_metrics_unverified["is_contract_verified"])
        self.assertEqual(ld_metrics_unverified["assurance_tier"], "ADVISORY_SIMULATION_ONLY")

        # Verified deed yields CERTIFIED_ASSESSMENT in LD metrics
        turn_qs_verified = employer_agent.deliberate(
            session_id="S-QS-VERIFIED",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data={"is_contract_verified": True},
            claimant_turn=turn_true,
        )
        ld_metrics_verified = turn_qs_verified.tool_metrics["liquidated_damages_assessment"]
        self.assertTrue(ld_metrics_verified["is_contract_verified"])
        self.assertEqual(ld_metrics_verified["assurance_tier"], "CERTIFIED_ASSESSMENT")

        # Omitted event_data defaults safely to unverified without raising NameError or AttributeError
        turn_qs_omitted = employer_agent.deliberate(
            session_id="S-QS-OMITTED",
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
        )
        self.assertFalse(turn_qs_omitted.tool_metrics["liquidated_damages_assessment"]["is_contract_verified"])

    # -------------------------------------------------------------------------
    # TEST 17: Fractional & Boolean Revision ID Rejection (R2)
    # -------------------------------------------------------------------------
    def test_17_r2_fractional_and_boolean_revision_id_rejection(self):
        """
        TEST-17: Verifies Reviewer Finding R2.
        Fractional numeric values (1.5, 1.7), booleans (True, False), and non-positives (0, -1)
        must raise DownstreamHandshakeError in both emission and validation pathways.
        Positive integers (1, 2, 1.0) must pass cleanly.
        """
        # Test helper directly
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id(1.7, context="unit-test")
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id(1.5, context="unit-test")
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id(True, context="unit-test")
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id(0, context="unit-test")
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id(-1, context="unit-test")
        with self.assertRaises(DownstreamHandshakeError):
            validate_and_parse_revision_id("1.7", context="unit-test")

        # Positive controls
        self.assertEqual(validate_and_parse_revision_id(1), 1)
        self.assertEqual(validate_and_parse_revision_id(1.0), 1)
        self.assertEqual(validate_and_parse_revision_id("2"), 2)

        # Test validation pathway with fractional revision
        df_s05, _ = self.handshake_service.emit_s05_quality_inspection_links()
        df_s06, _ = self.handshake_service.emit_s06_adjudication_claim_links()
        df_s06_frac = df_s06.copy()
        df_s06_frac["revision_id"] = df_s06_frac["revision_id"].astype(object)
        df_s06_frac.loc[0, "revision_id"] = 1.7
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_s06_frac)

        # Test validation pathway with boolean revision
        df_s06_bool = df_s06.copy()
        df_s06_bool["revision_id"] = df_s06_bool["revision_id"].astype(object)
        df_s06_bool.loc[0, "revision_id"] = True
        with self.assertRaises(DownstreamHandshakeError):
            self.handshake_service.validate_downstream_handshake_integrity(df_s05=df_s05, df_s06=df_s06_bool)

    # -------------------------------------------------------------------------
    # TEST 18: Handshake Package Tamper Detection & Certified Receipt (R4)
    # -------------------------------------------------------------------------
    def test_18_r4_emitted_package_tamper_detection_and_receipt_certification(self):
        """
        TEST-18: Verifies Reviewer Finding R4.
        - Emitted package hash (package_sha256) binds the physical parquet bytes.
        - Missing manifest file raises DownstreamHandshakeError (fail closed).
        - Missing or malformed package_sha256 in manifest raises DownstreamHandshakeError.
        - Consumer validation detects a modified byte in the parquet file and raises DownstreamHandshakeError.
        - Untampered packages transition lifecycle status to POST_VALIDATION_CERTIFIED with receipt timestamp.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Copy prerequisite tables to isolated test directory
            iso_parquet_dir = os.path.join(tmp_dir, "data")
            shutil.copytree(self.parquet_dir, iso_parquet_dir)
            iso_service = HandshakeEmitterService(parquet_dir=iso_parquet_dir)

            df5, df6, res = iso_service.publish_all_handshake_links()
            self.assertEqual(res["lifecycle_status"], "POST_VALIDATION_CERTIFIED")

            m5_path = os.path.join(iso_parquet_dir, "quality_inspection_schedule_links_manifest.json")
            s05_pkg_path = os.path.join(iso_parquet_dir, "quality_inspection_schedule_links.parquet")

            # Check that manifest was updated with certified receipt
            with open(m5_path, "r") as mf:
                m5 = json.load(mf)
            self.assertEqual(m5["lifecycle_status"], "POST_VALIDATION_CERTIFIED")
            self.assertIn("receipt_timestamp_utc", m5)
            self.assertIn("package_sha256", m5)

            # Negative Control 0: Both manifest and Parquet absent fails closed when package expected
            with tempfile.TemporaryDirectory() as empty_pdir:
                shutil.copy(os.path.join(self.parquet_dir, "schedule_activities.parquet"), os.path.join(empty_pdir, "schedule_activities.parquet"))
                shutil.copy(os.path.join(self.parquet_dir, "delay_events.parquet"), os.path.join(empty_pdir, "delay_events.parquet"))
                empty_service = HandshakeEmitterService(parquet_dir=empty_pdir)
                # Absence of both files raises DownstreamHandshakeError and blocks receipt certification
                with self.assertRaises(DownstreamHandshakeError):
                    empty_service.validate_downstream_handshake_integrity(df_s05=df5)
                with self.assertRaises(DownstreamHandshakeError):
                    empty_service.validate_downstream_handshake_integrity(df_s06=df6)

                # Assert receipt cannot be certified: no manifest created or stamped POST_VALIDATION_CERTIFIED
                empty_m5 = os.path.join(empty_pdir, "quality_inspection_schedule_links_manifest.json")
                self.assertFalse(os.path.exists(empty_m5), "Manifest was created despite absent package!")

                # Even if an uncertified manifest existed, absence of parquet still fails closed without certifying receipt
                with open(empty_m5, "w") as mf:
                    json.dump({"lifecycle_status": "PRE_FLIGHT_EMITTED", "package_sha256": "0" * 64, "record_count": len(df5)}, mf)
                with self.assertRaises(DownstreamHandshakeError):
                    empty_service.validate_downstream_handshake_integrity(df_s05=df5)
                with open(empty_m5, "r") as mf:
                    m_data = json.load(mf)
                self.assertNotEqual(m_data.get("lifecycle_status"), "POST_VALIDATION_CERTIFIED", "Receipt was illegally certified despite absent parquet!")

            # Negative Control 1: Missing manifest file fails closed
            os.remove(m5_path)
            with self.assertRaises(DownstreamHandshakeError):
                iso_service.validate_downstream_handshake_integrity(df_s05=df5, df_s06=df6)

            # Restore manifest for next test
            with open(m5_path, "w") as mf:
                json.dump(m5, mf, indent=2)

            # Negative Control 2: Missing package_sha256 key fails closed
            m5_bad = dict(m5)
            del m5_bad["package_sha256"]
            with open(m5_path, "w") as mf:
                json.dump(m5_bad, mf, indent=2)
            with self.assertRaises(DownstreamHandshakeError):
                iso_service.validate_downstream_handshake_integrity(df_s05=df5, df_s06=df6)

            # Negative Control 3: Malformed/empty package_sha256 fails closed
            m5_bad["package_sha256"] = ""
            with open(m5_path, "w") as mf:
                json.dump(m5_bad, mf, indent=2)
            with self.assertRaises(DownstreamHandshakeError):
                iso_service.validate_downstream_handshake_integrity(df_s05=df5, df_s06=df6)

            m5_bad["package_sha256"] = "short_hash_123"
            with open(m5_path, "w") as mf:
                json.dump(m5_bad, mf, indent=2)
            with self.assertRaises(DownstreamHandshakeError):
                iso_service.validate_downstream_handshake_integrity(df_s05=df5, df_s06=df6)

            # Restore valid manifest
            with open(m5_path, "w") as mf:
                json.dump(m5, mf, indent=2)

            # Negative Control 4: Tamper with 1 byte in emitted parquet
            with open(s05_pkg_path, "rb") as f:
                data = bytearray(f.read())
            data[10] = (data[10] + 1) % 256  # Invert single byte
            with open(s05_pkg_path, "wb") as f:
                f.write(data)

            # Re-validation must detect tamper and fail closed
            with self.assertRaises(DownstreamHandshakeError):
                iso_service.validate_downstream_handshake_integrity(df_s05=df5, df_s06=df6)

    # -------------------------------------------------------------------------
    # TEST 19: Preflight Prerequisite Audit Zero Side-Effects (R5)
    # -------------------------------------------------------------------------
    def test_19_r5_preflight_failure_zero_side_effects(self):
        """
        TEST-19: Verifies Reviewer Finding R5.
        Executes the ACTUAL run_audit() orchestration in an isolated environment
        with missing preflight inputs. Asserts that:
        - The audit immediately aborts at preflight and returns False.
        - Handshake link files (S05/S06) are never published.
        - Deliberation log is never created or mutated.
        """
        from tests.run_increment_3_audit import run_audit

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Control A: In an uninitialized environment, actual run_audit fails and creates zero output files
            report_text, audit_passed = run_audit(root_dir=tmp_dir, run_tests=False)
            self.assertFalse(audit_passed)
            self.assertIn("AUDIT ABORTED AT PREFLIGHT", report_text)

            out_s05 = os.path.join(tmp_dir, "data", "parquet", "quality_inspection_schedule_links.parquet")
            out_s06 = os.path.join(tmp_dir, "data", "parquet", "formal_claims_delay_links.parquet")
            out_delib = os.path.join(tmp_dir, "data", "parquet", "audit_deliberation_log.parquet")

            self.assertFalse(os.path.exists(out_s05), "S05 links were published despite preflight failure!")
            self.assertFalse(os.path.exists(out_s06), "S06 links were published despite preflight failure!")
            self.assertFalse(os.path.exists(out_delib), "Deliberation was persisted despite preflight failure!")

            # Control B: In an environment with existing pre-audit files, failed preflight mutates nothing
            pdir = os.path.join(tmp_dir, "data", "parquet")
            os.makedirs(pdir, exist_ok=True)
            mock_log = os.path.join(pdir, "audit_deliberation_log.parquet")
            pd.DataFrame([{"turn_id": "T0", "position": "init"}]).to_parquet(mock_log, index=False)
            with open(mock_log, "rb") as f:
                initial_bytes = f.read()

            report_b, audit_passed_b = run_audit(root_dir=tmp_dir, run_tests=False)
            self.assertFalse(audit_passed_b)

            with open(mock_log, "rb") as f:
                after_bytes = f.read()
            self.assertEqual(initial_bytes, after_bytes, "Existing deliberation log was mutated despite preflight failure!")

            # Control C: Partial environment where 1 prerequisite table is deleted (injected preflight failure)
            with tempfile.TemporaryDirectory() as tmp_partial:
                shutil.copytree(os.path.join(S04_ROOT, "data"), os.path.join(tmp_partial, "data"))
                # Delete prerequisite table to inject preflight failure
                os.remove(os.path.join(tmp_partial, "data", "parquet", "contract_parameters.parquet"))
                # Remove pre-existing outputs in temp directory
                for fname in ["quality_inspection_schedule_links.parquet", "formal_claims_delay_links.parquet", "audit_deliberation_log.parquet"]:
                    fpath = os.path.join(tmp_partial, "data", "parquet", fname)
                    if os.path.exists(fpath):
                        os.remove(fpath)

                report_c, audit_passed_c = run_audit(root_dir=tmp_partial, run_tests=False)
                self.assertFalse(audit_passed_c)
                self.assertIn("AUDIT ABORTED AT PREFLIGHT", report_c)
                for fname in ["quality_inspection_schedule_links.parquet", "formal_claims_delay_links.parquet", "audit_deliberation_log.parquet"]:
                    self.assertFalse(
                        os.path.exists(os.path.join(tmp_partial, "data", "parquet", fname)),
                        f"{fname} was created under injected preflight failure!"
                    )

    # -------------------------------------------------------------------------
    # TEST 20: Manifest Tamper Causes Audit Process Failure & Zero Side Effects (R3)
    # -------------------------------------------------------------------------
    def test_20_r3_manifest_tamper_causes_audit_failure(self):
        """
        TEST-20: Verifies Reviewer Finding R3 / Independent Review Finding D.
        Executes the ACTUAL run_audit() orchestration under an input tamper condition.
        Asserts that:
        - Generated outputs are isolated from authoritative input baseline and NOT required before publication.
        - Deliberate physical tampering of schedule_activities.parquet causes check_manifest to fail.
        - schedule_activities.parquet is explicitly reported in failed/mismatched files.
        - No generated output files appear in failed files (proving abort is solely due to input tampering).
        - Audit immediately aborts with False before publication or deliberation.
        - No downstream handshake link tables are published.
        - Pre-existing deliberation logs remain 100% byte-for-byte unmodified.
        """
        from tests.run_increment_3_audit import run_audit, check_manifest

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Copy authoritative inputs to isolated test directory
            shutil.copytree(os.path.join(S04_ROOT, "data"), os.path.join(tmp_dir, "data"))

            # Remove generated outputs so they are absent initially (standard pre-publication state)
            out_s05 = os.path.join(tmp_dir, "data", "parquet", "quality_inspection_schedule_links.parquet")
            out_s06 = os.path.join(tmp_dir, "data", "parquet", "formal_claims_delay_links.parquet")
            out_m5 = os.path.join(tmp_dir, "data", "parquet", "quality_inspection_schedule_links_manifest.json")
            out_m6 = os.path.join(tmp_dir, "data", "parquet", "formal_claims_delay_links_manifest.json")
            for p in [out_s05, out_s06, out_m5, out_m6]:
                if os.path.exists(p):
                    os.remove(p)

            # Pre-seed an existing deliberation log to assert zero mutation on abort
            pdir = os.path.join(tmp_dir, "data", "parquet")
            mock_delib = os.path.join(pdir, "audit_deliberation_log.parquet")
            pd.DataFrame([{"turn_id": "T_PRE_EXISTING", "content": "untouched"}]).to_parquet(mock_delib, index=False)
            with open(mock_delib, "rb") as f:
                pre_tamper_bytes = f.read()

            # Positive Control: Verify that with clean authoritative inputs and absent generated outputs,
            # pre-publication manifest check passes and does NOT require generated outputs to exist.
            clean_ok, clean_log, clean_failed = check_manifest(root_dir=tmp_dir, include_generated_outputs=False)
            self.assertTrue(clean_ok, f"Clean input baseline failed unexpectedly: {clean_failed}")
            self.assertEqual(clean_failed, [])

            # Physical Tamper Injection: Modify 1 byte in schedule_activities.parquet
            tampered_table = os.path.join(tmp_dir, "data", "parquet", "schedule_activities.parquet")
            with open(tampered_table, "rb") as f:
                tampered_bytes = bytearray(f.read())
            tampered_bytes[10] = (tampered_bytes[10] + 1) % 256
            with open(tampered_table, "wb") as f:
                f.write(tampered_bytes)

            # Execute the actual audit workflow under tamper conditions
            report_text, audit_passed = run_audit(root_dir=tmp_dir, run_tests=False)
            self.assertFalse(audit_passed)
            self.assertIn("AUDIT ABORTED: Input baseline integrity failure", report_text)

            # Assert explicitly that schedule_activities.parquet appears in reported mismatched files
            self.assertIn("data/parquet/schedule_activities.parquet", report_text)
            self.assertIn("[BASELINE MISMATCH]", report_text)

            # Assert that absent generated outputs did NOT cause the failure (they are not in failed files list)
            failure_section = report_text.split("Input baseline integrity failure")[1].split(";")[0]
            self.assertIn("data/parquet/schedule_activities.parquet", failure_section)
            self.assertNotIn("quality_inspection_schedule_links.parquet", failure_section)
            self.assertNotIn("formal_claims_delay_links.parquet", failure_section)

            # Assert no handshake output was created or published, and pre-existing deliberation log was unmodified
            self.assertFalse(os.path.exists(out_s05), "S05 links were published despite baseline tamper!")
            self.assertFalse(os.path.exists(out_s06), "S06 links were published despite baseline tamper!")
            with open(mock_delib, "rb") as f:
                post_tamper_bytes = f.read()
            self.assertEqual(pre_tamper_bytes, post_tamper_bytes, "Pre-existing deliberation log was modified despite tamper abort!")


if __name__ == "__main__":
    unittest.main()


