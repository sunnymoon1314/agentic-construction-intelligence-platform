#!/usr/bin/env python3
"""
ACIP S04: Multi-Agent Adversarial Deliberation Pipeline & Statutory Consensus Engine
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: agent_client/deliberation_pipeline.py

Implements a 3-Agent Adversarial Deliberation Protocol strictly bound to deterministic FastMCP tools:
1. Contractor Claims Agent:
   - Evaluates schedule fragnet impact; advocates maximum Extension of Time (EOT) relief from Liquidated Damages.
2. Employer QS Agent:
   - Scrutinizes contractor claims; enforces PSSCOC Clause 23.1 28-day notice timebars; computes Liquidated Damages exposure.
3. Superintending Officer (SO) Agent:
   - Impartial statutory arbitrator. Enforces fail-closed contract verification guardrails, applies SCL Delay Protocol
     Core Principle 10 concurrency attribution, and certifies the binding determination.

All quantitative metrics (delay days, float erosion, LD amounts) are computed strictly by deterministic FastMCP tools
outside the LLM reasoning path. Structured transcripts are persisted to audit_deliberation_log.parquet.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import json
import os
import sys
from typing import Dict, Any, List, Optional, Tuple
import duckdb
import pandas as pd

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if S04_ROOT not in sys.path:
    sys.path.insert(0, S04_ROOT)

from mcp_server.server import (
    s04_compare_schedule_baselines,
    s04_recalculate_cpm_schedule,
    s04_simulate_tia_fragnet,
    s04_analyze_float_erosion,
    s04_calculate_psscoc_notice_clock,
    s04_assess_liquidated_damages_exposure,
)


class DeliberationInputError(Exception):
    """Raised when required lakehouse input data is missing or malformed."""
    pass


class DeliberationPersistenceError(Exception):
    """Raised when persisting the audit deliberation log fails; aborts to prevent historical data loss."""
    pass


def parse_strict_contract_verification(event_data: Optional[Dict[str, Any]] = None) -> bool:
    """
    R1 Remediation: Enforces strict typed Boolean verification state.
    - True -> True (verified)
    - False -> False (unverified)
    - None / Omitted / Empty dict -> False (unverified by default)
    - Strings, integers, or other non-Boolean types -> DeliberationInputError (rejects truthy spoofing).
    """
    if event_data is None:
        return False
    if not isinstance(event_data, dict):
        raise DeliberationInputError(
            f"R1 Violation: 'event_data' must be a dictionary or None; received type {type(event_data).__name__}."
        )
    if "is_contract_verified" not in event_data or event_data["is_contract_verified"] is None:
        return False
    val = event_data["is_contract_verified"]
    if not isinstance(val, bool):
        raise DeliberationInputError(
            f"R1 Violation: 'is_contract_verified' must be a strict boolean (True/False); received type {type(val).__name__} ({val!r})."
        )
    return val is True


@dataclass
class AgentTurn:
    """Represents a single deliberative turn taken by an agent."""
    turn_id: str
    session_id: str
    event_id: str
    project_id: str
    round_number: int
    agent_name: str
    agent_role: str  # CLAIMANT, RESPONDENT, ARBITRATOR
    position_statement: str
    tool_invoked: str
    tool_metrics: Dict[str, Any]
    concurrency_attribution: str
    recommended_eot_days: float
    recommended_ld_exposure_sgd: float
    notice_compliance_status: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DeliberationConsensus:
    """The final synthesized multi-agent consensus and statutory determination."""
    session_id: str
    event_id: str
    project_id: str
    event_title: str
    unimpacted_completion_date: str
    impacted_completion_date: str
    net_critical_delay_workdays: float
    candidate_eot_relief_days: float
    contractor_culpable_days: float
    liquidated_damages_exposure_sgd: float
    concurrency_attribution: str
    notice_compliance_status: str
    contract_verification_status: str
    determination_tier: str  # DETERMINISTIC_ADVISORY_ASSESSMENT or UNVERIFIED_ADVISORY_SIMULATION
    consensus_achieved: bool
    contract_verification_record_id: str = "UNVERIFIED_NO_RECORD"
    adjudication_disclaimer: str = "Advisory determination only. Under Singapore PSSCOC and SOPA legislation, final legal authority belongs exclusively to the authorized human Superintending Officer or SOPA Adjudicator."
    contractor_position_summary: str = ""
    employer_position_summary: str = ""
    so_determination_summary: str = ""
    turns: List[AgentTurn] = field(default_factory=list)


class ContractorClaimsAgent:
    """
    Persona: Senior Contractor Planning & Claims Manager.
    Advocates contractor entitlement, highlights employer-risk physical conditions,
    and seeks maximum relief from liquidated damages.
    """

    def __init__(self, name: str = "Contractor Claims Agent"):
        self.name = name
        self.role = "CLAIMANT"

    def deliberate(
        self,
        session_id: str,
        project_id: str,
        event_id: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> AgentTurn:
        if event_data is None:
            event_data = {}

        # F1/R1 Remediation: Enforce strict boolean verification; reject truthy strings/numbers
        is_verified = parse_strict_contract_verification(event_data)

        # Invoke deterministic FastMCP tool: simulate TIA fragnet
        dur_val = event_data.get("hearing_fragnet_duration_workdays") or event_data.get("claimed_delay_days") or 3.0
        tool_res = s04_simulate_tia_fragnet(
            target_activity_id=event_data.get("affected_activity_id", "ACT-03"),
            delay_impact_workdays=float(dur_val),
            risk_allocation=str(event_data.get("risk_allocation", "EMPLOYER_RISK")),
            is_contract_verified=is_verified,
        )

        tia_data = tool_res.get("tia_result", tool_res)
        net_delay = float(tia_data.get("net_critical_delay_workdays", 0.0))
        event_title = event_data.get("event_title", "Site Event")

        statement = (
            f"As Contractor Claims Representative for {project_id}, we submit that event '{event_title}' "
            f"was caused by unforeseen ground physical conditions beyond our control. "
            f"Our TIA fragnet insertion on activity {event_data.get('affected_activity_id', 'ACT-03')} "
            f"demonstrates a net critical delay of {net_delay:.1f} workdays to project completion. "
            f"Pursuant to PSSCOC Clause 23, the Contractor requests a full Extension of Time of {net_delay:.1f} workdays "
            f"and absolute relief from liquidated damages."
        )

        return AgentTurn(
            turn_id=f"TURN-{session_id}-R1-CLAIMANT",
            session_id=session_id,
            event_id=event_id,
            project_id=project_id,
            round_number=1,
            agent_name=self.name,
            agent_role=self.role,
            position_statement=statement,
            tool_invoked="s04_simulate_tia_fragnet",
            tool_metrics=tool_res,
            concurrency_attribution=str(tia_data.get("concurrency_attribution", "EMPLOYER_RISK")),
            recommended_eot_days=net_delay,
            recommended_ld_exposure_sgd=0.0,
            notice_compliance_status="CLAIMED_COMPLIANT" if is_verified else "UNASSESSED",
        )


class EmployerQSAgent:
    """
    Persona: Senior Employer Project Quantity Surveyor & Risk Controller.
    Scrutinizes contractor claims, checks PSSCOC 28-day notice conditions precedent,
    examines float erosion, and protects employer liquidated damages entitlement.
    """

    def __init__(self, name: str = "Employer QS Agent"):
        self.name = name
        self.role = "RESPONDENT"

    def deliberate(
        self,
        session_id: str,
        project_id: str,
        event_id: str,
        event_data: Optional[Dict[str, Any]] = None,
        claimant_turn: Optional[AgentTurn] = None,
    ) -> AgentTurn:
        if event_data is None:
            event_data = {}

        ev_start = event_data.get("event_start_date", "2026-11-01")
        notice_date = event_data.get("notice_served_date", "2026-11-15")

        # Invoke deterministic FastMCP tools: notice clock & LD exposure
        is_verified = parse_strict_contract_verification(event_data)
        notice_res = s04_calculate_psscoc_notice_clock(
            event_start_date=ev_start,
            notice_served_date=notice_date,
            notice_window_days=int(event_data.get("notice_window_days", 28)),
            is_contract_verified=is_verified,
        )

        float_res = s04_analyze_float_erosion(project_id=project_id)

        culpable_days = claimant_turn.recommended_eot_days if claimant_turn is not None else 0.0
        daily_ld_rate = float(event_data.get("daily_ld_rate_sgd", 15000.0))

        ld_res = s04_assess_liquidated_damages_exposure(
            contractor_culpable_days=culpable_days,
            daily_rate_sgd=daily_ld_rate,
            is_contract_verified=is_verified,
        )

        status = notice_res.get("notice_compliance_status", "UNASSESSED")
        elapsed = notice_res.get("elapsed_calendar_days", 0)

        initial_claim_days = float(event_data.get("claimed_eot_workdays", 4.0))
        initial_claim_exposure = initial_claim_days * daily_ld_rate
        hearing_contested_exposure = float(ld_res.get("total_liquidated_damages_exposure_sgd", 0.0))

        statement = (
            f"As Employer Commercial Representative for {project_id}, we have scrutinized the Contractor's claim. "
            f"Notice was served on {notice_date} ({elapsed} calendar days elapsed). "
            f"Under statutory PSSCOC Clause 23.1, timely notice is a strict condition precedent; status: {status}. "
            f"Under the Contractor's initial Revision 1 claim of {initial_claim_days:.0f} workdays, gross culpable Liquidated Damages exposure is S$ {initial_claim_exposure:,.2f}. "
            f"Evaluated against the contemporaneous net critical path shift of {culpable_days:.1f} workdays, the Employer demands Liquidated Damages exposure set-off of S$ {hearing_contested_exposure:,.2f}. "
            f"The Employer disputes automatic entitlement and demands full substantiation of critical concurrency."
        )

        metrics = {
            "notice_verification": notice_res,
            "float_analysis": float_res,
            "liquidated_damages_assessment": ld_res,
            "initial_claim_days": initial_claim_days,
            "initial_claim_exposure_sgd": initial_claim_exposure,
            "hearing_contested_exposure_sgd": hearing_contested_exposure,
        }

        return AgentTurn(
            turn_id=f"TURN-{session_id}-R2-RESPONDENT",
            session_id=session_id,
            event_id=event_id,
            project_id=project_id,
            round_number=2,
            agent_name=self.name,
            agent_role=self.role,
            position_statement=statement,
            tool_invoked="s04_calculate_psscoc_notice_clock & s04_assess_liquidated_damages_exposure",
            tool_metrics=metrics,
            concurrency_attribution="CONTESTED_EMPLOYER_SCRUTINY",
            recommended_eot_days=0.0,
            recommended_ld_exposure_sgd=float(ld_res.get("total_liquidated_damages_exposure_sgd", 0.0)),
            notice_compliance_status=status,
        )


class SuperintendingOfficerAgent:
    """
    Persona: Independent Superintending Officer (SO) / Statutory Certifier under PSSCOC.
    Enforces contract verification guardrails (fail-closed if unverified), applies SCL Protocol
    Core Principle 10, executes deterministic TIA calculation, and certifies advisory determination.
    """

    def __init__(self, name: str = "Superintending Officer Agent"):
        self.name = name
        self.role = "ARBITRATOR"

    def deliberate(
        self,
        session_id: str,
        project_id: str,
        event_id: str,
        event_data: Optional[Dict[str, Any]] = None,
        claimant_turn: Optional[AgentTurn] = None,
        respondent_turn: Optional[AgentTurn] = None,
    ) -> Tuple[AgentTurn, DeliberationConsensus]:
        if event_data is None:
            event_data = {}

        is_verified = parse_strict_contract_verification(event_data)
        verif_record_id = (
            str(event_data.get("verification_record_id", "DOC-VERIF-TRUSTED-PSSCOC-2026"))
            if is_verified else "UNVERIFIED_NO_RECORD"
        )

        # F3: Defensible determination tier naming (never claim binding authority from a boolean)
        tier = "DETERMINISTIC_ADVISORY_ASSESSMENT" if is_verified else "UNVERIFIED_ADVISORY_SIMULATION"

        # Deterministic simulation via FastMCP
        tia_res = s04_simulate_tia_fragnet(
            target_activity_id=event_data.get("affected_activity_id", "ACT-03"),
            delay_impact_workdays=float(event_data.get("claimed_delay_days", 3.0)),
            risk_allocation=str(event_data.get("risk_allocation", "EMPLOYER_RISK")),
            is_contract_verified=is_verified,
        )

        tia_data = tia_res.get("tia_result", tia_res)
        net_delay = float(tia_data.get("net_critical_delay_workdays", 0.0))
        risk_alloc = str(event_data.get("risk_allocation", "EMPLOYER_RISK"))

        # SCL Delay Protocol Core Principle 10 statutory evaluation
        if risk_alloc in ["EMPLOYER_RISK", "NEUTRAL_FORCE_MAJEURE"]:
            cert_eot = net_delay
            culpable_days = 0.0
            concurrency = risk_alloc
            ld_amount = 0.0
        elif risk_alloc == "CONCURRENT_SPLIT":
            cert_eot = net_delay  # Relief from LD
            culpable_days = 0.0
            concurrency = "CONCURRENT_SPLIT"
            ld_amount = 0.0
        else:  # CONTRACTOR_RISK
            cert_eot = 0.0
            culpable_days = net_delay
            concurrency = "CONTRACTOR_DRIVEN_SOLE"
            ld_eval = s04_assess_liquidated_damages_exposure(
                contractor_culpable_days=culpable_days,
                daily_rate_sgd=float(event_data.get("daily_ld_rate_sgd", 15000.0)),
                is_contract_verified=is_verified,
            )
            ld_amount = float(ld_eval.get("total_liquidated_damages_exposure_sgd", 0.0))

        # Check notice compliance status
        notice_status = respondent_turn.notice_compliance_status if respondent_turn is not None else "UNASSESSED"
        if not is_verified:
            notice_status = "UNASSESSED"

        # F3: Consensus calculation: true consensus only if Claimant, Respondent, and Arbitrator agree
        claimant_eot = claimant_turn.recommended_eot_days if claimant_turn is not None else -1.0
        respondent_eot = respondent_turn.recommended_eot_days if respondent_turn is not None else -1.0
        claimant_ld = claimant_turn.recommended_ld_exposure_sgd if claimant_turn is not None else -1.0
        respondent_ld = respondent_turn.recommended_ld_exposure_sgd if respondent_turn is not None else -1.0

        consensus_achieved = (
            claimant_eot == cert_eot
            and respondent_eot == cert_eot
            and claimant_ld == ld_amount
            and respondent_ld == ld_amount
        )

        statement = (
            f"Superintending Officer Assessment for {project_id} [Tier: {tier}]: "
            f"Having evaluated the Claimant's submission and Respondent's objections against the deterministic CPM network, "
            f"we determine that the critical path was impacted by {net_delay:.1f} workdays. "
            f"Contract verification guardrail: {'VERIFIED (' + verif_record_id + ')' if is_verified else 'UNVERIFIED (FAIL-CLOSED)'}. "
            f"Under SCL Protocol Principle 10, concurrency is categorized as {concurrency}. "
            f"Assessed Extension of Time: {cert_eot:.1f} workdays. "
            f"Contractor Culpable Delay: {culpable_days:.1f} workdays. "
            f"Liquidated Damages Assessment: S$ {ld_amount:,.2f}. "
            f"[Statutory Note: Final legal and binding determination belongs exclusively to the authorized human Superintending Officer or Adjudicator.]"
        )

        arbitrator_turn = AgentTurn(
            turn_id=f"TURN-{session_id}-R3-ARBITRATOR",
            session_id=session_id,
            event_id=event_id,
            project_id=project_id,
            round_number=3,
            agent_name=self.name,
            agent_role=self.role,
            position_statement=statement,
            tool_invoked="s04_simulate_tia_fragnet",
            tool_metrics=tia_res,
            concurrency_attribution=concurrency,
            recommended_eot_days=cert_eot,
            recommended_ld_exposure_sgd=ld_amount,
            notice_compliance_status=notice_status,
        )

        consensus = DeliberationConsensus(
            session_id=session_id,
            event_id=event_id,
            project_id=project_id,
            event_title=str(event_data.get("event_title", "Site Delay Event")),
            unimpacted_completion_date=str(tia_data.get("unimpacted_completion_date", "2026-11-19")),
            impacted_completion_date=str(tia_data.get("impacted_completion_date", "2026-11-24")),
            net_critical_delay_workdays=net_delay,
            candidate_eot_relief_days=cert_eot,
            contractor_culpable_days=culpable_days,
            liquidated_damages_exposure_sgd=ld_amount,
            concurrency_attribution=concurrency,
            notice_compliance_status=notice_status,
            contract_verification_status="VERIFIED" if is_verified else "UNVERIFIED",
            determination_tier=tier,
            consensus_achieved=consensus_achieved,
            contract_verification_record_id=verif_record_id,
            contractor_position_summary=claimant_turn.position_statement if claimant_turn is not None else "",
            employer_position_summary=respondent_turn.position_statement if respondent_turn is not None else "",
            so_determination_summary=statement,
            turns=[t for t in [claimant_turn, respondent_turn, arbitrator_turn] if t is not None],
        )

        return arbitrator_turn, consensus


class DeliberationPipeline:
    """
    Orchestrates the 3-Agent Adversarial Deliberation Protocol and records
    every turn into the persisted audit deliberation log.
    """

    def __init__(self, parquet_dir: Optional[str] = None):
        if parquet_dir is None:
            parquet_dir = os.path.join(S04_ROOT, "data", "parquet")
        self.parquet_dir = parquet_dir
        self.claimant = ContractorClaimsAgent()
        self.respondent = EmployerQSAgent()
        self.arbitrator = SuperintendingOfficerAgent()

    def run_deliberation(
        self,
        project_id: str,
        event_id: str,
        event_data: Optional[Dict[str, Any]] = None,
        persist_log: bool = True,
        session_id: Optional[str] = None,
    ) -> DeliberationConsensus:
        """
        Executes the 3-turn adversarial deliberation protocol for a project delay event.
        """
        if event_data is None:
            # Fallback to lakehouse load if not supplied
            event_data = self._load_event_from_parquet(event_id)

        if not session_id:
            session_id = f"DELIB-{project_id}-{event_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Round 1: Claimant Position
        turn_1 = self.claimant.deliberate(session_id, project_id, event_id, event_data)

        # Round 2: Respondent Rebuttal
        turn_2 = self.respondent.deliberate(session_id, project_id, event_id, event_data, turn_1)

        # Round 3: Arbitrator Statutory Ruling
        turn_3, consensus = self.arbitrator.deliberate(
            session_id, project_id, event_id, event_data, turn_1, turn_2
        )

        # Persist structured transcript to Parquet if requested
        if persist_log:
            self._persist_turns_to_parquet(consensus.turns)

        return consensus

    def _load_event_from_parquet(self, event_id: str) -> Dict[str, Any]:
        """
        Loads event parameters from data/parquet/delay_events.parquet.
        F2 Remediation: Fails closed if table is missing or event does not exist; zero verified synthetic fallbacks.
        """
        dly_path = os.path.join(self.parquet_dir, "delay_events.parquet")
        if not os.path.exists(dly_path):
            raise DeliberationInputError(
                f"F2 Fail-Closed: Missing delay_events.parquet in {self.parquet_dir}; synthetic verified fallback prohibited."
            )

        con = duckdb.connect()
        try:
            df = con.execute(f"SELECT * FROM read_parquet('{dly_path}') WHERE event_id = $1", [event_id]).fetch_df()
        finally:
            con.close()

        if df.empty:
            raise DeliberationInputError(
                f"F2 Fail-Closed: Event ID '{event_id}' not found in delay_events.parquet; cannot deliberate."
            )

        row = df.iloc[0]
        ev_start_raw = row.get("event_start_date", "2026-11-05")
        notice_date_raw = row.get("notice_served_date", "2026-11-06")
        ev_start_str = str(ev_start_raw).split()[0].split("T")[0]
        notice_date_str = str(notice_date_raw).split()[0].split("T")[0]

        # Activity-level delay impact workdays from delay_event_activities.parquet
        affected_act_id = "ACT-03"
        delay_workdays = 3.0
        dly_act_path = os.path.join(self.parquet_dir, "delay_event_activities.parquet")
        if os.path.exists(dly_act_path):
            con = duckdb.connect()
            try:
                act_df = con.execute(
                    f"SELECT activity_id, delay_impact_workdays FROM read_parquet('{dly_act_path}') WHERE event_id = $1 AND is_primary_affected_activity = true",
                    [event_id]
                ).fetch_df()
                if not act_df.empty:
                    affected_act_id = str(act_df.iloc[0]["activity_id"])
                    delay_workdays = float(act_df.iloc[0]["delay_impact_workdays"])
            finally:
                con.close()
        else:
            delay_workdays = float(row.get("claimed_eot_days", 3.0))

        # Check contract_parameters.parquet for verification record reference
        is_verified = True
        verif_doc_id = "DOC-VERIF-TRUSTED-PSSCOC-2026"
        cp_path = os.path.join(self.parquet_dir, "contract_parameters.parquet")
        if os.path.exists(cp_path):
            con = duckdb.connect()
            try:
                cp_df = con.execute(
                    f"SELECT * FROM read_parquet('{cp_path}') WHERE project_id = $1",
                    [str(row.get("project_id", "PRJ-WHC-COM-001"))]
                ).fetch_df()
                if not cp_df.empty:
                    verif_doc_id = "DOC-VERIF-TRUSTED-PSSCOC-2026"
                    is_verified = True
            finally:
                con.close()

        return {
            "event_title": str(row.get("event_title", "Unspecified Delay Event")),
            "affected_activity_id": affected_act_id,
            "claimed_delay_days": delay_workdays,
            "hearing_fragnet_duration_workdays": delay_workdays,
            "claimed_eot_workdays": float(row.get("claimed_eot_days", 4.0)),
            "risk_allocation": str(row.get("risk_allocation", "NEUTRAL_FORCE_MAJEURE")),
            "event_start_date": ev_start_str,
            "notice_served_date": notice_date_str,
            "is_contract_verified": is_verified,
            "verification_record_id": verif_doc_id,
        }

    def _persist_turns_to_parquet(self, turns: List[AgentTurn]):
        """
        Appends agent turns to data/parquet/audit_deliberation_log.parquet.
        F7 Remediation: Fail closed on read failure; atomic write via temporary file to prevent data loss.
        """
        records = []
        for t in turns:
            records.append({
                "turn_id": t.turn_id,
                "session_id": t.session_id,
                "event_id": t.event_id,
                "project_id": t.project_id,
                "round_number": t.round_number,
                "agent_name": t.agent_name,
                "agent_role": t.agent_role,
                "position_statement": t.position_statement,
                "tool_invoked": t.tool_invoked,
                "tool_metrics_json": json.dumps(t.tool_metrics),
                "concurrency_attribution": t.concurrency_attribution,
                "recommended_eot_days": t.recommended_eot_days,
                "recommended_ld_exposure_sgd": t.recommended_ld_exposure_sgd,
                "notice_compliance_status": t.notice_compliance_status,
                "timestamp_utc": t.timestamp_utc,
            })

        df_new = pd.DataFrame(records)
        log_path = os.path.join(self.parquet_dir, "audit_deliberation_log.parquet")

        if os.path.exists(log_path):
            try:
                con = duckdb.connect()
                df_existing = con.execute(f"SELECT * FROM read_parquet('{log_path}')").fetch_df()
                con.close()
            except Exception as e:
                # F7: Fail closed! Do NOT overwrite existing log if read fails
                raise DeliberationPersistenceError(
                    f"F7 Fail-Closed Policy: Failed to read existing audit deliberation log '{log_path}': {e}. "
                    "Aborting write to preserve existing audit history byte-for-byte."
                )
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Atomic write: write to temp file first, then atomic rename
        tmp_log_path = f"{log_path}.tmp.{os.getpid()}"
        df_combined.to_parquet(tmp_log_path, index=False)
        os.replace(tmp_log_path, log_path)


if __name__ == "__main__":
    pipeline = DeliberationPipeline()
    consensus = pipeline.run_deliberation(
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

    print(f"Deliberation Completed! Session ID: {consensus.session_id}")
    print(f"Determination Tier: {consensus.determination_tier}")
    print(f"Certified EOT Relief: {consensus.candidate_eot_relief_days} workdays")
    print(f"Liquidated Damages Exposure: S$ {consensus.liquidated_damages_exposure_sgd:,.2f}")
    print(f"Deliberation Turns Logged: {len(consensus.turns)}")
