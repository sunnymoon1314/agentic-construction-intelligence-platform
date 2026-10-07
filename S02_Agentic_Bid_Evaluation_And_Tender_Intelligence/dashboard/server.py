#!/usr/bin/env python3
"""
S02: Interactive Analytical Dashboard Server
Project: Woodlands Health Campus Acute Care Wing (S$120M Baseline)
Serves the executive tender evaluation visual intelligence interface on port 8085.
"""

import os
import json
import http.server
import socketserver
import duckdb
from urllib.parse import urlparse

PORT = 8085
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
S02_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(S02_DIR, "data", "hospital_tender.duckdb")

def query_dicts(con, sql, params=None):
    cursor = con.execute(sql, params) if params else con.execute(sql)
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def get_projects_list():
    if not os.path.exists(DB_PATH):
        return []
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return query_dicts(con, "SELECT * FROM projects ORDER BY project_id")
    finally:
        con.close()

def get_display_engine():
    raw_provider = os.getenv("CLOUD_PROVIDER", "Local").strip()
    if raw_provider.upper() in ["AWS", "GCP"]:
        return f"{raw_provider.upper()} Engine"
    elif raw_provider.upper() == "AZURE":
        return "Azure Engine"
    else:
        return "Local Engine"

def get_tender_analytics(project_id="PRJ-WHC-001"):
    if not os.path.exists(DB_PATH):
        return {"error": "Database not initialized. Please run python3 data/generate_tender_data.py first."}

    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        # 1. Fetch Selected Project
        proj_row = query_dicts(con, "SELECT * FROM projects WHERE project_id = ?", [project_id])
        if not proj_row:
            # Fallback to first project
            proj_row = query_dicts(con, "SELECT * FROM projects ORDER BY project_id LIMIT 1")
        current_project = proj_row[0] if proj_row else {
            "project_id": "PRJ-WHC-001",
            "tender_id": "TND-WHC-2026-001",
            "project_name": "Woodlands Health Campus — Acute Care Wing",
            "client_name": "Ministry of Health Holdings (MOHH)",
            "sector": "Healthcare Infrastructure",
            "pte_budget_sgd": 120000000.0,
            "currency": "SGD"
        }
        tender_id = current_project["tender_id"]

        # All Projects for Dropdown
        all_projects = query_dicts(con, "SELECT project_id, tender_id, project_name, sector, pte_budget_sgd, status FROM projects ORDER BY project_id")

        # 2. Base PTE & Trades
        trades = query_dicts(con, "SELECT * FROM trades ORDER BY trade_id")
        boq_items = query_dicts(con, "SELECT * FROM boq_items ORDER BY item_code")
        pte_total = current_project["pte_budget_sgd"]

        # 3. Bidders for this project from project_bidders cross table JOIN contractors
        bidders_df = query_dicts(con, """
            SELECT 
                pb.project_id,
                pb.bidder_id,
                c.company_name as bidder_name,
                pb.contractor_uen as uen,
                c.bca_grade,
                20 as track_record_years,
                c.conquas_score,
                c.mom_sdp as safety_demerit_points,
                c.net_worth_sgd,
                pb.total_submitted_bid,
                pb.bidder_status,
                pb.commercial_strategy,
                pb.flri_index,
                pb.variance_vs_pte_pct
            FROM project_bidders pb
            JOIN contractors c ON pb.contractor_uen = c.uen
            WHERE pb.project_id = ?
            ORDER BY pb.bidder_id
        """, [current_project["project_id"]])

        # 4. Trade summaries per bidder (from bid_line_items if WHC, else synthetic ratio)
        bidder_trades = query_dicts(con, """
            SELECT 
                r.bidder_id,
                b.bidder_name,
                i.trade_id,
                t.trade_name,
                t.category,
                SUM(r.submitted_total_amount) as trade_total
            FROM bid_line_items r
            JOIN boq_items i ON r.item_code = i.item_code
            JOIN trades t ON i.trade_id = t.trade_id
            JOIN bidders b ON r.bidder_id = b.bidder_id AND r.tender_id = b.tender_id
            WHERE r.tender_id = ?
            GROUP BY r.bidder_id, b.bidder_name, i.trade_id, t.trade_name, t.category
            ORDER BY r.bidder_id, i.trade_id
        """, [tender_id])

        # Substructure benchmarks (22.61% for WHC baseline)
        pte_substructure = sum(item["pte_total_amount"] for item in boq_items if item["trade_id"] in ["TRD-01", "TRD-02", "TRD-03"])
        pte_sub_pct = (pte_substructure / sum(item["pte_total_amount"] for item in boq_items)) * 100 if boq_items else 22.61

        # Compile bidder analytics
        bidder_summaries = []
        for b in bidders_df:
            bid_id = b["bidder_id"]
            tot = b["total_submitted_bid"]
            
            # Substructure calculation
            matching_sub = [bt["trade_total"] for bt in bidder_trades if bt["bidder_id"] == bid_id and bt["trade_id"] in ["TRD-01", "TRD-02", "TRD-03"]]
            if matching_sub:
                sub_sum = sum(matching_sub)
                sub_pct = (sub_sum / tot * 100) if tot > 0 else 0.0
                flri = sub_pct / pte_sub_pct if pte_sub_pct > 0 else 1.0
                unearned_extraction = max(0.0, sub_sum - (pte_substructure * (tot / pte_total)))
            else:
                # Derived from cross table FLRI
                flri = b.get("flri_index", 1.0) or 1.0
                sub_pct = pte_sub_pct * flri
                sub_sum = (sub_pct / 100.0) * tot
                unearned_extraction = max(0.0, sub_sum - (pte_substructure * (tot / pte_total)))

            # Quality score
            conquas_sub = (b["conquas_score"] / 100.0) * 40.0
            grade_pts = 15.0 if "A1" in b["bca_grade"] else 10.0
            track_pts = min(15.0, (b["track_record_years"] / 25.0) * 15.0)
            safety_pts = max(0.0, 30.0 - (b["safety_demerit_points"] * 2.5))
            qual_score = conquas_sub + grade_pts + track_pts + safety_pts

            bidder_summaries.append({
                "bidder_id": bid_id,
                "name": b["bidder_name"],
                "uen": b["uen"],
                "bca_grade": b["bca_grade"],
                "track_record_years": b["track_record_years"],
                "conquas_score": b["conquas_score"],
                "safety_demerit_points": b["safety_demerit_points"],
                "total_bid": tot,
                "variance_vs_pte_pct": b.get("variance_vs_pte_pct", ((tot - pte_total) / pte_total) * 100),
                "substructure_sum": sub_sum,
                "substructure_pct": sub_pct,
                "flri": flri,
                "unearned_extraction": unearned_extraction,
                "qual_score": qual_score,
                "is_front_loader": flri >= 1.30 or sub_pct >= 32.0,
                "strategy": b["commercial_strategy"],
                "bidder_status": b["bidder_status"]
            })

        # Median price computation
        all_prices = sorted([bs["total_bid"] for bs in bidder_summaries])
        p_med = all_prices[len(all_prices) // 2] if all_prices else pte_total

        for bs in bidder_summaries:
            bid = bs["total_bid"]
            if bid < 0.75 * p_med:
                price_score = 10.0 + ((bid / (0.75 * p_med)) * 25.0)
                bs["commercial_status"] = "STATUTORY_ALT_WARNING"
            elif bid > 1.25 * p_med:
                price_score = max(10.0, 50.0 - ((bid - (1.25 * p_med)) / p_med * 50.0))
                bs["commercial_status"] = "OUTLIER_OVERPRICED"
            else:
                price_score = 100.0 - (abs(1.0 - (bid / p_med)) * 150.0)
                bs["commercial_status"] = "COMPLIANT_BAND"

            bs["price_score"] = round(price_score, 2)
            bs["pqm_composite"] = round((price_score * 0.5) + (bs["qual_score"] * 0.5), 2)

        # Rank by PQM composite
        bidder_summaries.sort(key=lambda x: x["pqm_composite"], reverse=True)
        for idx, bs in enumerate(bidder_summaries, 1):
            bs["rank"] = idx

        contractors_count = con.execute("SELECT count(*) FROM contractors").fetchone()[0]
        exclusions = query_dicts(con, "SELECT * FROM bidder_qualifications WHERE tender_id = ?", [tender_id])

        # Granular Forensic BOQ Line Items per Bidder
        boq_drilldown = query_dicts(con, """
            SELECT 
                r.tender_id,
                r.bidder_id,
                r.item_code,
                i.item_description,
                i.trade_id,
                t.trade_name,
                t.category,
                i.unit,
                i.quantity,
                i.pte_unit_rate,
                i.pte_total_amount,
                r.submitted_unit_rate,
                r.submitted_total_amount,
                r.variance_vs_pte_pct,
                ROUND(r.submitted_total_amount - i.pte_total_amount, 2) as delta_sgd
            FROM bid_line_items r
            JOIN boq_items i ON r.item_code = i.item_code
            JOIN trades t ON i.trade_id = t.trade_id
            WHERE r.tender_id = ?
            ORDER BY r.bidder_id, r.item_code
        """, [tender_id])

        return {
            "project_id": current_project["project_id"],
            "tender_id": current_project["tender_id"],
            "project_name": current_project["project_name"],
            "client_name": current_project["client_name"],
            "sector": current_project["sector"],
            "all_projects": all_projects,
            "total_contractors_registry": contractors_count,
            "shortlisted_bidders_count": len(bidder_summaries),
            "pte_total": pte_total,
            "pte_substructure": pte_substructure,
            "pte_sub_pct": pte_sub_pct,
            "p_med": p_med,
            "engine": get_display_engine(),
            "trades": trades,
            "bidders": bidder_summaries,
            "bidder_trades": bidder_trades,
            "exclusions": exclusions,
            "boq_drilldown": boq_drilldown
        }
    finally:
        con.close()

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        from urllib.parse import parse_qs
        query_params = parse_qs(parsed.query)

        if parsed.path == "/api/projects":
            projects = get_projects_list()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(projects, indent=2).encode("utf-8"))
            return
        elif parsed.path == "/api/data":
            project_id = query_params.get("project_id", ["PRJ-WHC-001"])[0]
            data = get_tender_analytics(project_id=project_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return
        elif parsed.path == "/api/boq-drilldown":
            project_id = query_params.get("project_id", ["PRJ-WHC-001"])[0]
            bidder_id = query_params.get("bidder_id", [None])[0]
            data = get_tender_analytics(project_id=project_id)
            drilldown = data.get("boq_drilldown", [])
            if bidder_id:
                drilldown = [x for x in drilldown if x["bidder_id"] == bidder_id]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(drilldown, indent=2).encode("utf-8"))
            return
        elif parsed.path in ["/", "", "/index.html"]:
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                engine_str = get_display_engine()
                content = content.replace('id="engineBadge">Local Engine</span>', f'id="engineBadge">{engine_str}</span>')
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            self.path = "/index.html"
        return super().do_GET()

def run():
    print(f"Starting S02 Tender Evaluation Intelligence Dashboard on port {PORT}...")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🚀 Dashboard live at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
