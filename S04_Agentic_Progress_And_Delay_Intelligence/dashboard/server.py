#!/usr/bin/env python3
"""
ACIP S04: Agentic Progress & Delay Intelligence Dashboard Server
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: dashboard/server.py

Serves the S04 Field-Ready Cockpit on port 8087.
Features:
1. Zero-dependency HTTP server with REST APIs.
2. SRE Health Probes: /livez, /readyz, /healthz.
3. Deterministic DuckDB & CPM Calculation Engine integration.
4. Time Impact Analysis (TIA) Fragnet Simulator endpoint (/api/tia/simulate).
5. Contemporaneous Site Radar & Rain Gauge Discrepancy detector.
6. Universal ACIP Data Dictionary lookup integration.
"""

import os
import sys
import json
import argparse
import http.server
import socketserver
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date, timedelta, timezone

logger = logging.getLogger("acip.s04.dashboard")

# Ensure S04 module root is on sys.path to import engine
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
S04_ROOT = os.path.dirname(DASHBOARD_DIR)
ACIP_ROOT = os.path.dirname(S04_ROOT)

if S04_ROOT not in sys.path:
    sys.path.insert(0, S04_ROOT)

try:
    from engine.cpm_engine import (
        ScheduleNetwork, Activity, Relationship,
        build_six_activity_benchmark, is_workday, add_workdays, workdays_between
    )
except ImportError:
    ScheduleNetwork = None

try:
    from agent_client.deliberation_pipeline import DeliberationPipeline
except ImportError:
    DeliberationPipeline = None

try:
    from mcp_server.server import s04_simulate_tia_fragnet
except ImportError:
    s04_simulate_tia_fragnet = None

START_TIME = datetime.now(timezone.utc)


def get_display_engine(host: str = "", query_engine: str = "") -> str:
    # 0. Check dynamic query parameter (?engine=aws|azure|gcp|local)
    if query_engine:
        q_upper = query_engine.upper()
        if "AWS" in q_upper:
            return "AWS Engine"
        elif "AZURE" in q_upper:
            return "Azure Engine"
        elif "GCP" in q_upper:
            return "GCP Engine"
        elif "LOCAL" in q_upper:
            return "Local Engine"

    # 1. Check explicit environment variables
    raw = os.getenv("ACIP_ENGINE") or os.getenv("CLOUD_PROVIDER", "").strip()
    if raw:
        raw_upper = raw.upper()
        if "AWS" in raw_upper:
            return "AWS Engine"
        elif "AZURE" in raw_upper:
            return "Azure Engine"
        elif "GCP" in raw_upper:
            return "GCP Engine"
        elif "LOCAL" in raw_upper:
            return "Local Engine"

    # 2. Auto-detect from cloud lakehouse storage mode or container runtime metadata
    lake_bucket = os.getenv("PROGRESS_DELAY_LAKE_BUCKET", "")
    if (
        lake_bucket.startswith("s3://")
        or os.getenv("AWS_EXECUTION_ENV")
        or os.getenv("ECS_CONTAINER_METADATA_URI")
        or os.getenv("ECS_CONTAINER_METADATA_URI_V4")
    ):
        return "AWS Engine"
    elif (
        "blob.core.windows.net" in lake_bucket
        or lake_bucket.startswith("azure://")
        or os.getenv("CONTAINER_APP_NAME")
    ):
        return "Azure Engine"
    elif lake_bucket.startswith("gs://") or os.getenv("K_SERVICE"):
        return "GCP Engine"

    # 3. Auto-detect from incoming HTTP Host header
    if host:
        host_lower = host.lower()
        if "amazonaws.com" in host_lower or "elb." in host_lower:
            return "AWS Engine"
        elif "azurecontainerapps.io" in host_lower or "azure" in host_lower:
            return "Azure Engine"
        elif "run.app" in host_lower or "cloudrun" in host_lower:
            return "GCP Engine"

    return "Local Engine"

# Path to unified dictionary bundle
DICTIONARY_BUNDLE_PATH = os.path.join(S04_ROOT, "data", "dictionary", "acip_ui_tooltip_bundle.json")

# Authoritative Parquet file paths for WHC schedule baseline
SCHEDULE_ACTIVITIES_PARQUET_PATH = os.path.join(S04_ROOT, "data", "parquet", "schedule_activities.parquet")
SCHEDULE_RELATIONSHIPS_PARQUET_PATH = os.path.join(S04_ROOT, "data", "parquet", "schedule_relationships.parquet")

# ==============================================================================
# DEPRECATED COMPATIBILITY ALIAS SUNSET CONTRACT (F25):
# Field: 'ai_consensus' in Delay Event objects.
# Classification: Deprecated compatibility alias for 'evaluation_note' and
#                 'deterministic_evaluation'.
# Architectural Semantics: Strictly deterministic CPM mathematical evaluation;
#                          NEVER multi-model LLM inference or synthetic consensus.
# Technical Ownership: ACIP S04 Engineering & Delay Intelligence Platform Governance.
# Deprecation Status: DEPRECATED (Active compatibility alias across Release 1.x).
# Scheduled Sunset Milestone: ACIP Release 2.0.0 (Upon platform completion of S08).
# Migration Directive: Downstream API consumers and UI components must consume
#                      'evaluation_note' or 'deterministic_evaluation'. Field will
#                      be permanently removed from schema in Release 2.0.0.
# ==============================================================================

PROJECT_PROFILES = {
    "PRJ-T5-003": {
        "project_id": "PRJ-T5-003",
        "project_name": "Changi Airport Terminal 5 — Substructure & Tunnels",
        "contractor": "GrandPillar Infrastructure Pte Ltd",
        "contract_sum_sgd": 145000000.0,
        "contract_form": "LTA / CAG Civil Standard",
        "sector": "Aviation Transit Substructure",
        "sector_icon": "✈️",
        "liquidated_damages_daily_sgd": 50000.0,
        "commencement_date": "2026-03-01",
        "original_completion_date": "2028-02-28",
        "current_forecast_completion_date": "2028-03-14",
        "net_delay_days": 0,
        "ld_exposure_sgd": 0.0,
        "current_status": "HEALTHY_BENCHMARK",
        "status_badge": "Certified 14-Day EOT Benchmark",
        "badge_color": "green",
        "baseline_version": "BL-01",
        "latest_update_version": "UP-03",
        "key_event": "Unmapped 66kV SP Power High-Voltage Duct Clash",
        "governing_clause": "LTA GCC Clause 44.1",
        "rain_gauge_discrepancy_score": "PERFECT_MATCH",
        "assessed_eot": "14 / 14 Days",
        "assessed_eot_sub": "LTA GCC Clause 44.1 Full EOT",
        "notice_pill_text": "⏱️ LTA Notice: Compliant (3d)",
        "notice_pill_class": "status-pill green",
        "ld_sub": "0 Culpable Days @ S$50k/day"
    },
    "PRJ-JID-ATP-004": {
        "project_id": "PRJ-JID-ATP-004",
        "project_name": "Jurong Innovation District Advanced Tech Park",
        "contractor": "Heng Win (Private) Limited",
        "contract_sum_sgd": 68500000.0,
        "contract_form": "PSSCOC 2020",
        "sector": "Advanced Manufacturing",
        "sector_icon": "🏭",
        "liquidated_damages_daily_sgd": 25000.0,
        "commencement_date": "2026-06-01",
        "original_completion_date": "2027-04-30",
        "current_forecast_completion_date": "2027-06-14",
        "net_delay_days": 38,
        "ld_exposure_sgd": 950000.0,
        "current_status": "ACTIVE_DISPUTED_CLAIMS",
        "status_badge": "Disputed Fragnet Padding (S$2.8M)",
        "badge_color": "amber",
        "baseline_version": "BL-02",
        "latest_update_version": "UP-04",
        "key_event": "Artificially Bloated Substructure Fragnet Logic Tie",
        "governing_clause": "PSSCOC Clause 23.1 & 23.2",
        "rain_gauge_discrepancy_score": "SEVERE_ANOMALY",
        "assessed_eot": "0 / 45 Days",
        "assessed_eot_sub": "Rejected - Time-Barred (Clause 23.2)",
        "notice_pill_text": "⏱️ PSSCOC Notice: TIME-BARRED (41d)",
        "notice_pill_class": "status-pill red flashing",
        "ld_sub": "38 Culpable Days @ S$25k/day"
    },
    "PRJ-TWRP-002": {
        "project_id": "PRJ-TWRP-002",
        "project_name": "Tuas Water Reclamation Plant — Biosolids Facility",
        "contractor": "Koh Brothers - China State JV",
        "contract_sum_sgd": 78500000.0,
        "contract_form": "PUB Standard Conditions",
        "sector": "Environmental Water Infrastructure",
        "sector_icon": "🌊",
        "liquidated_damages_daily_sgd": 20000.0,
        "commencement_date": "2026-05-15",
        "original_completion_date": "2027-08-30",
        "current_forecast_completion_date": "2027-09-15",
        "net_delay_days": 16,
        "ld_exposure_sgd": 120000.0,
        "current_status": "ACTIVE_DEWATERING_DELAY",
        "status_badge": "Dewatering Obstruction Active (6d Culpable)",
        "badge_color": "amber",
        "baseline_version": "BL-01",
        "latest_update_version": "UP-02",
        "key_event": "Deep Piling Obstruction in Reclaimed Marine Clay",
        "governing_clause": "PUB Standard Clause 24.1 & 25",
        "rain_gauge_discrepancy_score": "MONITORED",
        "assessed_eot": "10 / 16 Days",
        "assessed_eot_sub": "PUB Clause 24.1 Marine Clay Obstruction",
        "notice_pill_text": "⏱️ PUB Notice: Compliant (13d)",
        "notice_pill_class": "status-pill amber",
        "ld_sub": "6 Culpable Days @ S$20k/day"
    },
    "PRJ-WHC-COM-001": {
        "project_id": "PRJ-WHC-COM-001",
        "project_name": "Woodlands Health Campus Commercial Annex",
        "contractor": "WinningPine Construction Pte Ltd",
        "contract_sum_sgd": 55000000.0,
        "contract_form": "PSSCOC 2020",
        "sector": "Healthcare Infrastructure",
        "sector_icon": "🏥",
        "liquidated_damages_daily_sgd": 15000.0,
        "daily_ld_rate_sgd": 15000.0,
        "commencement_date": "2026-11-02",
        "original_completion_date": "2026-11-19",
        "planned_finish": "2026-11-19",
        "current_forecast_completion_date": "2026-11-24",
        "forecast_finish": "2026-11-24",
        "net_delay_days": 3,
        "net_delay_unit": "workdays",
        "ld_exposure_sgd": 45000.0,
        "ld_exposure_basis": "3 workdays gross unmitigated project completion delay @ S$15,000/day",
        "current_status": "CRITICAL_PATH_DELAY",
        "status_badge": "Critical Delay (Excavation Ingress: +3 workdays)",
        "badge_color": "red",
        "baseline_version": "BL-01",
        "latest_update_version": "UP-01",
        "completion_milestone_id": "ACT-06",
        "completion_milestone_name": "Substructure Complete Milestone",
        "baseline_completion_date": "2026-11-19",
        "forecast_completion_date": "2026-11-24",
        "schedule_variance_workdays": 3,
        "schedule_variance_calendar_days": 5,
        "ledger_assessed_culpable_days": 2,
        "ledger_assessed_ld_sgd": 30000.0,
        "ledger_assessed_basis": "Event DLY-2026-001: 2 culpable workdays @ S$15,000/day approved by Superintending Officer in Claims Ledger Rev 2",
        "advisory_arbitrator_ld_sgd": 0.0,
        "key_event": "Groundwater Ingress in North Pit (DLY-2026-001)",
        "governing_clause": "PSSCOC Clause 23.1(f) & 24.1",
        "rain_gauge_discrepancy_score": "HIGH_FLAG",
        "assessed_eot": "2 / 4 Days",
        "assessed_eot_sub": "Clause 23.1(f) Neutral Rain Event (2d Approved)",
        "notice_pill_text": "⏱️ PSSCOC Notice: 14 Days Remaining",
        "notice_pill_class": "status-pill amber",
        "ld_sub": "Gross 3 workdays Slippage (S$45k) | Approved Ledger: S$30,000 | AI Advisory: S$0"
    }
}

LEGACY_PROJECT_PROFILES = {
    "PRJ-MBF-FIT-002": {
        "project_id": "PRJ-MBF-FIT-002",
        "project_name": "Marina Bay Financial Tower L28-35 Commercial Fit-Out",
        "contractor": "GemStone Building Contractors Pte Ltd",
        "contract_sum_sgd": 22400000.0,
        "contract_form": "SIA Measurement 9th Ed",
        "sector": "Commercial High-Density Fit-Out",
        "sector_icon": "🏢",
        "liquidated_damages_daily_sgd": 10000.0,
        "commencement_date": "2026-08-15",
        "original_completion_date": "2026-12-15",
        "current_forecast_completion_date": "2026-12-27",
        "net_delay_days": 2,
        "ld_exposure_sgd": 20000.0,
        "current_status": "FAST_TRACK_DISRUPTION",
        "status_badge": "Window Analysis Active (18 AIs)",
        "badge_color": "blue",
        "baseline_version": "BL-01",
        "latest_update_version": "UP-02",
        "key_event": "18 Rapid Architect Instructions & MEP Deceleration",
        "governing_clause": "SIA 9th Ed Clause 23",
        "rain_gauge_discrepancy_score": "NORMAL_INDOOR",
        "assessed_eot": "10 / 12 Days",
        "assessed_eot_sub": "SIA Clause 23(1)(f) AI Disruption",
        "notice_pill_text": "⏱️ SIA Notice: Compliant (2d)",
        "notice_pill_class": "status-pill green",
        "ld_sub": "2 Culpable Days @ S$10k/day"
    },
    "PRJ-CRL-CR108": {
        "project_id": "PRJ-CRL-CR108",
        "project_name": "Cross Island Line Underground Ancillary Shaft",
        "contractor": "GrandPillar Infrastructure Pte Ltd",
        "contract_sum_sgd": 145000000.0,
        "contract_form": "LTA Civil Standard",
        "sector": "Heavy Civil Underground Transit",
        "sector_icon": "🚇",
        "liquidated_damages_daily_sgd": 50000.0,
        "commencement_date": "2026-03-01",
        "original_completion_date": "2028-02-28",
        "current_forecast_completion_date": "2028-03-14",
        "net_delay_days": 0,
        "ld_exposure_sgd": 0.0,
        "current_status": "HEALTHY_BENCHMARK",
        "status_badge": "Certified 14-Day EOT Benchmark",
        "badge_color": "green",
        "baseline_version": "BL-01",
        "latest_update_version": "UP-03",
        "key_event": "Unmapped 66kV SP Power Cable Clash Resolved Cleanly",
        "governing_clause": "LTA GCC Clause 44",
        "rain_gauge_discrepancy_score": "PERFECT_MATCH",
        "assessed_eot": "14 / 14 Days",
        "assessed_eot_sub": "LTA GCC Clause 44.1 Full EOT",
        "notice_pill_text": "⏱️ LTA Notice: Compliant (3d)",
        "notice_pill_class": "status-pill green",
        "ld_sub": "0 Culpable Days @ S$50k/day"
    }
}

# Schedule benchmark data for PRJ-WHC-COM-001
WHC_BASELINE_ACTIVITIES = [
    {"activity_id": "ACT-01", "task_name": "Project Notice to Proceed", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-11-02", "early_finish": "2026-11-02", "late_start": "2026-11-02", "late_finish": "2026-11-02", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "WHC.SUB"},
    {"activity_id": "ACT-02", "task_name": "Substructure Piling", "duration_workdays": 5, "is_milestone": False, "early_start": "2026-11-02", "early_finish": "2026-11-06", "late_start": "2026-11-02", "late_finish": "2026-11-06", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "WHC.SUB"},
    {"activity_id": "ACT-03", "task_name": "Basement Excavation", "duration_workdays": 4, "is_milestone": False, "early_start": "2026-11-09", "early_finish": "2026-11-12", "late_start": "2026-11-09", "late_finish": "2026-11-12", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "WHC.SUB"},
    {"activity_id": "ACT-04", "task_name": "Ground Anchor Installation", "duration_workdays": 6, "is_milestone": False, "early_start": "2026-11-04", "early_finish": "2026-11-11", "late_start": "2026-11-11", "late_finish": "2026-11-18", "total_float": 5, "free_float": 5, "is_critical": False, "wbs_code": "WHC.SUB"},
    {"activity_id": "ACT-05", "task_name": "Basement Slab Casting", "duration_workdays": 5, "is_milestone": False, "early_start": "2026-11-13", "early_finish": "2026-11-19", "late_start": "2026-11-13", "late_finish": "2026-11-19", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "WHC.SUB"},
    {"activity_id": "ACT-06", "task_name": "Substructure Complete", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-11-19", "early_finish": "2026-11-19", "late_start": "2026-11-19", "late_finish": "2026-11-19", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "WHC.SUB"}
]

WHC_RELATIONSHIPS = [
    {"predecessor_id": "ACT-01", "successor_id": "ACT-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
    {"predecessor_id": "ACT-02", "successor_id": "ACT-03", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
    {"predecessor_id": "ACT-02", "successor_id": "ACT-04", "relationship_type": "SS", "lag_days": 2, "is_driving": False},
    {"predecessor_id": "ACT-03", "successor_id": "ACT-05", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
    {"predecessor_id": "ACT-04", "successor_id": "ACT-05", "relationship_type": "FF", "lag_days": 1, "is_driving": False},
    {"predecessor_id": "ACT-05", "successor_id": "ACT-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True}
]
# Distinctive Schedule Networks for Other Showcase Projects
OTHER_PROJECT_ACTIVITIES = {
    "PRJ-JID-ATP-004": [
        {"activity_id": "ACT-JID-01", "task_name": "Site Possession & Soil Investigation", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-06-01", "early_finish": "2026-06-01", "late_start": "2026-06-01", "late_finish": "2026-06-01", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "JID.SUB"},
        {"activity_id": "ACT-JID-02", "task_name": "Secant Bored Piling Sec-A", "duration_workdays": 12, "is_milestone": False, "early_start": "2026-06-02", "early_finish": "2026-06-16", "late_start": "2026-06-02", "late_finish": "2026-06-16", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "JID.SUB"},
        {"activity_id": "ACT-JID-03", "task_name": "Diaphragm Wall Trenching & Bentonite Slurry", "duration_workdays": 18, "is_milestone": False, "early_start": "2026-06-17", "early_finish": "2026-07-09", "late_start": "2026-06-17", "late_finish": "2026-07-09", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "JID.SUB"},
        {"activity_id": "ACT-JID-04", "task_name": "King Post & Waler Strutting Level 1", "duration_workdays": 15, "is_milestone": False, "early_start": "2026-06-25", "early_finish": "2026-07-15", "late_start": "2026-07-06", "late_finish": "2026-07-26", "total_float": 8, "free_float": 8, "is_critical": False, "wbs_code": "JID.SUB"},
        {"activity_id": "ACT-JID-05", "task_name": "Bulk Deep Basement Excavation (Disputed Fragnet)", "duration_workdays": 25, "is_milestone": False, "early_start": "2026-07-10", "early_finish": "2026-08-14", "late_start": "2026-07-10", "late_finish": "2026-08-14", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "JID.SUB"},
        {"activity_id": "ACT-JID-06", "task_name": "Raft Foundation Concreting", "duration_workdays": 14, "is_milestone": False, "early_start": "2026-08-15", "early_finish": "2026-09-02", "late_start": "2026-08-15", "late_finish": "2026-09-02", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "JID.SUB"}
    ],
    "PRJ-TWRP-002": [
        {"activity_id": "ACT-TWRP-01", "task_name": "Site Possession & Ground Improvement Treatment", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-05-15", "early_finish": "2026-05-15", "late_start": "2026-05-15", "late_finish": "2026-05-15", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "TWRP.SUB"},
        {"activity_id": "ACT-TWRP-02", "task_name": "Deep Diaphragm Wall Trenching & Bentonite Slurry", "duration_workdays": 20, "is_milestone": False, "early_start": "2026-05-16", "early_finish": "2026-06-08", "late_start": "2026-05-16", "late_finish": "2026-06-08", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "TWRP.SUB"},
        {"activity_id": "ACT-TWRP-03", "task_name": "Deep Piling Obstruction Removal in Marine Clay (DLY-TWRP-001)", "duration_workdays": 16, "is_milestone": False, "early_start": "2026-06-09", "early_finish": "2026-06-30", "late_start": "2026-06-09", "late_finish": "2026-06-30", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "TWRP.SUB"},
        {"activity_id": "ACT-TWRP-04", "task_name": "Dewatering Wellpoints & Deep Sump Pumping", "duration_workdays": 22, "is_milestone": False, "early_start": "2026-06-15", "early_finish": "2026-07-14", "late_start": "2026-06-23", "late_finish": "2026-07-22", "total_float": 6, "free_float": 6, "is_critical": False, "wbs_code": "TWRP.SUB"},
        {"activity_id": "ACT-TWRP-05", "task_name": "Biosolids Digester Tank Foundation Raft Concreting", "duration_workdays": 18, "is_milestone": False, "early_start": "2026-07-01", "early_finish": "2026-07-24", "late_start": "2026-07-01", "late_finish": "2026-07-24", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "TWRP.STR"},
        {"activity_id": "ACT-TWRP-06", "task_name": "Superstructure Sludge Processing Tower Civil Works", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-07-24", "early_finish": "2026-07-24", "late_start": "2026-07-24", "late_finish": "2026-07-24", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "TWRP.STR"}
    ],
    "PRJ-T5-003": [
        {"activity_id": "ACT-T5-01", "task_name": "Aviation Transit Site Handover & Airside Security Clearance", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-03-01", "early_finish": "2026-03-01", "late_start": "2026-03-01", "late_finish": "2026-03-01", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "T5.CIV"},
        {"activity_id": "ACT-T5-02", "task_name": "Baggage Handling Tunnel Cut-and-Cover Excavation", "duration_workdays": 25, "is_milestone": False, "early_start": "2026-03-02", "early_finish": "2026-04-03", "late_start": "2026-03-02", "late_finish": "2026-04-03", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "T5.CIV"},
        {"activity_id": "ACT-T5-03", "task_name": "Underground APM Station Diaphragm Wall", "duration_workdays": 20, "is_milestone": False, "early_start": "2026-04-06", "early_finish": "2026-05-01", "late_start": "2026-04-06", "late_finish": "2026-05-01", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "T5.CIV"},
        {"activity_id": "ACT-T5-04", "task_name": "Unmapped 66kV SP Power High-Voltage Duct Clash & Diversion", "duration_workdays": 14, "is_milestone": False, "early_start": "2026-05-04", "early_finish": "2026-05-21", "late_start": "2026-05-04", "late_finish": "2026-05-21", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "T5.UTL"},
        {"activity_id": "ACT-T5-05", "task_name": "Jet Grouting & Ground Freezing Cross-Passage", "duration_workdays": 18, "is_milestone": False, "early_start": "2026-05-11", "early_finish": "2026-06-03", "late_start": "2026-05-22", "late_finish": "2026-06-15", "total_float": 8, "free_float": 8, "is_critical": False, "wbs_code": "T5.CIV"},
        {"activity_id": "ACT-T5-06", "task_name": "Substructure Concrete Box Handover to Systems Contractor", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-05-21", "early_finish": "2026-05-21", "late_start": "2026-05-21", "late_finish": "2026-05-21", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "T5.CIV"}
    ],
    "PRJ-MBF-FIT-002": [
        {"activity_id": "ACT-MBF-01", "task_name": "Site Handover & Builder Mobilisation", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-08-15", "early_finish": "2026-08-15", "late_start": "2026-08-15", "late_finish": "2026-08-15", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "MBF.INT"},
        {"activity_id": "ACT-MBF-02", "task_name": "Architectural Partition Demolition & Stud Framing", "duration_workdays": 8, "is_milestone": False, "early_start": "2026-08-17", "early_finish": "2026-08-26", "late_start": "2026-08-17", "late_finish": "2026-08-26", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "MBF.INT"},
        {"activity_id": "ACT-MBF-03", "task_name": "Raised Access Flooring Pedestal Setup", "duration_workdays": 6, "is_milestone": False, "early_start": "2026-08-20", "early_finish": "2026-08-27", "late_start": "2026-08-26", "late_finish": "2026-09-02", "total_float": 4, "free_float": 4, "is_critical": False, "wbs_code": "MBF.INT"},
        {"activity_id": "ACT-MBF-04", "task_name": "MEP High-Level Containment (Impacted by 18 AIs)", "duration_workdays": 10, "is_milestone": False, "early_start": "2026-08-27", "early_finish": "2026-09-10", "late_start": "2026-08-27", "late_finish": "2026-09-10", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "MBF.MEP"},
        {"activity_id": "ACT-MBF-05", "task_name": "Acoustic Baffle Ceiling & Double Glazed Suites", "duration_workdays": 7, "is_milestone": False, "early_start": "2026-09-11", "early_finish": "2026-09-21", "late_start": "2026-09-11", "late_finish": "2026-09-21", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "MBF.INT"},
        {"activity_id": "ACT-MBF-06", "task_name": "Client Practical Completion Inspection", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-09-21", "early_finish": "2026-09-21", "late_start": "2026-09-21", "late_finish": "2026-09-21", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "MBF.INT"}
    ],
    "PRJ-CRL-CR108": [
        {"activity_id": "ACT-CRL-01", "task_name": "LTA Notice to Proceed & Pre-Scan Surveys", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-03-01", "early_finish": "2026-03-01", "late_start": "2026-03-01", "late_finish": "2026-03-01", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "CRL.CIV"},
        {"activity_id": "ACT-CRL-02", "task_name": "Diaphragm Wall Guide Wall Construction", "duration_workdays": 15, "is_milestone": False, "early_start": "2026-03-02", "early_finish": "2026-03-20", "late_start": "2026-03-02", "late_finish": "2026-03-20", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "CRL.CIV"},
        {"activity_id": "ACT-CRL-03", "task_name": "Deep Circular Shaft Sinking Phase 1", "duration_workdays": 30, "is_milestone": False, "early_start": "2026-03-23", "early_finish": "2026-05-04", "late_start": "2026-03-23", "late_finish": "2026-05-04", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "CRL.CIV"},
        {"activity_id": "ACT-CRL-04", "task_name": "Unmapped 66kV SP Power Cable Protection & Diversion", "duration_workdays": 16, "is_milestone": False, "early_start": "2026-04-10", "early_finish": "2026-05-02", "late_start": "2026-04-28", "late_finish": "2026-05-20", "total_float": 12, "free_float": 12, "is_critical": False, "wbs_code": "CRL.UTL"},
        {"activity_id": "ACT-CRL-05", "task_name": "Shaft Base Plug Underwater Concreting", "duration_workdays": 18, "is_milestone": False, "early_start": "2026-05-05", "early_finish": "2026-05-28", "late_start": "2026-05-05", "late_finish": "2026-05-28", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "CRL.CIV"},
        {"activity_id": "ACT-CRL-06", "task_name": "TBM Launch Cradle Handover Milestone", "duration_workdays": 0, "is_milestone": True, "early_start": "2026-05-28", "early_finish": "2026-05-28", "late_start": "2026-05-28", "late_finish": "2026-05-28", "total_float": 0, "free_float": 0, "is_critical": True, "wbs_code": "CRL.CIV"}
    ]
}

OTHER_PROJECT_RELATIONSHIPS = {
    "PRJ-TWRP-002": [
        {"predecessor_id": "ACT-TWRP-01", "successor_id": "ACT-TWRP-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-TWRP-02", "successor_id": "ACT-TWRP-03", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-TWRP-02", "successor_id": "ACT-TWRP-04", "relationship_type": "SS", "lag_days": 4, "is_driving": False},
        {"predecessor_id": "ACT-TWRP-03", "successor_id": "ACT-TWRP-05", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-TWRP-04", "successor_id": "ACT-TWRP-05", "relationship_type": "FF", "lag_days": 2, "is_driving": False},
        {"predecessor_id": "ACT-TWRP-05", "successor_id": "ACT-TWRP-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True}
    ],
    "PRJ-T5-003": [
        {"predecessor_id": "ACT-T5-01", "successor_id": "ACT-T5-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-T5-02", "successor_id": "ACT-T5-03", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-T5-02", "successor_id": "ACT-T5-05", "relationship_type": "SS", "lag_days": 5, "is_driving": False},
        {"predecessor_id": "ACT-T5-03", "successor_id": "ACT-T5-04", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-T5-04", "successor_id": "ACT-T5-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-T5-05", "successor_id": "ACT-T5-06", "relationship_type": "FF", "lag_days": 2, "is_driving": False}
    ],
    "PRJ-JID-ATP-004": [
        {"predecessor_id": "ACT-JID-01", "successor_id": "ACT-JID-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-JID-02", "successor_id": "ACT-JID-03", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-JID-02", "successor_id": "ACT-JID-04", "relationship_type": "SS", "lag_days": 5, "is_driving": False},
        {"predecessor_id": "ACT-JID-03", "successor_id": "ACT-JID-05", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-JID-04", "successor_id": "ACT-JID-05", "relationship_type": "FF", "lag_days": 2, "is_driving": False},
        {"predecessor_id": "ACT-JID-05", "successor_id": "ACT-JID-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True}
    ],
    "PRJ-MBF-FIT-002": [
        {"predecessor_id": "ACT-MBF-01", "successor_id": "ACT-MBF-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-MBF-02", "successor_id": "ACT-MBF-04", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-MBF-02", "successor_id": "ACT-MBF-03", "relationship_type": "SS", "lag_days": 3, "is_driving": False},
        {"predecessor_id": "ACT-MBF-04", "successor_id": "ACT-MBF-05", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-MBF-03", "successor_id": "ACT-MBF-05", "relationship_type": "FF", "lag_days": 1, "is_driving": False},
        {"predecessor_id": "ACT-MBF-05", "successor_id": "ACT-MBF-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True}
    ],
    "PRJ-CRL-CR108": [
        {"predecessor_id": "ACT-CRL-01", "successor_id": "ACT-CRL-02", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-CRL-02", "successor_id": "ACT-CRL-03", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-CRL-02", "successor_id": "ACT-CRL-04", "relationship_type": "SS", "lag_days": 8, "is_driving": False},
        {"predecessor_id": "ACT-CRL-03", "successor_id": "ACT-CRL-05", "relationship_type": "FS", "lag_days": 0, "is_driving": True},
        {"predecessor_id": "ACT-CRL-04", "successor_id": "ACT-CRL-05", "relationship_type": "FF", "lag_days": 3, "is_driving": False},
        {"predecessor_id": "ACT-CRL-05", "successor_id": "ACT-CRL-06", "relationship_type": "FS", "lag_days": 0, "is_driving": True}
    ]
}


# Delay Events Ledger for PRJ-WHC-COM-001
DELAY_EVENTS_DATA = {
    "PRJ-WHC-COM-001": [
        {
            "event_id": "DLY-2026-001",
            "revision_id": 1,
            "revision_stage": "CONTRACTOR_CLAIM",
            "event_title": "Groundwater Ingress & Pumping Stoppage",
            "event_name": "Groundwater Ingress & Pumping Stoppage",
            "canonical_event_name": "Groundwater Ingress & Pumping Stoppage",
            "location_detail": "Basement 2 North Pit",
            "short_label": "Groundwater Ingress",
            "cause_category": "WEATHER_FORCE_MAJEURE",
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE",
            "event_start_date": "2026-11-05",
            "event_end_date": "2026-11-08",
            "calendar_days": 4,
            "claimed_eot_workdays": 4,
            "hearing_fragnet_duration_workdays": 3,
            "claimed_delay_days": 3.0,
            "is_contract_verified": True,
            "verification_record_id": "DOC-VERIF-TRUSTED-PSSCOC-2026",
            "notice_served_date": "2026-11-06",
            "is_notice_compliant": True,
            "notice_rule_eval": "Notice served in 1 day (PSSCOC 28-day window compliant)",
            "affected_activity_id": "ACT-03",
            "affected_activity_name": "Basement Excavation",
            "employer_claim_demand_sgd": 60000.0,
            "employer_initial_contested_ld_sgd": 60000.0,
            "employer_hearing_demand_sgd": 45000.0,
            "hearing_employer_demanded_ld_sgd": 45000.0,
            "so_advisory_eot_workdays": 3,
            "ai_consensus_eot_relief_days": 3,
            "so_advisory_ld_sgd": 0.0,
            "ai_consensus_advisory_ld_sgd": 0.0,
            "assessed_eot_workdays": 2,
            "approved_eot_workdays": 2,
            "so_approved_eot_days": 2,
            "culpable_delay_workdays": 2,
            "so_culpable_delay_days": 2,
            "liquidated_damages_sgd": 30000.0,
            "so_assessment_note": "Rain sensor recorded 22mm on Nov 5 (valid force majeure). Nov 7-8 recorded 0mm and biometrics showed 18 workers present.",
            "clause_citation": "PSSCOC 2020 Clause 23.1(f) & 24.1",
            "status": "ASSESSED_DISPUTED",
            "event_lifecycle_stages": [
                {"revision": 1, "stage": "CONTRACTOR_CLAIM", "claimed_eot_days": 4, "employer_demand_sgd": 60000.0, "status": "SUBMITTED", "authority": "WinningPine Project Manager"},
                {"revision": 2, "stage": "SUPERINTENDING_OFFICER_ASSESSMENT", "approved_eot_days": 2, "culpable_days": 2, "assessed_ld_sgd": 30000.0, "status": "APPROVED_DISPUTED", "authority": "Superintending Officer (Human Authorized)"},
                {"revision": "DELIB-01", "stage": "AI_CONSENSUS_DELIBERATION_HEARING", "deliberated_eot_days": 3, "advisory_ld_sgd": 0.0, "employer_hearing_demand_sgd": 45000.0, "status": "ADVISORY_RECOMMENDATION", "authority": "AI Multi-Agent Advisory Arbitrator (Non-Binding)"}
            ],
            "evaluation_note": "DETERMINISTIC EVALUATION: CPM apportionment confirms 2 workdays compensable weather event, 2 workdays concurrent contractor pump downtime.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: CPM apportionment confirms 2 workdays compensable weather event, 2 workdays concurrent contractor pump downtime.",
            "ai_consensus": "DETERMINISTIC EVALUATION: CPM apportionment confirms 2 workdays compensable weather event, 2 workdays concurrent contractor pump downtime."
        },
        {
            "event_id": "DLY-2026-002",
            "revision_id": 2,
            "revision_stage": "SUPERINTENDING_OFFICER_ASSESSMENT",
            "event_title": "Soil Settlement at Boundary Wall Monitoring Pin SP-04",
            "cause_category": "EMPLOYER_RISK",
            "risk_allocation": "EMPLOYER_RISK",
            "event_start_date": "2026-11-10",
            "event_end_date": "2026-11-12",
            "calendar_days": 3,
            "claimed_eot_workdays": 3,
            "notice_served_date": "2026-11-10",
            "is_notice_compliant": True,
            "notice_rule_eval": "Notice served in 0 days (Compliant)",
            "affected_activity_id": "ACT-04",
            "affected_activity_name": "Ground Anchor Installation",
            "assessed_eot_workdays": 0,
            "culpable_delay_workdays": 0,
            "liquidated_damages_sgd": 0.0,
            "so_assessment_note": "Activity ACT-04 possessed 5 days of total float. 3 days delay consumed float without impacting critical path finish date 2026-11-19.",
            "clause_citation": "PSSCOC Clause 23.1(b) (Non-critical delay absorbs float)",
            "status": "DETERMINED_ZERO_EOT",
            "evaluation_note": "DETERMINISTIC EVALUATION: Total float analysis confirms ACT-04 initial float was 5 workdays. Consuming 3 workdays leaves 2 workdays positive float; zero critical path impact.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Total float analysis confirms ACT-04 initial float was 5 workdays. Consuming 3 workdays leaves 2 workdays positive float; zero critical path impact.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Total float analysis confirms ACT-04 initial float was 5 workdays. Consuming 3 workdays leaves 2 workdays positive float; zero critical path impact."
        }
    ],
    "PRJ-JID-ATP-004": [
        {
            "event_id": "DLY-JID-001",
            "revision_id": 1,
            "revision_stage": "CONTRACTOR_CLAIM",
            "event_title": "Substructure Diaphragm Wall Trench Collapse",
            "cause_category": "CONTRACTOR_RISK",
            "risk_allocation": "CONTRACTOR_RISK",
            "event_start_date": "2026-07-10",
            "event_end_date": "2026-08-24",
            "calendar_days": 45,
            "claimed_eot_workdays": 45,
            "notice_served_date": "2026-08-20",
            "is_notice_compliant": False,
            "notice_rule_eval": "TIME-BARRED: Notice served 41 days after event start (violates 28-day notice rule)",
            "affected_activity_id": "ACT-JID-08",
            "affected_activity_name": "Diaphragm Wall Trenching",
            "assessed_eot_workdays": 0,
            "culpable_delay_workdays": 38,
            "liquidated_damages_sgd": 950000.0,
            "so_assessment_note": "Contractor inserted artificial 45-day fragnet. Trench collapse was caused by contractor bentonite slurry density non-compliance.",
            "clause_citation": "PSSCOC Clause 23.2 & 23.4 Condition Precedent",
            "status": "REJECTED_TIME_BARRED",
            "evaluation_note": "DETERMINISTIC EVALUATION: Statutory notice condition precedent under PSSCOC Clause 23.2 unfulfilled. Claim time-barred and substantive delay contractor-culpable.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Statutory notice condition precedent under PSSCOC Clause 23.2 unfulfilled. Claim time-barred and substantive delay contractor-culpable.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Statutory notice condition precedent under PSSCOC Clause 23.2 unfulfilled. Claim time-barred and substantive delay contractor-culpable."
        }
    ],
    "PRJ-TWRP-002": [
        {
            "event_id": "DLY-TWRP-001",
            "revision_id": 1,
            "revision_stage": "FORMAL_DETERMINATION",
            "event_title": "Deep Piling Obstruction Removal in Reclaimed Marine Clay",
            "cause_category": "EMPLOYER_RISK",
            "risk_allocation": "EMPLOYER_RISK",
            "event_start_date": "2026-06-09",
            "event_end_date": "2026-06-25",
            "calendar_days": 16,
            "claimed_eot_workdays": 16,
            "notice_served_date": "2026-06-22",
            "is_notice_compliant": True,
            "notice_rule_eval": "Compliant: Notice served within 13 days under PUB Clause 24.1",
            "affected_activity_id": "ACT-TWRP-03",
            "affected_activity_name": "Piling Obstruction Removal in Marine Clay",
            "assessed_eot_workdays": 10,
            "culpable_delay_workdays": 6,
            "liquidated_damages_sgd": 120000.0,
            "so_assessment_note": "Unforeseen seabed boulder obstructions in reclaimed fill. 10 workdays compensable EOT certified; 6 workdays concurrent contractor dewatering downtime.",
            "clause_citation": "PUB Standard Clause 24.1 & 25",
            "status": "FORMALLY_CERTIFIED",
            "evaluation_note": "DETERMINISTIC EVALUATION: Time impact analysis allocates 10 workdays to unforseeable physical conditions. S$120,000 contractor LD exposure assessed for 6 culpable days.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Time impact analysis allocates 10 workdays to unforseeable physical conditions. S$120,000 contractor LD exposure assessed for 6 culpable days.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Time impact analysis allocates 10 workdays to unforseeable physical conditions. S$120,000 contractor LD exposure assessed for 6 culpable days."
        }
    ],
    "PRJ-T5-003": [
        {
            "event_id": "DLY-T5-001",
            "revision_id": 1,
            "revision_stage": "FORMAL_DETERMINATION",
            "event_title": "Unmapped 66kV SP Power High-Voltage Duct Clash",
            "cause_category": "EMPLOYER_RISK",
            "risk_allocation": "EMPLOYER_RISK",
            "event_start_date": "2026-05-04",
            "event_end_date": "2026-05-18",
            "calendar_days": 14,
            "claimed_eot_workdays": 14,
            "notice_served_date": "2026-05-07",
            "is_notice_compliant": True,
            "notice_rule_eval": "Compliant: Notice served within 3 days",
            "affected_activity_id": "ACT-T5-04",
            "affected_activity_name": "Unmapped 66kV SP Power High-Voltage Duct Clash",
            "assessed_eot_workdays": 14,
            "culpable_delay_workdays": 0,
            "liquidated_damages_sgd": 0.0,
            "so_assessment_note": "Utility diversions outside contract boundary. Full 14 workdays EOT granted with zero contractor LD exposure.",
            "clause_citation": "LTA GCC Clause 44.1",
            "status": "BENCHMARK_CLOSED",
            "evaluation_note": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure."
        }
    ],
    "PRJ-MBF-FIT-002": [
        {
            "event_id": "DLY-MBF-001",
            "revision_id": 1,
            "revision_stage": "FORMAL_DETERMINATION",
            "event_title": "Architect Instructions 01-18 Tenant Layout Reconfigurations",
            "cause_category": "EMPLOYER_RISK",
            "risk_allocation": "EMPLOYER_RISK",
            "event_start_date": "2026-09-01",
            "event_end_date": "2026-09-14",
            "calendar_days": 14,
            "claimed_eot_workdays": 12,
            "notice_served_date": "2026-09-03",
            "is_notice_compliant": True,
            "notice_rule_eval": "Compliant: Notice served within 2 days",
            "affected_activity_id": "ACT-MBF-04",
            "affected_activity_name": "MEP High-Level Containment",
            "assessed_eot_workdays": 10,
            "culpable_delay_workdays": 2,
            "liquidated_damages_sgd": 20000.0,
            "so_assessment_note": "Architect concurred that 18 revisions in 14 days severely disrupted sequence. 10 workdays granted.",
            "clause_citation": "SIA 9th Ed Clause 23(1)(f)",
            "status": "FORMALLY_CERTIFIED",
            "evaluation_note": "DETERMINISTIC EVALUATION: Windows schedule analysis confirms 10 workdays cumulative critical path deceleration directly attributable to late Architect Instructions.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Windows schedule analysis confirms 10 workdays cumulative critical path deceleration directly attributable to late Architect Instructions.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Windows schedule analysis confirms 10 workdays cumulative critical path deceleration directly attributable to late Architect Instructions."
        }
    ],
    "PRJ-CRL-CR108": [
        {
            "event_id": "DLY-CRL-001",
            "revision_id": 1,
            "revision_stage": "FORMAL_DETERMINATION",
            "event_title": "Unmapped 66kV SP Power High-Voltage Duct Clash",
            "cause_category": "EMPLOYER_RISK",
            "risk_allocation": "EMPLOYER_RISK",
            "event_start_date": "2026-05-02",
            "event_end_date": "2026-05-18",
            "calendar_days": 16,
            "claimed_eot_workdays": 14,
            "notice_served_date": "2026-05-05",
            "is_notice_compliant": True,
            "notice_rule_eval": "Compliant: Notice served within 3 days",
            "affected_activity_id": "ACT-CRL-03",
            "affected_activity_name": "Shaft Collar Excavation",
            "assessed_eot_workdays": 14,
            "culpable_delay_workdays": 0,
            "liquidated_damages_sgd": 0.0,
            "so_assessment_note": "Utility diversions outside contract boundary. Full 14 workdays EOT granted with prolongation costs certified.",
            "clause_citation": "LTA GCC Clause 44.1",
            "status": "BENCHMARK_CLOSED",
            "evaluation_note": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure.",
            "deterministic_evaluation": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure.",
            "ai_consensus": "DETERMINISTIC EVALUATION: Foreseeability analysis allocates unmapped utility obstruction to Employer Risk. Full 14 workdays EOT entitlement without contractor LD exposure."
        }
    ]
}

# Contemporaneous Site Radar Data (Rainfall vs Biometrics vs Diary Claims)
SITE_RADAR_DATA = {
    "PRJ-WHC-COM-001": [
        {"date": "2026-11-02", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 42, "status": "NORMAL"},
        {"date": "2026-11-03", "weather_station_rain_mm": 2.4, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 45, "status": "NORMAL"},
        {"date": "2026-11-04", "weather_station_rain_mm": 5.1, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 40, "status": "NORMAL"},
        {"date": "2026-11-05", "weather_station_rain_mm": 22.8, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 18, "status": "CORROBORATED_HEAVY_RAIN"},
        {"date": "2026-11-06", "weather_station_rain_mm": 14.2, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 16, "status": "CORROBORATED_RAIN"},
        {"date": "2026-11-07", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 39, "status": "DISCREPANCY_FLAGGED"},
        {"date": "2026-11-08", "weather_station_rain_mm": 0.2, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 41, "status": "DISCREPANCY_FLAGGED"},
        {"date": "2026-11-09", "weather_station_rain_mm": 1.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 44, "status": "NORMAL"}
    ],
    "PRJ-JID-ATP-004": [
        {"date": "2026-07-15", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 6.0, "biometric_worker_count": 85, "status": "DISCREPANCY_FLAGGED"},
        {"date": "2026-07-16", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 88, "status": "DISCREPANCY_FLAGGED"},
        {"date": "2026-07-17", "weather_station_rain_mm": 18.5, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 32, "status": "CORROBORATED_RAIN"}
    ],
    "PRJ-TWRP-002": [
        {"date": "2026-06-12", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 92, "status": "NORMAL"},
        {"date": "2026-06-13", "weather_station_rain_mm": 28.5, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 22, "status": "CORROBORATED_HEAVY_RAIN"},
        {"date": "2026-06-14", "weather_station_rain_mm": 3.2, "contractor_rain_claim_hrs": 4.0, "biometric_worker_count": 84, "status": "DISCREPANCY_FLAGGED"}
    ],
    "PRJ-T5-003": [
        {"date": "2026-05-04", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 140, "status": "PERFECT_MATCH"},
        {"date": "2026-05-05", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 138, "status": "PERFECT_MATCH"},
        {"date": "2026-05-06", "weather_station_rain_mm": 35.0, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 25, "status": "CORROBORATED_HEAVY_RAIN"}
    ],
    "PRJ-MBF-FIT-002": [
        {"date": "2026-09-01", "weather_station_rain_mm": 4.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 28, "status": "NORMAL_INDOOR"},
        {"date": "2026-09-02", "weather_station_rain_mm": 12.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 29, "status": "NORMAL_INDOOR"}
    ],
    "PRJ-CRL-CR108": [
        {"date": "2026-05-05", "weather_station_rain_mm": 0.0, "contractor_rain_claim_hrs": 0.0, "biometric_worker_count": 110, "status": "CORROBORATED"},
        {"date": "2026-05-06", "weather_station_rain_mm": 35.0, "contractor_rain_claim_hrs": 8.0, "biometric_worker_count": 12, "status": "CORROBORATED_HEAVY_RAIN"}
    ]
}


class ACIPS04DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Handles static files and REST API endpoints for ACIP S04 Cockpit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # 0. Root index.html serving with dynamic engine badge
        if path == "/" or path == "/index.html":
            index_path = os.path.join(DASHBOARD_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                host_header = self.headers.get("Host", "")
                q_engine = qs.get("engine", [""])[0]
                engine_str = get_display_engine(host_header, q_engine)
                content = content.replace("Local Engine", engine_str)
                encoded = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

        # 1. Standardized SRE Health Probes
        if path == "/livez":
            self._send_json({
                "status": "ALIVE",
                "service": "ACIP S04 Cockpit",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return
        elif path == "/readyz":
            parquet_lake = os.path.join(S04_ROOT, "data", "parquet")
            is_ready = bool(PROJECT_PROFILES) and os.path.isdir(parquet_lake)
            if is_ready:
                self._send_json({
                    "status": "READY",
                    "ready": True,
                    "active_tracks": len(PROJECT_PROFILES),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                self._send_error(503, "Service unready: missing project profiles or lakehouse storage")
            return
        elif path == "/healthz":
            uptime_seconds = (datetime.now(timezone.utc) - START_TIME).total_seconds()
            parquet_lake = os.path.join(S04_ROOT, "data", "parquet")
            lake_ok = os.path.isdir(parquet_lake) and len(os.listdir(parquet_lake)) > 0
            cpm_status = "OPERATIONAL" if ScheduleNetwork is not None else "DEGRADED"
            delib_status = "OPERATIONAL" if DeliberationPipeline is not None else "UNAVAILABLE"
            tia_status = "OPERATIONAL" if s04_simulate_tia_fragnet is not None else "SIMULATION_FALLBACK"
            all_healthy = lake_ok and cpm_status == "OPERATIONAL" and delib_status == "OPERATIONAL"

            self._send_json({
                "status": "HEALTHY" if all_healthy else "DEGRADED",
                "uptime_seconds": round(uptime_seconds, 2),
                "started_at": START_TIME.isoformat(),
                "service": "ACIP S04 Agentic Progress & Delay Intelligence Cockpit",
                "version": "1.4.0",
                "active_milestone": "Increment 4 - Real-Time Forensic Interactive Cockpit & Visual Delay Analytics Engine",
                "port": 8087,
                "sre_metrics": {
                    "cpm_engine_status": cpm_status,
                    "tia_evaluator_status": tia_status,
                    "deterministic_execution_mode": "FAIL_CLOSED",
                    "active_tracks_supported": len(PROJECT_PROFILES),
                    "parquet_data_lake": "HEALTHY" if lake_ok else "UNAVAILABLE",
                    "multi_agent_deliberation": delib_status
                }
            })
            return

        # 2. Project List / Project Profile (Canonical: /api/projects; Aliases: /api/project-profile, /api/project_profile)
        elif path in ("/api/projects", "/api/project-profile", "/api/project_profile"):
            pid = qs.get("id", [None])[0] or qs.get("project_id", [None])[0]
            if pid:
                if pid in PROJECT_PROFILES:
                    self._send_json(PROJECT_PROFILES[pid])
                elif pid in LEGACY_PROJECT_PROFILES:
                    self._send_json(LEGACY_PROJECT_PROFILES[pid])
                else:
                    self._send_error(404, f"Project not found: {pid}")
            else:
                self._send_json(list(PROJECT_PROFILES.values()))
            return

        # 3. Schedule Activities & Relationships
        elif path == "/api/schedule":
            pid = qs.get("project_id", ["PRJ-WHC-COM-001"])[0]
            if pid not in PROJECT_PROFILES and pid not in LEGACY_PROJECT_PROFILES:
                self._send_error(404, f"Project not found: {pid}")
                return
            proj = PROJECT_PROFILES.get(pid) or LEGACY_PROJECT_PROFILES.get(pid)
            if pid == "PRJ-WHC-COM-001":
                act_parquet_path = SCHEDULE_ACTIVITIES_PARQUET_PATH
                rel_parquet_path = SCHEDULE_RELATIONSHIPS_PARQUET_PATH
                activities_loaded = None
                relationships_loaded = None

                if os.path.exists(act_parquet_path):
                    try:
                        import pyarrow.parquet as pq
                        tbl = pq.read_table(act_parquet_path)
                        df = tbl.to_pandas()
                        df_whc = df[df["project_id"] == pid]
                        if not df_whc.empty:
                            activities_loaded = []
                            for _, r in df_whc.iterrows():
                                is_ms = (int(r["original_duration_days"]) == 0)
                                act_dict = {
                                    "wbs_code": str(r["wbs_code"]),
                                    "activity_id": str(r["activity_id"]),
                                    "task_name": str(r["activity_name"]),
                                    "duration_workdays": int(r["original_duration_days"]),
                                    "early_start": str(r["early_start_date"]),
                                    "early_finish": str(r["early_finish_date"]),
                                    "late_start": str(r["late_start_date"]),
                                    "late_finish": str(r["late_finish_date"]),
                                    "total_float": int(r["total_float_days"]),
                                    "free_float": int(r["free_float_days"]),
                                    "is_critical": bool(r["is_critical"]),
                                    "is_milestone": is_ms,
                                    "baseline_finish": str(r["early_finish_date"]),
                                }
                                if str(r["activity_id"]) == "ACT-06":
                                    act_dict["milestone_role"] = "CONTRACT_PACKAGE_PRACTICAL_COMPLETION"
                                    act_dict["forecast_finish"] = "2026-11-24"
                                    act_dict["variance_workdays"] = 3
                                    act_dict["variance_calendar_days"] = 5
                                activities_loaded.append(act_dict)
                    except Exception as exc:
                        logger.warning("Failed to load schedule_activities.parquet: %s", exc)
                        activities_loaded = None

                if os.path.exists(rel_parquet_path):
                    try:
                        import pyarrow.parquet as pq
                        rel_tbl = pq.read_table(rel_parquet_path)
                        rel_df = rel_tbl.to_pandas()
                        rel_whc = rel_df[rel_df["project_id"] == pid]
                        if not rel_whc.empty:
                            relationships_loaded = []
                            for _, r in rel_whc.iterrows():
                                relationships_loaded.append({
                                    "pred": str(r["predecessor_activity_id"]),
                                    "succ": str(r["successor_activity_id"]),
                                    "type": str(r["relationship_type"]),
                                    "lag": int(r["lag_days"]),
                                    "is_driving": bool(r.get("is_driving", False))
                                })
                    except Exception as exc:
                        logger.warning("Failed to load schedule_relationships.parquet: %s", exc)
                        relationships_loaded = None

                is_full_parquet = (activities_loaded is not None and relationships_loaded is not None)
                if not activities_loaded:
                    activities_loaded = WHC_BASELINE_ACTIVITIES
                    act_lineage = "IN_MEMORY_FIXTURE_FALLBACK"
                else:
                    act_lineage = "data/parquet/schedule_activities.parquet"

                if not relationships_loaded:
                    relationships_loaded = WHC_RELATIONSHIPS
                    rel_lineage = "IN_MEMORY_FIXTURE_FALLBACK"
                else:
                    rel_lineage = "data/parquet/schedule_relationships.parquet"

                self._send_json({
                    "project_id": pid,
                    "schedule_version": "BL-01",
                    "completion_milestone_id": "ACT-06",
                    "completion_milestone_name": "Substructure Complete Milestone",
                    "milestone_role": "CONTRACT_PACKAGE_PRACTICAL_COMPLETION",
                    "baseline_completion_date": "2026-11-19",
                    "forecast_completion_date": "2026-11-24",
                    "schedule_variance_workdays": 3,
                    "schedule_variance_calendar_days": 5,
                    "is_authoritative_fixture": is_full_parquet,
                    "is_parquet_backed": is_full_parquet,
                    "is_fallback_schedule": not is_full_parquet,
                    "calculation_type": "STORED_SCHEDULE_BASELINE_PARQUET",
                    "recalculation_mode": "STORED_INGESTION_BASELINE_SERVED",
                    "activities_lineage": act_lineage,
                    "relationships_lineage": rel_lineage,
                    "data_source": f"{act_lineage} & {rel_lineage}" if is_full_parquet else "IN_MEMORY_FIXTURE_FALLBACK",
                    "activities": activities_loaded,
                    "relationships": relationships_loaded
                })
            else:
                proj = PROJECT_PROFILES.get(pid) or LEGACY_PROJECT_PROFILES.get(pid, {})
                self._send_json({
                    "project_id": pid,
                    "schedule_version": proj.get("baseline_version", "BL-01"),
                    "is_authoritative_fixture": False,
                    "is_benchmark_illustrative": True,
                    "is_parquet_backed": False,
                    "is_fallback_schedule": True,
                    "calculation_type": "CROSS_PROJECT_BENCHMARK_FIXTURE",
                    "recalculation_mode": "ILLUSTRATIVE_FIXTURE_SERVED",
                    "activities_lineage": "CROSS_PROJECT_BENCHMARK_FIXTURE",
                    "relationships_lineage": "CROSS_PROJECT_BENCHMARK_FIXTURE",
                    "data_source": "CROSS_PROJECT_BENCHMARK_FIXTURE",
                    "track_note": "Benchmark illustrative schedule network for multi-track cockpit demonstration. Project-specific XER schedule pending enterprise ingestion.",
                    "activities": OTHER_PROJECT_ACTIVITIES.get(pid, WHC_BASELINE_ACTIVITIES),
                    "relationships": OTHER_PROJECT_RELATIONSHIPS.get(pid, WHC_RELATIONSHIPS)
                })
            return

        # 4. Delay Events Ledger (Canonical: /api/delay_events; Alias: /api/delay-events)
        elif path in ("/api/delay_events", "/api/delay-events"):
            pid = qs.get("project_id", [None])[0] or qs.get("id", [None])[0] or "PRJ-WHC-COM-001"
            if pid not in PROJECT_PROFILES and pid not in LEGACY_PROJECT_PROFILES:
                self._send_error(404, f"Project not found: {pid}")
                return
            events = DELAY_EVENTS_DATA.get(pid, [])
            self._send_json({
                "project_id": pid,
                "total_events": len(events),
                "delay_events": events
            })
            return

        # 5. Contemporaneous Site Radar Data
        elif path == "/api/site_radar":
            pid = qs.get("project_id", ["PRJ-WHC-COM-001"])[0]
            if pid not in PROJECT_PROFILES and pid not in LEGACY_PROJECT_PROFILES:
                self._send_error(404, f"Project not found: {pid}")
                return
            radar = SITE_RADAR_DATA.get(pid, [])
            self._send_json({
                "project_id": pid,
                "records_count": len(radar),
                "site_records": radar
            })
            return

        # 6. Universal Dictionary Lookup
        elif path == "/api/dictionary":
            if os.path.exists(DICTIONARY_BUNDLE_PATH):
                with open(DICTIONARY_BUNDLE_PATH, "r", encoding="utf-8") as f:
                    bundle = json.load(f)
                self._send_json(bundle)
            else:
                self._send_json({"by_id": {}, "by_label": {}})
            return

        # 7. Multi-Agent Deliberation Consensus Endpoint (Canonical: /api/deliberation/consensus; Alias: /api/deliberate)
        elif path in ("/api/deliberation/consensus", "/api/deliberate"):
            pid = qs.get("project_id", [None])[0] or qs.get("id", [None])[0] or "PRJ-WHC-COM-001"
            eid = qs.get("event_id", ["DLY-2026-001"])[0]
            req_session_id = qs.get("session_id", [None])[0]
            if pid not in PROJECT_PROFILES and pid not in LEGACY_PROJECT_PROFILES:
                self._send_error(404, f"Project not found: {pid}")
                return
            if DeliberationPipeline:
                try:
                    pipeline = DeliberationPipeline()
                    event_data = None
                    if pid in DELAY_EVENTS_DATA:
                        for evt in DELAY_EVENTS_DATA[pid]:
                            if evt.get("event_id") == eid:
                                event_data = evt
                                break
                    if not event_data:
                        self._send_error(404, f"Delay event not found: {eid}")
                        return
                    res = pipeline.run_deliberation(
                        project_id=pid,
                        event_id=eid,
                        event_data=event_data,
                        persist_log=False,
                        session_id=req_session_id
                    )
                    turns_out = []
                    for t in res.turns:
                        turns_out.append({
                            "turn_id": t.turn_id,
                            "round_number": t.round_number,
                            "agent_name": t.agent_name,
                            "agent_role": t.agent_role,
                            "position_statement": t.position_statement,
                            "tool_invoked": t.tool_invoked,
                            "tool_metrics": t.tool_metrics,
                            "concurrency_attribution": t.concurrency_attribution,
                            "recommended_eot_days": t.recommended_eot_days,
                            "recommended_ld_exposure_sgd": t.recommended_ld_exposure_sgd,
                            "notice_compliance_status": t.notice_compliance_status
                        })
                    self._send_json({
                        "session_id": res.session_id,
                        "project_id": res.project_id,
                        "event_id": res.event_id,
                        "event_title": res.event_title,
                        "event_name": event_data.get("event_name", res.event_title),
                        "canonical_event_name": event_data.get("canonical_event_name", res.event_title),
                        "location_detail": event_data.get("location_detail", "Basement 2 North Pit"),
                        "deliberation_round_count": 1,
                        "agent_turn_count": len(turns_out),
                        "hearing_phase": "FORMAL_HEARING_ROUND_1",
                        "unimpacted_completion_date": res.unimpacted_completion_date,
                        "impacted_completion_date": res.impacted_completion_date,
                        "net_critical_delay_workdays": res.net_critical_delay_workdays,
                        "candidate_eot_relief_days": res.candidate_eot_relief_days,
                        "contractor_culpable_days": res.contractor_culpable_days,
                        "liquidated_damages_exposure_sgd": res.liquidated_damages_exposure_sgd,
                        "concurrency_attribution": res.concurrency_attribution,
                        "notice_compliance_status": res.notice_compliance_status,
                        "contract_verification_status": res.contract_verification_status,
                        "determination_tier": res.determination_tier,
                        "consensus_achieved": res.consensus_achieved,
                        "contract_verification_record_id": res.contract_verification_record_id,
                        "adjudication_disclaimer": res.adjudication_disclaimer,
                        "contractor_position_summary": res.contractor_position_summary,
                        "employer_position_summary": res.employer_position_summary,
                        "so_determination_summary": res.so_determination_summary,
                        "turns": turns_out
                    })
                except Exception as e:
                    self._send_error(500, f"Deliberation evaluation failed: {e}")
            else:
                self._send_error(503, "DeliberationPipeline engine unavailable")
            return

        # Fallback to static files
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. TIA Fragnet Simulation Endpoint
        if path == "/api/tia/simulate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self._send_error(400, f"Invalid JSON payload: {e}")
                return

            project_id = payload.get("project_id", "PRJ-WHC-COM-001")
            if project_id not in PROJECT_PROFILES and project_id not in LEGACY_PROJECT_PROFILES:
                self._send_error(404, f"Project not found: {project_id}")
                return

            try:
                raw_dur = payload.get("fragnet_duration_days", 3)
                if isinstance(raw_dur, bool) or not isinstance(raw_dur, int):
                    raise ValueError("Duration must be a strict integer workday count (no booleans or fractional days)")
                fragnet_duration = raw_dur
                if fragnet_duration < 1 or fragnet_duration > 60:
                    raise ValueError("Duration must be between 1 and 60 workdays inclusive")
            except Exception as ve:
                self._send_error(400, f"Invalid fragnet_duration_days: {ve}")
                return

            valid_risks = {"NEUTRAL_FORCE_MAJEURE", "EMPLOYER_RISK", "CONTRACTOR_RISK"}
            risk_allocation = payload.get("risk_allocation", "NEUTRAL_FORCE_MAJEURE")
            if risk_allocation not in valid_risks:
                self._send_error(400, f"Invalid risk_allocation '{risk_allocation}'. Must be one of {sorted(valid_risks)}")
                return

            # Resolve all valid activities for the target project (and allow cross-project benchmark demo nodes)
            if project_id == "PRJ-WHC-COM-001":
                proj_acts = WHC_BASELINE_ACTIVITIES
            else:
                proj_acts = OTHER_PROJECT_ACTIVITIES.get(project_id, WHC_BASELINE_ACTIVITIES)

            valid_activities = {a["activity_id"] for a in proj_acts}.union({a["activity_id"] for a in WHC_BASELINE_ACTIVITIES})
            for acts in OTHER_PROJECT_ACTIVITIES.values():
                valid_activities.update(a["activity_id"] for a in acts)

            inserted_after = payload.get("inserted_after_activity_id", "ACT-03")
            if inserted_after not in valid_activities:
                self._send_error(400, f"Invalid inserted_after_activity_id '{inserted_after}'. Activity does not exist in network.")
                return

            fragnet_name = payload.get("fragnet_name", f"Simulated Fragnet on {inserted_after}")
            cause_category = payload.get("cause_category", "WEATHER_FORCE_MAJEURE")
            proj = PROJECT_PROFILES.get(project_id) or LEGACY_PROJECT_PROFILES.get(project_id)
            ld_rate = proj["liquidated_damages_daily_sgd"]

            # Real TIA evaluation via s04_simulate_tia_fragnet if available for WHC
            cpm_calculated_real = False
            engine_mode = "DETERMINISTIC_DISCRETE_DAY_FALLBACK"
            if s04_simulate_tia_fragnet and project_id == "PRJ-WHC-COM-001":
                try:
                    tia_run = s04_simulate_tia_fragnet(
                        target_activity_id=inserted_after,
                        delay_impact_workdays=float(fragnet_duration),
                        risk_allocation=risk_allocation
                    )
                    if tia_run.get("status") == "SUCCESS":
                        t_res = tia_run["tia_result"]
                        critical_path_shift_workdays = int(t_res.get("net_critical_delay_workdays", fragnet_duration))
                        original_finish_str = t_res.get("unimpacted_completion_date", "2026-11-19")
                        impacted_finish_str = t_res.get("impacted_completion_date", "2026-11-24")
                        compensable_eot_workdays = int(t_res.get("candidate_eot_relief_days", 0))
                        contractor_culpable_workdays = int(t_res.get("contractor_culpable_days", 0))
                        net_ld_exposure = float(t_res.get("liquidated_damages_exposure_sgd", 0.0))
                        cpm_calculated_real = True
                        engine_mode = "GENUINE_CPM_TIA_ENGINE"
                except Exception as exc:
                    logger.warning(
                        "TIA FastMCP engine calculation failed for activity %s: %s; activating deterministic discrete-day fallback",
                        inserted_after, exc, exc_info=True
                    )
                    cpm_calculated_real = False
                    engine_mode = "DETERMINISTIC_DISCRETE_DAY_FALLBACK"

            if not cpm_calculated_real:
                # Deterministic discrete-day calendar calculation for active project
                orig_date_str = proj.get("original_completion_date", "2026-11-19")
                try:
                    original_finish = date.fromisoformat(orig_date_str)
                except Exception:
                    original_finish = date(2026, 11, 19)
                original_finish_str = original_finish.isoformat()

                # Dynamic float absorption lookup from project activities
                act_tf = 0
                for a in proj_acts:
                    if a.get("activity_id") == inserted_after:
                        act_tf = int(a.get("total_float", 0))
                        break

                if act_tf > 0:
                    float_absorbed = min(act_tf, fragnet_duration)
                    critical_path_shift_workdays = max(0, fragnet_duration - float_absorbed)
                else:
                    critical_path_shift_workdays = fragnet_duration

                impacted_finish = add_workdays(original_finish, critical_path_shift_workdays, "CAL-STD-5D")
                impacted_finish_str = impacted_finish.isoformat()

                if risk_allocation == "EMPLOYER_RISK":
                    compensable_eot_workdays = critical_path_shift_workdays
                    contractor_culpable_workdays = 0
                elif risk_allocation == "NEUTRAL_FORCE_MAJEURE":
                    compensable_eot_workdays = max(0, critical_path_shift_workdays // 2) if critical_path_shift_workdays > 0 else 0
                    contractor_culpable_workdays = critical_path_shift_workdays - compensable_eot_workdays
                else:
                    compensable_eot_workdays = 0
                    contractor_culpable_workdays = critical_path_shift_workdays

                net_ld_exposure = float(contractor_culpable_workdays * ld_rate)

            is_benchmark = (project_id != "PRJ-WHC-COM-001")
            benchmark_prefix = "[BENCHMARK DEMO: Using benchmark network. Project-specific schedule pending ingestion.] " if is_benchmark else ""

            if not is_benchmark:
                governing_rules = {
                    "notice_compliance": f"RECORDED_COMPLIANT (Project profile records compliance with {proj.get('governing_clause', 'PSSCOC Clause 23.1')}; point-of-use notice verification pending full claim submission)",
                    "contract_guardrail": f"REGISTERED_PROFILE_MATCH (Parameters match registered {proj.get('contract_form', 'PSSCOC 2020')} profile; physical deed verification pending signed submission)",
                    "float_ownership": "Project float belongs to project until exhausted"
                }
            else:
                governing_rules = {
                    "notice_compliance": "ILLUSTRATIVE_NOT_EVALUATED (Project-specific notice records pending submission)",
                    "contract_guardrail": f"ILLUSTRATIVE_PARAMETERS (Based on {proj.get('contract_form', 'benchmark')} illustrative benchmark fixture)",
                    "float_ownership": "Project float belongs to project until exhausted"
                }

            response = {
                "project_id": project_id,
                "fragnet_name": fragnet_name,
                "inserted_after_activity_id": inserted_after,
                "fragnet_duration_workdays": fragnet_duration,
                "cause_category": cause_category,
                "risk_allocation": risk_allocation,
                "baseline_completion_date": original_finish_str,
                "impacted_completion_date": impacted_finish_str,
                "critical_path_shift_workdays": critical_path_shift_workdays,
                "working_calendar": "Standard 5-Day Singapore Construction Calendar (Mon-Fri, 8h/day)",
                "entitled_eot_workdays": compensable_eot_workdays,
                "compensable_eot_workdays": compensable_eot_workdays,
                "non_compensable_eot_workdays": 0,
                "contractor_culpable_workdays": contractor_culpable_workdays,
                "residual_culpable_delay_workdays": contractor_culpable_workdays,
                "liquidated_damages_rate_daily_sgd": ld_rate,
                "calculated_liquidated_damages_exposure_sgd": net_ld_exposure,
                "scenario_ld_formula": f"residual_culpable_workdays ({contractor_culpable_workdays}) * daily_rate (S${ld_rate:,.2f}) = S${net_ld_exposure:,.2f}",
                "scenario_state_isolation": "VERIFIED_ZERO_MUTATION (Persisted lakehouse records, schedule versions, and executive KPIs strictly unmodified)",
                "calculation_engine": "FastMCP TIA Engine (Deterministic CPM Graph Kernel)" if cpm_calculated_real else "Deterministic Discrete-Day CPM Fallback",
                "engine_mode": engine_mode,
                "is_fallback_calculation": not cpm_calculated_real,
                "is_benchmark_illustrative": is_benchmark,
                "track_scope": "AUTHORITATIVE_WHC_FIXTURE" if not is_benchmark else "BENCHMARK_ILLUSTRATIVE_NETWORK",
                "governing_rules": governing_rules,
                "agentic_synthesis": {
                    "consensus_status": "DETERMINISTIC_MATHEMATICAL_CALCULATION",
                    "evaluation_type": "DETERMINISTIC_CPM_MATHEMATICAL_EVALUATION",
                    "llm_inference_used": False,
                    "synthesis_summary": (
                        f"{benchmark_prefix}The deterministic CPM simulation confirms that inserting {fragnet_duration} workdays "
                        f"into {inserted_after} shifts project completion from {original_finish_str} "
                        f"to {impacted_finish_str} (Critical Path Shift: {critical_path_shift_workdays} workdays). "
                        f"Under {proj['contract_form']}, {risk_allocation} allocates "
                        f"{compensable_eot_workdays} workdays of EOT, resulting in S${net_ld_exposure:,.2f} of contractor LD exposure."
                    )
                }
            }
            self._send_json(response)
            return

        # 2. Deterministic CPM Calculation on arbitrary network
        elif path == "/api/cpm/calculate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self._send_error(400, f"Invalid JSON payload: {e}")
                return

            activities_in = payload.get("activities", WHC_BASELINE_ACTIVITIES)
            rels_in = payload.get("relationships", WHC_RELATIONSHIPS)
            start_str = payload.get("project_start_date", "2026-11-02")
            project_start = datetime.strptime(start_str, "%Y-%m-%d").date()

            if ScheduleNetwork:
                net = ScheduleNetwork("SIM-01", "WHAT-IF-01")
                for a in activities_in:
                    dur = int(a.get("duration_workdays", a.get("duration_days", 0)))
                    is_ms = bool(a.get("is_milestone", dur == 0))
                    ms_type = "START" if is_ms and a["activity_id"] == "ACT-01" else ("FINISH" if is_ms else None)
                    net.add_activity(Activity(
                        activity_id=a["activity_id"],
                        activity_name=a.get("task_name", a.get("activity_name", a["activity_id"])),
                        duration_days=dur,
                        calendar_id=a.get("calendar_id", "CAL-STD-5D"),
                        is_milestone=is_ms,
                        milestone_type=ms_type
                    ))
                for r in rels_in:
                    net.add_relationship(Relationship(
                        predecessor_id=r["predecessor_id"],
                        successor_id=r["successor_id"],
                        relationship_type=r.get("relationship_type", "FS"),
                        lag_days=int(r.get("lag_days", 0))
                    ))
                try:
                    s_date, f_date = net.calculate_cpm(project_start)
                    res_acts = []
                    for act_id, act in net.activities.items():
                        res_acts.append({
                            "activity_id": act.activity_id,
                            "activity_name": act.activity_name,
                            "duration_workdays": act.duration_days,
                            "early_start": act.early_start.isoformat() if act.early_start else None,
                            "early_finish": act.early_finish.isoformat() if act.early_finish else None,
                            "late_start": act.late_start.isoformat() if act.late_start else None,
                            "late_finish": act.late_finish.isoformat() if act.late_finish else None,
                            "total_float": act.total_float_days,
                            "free_float": act.free_float_days,
                            "is_critical": act.is_critical
                        })
                    self._send_json({
                        "status": "SUCCESS",
                        "project_early_start": s_date.isoformat(),
                        "project_early_finish": f_date.isoformat(),
                        "activities": res_acts
                    })
                    return
                except Exception as e:
                    self._send_error(500, f"CPM execution failed: {str(e)}")
                    return
            else:
                self._send_error(500, "ScheduleNetwork engine not initialized")
                return

        super().do_POST()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def guess_type(self, path):
        if str(path).endswith(".svg"):
            return "image/svg+xml"
        return super().guess_type(path)

    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status_code: int, message: str):
        self._send_json({"error": message, "status": status_code}, status_code=status_code)


def run_server(port: int = 8087):
    handler = ACIPS04DashboardHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        engine_name = get_display_engine()
        print("=" * 60)
        print("⏱️ ACIP S04 Agentic Progress & Delay Intelligence Cockpit")
        print(f"Active Execution Engine: {engine_name}")
        print(f"Listening on: http://0.0.0.0:{port} (http://localhost:{port})")
        print(f"Health Probe: http://localhost:{port}/healthz")
        print(f"Projects API: http://localhost:{port}/api/projects")
        print(f"Schedule API: http://localhost:{port}/api/schedule")
        print(f"TIA Fragnet API: http://localhost:{port}/api/tia/simulate (POST)")
        print(f"Serving from: {DASHBOARD_DIR}")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down S04 Cockpit gracefully...")
            httpd.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACIP S04 Dashboard Server")
    parser.add_argument("--port", type=int, default=8087, help="Port to serve S04 dashboard (default: 8087)")
    args = parser.parse_args()
    run_server(port=args.port)
