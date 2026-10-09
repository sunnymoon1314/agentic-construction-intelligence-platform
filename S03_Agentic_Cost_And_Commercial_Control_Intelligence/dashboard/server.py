#!/usr/bin/env python3
"""
S03: Interactive Cost & Commercial Control Dashboard Server
Module: ACIP S03 (Agentic Cost & Commercial Control Platform)
File: dashboard/server.py

Serves the executive commercial intelligence cockpit on configurable user-defined port (default 8086).
Features zero-dependency standard http.server with full REST API and static asset hosting.
"""

import os
import sys
import json
import argparse
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date

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
from agent_client.evaluator import MultiAgentCommercialPipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
START_TIME = datetime.now()

def get_display_engine(host: str = "") -> str:
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
    lake_bucket = os.getenv("COMMERCIAL_LAKE_BUCKET", "")
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

def get_full_project_analytics(project_id: str = "PRJ-WHC-COM-001") -> dict:
    """Aggregates multi-table DuckDB analytics into a reactive cockpit payload."""
    con = get_connection()
    prj_src = get_table_source("projects")
    sor_src = get_table_source("schedule_of_rates")
    clm_src = get_table_source("interim_claims")
    ci_src = get_table_source("claim_items")
    vo_src = get_table_source("variation_orders")
    safety_src = get_table_source("site_safety_incidents")
    eac_src = get_table_source("cost_forecast_eac")

    # 1. Project Header & Financials
    proj_row = con.execute(f"SELECT * FROM {prj_src} WHERE project_id = '{project_id}'").fetchone()
    if not proj_row:
        proj_row = con.execute(f"SELECT * FROM {prj_src} LIMIT 1").fetchone()
    
    project_id = proj_row[0]
    project_meta = {
        "project_id": proj_row[0],
        "project_name": proj_row[1],
        "contract_type": proj_row[2],
        "employer_name": proj_row[3],
        "main_contractor_uen": proj_row[4],
        "main_contractor_name": proj_row[5],
        "currency": proj_row[6],
        "base_contract_sum": float(proj_row[7]),
        "contingency_allocation": float(proj_row[8]),
        "total_approved_budget": float(proj_row[9]),
        "retention_max_cap_pct": float(proj_row[10]),
        "retention_limit_sgd": float(proj_row[11]),
        "contract_response_days_ceiling": int(proj_row[12])
    }

    # 2. Interim Claim & Cumulative Accounting
    clm_row = con.execute(f"SELECT * FROM {clm_src} WHERE project_id = '{project_id}' LIMIT 1").fetchone()
    claim_summary = {}
    claim_id = "CLM-WHC-008"
    if clm_row:
        claim_id = clm_row[0]
        claim_summary = {
            "claim_id": clm_row[0],
            "valuation_month": clm_row[2],
            "date_served": str(clm_row[3]),
            "statutory_response_deadline": str(clm_row[4]),
            "previous_cumulative_certified_gross": float(clm_row[5]),
            "contractor_claimed_gross_this_period": float(clm_row[6]),
            "openbim_verified_gross_this_period": float(clm_row[7]),
            "over_certification_disallowance": float(clm_row[8]),
            "retention_held_to_date": float(clm_row[9]),
            "statutory_safety_set_off": float(clm_row[10]),
            "net_payable_certified_this_period": float(clm_row[11])
        }

    # 3. openBIM Takeoff Reconciler Line Items
    ci_rows = con.execute(f"SELECT * FROM {ci_src} WHERE claim_id = '{claim_id}'").fetchall()
    claim_items = []
    for r in ci_rows:
        claim_items.append({
            "item_code": r[1],
            "description": r[2],
            "contract_unit_rate": float(r[3]),
            "contractor_claimed_cumulative_qty": float(r[4]),
            "contractor_claimed_pct": float(r[5]),
            "contractor_claimed_cumulative_amount": float(r[6]),
            "ifc_openbim_verified_qty": float(r[7]),
            "ifc_openbim_verified_pct": float(r[8]),
            "ifc_openbim_verified_amount": float(r[9]),
            "discrepancy_amount": float(r[10]),
            "discrepancy_status": r[11]
        })

    # 4. Variation Orders (12 VOs)
    vo_rows = con.execute(f"SELECT * FROM {vo_src} WHERE project_id = '{project_id}'").fetchall()
    vos = []
    for r in vo_rows:
        vos.append({
            "vo_id": r[0],
            "instruction_reference": r[2],
            "instruction_date": str(r[3]),
            "claim_notice_date": str(r[4]),
            "days_elapsed_notice": int(r[5]),
            "timebar_status": r[6],
            "description": r[7],
            "trade_id": r[8],
            "claimed_item_code": r[9],
            "quantity": float(r[10]),
            "unit": r[11],
            "proposed_valuation_tier": r[12],
            "contractor_proposed_rate": float(r[13]),
            "contractor_claimed_amount": float(r[14]),
            "action_taken": r[15],
            "authoritative_rate_applied": float(r[16]),
            "certified_amount": float(r[17]),
            "deduction_disallowed": float(r[18]),
            "fraud_flag": r[19]
        })

    # 5. MOM Safety Incidents
    safety_row = con.execute(f"SELECT * FROM {safety_src} WHERE project_id = '{project_id}' LIMIT 1").fetchone()
    safety_data = {}
    if safety_row:
        safety_data = {
            "mom_demerit_points": int(safety_row[2]),
            "swo_idle_days": int(safety_row[3]),
            "unremediated_fines": float(safety_row[4]),
            "swo_deduction": float(safety_row[5]),
            "sdp_deduction": float(safety_row[6]),
            "fines_deduction": float(safety_row[7]),
            "total_safety_set_off": float(safety_row[8])
        }

    # 6. Predictive EAC & Contingency Velocity
    eac_data = get_predictive_eac(project_id, current_month="2026-10")

    # 7. Live Statutory Countdown Clock
    clock_data = serve_sopa_deadline_clock(claim_summary.get("date_served", "2026-10-01"), 14)

    # 8. Statutory Section 11 Markdown Dossier
    sopa_res = generate_sopa_response(project_id, claim_id)

    # 9. Multi-Agent Deliberation Pipeline
    pipeline = MultiAgentCommercialPipeline()
    agent_audit = pipeline.run_full_audit(project_id, claim_id)

    con.close()

    return {
        "status": "SUCCESS",
        "project": project_meta,
        "interim_claim": claim_summary,
        "openbim_takeoff_items": claim_items,
        "variation_orders": vos,
        "safety_incidents": safety_data,
        "predictive_eac": eac_data,
        "sopa_countdown_clock": clock_data,
        "statutory_dossier_markdown": sopa_res["dossier_markdown"],
        "agent_deliberation": agent_audit,
        "engine": get_display_engine()
    }

class CommercialDashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Handles REST API queries and serves single-page executive web cockpit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API: List Projects
        if path == "/api/projects":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = list_commercial_projects()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # 2. API: Commercial Analytics for selected project
        elif path == "/api/commercial-analytics":
            project_id = query.get("project_id", ["PRJ-WHC-COM-001"])[0]
            engine_param = query.get("engine", [None])[0]
            host_header = self.headers.get("Host", "").lower()
            try:
                data = get_full_project_analytics(project_id)
                if engine_param:
                    engine_map = {
                        "aws": "AWS Engine",
                        "azure": "Azure Engine",
                        "gcp": "GCP Engine",
                        "local": "Local Engine"
                    }
                    data["engine"] = engine_map.get(engine_param.lower(), f"{engine_param.upper()} Engine")
                else:
                    data["engine"] = get_display_engine(host_header)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        # 3. API: SRE Observability Health Endpoint
        elif path == "/api/health":
            uptime_seconds = int((datetime.now() - START_TIME).total_seconds())
            health_payload = {
                "status": "HEALTHY",
                "uptime_seconds": uptime_seconds,
                "database": "DUCKDB_OLAP_COLUMNAR",
                "cloud_storage_mode": "PARQUET_LAKEHOUSE" if os.getenv("COMMERCIAL_LAKE_BUCKET") else "LOCAL_STORAGE",
                "active_tools_count": 6,
                "server_port": getattr(self.server, "port", 8086),
                "timestamp": datetime.now().isoformat()
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health_payload).encode("utf-8"))
            return

        # 4. Fallback: Serve static files (index.html) with pre-rendered active engine badge
        if path in ["/", "", "/index.html"]:
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                host_header = self.headers.get("Host", "").lower()
                engine_str = get_display_engine(host_header)
                content = content.replace('id="engineBadge">Local Engine</span>', f'id="engineBadge">{engine_str}</span>')
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            self.path = "/index.html"

        return super().do_GET()


def run_server(port: int = 8086):
    """Starts the commercial dashboard server on configurable port."""
    server_address = ("", port)
    
    # Allow port reuse to prevent address already in use errors
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(server_address, CommercialDashboardHandler) as httpd:
        httpd.port = port
        engine_name = get_display_engine()
        print("=" * 70)
        print("ACIP S03: Commercial Control & Cost Intelligence Cockpit")
        print(f"Active Execution Engine: {engine_name}")
        print("=" * 70)
        print(f"Server running at: http://localhost:{port}")
        print("Press Ctrl+C to terminate.")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server gracefully...")
            httpd.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACIP S03 Interactive Commercial Dashboard Server")
    default_port = int(os.getenv("PORT", 8086))
    parser.add_argument("--port", type=int, default=default_port, help=f"Server port (default: {default_port})")
    args = parser.parse_args()
    run_server(args.port)
