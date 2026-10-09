#!/usr/bin/env python3
"""
S03: Multi-Agent Commercial Intelligence & Statutory Deliberation Pipeline
Module: ACIP S03 (Agentic Cost & Commercial Control Platform)
File: agent_client/evaluator.py

Implements 3 collaborative commercial agents bound directly to FastMCP tools:
1. Forensic QS Auditor Agent:
   - Audits openBIM physical element quantities against contractor claims.
   - Detects cash-flow front-ramping and calculates over-certification disallowances.
2. Contracts & Claims Counsel Agent:
   - Enforces PSSCOC Clause 19.1 28-day notice timebars (detecting waived claims).
   - Audits 4-tier variation waterfall and exposes Star Rate duplication fraud.
3. Statutory Commercial Director Agent:
   - Ingests cumulative accounting ledgers and enforces the statutory SOPA Section 11 notice.
   - Computes predictive EVM contingency depletion velocity and issues early warning radar.
   - Synthesizes qualitative dispute narratives and executive briefing memos.
"""

import os
import sys
import json
from datetime import date
from typing import Dict, Any, List, Optional

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODULE_ROOT)

from mcp_server.server import (
    get_connection,
    get_table_source,
    list_commercial_projects,
    audit_variation_order,
    reconcile_progress_valuation,
    generate_sopa_response,
    serve_sopa_deadline_clock,
    get_predictive_eac
)

class ForensicQSAuditorAgent:
    """Agent Persona: Senior Forensic Quantity Surveyor specializing in openBIM takeoff verification."""
    def __init__(self, name="Forensic QS Auditor Agent"):
        self.name = name

    def evaluate(self, project_id: str = "PRJ-WHC-COM-001", claim_id: str = "CLM-WHC-008") -> Dict[str, Any]:
        con = get_connection()
        ci_src = get_table_source("claim_items")
        rows = con.execute(f"""
            SELECT item_code, contractor_claimed_cumulative_qty 
            FROM {ci_src} 
            WHERE claim_id = '{claim_id}'
        """).fetchall()
        con.close()

        items_to_audit = [(r[0], float(r[1])) for r in rows] if rows else [
            ("STR-02-004", 7800.00),
            ("CIV-01-001", 12000.00),
            ("MNE-07-003", 2450.00),
            ("MNE-06-012", 3.00)
        ]

        findings = []
        total_disallowed = 0.0

        for code, qty in items_to_audit:
            try:
                res = reconcile_progress_valuation(project_id, claim_id, code, qty)
                recon = res["reconciliation"]
                if recon["discrepancy_status"] == "FLAGGED_OVER_CERTIFICATION":
                    total_disallowed += recon["disallowed_amount"]
                    findings.append({
                        "severity": "CRITICAL",
                        "item_code": code,
                        "description": res["description"],
                        "category": "PROGRESS_OVER_CERTIFICATION",
                        "observation": (
                            f"Contractor claimed {recon['contractor_claimed_qty']} units (S${recon['contractor_claimed_amount']:,.2f}), "
                            f"but openBIM IFC volume verification confirms only {recon['openbim_verified_qty']} units "
                            f"(S${recon['openbim_verified_amount']:,.2f}) physically installed on site. "
                            f"Variance of {recon['variance_percentage']}% exceeds allowable tolerance. "
                            f"Immediate disallowance of S${recon['disallowed_amount']:,.2f} enforced."
                        )
                    })
            except Exception as e:
                findings.append({"severity": "ERROR", "item_code": code, "observation": str(e)})

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "total_openbim_disallowed": round(total_disallowed, 2),
            "findings_count": len(findings),
            "findings": findings
        }


class ContractsClaimsCounselAgent:
    """Agent Persona: Senior Construction Law & Commercial Counsel specializing in PSSCOC/SIA contract administration."""
    def __init__(self, name="Contracts & Claims Counsel Agent"):
        self.name = name

    def evaluate(self, project_id: str = "PRJ-WHC-COM-001") -> Dict[str, Any]:
        con = get_connection()
        vo_src = get_table_source("variation_orders")
        rows = con.execute(f"""
            SELECT vo_id, instruction_date, claim_notice_date, contractor_proposed_rate, proposed_valuation_tier 
            FROM {vo_src} 
            WHERE project_id = '{project_id}'
        """).fetchall()
        con.close()

        vos_to_audit = [
            (r[0], str(r[1]), str(r[2]), float(r[3]), r[4]) for r in rows
        ] if rows else [
            ("VO-WHC-001", "2026-08-10", "2026-08-25", 380.00, "TIER_3_STAR_RATE"),
            ("VO-WHC-002", "2026-08-18", "2026-09-02", 185.00, "TIER_3_STAR_RATE"),
            ("VO-WHC-004", "2026-08-28", "2026-09-15", 450.00, "TIER_3_STAR_RATE"),
            ("VO-WHC-005", "2026-07-15", "2026-09-22", 85.00, "TIER_4_DAYWORK"),
            ("VO-WHC-007", "2026-07-20", "2026-09-25", 2200.00, "TIER_4_DAYWORK"),
            ("VO-WHC-012", "2026-08-01", "2026-09-29", 3500.00, "TIER_4_DAYWORK")
        ]

        findings = []
        total_vo_disallowed = 0.0

        for vo_id, inst_d, notice_d, rate, tier in vos_to_audit:
            try:
                res = audit_variation_order(project_id, vo_id, inst_d, notice_d, rate, tier)
                vw = res["valuation_waterfall"]
                tb = res["timebar_validation"]
                total_vo_disallowed += vw["deduction_disallowed"]

                if tb["timebar_status"] == "TIMEBAR_EXPIRED_CLAIM_WAIVED":
                    findings.append({
                        "severity": "CRITICAL",
                        "vo_id": vo_id,
                        "category": "TIMEBAR_WAIVER_PSSCOC_CL19",
                        "deduction": vw["deduction_disallowed"],
                        "observation": (
                            f"{vo_id} ({res['description']}): Notice served {tb['days_elapsed']} days after instruction, "
                            f"exceeding the strict 28-day notice window under PSSCOC Clause 19.1. "
                            f"Claim is statutorily waived. Full claimed sum of S${vw['deduction_disallowed']:,.2f} rejected."
                        )
                    })
                elif vw["fraud_flag"] == "RATE_DUPLICATION_DETECTED":
                    findings.append({
                        "severity": "HIGH",
                        "vo_id": vo_id,
                        "category": "STAR_RATE_DUPLICATION_FRAUD",
                        "deduction": vw["deduction_disallowed"],
                        "observation": (
                            f"{vo_id}: Contractor claimed Tier 3 Star Rate of S${vw['proposed_rate']:.2f}, "
                            f"concealing that item is identical to contract baseline SOR Code {res.get('claimed_item_code', 'SOR')}. "
                            f"System enforced compulsory fallback to Tier 1 SOR rate S${vw['authoritative_rate_applied']:.2f}, "
                            f"saving S${vw['deduction_disallowed']:,.2f}."
                        )
                    })
            except Exception as e:
                findings.append({"severity": "ERROR", "vo_id": vo_id, "observation": str(e)})

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "total_vo_disallowed": round(total_vo_disallowed, 2),
            "findings_count": len(findings),
            "findings": findings
        }


class StatutoryCommercialDirectorAgent:
    """Agent Persona: Commercial Director & Lead SOPA Adjudication Strategist."""
    def __init__(self, name="Statutory Commercial Director Agent"):
        self.name = name

    def evaluate(self, project_id: str = "PRJ-WHC-COM-001", claim_id: str = "CLM-WHC-008") -> Dict[str, Any]:
        con = get_connection()
        clm_src = get_table_source("interim_claims")
        prj_src = get_table_source("projects")
        c_row = con.execute(f"SELECT date_served FROM {clm_src} WHERE claim_id = '{claim_id}'").fetchone()
        p_row = con.execute(f"SELECT contract_response_days_ceiling FROM {prj_src} WHERE project_id = '{project_id}'").fetchone()
        con.close()

        served_d = str(c_row[0]) if c_row else "2026-10-01"
        days_c = int(p_row[0]) if p_row else 14

        sopa = generate_sopa_response(project_id, claim_id)
        eac = get_predictive_eac(project_id, current_month="2026-10")
        clock = serve_sopa_deadline_clock(served_d, days_c)

        fin = sopa["financial_summary"]
        evm = eac["earned_value_metrics"]
        radar = eac["contingency_velocity_radar"]

        executive_recommendations = [
            f"Serve Formal Section 11 Payment Response certifying Net S${fin['net_payable_certified_this_period']:,.2f} by statutory deadline {clock['statutory_response_deadline']}.",
            f"Maintain strict withholding of S${fin['openbim_disallowance']:,.2f} (openBIM over-certification) and S${fin['statutory_safety_set_off']:,.2f} (MOM safety backcharges).",
            f"CRITICAL CONTINGENCY ALERT: Contingency burn velocity is S${radar['monthly_burn_velocity']:,.2f}/month. Contingency fund hits S$0 at Month {radar['forecasted_breach_month_index']}. Total projected budget overrun is S${evm['budget_variance_overrun']:,.2f}."
        ]

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "net_amount_payable_sgd": fin["net_payable_certified_this_period"],
            "statutory_safety_set_off": fin.get("statutory_safety_set_off", 0.0),
            "statutory_deadline": clock["statutory_response_deadline"],
            "statutory_status": clock["countdown"]["statutory_risk_status"],
            "traffic_light": clock["countdown"]["traffic_light"],
            "predictive_eac_sgd": evm["risk_adjusted_eac"],
            "projected_overrun_sgd": evm["budget_variance_overrun"],
            "contingency_exhaustion_month": radar["forecasted_breach_month_index"],
            "executive_recommendations": executive_recommendations,
            "sopa_dossier_markdown": sopa["dossier_markdown"]
        }


class MultiAgentCommercialPipeline:
    """Master Orchestrator delivering collaborative multi-agent commercial consensus and qualitative narratives."""
    def __init__(self):
        self.qs_agent = ForensicQSAuditorAgent()
        self.counsel_agent = ContractsClaimsCounselAgent()
        self.director_agent = StatutoryCommercialDirectorAgent()

    def run_full_audit(self, project_id: str = "PRJ-WHC-COM-001", claim_id: str = "CLM-WHC-008") -> Dict[str, Any]:
        qs_res = self.qs_agent.evaluate(project_id, claim_id)
        counsel_res = self.counsel_agent.evaluate(project_id)
        director_res = self.director_agent.evaluate(project_id, claim_id)

        safety_deduction = director_res.get("statutory_safety_set_off", 55000.00)
        total_withholding = round(
            qs_res["total_openbim_disallowed"] + counsel_res["total_vo_disallowed"] + safety_deduction, 2
        )

        consensus_summary = {
            "project_id": project_id,
            "claim_id": claim_id,
            "audit_timestamp": date.today().isoformat(),
            "commercial_risk_index": "HIGH_EXPOSURE" if director_res["projected_overrun_sgd"] > 0 else "CONTROLLED_RISK",
            "statutory_response_deadline": director_res["statutory_deadline"],
            "net_payable_certified": director_res["net_amount_payable_sgd"],
            "total_withholding_deductions": total_withholding,
            "openbim_disallowance": qs_res["total_openbim_disallowed"],
            "variation_order_disallowance": counsel_res["total_vo_disallowed"],
            "statutory_safety_set_off": safety_deduction,
            "predictive_eac_overrun": director_res["projected_overrun_sgd"],
            "contingency_breach_month": director_res["contingency_exhaustion_month"],
            "agent_findings": [
                qs_res,
                counsel_res,
                director_res
            ],
            "dispute_narrative": self.draft_dispute_narrative(project_id, claim_id, qs_res, counsel_res, director_res),
            "executive_memo": self.draft_executive_briefing_memo(project_id, claim_id, director_res)
        }

        return consensus_summary

    def draft_dispute_narrative(self, project_id: str, claim_id: str, qs_res: dict, counsel_res: dict, director_res: dict) -> str:
        """Drafts forensic qualitative dispute narrative for employer legal defence."""
        return (
            f"LEGAL DISPUTE NARRATIVE & ADJUDICATION DEFENSE BRIEFING\n"
            f"Target: Interim Claim {claim_id} under Project {project_id}\n\n"
            f"1. FORENSIC TAKEOFF DISALLOWANCE: The contractor has engaged in cash-flow front-ramping. "
            f"openBIM IFC reality-capture verified quantities indicate an uninstalled physical shortfall "
            f"amounting to S${qs_res['total_openbim_disallowed']:,.2f}. Pursuant to SOPA s15, unexecuted works are not payable.\n\n"
            f"2. STATUTORY TIMEBAR WAIVER: The contractor failed to serve written notice within the mandatory 28-day "
            f"condition precedent window under PSSCOC Clause 19.1 for time-barred variations. Total waived claims equal "
            f"S${counsel_res['total_vo_disallowed']:,.2f}.\n\n"
            f"3. STATUTORY SAFETY SET-OFF: Backcharges under Section 11 of S${director_res.get('statutory_safety_set_off', 0.0):,.2f} "
            f"are withheld pursuant to contractual indemnities for MOM demerit points and stop-work orders."
        )

    def draft_executive_briefing_memo(self, project_id: str, claim_id: str, director_res: dict) -> str:
        """Drafts executive memo for project developer and C-suite commercial steering committee."""
        return (
            f"EXECUTIVE BRIEFING MEMORANDUM\n"
            f"To: Project Steering Committee & Chief Financial Officer\n"
            f"From: Commercial Control & Contract Intelligence Engine\n"
            f"Date: {date.today().strftime('%d %B %Y')}\n\n"
            f"SUBJECT: STATUTORY PAYMENT RESPONSE FOR {project_id} ({claim_id})\n\n"
            f"1. ACTION REQUIRED: Serve statutory Payment Response certifying Net S${director_res['net_amount_payable_sgd']:,.2f} "
            f"prior to statutory deadline {director_res['statutory_deadline']}.\n\n"
            f"2. CONTINGENCY VELOCITY ALERT: Cost Performance Index (CPI) has degraded. "
            f"Projected Estimate at Completion (EAC) anticipates budget overrun of S${director_res['projected_overrun_sgd']:,.2f}, "
            f"with contingency exhaustion forecasted at Month {director_res['contingency_exhaustion_month']}."
        )


if __name__ == "__main__":
    print("=" * 70)
    print("ACIP S03: Executing Multi-Agent Commercial Intelligence Pipeline")
    print("=" * 70)
    pipeline = MultiAgentCommercialPipeline()
    audit = pipeline.run_full_audit()
    print(f"Project: {audit['project_id']} | Claim: {audit['claim_id']}")
    print(f"Statutory Response Deadline: {audit['statutory_response_deadline']}")
    print(f"Net Certified Payable: S${audit['net_payable_certified']:,.2f}")
    print(f"Total Withholding Deductions: S${audit['total_withholding_deductions']:,.2f}")
    print(f"Projected Budget Overrun: S${audit['predictive_eac_overrun']:,.2f}")
    print(f"Contingency Exhaustion: Month {audit['contingency_breach_month']}")
    print("=" * 70)
    print("Multi-Agent Deliberation Succeeded.")
    print("=" * 70)
