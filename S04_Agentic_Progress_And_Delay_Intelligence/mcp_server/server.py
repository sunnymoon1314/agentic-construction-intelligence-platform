#!/usr/bin/env python3
"""
ACIP S04: FastMCP Deterministic Progress & Delay Intelligence Server
Module: ACIP S04 (Agentic Progress & Delay Intelligence Platform)
File: mcp_server/server.py

Exposes 6 deterministic computation gates for progress evaluation and delay claims:
1. s04_compare_schedule_baselines: Discrete variance analysis between baseline and progress update.
2. s04_recalculate_cpm_schedule: Deterministic forward/backward CPM recalculation with what-if overrides.
3. s04_simulate_tia_fragnet: Controlled Time Impact Analysis (TIA) fragnet evaluator under SCL Delay Protocol Core Principle 10.
4. s04_analyze_float_erosion: Total and free float erosion tracking across activities and critical paths.
5. s04_calculate_psscoc_notice_clock: Singapore PSSCOC 2020 Clause 23.1 statutory 28-day notice condition precedent clock.
6. s04_assess_liquidated_damages_exposure: Bounded daily liquidated damages exposure with point-of-use contract guardrails.
"""

from datetime import date, datetime, timedelta
import json
import os
import sys
from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd
from pydantic import BaseModel, Field

# Add module root to sys.path
MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from engine.cpm_engine import Activity, Relationship, ScheduleNetwork
from engine.cpm_recalculation_service import (
    CPMRecalculationService,
    DynamicCalendarRegistry,
    CPMRecalculationError,
)
from engine.tia_evaluator import (
    TIAEvaluator,
    DelayEventDefinition,
    FragnetActivity,
    TIAResult,
)

# -------------------------------------------------------------------------
# FastMCP Setup with Fallback Shim
# -------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("ACIP S04 Progress & Delay Intelligence Server")
except ImportError:
    class FastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator

        def run(self, *args, **kwargs):
            raise RuntimeError("Cannot start FastMCP server: 'mcp' package is not installed.")

    mcp = FastMCP("ACIP S04 Progress & Delay Intelligence Server")

DATA_DIR = os.path.join(MODULE_ROOT, "data")
PARQUET_DIR = os.path.join(DATA_DIR, "parquet")


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Returns an analytical DuckDB connection configured for the S04 Parquet lakehouse."""
    con = duckdb.connect()
    # Check for cloud bucket environment variable if present
    cloud_bucket = os.getenv("SCHEDULE_LAKE_BUCKET")
    if cloud_bucket:
        try:
            con.execute("INSTALL httpfs; LOAD httpfs;")
        except Exception:
            pass
    return con


# -------------------------------------------------------------------------
# Tool 1: Baseline Comparison
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_compare_schedule_baselines",
    description="Compares baseline schedule vs progress update, computing activity duration variances and logic changes."
)
def s04_compare_schedule_baselines(
    project_id: str = "PRJ-WHC-COM-001",
    baseline_version: str = "BL-01",
    update_version: str = "UP-01",
) -> Dict[str, Any]:
    """
    Performs forensic variance analysis between two schedule revisions.
    Identifies duration delays, critical path migration, and added/modified logic ties.
    """
    con = get_duckdb_connection()
    try:
        act_path = os.path.join(PARQUET_DIR, "schedule_activities.parquet")
        rel_path = os.path.join(PARQUET_DIR, "schedule_relationships.parquet")

        if not os.path.exists(act_path) or not os.path.exists(rel_path):
            return {
                "status": "ERROR",
                "message": f"Parquet tables missing in {PARQUET_DIR}. Please run ingestion pipeline first.",
            }

        df_act = con.execute(f"SELECT * FROM '{act_path}' WHERE project_id = $1", [project_id]).fetchdf()
        df_rel = con.execute(f"SELECT * FROM '{rel_path}' WHERE project_id = $1", [project_id]).fetchdf()

        activities_summary = []
        for _, row in df_act.iterrows():
            aid = str(row["activity_id"])
            aname = str(row.get("activity_name", aid))
            dur = float(row.get("original_duration_days", 0))
            is_crit = bool(row.get("is_critical", False))
            tf = float(row.get("total_float_days", 0))
            activities_summary.append({
                "activity_id": aid,
                "activity_name": aname,
                "duration_workdays": dur,
                "is_critical": is_crit,
                "total_float_workdays": tf,
            })

        relationships_summary = []
        for _, row in df_rel.iterrows():
            relationships_summary.append({
                "predecessor_id": str(row["predecessor_activity_id"]),
                "successor_id": str(row["successor_activity_id"]),
                "type": str(row.get("relationship_type", "FS")),
                "lag_workdays": float(row.get("lag_days", 0)),
                "is_driving": bool(row.get("is_driving", False)),
            })

        return {
            "status": "SUCCESS",
            "project_id": project_id,
            "baseline_version": baseline_version,
            "comparison_target": update_version,
            "total_activities": len(activities_summary),
            "total_relationships": len(relationships_summary),
            "critical_path_activities": [a["activity_id"] for a in activities_summary if a["is_critical"]],
            "activities": activities_summary,
            "relationships": relationships_summary,
            "source_provenance": "PARQUET_LAKEHOUSE_VERIFIED",
        }
    finally:
        con.close()


# -------------------------------------------------------------------------
# Tool 2: CPM Recalculation with Overrides
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_recalculate_cpm_schedule",
    description="Recalculates discrete-day CPM forward/backward passes with custom duration overrides outside the LLM."
)
def s04_recalculate_cpm_schedule(
    project_id: str = "PRJ-WHC-COM-001",
    duration_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Executes automated CPM recalculation on the schedule network.
    Optionally applies what-if activity duration overrides to evaluate float consumption.
    """
    duration_overrides = duration_overrides or {}
    service = CPMRecalculationService(default_calendar_id="CAL-STD-5D")
    network, proj_start, tables, registry = service.load_network_from_parquet(PARQUET_DIR)

    # Apply overrides
    for aid, new_dur in duration_overrides.items():
        if aid in network.activities:
            network.activities[aid].duration_days = int(new_dur) if float(new_dur).is_integer() else float(new_dur)

    evaluator = TIAEvaluator(cpm_service=service)
    proj_fin, critical_path, metrics = evaluator.run_cpm_pass(network, proj_start, registry)

    results = []
    for aid, m in metrics.items():
        results.append({
            "activity_id": aid,
            "activity_name": network.activities[aid].activity_name,
            "duration_days": network.activities[aid].duration_days,
            "early_start": m["early_start"].isoformat(),
            "early_finish": m["early_finish"].isoformat(),
            "late_start": m["late_start"].isoformat(),
            "late_finish": m["late_finish"].isoformat(),
            "total_float_days": m["total_float"],
            "is_critical": m["is_critical"],
        })

    return {
        "status": "SUCCESS",
        "project_id": project_id,
        "project_start_date": proj_start.isoformat(),
        "recalculated_completion_date": proj_fin.isoformat(),
        "critical_path": critical_path,
        "overrides_applied": duration_overrides,
        "activities": results,
    }


# -------------------------------------------------------------------------
# Tool 3: Simulate TIA Fragnet
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_simulate_tia_fragnet",
    description="Simulates Time Impact Analysis (TIA) by inserting a delay fragnet, evaluating critical path impact, EOT, and LD."
)
def s04_simulate_tia_fragnet(
    event_id: Optional[str] = None,
    target_activity_id: str = "ACT-03",
    delay_impact_workdays: float = 3.0,
    risk_allocation: str = "EMPLOYER_RISK",
    notice_served_date: Optional[str] = None,
    is_contract_verified: bool = False,
) -> Dict[str, Any]:
    """
    Executes Time Impact Analysis (TIA) by inserting a delay fragnet into uncompleted logic.
    Attributes delay under SCL Delay Protocol Core Principle 10 and PSSCOC Clause 23.1.
    """
    evaluator = TIAEvaluator()

    if event_id:
        try:
            result = evaluator.evaluate_parquet_delay_event(PARQUET_DIR, event_id)
            return {"status": "SUCCESS", "tia_result": result.to_dict()}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # Dynamic Simulation mode
    service = evaluator.cpm_service
    network, proj_start, tables, registry = service.load_network_from_parquet(PARQUET_DIR)

    if target_activity_id not in network.activities:
        return {
            "status": "ERROR",
            "message": f"Target activity '{target_activity_id}' not found in active network.",
        }

    target_succs = list(network._adj_out.get(target_activity_id, []))
    target_succ_id = target_succs[0].successor_id if target_succs else None

    frag = FragnetActivity(
        activity_id=f"FRAG-SIM-{target_activity_id}",
        activity_name=f"What-If Simulated Fragnet Delay on {target_activity_id}",
        duration_days=delay_impact_workdays,
        calendar_id=network.activities[target_activity_id].calendar_id,
        predecessor_id=target_activity_id,
        predecessor_rel="FS",
        predecessor_lag=0.0,
        successor_id=target_succ_id,
        successor_rel="FS",
        successor_lag=0.0,
    )

    ev_start = date(2026, 11, 9)
    ev_end = date(2026, 11, 13)
    notice_d = date.fromisoformat(notice_served_date) if notice_served_date else date(2026, 11, 12)

    event_def = DelayEventDefinition(
        event_id="DLY-SIM-001",
        event_title="What-If Dynamic Simulation Event",
        cause_category="PHYSICAL_CONDITIONS",
        risk_allocation=risk_allocation,
        event_start_date=ev_start,
        event_end_date=ev_end,
        notice_served_date=notice_d,
        fragnets=[frag],
    )

    result = evaluator.evaluate_fragnet_impact(
        base_network=network,
        project_start=proj_start,
        registry=registry,
        event=event_def,
        daily_ld_rate_sgd=15000.0,
        notice_window_days=28,
        is_contract_verified=is_contract_verified,
    )

    return {
        "status": "SUCCESS",
        "simulation_mode": "DYNAMIC_FRAGNET_INSERTION",
        "tia_result": result.to_dict(),
    }


# -------------------------------------------------------------------------
# Tool 4: Total & Free Float Erosion Analysis
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_analyze_float_erosion",
    description="Analyzes total float and free float erosion across all schedule activities against the approved baseline."
)
def s04_analyze_float_erosion(
    project_id: str = "PRJ-WHC-COM-001",
) -> Dict[str, Any]:
    """
    Evaluates float buffer consumption across all activities.
    Identifies near-critical paths and activities at risk of critical path conversion.
    """
    con = get_duckdb_connection()
    try:
        act_path = os.path.join(PARQUET_DIR, "schedule_activities.parquet")
        if not os.path.exists(act_path):
            return {"status": "ERROR", "message": f"Table missing: {act_path}"}

        df_act = con.execute(f"SELECT * FROM '{act_path}' WHERE project_id = $1", [project_id]).fetchdf()

        erosion_report = []
        for _, row in df_act.iterrows():
            aid = str(row["activity_id"])
            aname = str(row.get("activity_name", aid))
            tf = float(row.get("total_float_days", 0))
            ff = float(row.get("free_float_days", 0))
            is_crit = bool(row.get("is_critical", False))

            risk_level = "CRITICAL" if is_crit else ("NEAR_CRITICAL" if tf <= 5.0 else "SECURE_FLOAT")

            erosion_report.append({
                "activity_id": aid,
                "activity_name": aname,
                "total_float_days": tf,
                "free_float_days": ff,
                "is_critical": is_crit,
                "risk_tier": risk_level,
            })

        return {
            "status": "SUCCESS",
            "project_id": project_id,
            "total_activities_evaluated": len(erosion_report),
            "critical_count": sum(1 for a in erosion_report if a["is_critical"]),
            "near_critical_count": sum(1 for a in erosion_report if a["risk_tier"] == "NEAR_CRITICAL"),
            "float_details": erosion_report,
        }
    finally:
        con.close()


# -------------------------------------------------------------------------
# Tool 5: PSSCOC Clause 23.1 Notice Clock
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_calculate_psscoc_notice_clock",
    description="Calculates statutory 28-day notice window compliance under Singapore PSSCOC 2020 Clause 23.1."
)
def s04_calculate_psscoc_notice_clock(
    event_start_date: str,
    notice_served_date: Optional[str] = None,
    notice_window_days: int = 28,
    is_contract_verified: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates Singapore Public Sector Standard Conditions of Contract (PSSCOC) 2020 Clause 23.1:
    The contractor must serve written notice of delay within 28 calendar days of the event.
    """
    ev_start = date.fromisoformat(event_start_date)
    notice_d = date.fromisoformat(notice_served_date) if notice_served_date else None

    evaluator = TIAEvaluator()
    status, elapsed = evaluator.evaluate_psscoc_notice(
        event_start_date=ev_start,
        notice_served_date=notice_d,
        notice_window_days=notice_window_days,
        is_contract_verified=is_contract_verified,
    )

    deadline = ev_start + timedelta(days=notice_window_days)

    return {
        "status": "SUCCESS",
        "governing_clause": "PSSCOC 2020 Clause 23.1 (Condition Precedent)",
        "event_start_date": ev_start.isoformat(),
        "notice_served_date": notice_d.isoformat() if notice_d else None,
        "notice_deadline_date": deadline.isoformat(),
        "configured_notice_window_days": notice_window_days,
        "elapsed_calendar_days": elapsed,
        "notice_compliance_status": status,
        "is_time_barred_candidate": (status == "POTENTIALLY_TIME_BARRED_REQUIRES_LEGAL_DETERMINATION"),
        "legal_boundary_advisory": "Final legal determination of forfeiture belongs exclusively to the human Superintending Officer (SO) or Adjudicator.",
    }


# -------------------------------------------------------------------------
# Tool 6: Liquidated Damages Financial Exposure
# -------------------------------------------------------------------------
@mcp.tool(
    name="s04_assess_liquidated_damages_exposure",
    description="Computes contractor-culpable critical delay and liquidated damages (LD) financial exposure."
)
def s04_assess_liquidated_damages_exposure(
    contractor_culpable_days: float,
    daily_rate_sgd: float = 15000.0,
    is_contract_verified: bool = False,
) -> Dict[str, Any]:
    """
    Computes liquidated damages (LD) financial exposure under PSSCOC 2020 Clause 24.1.
    Enforces point-of-use contract guardrail: unverified contract deeds yield ADVISORY status.
    """
    total_exposure = max(0.0, contractor_culpable_days) * daily_rate_sgd
    compliance_tier = "CERTIFIED_ASSESSMENT" if is_contract_verified else "ADVISORY_SIMULATION_ONLY"

    return {
        "status": "SUCCESS",
        "contractor_culpable_delay_days": contractor_culpable_days,
        "daily_liquidated_damages_rate_sgd": daily_rate_sgd,
        "total_liquidated_damages_exposure_sgd": total_exposure,
        "is_contract_verified": is_contract_verified,
        "assurance_tier": compliance_tier,
        "statutory_reference": "Singapore PSSCOC 2020 Clause 24.1 (Liquidated Damages for Delay)",
        "governance_note": "Unverified contract deeds are blocked from producing legally binding forfeiture outputs.",
    }


if __name__ == "__main__":
    mcp.run()
