#!/usr/bin/env python3
"""
S02: FastMCP Deterministic Bid Evaluation & Tender Intelligence Server
Project: Woodlands Health Campus Acute Care Wing (S$120,000,000 Benchmark)

This server exposes deterministic computation gates for tender boards:
1. audit_rate_leveling: In-memory statistical Z-score outlier detection on BOQ line items.
2. detect_front_loading: Temporal cash-flow skew and front-loading risk index (FLRI).
3. check_scope_exclusions: Qualification schedule cross-examination & hidden variation liability.
4. evaluate_pqm_score: Deterministic BCA Price-Quality Method scoring with configurable weights.
5. generate_tender_evaluation_report: Authoritative tender committee executive summary.
"""

import os
import sys
import math
from typing import Optional, Dict, Any, List
import duckdb

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("ACIP S02 Tender Evaluation Server")
except ImportError:
    class FastMCP:
        def __init__(self, name):
            self.name = name
        def tool(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
        def run(self, *args, **kwargs):
            raise RuntimeError("Cannot start FastMCP server: 'mcp' package is not installed. Run 'pip install mcp' to enable MCP serving.")
    mcp = FastMCP("ACIP S02 Tender Evaluation Server")

DEFAULT_DB_PATH = os.getenv(
    "ACIP_DUCKDB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hospital_tender.duckdb")
)

def get_connection(db_path: Optional[str] = None):
    path = db_path or DEFAULT_DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tender database not found at: {path}. Run data/generate_tender_data.py first.")
    return duckdb.connect(path, read_only=True)

def validate_tender(con, tender_id: str):
    """Ensure tender_id exists in the database registry, avoiding silent empty results."""
    available = [r[0] for r in con.execute("SELECT tender_id FROM tenders").fetchall()]
    if tender_id not in available:
        raise ValueError(
            f"Tender '{tender_id}' not found in registry. "
            f"Available active tenders: {available}"
        )


@mcp.tool()
def list_tenders(db_path: Optional[str] = None) -> dict:
    """Discover available active public tenders registered in the analytical store.
    Returns tender IDs, project names, procuring client authorities, and budget benchmarks.
    """
    con = get_connection(db_path)
    rows = con.execute("SELECT tender_id, project_name, client_name, pte_budget_sgd, closing_date FROM tenders").fetchall()
    con.close()
    return {
        "status": "SUCCESS",
        "total_tenders": len(rows),
        "tenders": [
            {
                "tender_id": r[0],
                "project_name": r[1],
                "client_name": r[2],
                "pte_budget_sgd": r[3],
                "closing_date": r[4]
            }
            for r in rows
        ]
    }


@mcp.tool()
def audit_rate_leveling(db_path: Optional[str] = None, z_threshold: float = 1.5, tender_id: str = "TND-WHC-2026-001", variance_threshold_pct: float = 35.0) -> dict:
    """Audit contractor unit rates across all BOQ line items against PTE benchmark and statistical median.
    Flags line items with rate deviation >= variance_threshold_pct or significant Z-score deviation against peer distribution.
    """
    if db_path and db_path.startswith("TND-"):
        tender_id = db_path
        db_path = None
    con = get_connection(db_path)
    validate_tender(con, tender_id)

    # 1. Fetch line item data across all bidders for the specified tender
    query = """
    SELECT 
        b.item_code,
        q.item_description,
        q.trade_id,
        t.category,
        q.unit,
        q.pte_unit_rate,
        b.bidder_id,
        d.bidder_name,
        b.submitted_unit_rate,
        b.variance_vs_pte_pct
    FROM bid_line_items b
    JOIN boq_items q ON b.item_code = q.item_code
    JOIN trades t ON q.trade_id = t.trade_id
    JOIN bidders d ON b.bidder_id = d.bidder_id AND b.tender_id = d.tender_id
    WHERE b.tender_id = ?
    ORDER BY b.item_code, b.bidder_id
    """
    rows = con.execute(query, [tender_id]).fetchall()
    con.close()

    # Group by item_code
    items_map = {}
    for r in rows:
        item_code, desc, trade_id, cat, unit, pte_rate, bidder_id, bidder_name, sub_rate, var_pct = r
        if item_code not in items_map:
            items_map[item_code] = {
                "item_code": item_code,
                "description": desc,
                "category": cat,
                "unit": unit,
                "pte_rate": pte_rate,
                "bids": []
            }
        items_map[item_code]["bids"].append({
            "bidder_id": bidder_id,
            "bidder_name": bidder_name,
            "submitted_rate": sub_rate,
            "variance_pct": var_pct
        })

    flagged_anomalies = []

    for item_code, data in items_map.items():
        rates = [b["submitted_rate"] for b in data["bids"]]
        n = len(rates)
        mean_rate = sum(rates) / n
        variance = sum((x - mean_rate) ** 2 for x in rates) / (n - 1 if n > 1 else 1)
        std_dev = math.sqrt(variance)

        for b in data["bids"]:
            z_score = (b["submitted_rate"] - mean_rate) / std_dev if std_dev > 0.001 else 0.0
            is_anomaly = abs(z_score) >= z_threshold or abs(b["variance_pct"]) >= variance_threshold_pct

            if is_anomaly:
                flagged_anomalies.append({
                    "item_code": item_code,
                    "description": data["description"],
                    "category": data["category"],
                    "bidder_id": b["bidder_id"],
                    "bidder_name": b["bidder_name"],
                    "submitted_rate": b["submitted_rate"],
                    "pte_benchmark_rate": data["pte_rate"],
                    "market_mean_rate": round(mean_rate, 2),
                    "variance_vs_pte_pct": b["variance_pct"],
                    "z_score": round(z_score, 2),
                    "anomaly_type": "HIGH_OUTLIER" if z_score > 0 else "LOW_OUTLIER_OR_DUMPING"
                })

    return {
        "status": "SUCCESS",
        "total_line_items_audited": len(items_map),
        "total_anomalies_flagged": len(flagged_anomalies),
        "z_threshold_applied": z_threshold,
        "anomalies": flagged_anomalies
    }


@mcp.tool()
def detect_front_loading(db_path: Optional[str] = None, tender_id: str = "TND-WHC-2026-001", early_threshold_flri: float = 1.30) -> dict:
    """Detect contractor cash-flow front-loading by comparing early substructure works vs late works.
    Calculates Front-Loading Risk Index (FLRI) and flags cash extraction traps.
    """
    if db_path and db_path.startswith("TND-"):
        tender_id = db_path
        db_path = None
    con = get_connection(db_path)
    validate_tender(con, tender_id)

    # 1. Calculate PTE benchmark distribution
    pte_dist = con.execute("""
    SELECT 
        t.category,
        SUM(q.pte_total_amount) as total_amount
    FROM boq_items q
    JOIN trades t ON q.trade_id = t.trade_id
    GROUP BY t.category
    """).fetchall()

    pte_total = sum(r[1] for r in pte_dist)
    pte_substructure = next((r[1] for r in pte_dist if r[0] == "Substructure"), 0.0)
    pte_early_pct = (pte_substructure / pte_total) * 100.0

    # 2. Calculate bidder distributions for specific tender
    bidders = con.execute("SELECT bidder_id, bidder_name, total_submitted_bid FROM bidders WHERE tender_id = ?", [tender_id]).fetchall()

    results = []
    for b_id, b_name, b_total in bidders:
        cat_rows = con.execute("""
        SELECT 
            t.category,
            SUM(b.submitted_total_amount) as cat_amount
        FROM bid_line_items b
        JOIN boq_items q ON b.item_code = q.item_code
        JOIN trades t ON q.trade_id = t.trade_id
        WHERE b.bidder_id = ? AND b.tender_id = ?
        GROUP BY t.category
        """, [b_id, tender_id]).fetchall()

        sub_amount = next((r[1] for r in cat_rows if r[0] == "Substructure"), 0.0)
        late_amount = sum(r[1] for r in cat_rows if r[0] in ["Finishes", "Services", "External"])

        sub_pct = (sub_amount / b_total) * 100.0 if b_total > 0 else 0.0
        late_pct = (late_amount / b_total) * 100.0 if b_total > 0 else 0.0

        # Front-Loading Risk Index (FLRI): ratio of early works percentage vs PTE early works percentage
        flri = sub_pct / pte_early_pct if pte_early_pct > 0 else 1.0

        # Early cash drawdown skew above benchmark
        early_drawdown_premium = sub_amount - (pte_substructure * (b_total / pte_total))

        is_front_loaded = flri >= early_threshold_flri or sub_pct >= 32.0

        results.append({
            "bidder_id": b_id,
            "bidder_name": b_name,
            "total_submitted_bid": b_total,
            "substructure_amount": round(sub_amount, 2),
            "substructure_pct": round(sub_pct, 2),
            "late_works_pct": round(late_pct, 2),
            "benchmark_substructure_pct": round(pte_early_pct, 2),
            "front_loading_risk_index": round(flri, 2),
            "early_cash_extraction_sgd": round(max(0.0, early_drawdown_premium), 2),
            "risk_flag": "HIGH_FRONT_LOADING_RISK" if is_front_loaded else "BALANCED_RATE_DISTRIBUTION"
        })

    con.close()

    return {
        "status": "SUCCESS",
        "benchmark_pte_substructure_pct": round(pte_early_pct, 2),
        "front_loading_analysis": results
    }


@mcp.tool()
def check_scope_exclusions(db_path: Optional[str] = None, tender_id: str = "TND-WHC-2026-001") -> dict:
    """Scrutinize contractor qualification letters and schedules for concealed scope omissions.
    Calculates the adjusted tender price including employer variation liability.
    """
    if db_path and db_path.startswith("TND-"):
        tender_id = db_path
        db_path = None
    con = get_connection(db_path)
    validate_tender(con, tender_id)

    query = """
    SELECT 
        q.bidder_id,
        b.bidder_name,
        b.total_submitted_bid,
        q.clause_id,
        q.page_nr,
        q.clause_text,
        q.omitted_item_code,
        q.potential_cost_exposure,
        q.severity
    FROM bidder_qualifications q
    JOIN bidders b ON q.bidder_id = b.bidder_id AND q.tender_id = b.tender_id
    WHERE q.tender_id = ?
    """
    rows = con.execute(query, [tender_id]).fetchall()
    con.close()

    exclusions = []
    for r in rows:
        b_id, b_name, total_bid, clause_id, page_nr, text, item_code, exposure, sev = r
        adjusted_bid = total_bid + exposure
        exclusions.append({
            "bidder_id": b_id,
            "bidder_name": b_name,
            "submitted_bid_sum": total_bid,
            "clause_id": clause_id,
            "qualification_page_nr": page_nr,
            "clause_text": text,
            "omitted_item_code": item_code,
            "employer_cost_exposure_sgd": round(exposure, 2),
            "normalized_tender_sum_sgd": round(adjusted_bid, 2),
            "severity": sev,
            "advisory_finding": (
                f"Contractor submitted headline bid of S${total_bid:,.2f} with scope exclusion for "
                f"Item {item_code} on page {page_nr}. Equalized employer cost exposure is S${adjusted_bid:,.2f} per QS audit; formal clarification recommended."
            )
        })

    return {
        "status": "SUCCESS",
        "total_scope_exclusions_found": len(exclusions),
        "exclusions": exclusions
    }


@mcp.tool()
def evaluate_pqm_score(
    db_path: Optional[str] = None,
    price_weight: float = 0.50,
    quality_weight: float = 0.50,
    tender_id: str = "TND-WHC-2026-001"
) -> dict:
    """Execute deterministic BCA Price-Quality Method (PQM) scoring.
    Combines commercial bid leveling (Price Score) with statutory quality criteria (CONQUAS, safety demerits, track record).
    """
    if db_path and db_path.startswith("TND-"):
        tender_id = db_path
        db_path = None

    if abs((price_weight + quality_weight) - 1.0) > 0.001:
        raise ValueError("Price weight and Quality weight must sum to 1.0 (e.g. 0.5 and 0.5).")

    con = get_connection(db_path)
    validate_tender(con, tender_id)

    # Fetch PTE Benchmark
    pte = con.execute("SELECT SUM(pte_total_amount) FROM boq_items").fetchone()[0]

    # Fetch Bidders for specific tender
    bidders = con.execute("""
    SELECT 
        bidder_id,
        bidder_name,
        uen,
        bca_grade,
        track_record_years,
        conquas_score,
        safety_demerit_points,
        net_worth_sgd,
        total_submitted_bid
    FROM bidders
    WHERE tender_id = ?
    """, [tender_id]).fetchall()

    # Fetch Scope Exclusions to calculate Equalized/Normalized Bid Sums
    exclusions = con.execute("""
    SELECT bidder_id, COALESCE(SUM(potential_cost_exposure), 0.0)
    FROM bidder_qualifications
    WHERE tender_id = ?
    GROUP BY bidder_id
    """, [tender_id]).fetchall()
    exclusion_map = {row[0]: row[1] for row in exclusions}

    con.close()

    # Calculate true median using normalized tender sums (accounting for scope exclusions)
    normalized_sums = sorted([b[8] + exclusion_map.get(b[0], 0.0) for b in bidders])
    n = len(normalized_sums)
    if n == 0:
        median_sum = pte
    elif n % 2 == 1:
        median_sum = normalized_sums[n // 2]
    else:
        median_sum = (normalized_sums[n // 2 - 1] + normalized_sums[n // 2]) / 2.0

    scores = []
    for b in bidders:
        b_id, b_name, uen, grade, track_yrs, conquas, demerits, net_worth, bid_sum = b
        exposure = exclusion_map.get(b_id, 0.0)
        norm_bid_sum = bid_sum + exposure

        # 1. Commercial Price Score (0 - 100) based on normalized equalized sum
        ratio = norm_bid_sum / median_sum

        if ratio < 0.75:
            price_score_raw = max(10.0, 50.0 - ((0.75 - ratio) * 200.0))
            alt_flag = "SCREENING_ALT_HEURISTIC_POTENTIAL_DUMPING"
        elif 0.90 <= ratio <= 1.05:
            price_score_raw = 100.0 - (abs(1.0 - ratio) * 150.0)
            alt_flag = "COMPLIANT_COMMERCIAL_RANGE"
        elif ratio < 0.90:
            price_score_raw = 85.0 - ((0.90 - ratio) * 100.0)
            alt_flag = "BELOW_MARKET_MONITOR"
        else:
            # Smooth continuous curve anchored at 92.5 at boundary ratio 1.05
            price_score_raw = max(10.0, 92.5 - ((ratio - 1.05) * 180.0))
            alt_flag = "PREMIUM_PRICE_DEFENSIVE"

        price_score_raw = min(100.0, max(0.0, price_score_raw))

        # 2. Technical Quality Score (0 - 100)
        conquas_pts = (conquas / 100.0) * 40.0
        grade_pts = 15.0 if grade == "CW01-A1" else 10.0
        exp_pts = min(15.0, (track_yrs / 25.0) * 15.0)
        track_record_pts = grade_pts + exp_pts
        safety_deduction = demerits * 2.5
        safety_pts = max(0.0, 30.0 - safety_deduction)

        quality_score_raw = conquas_pts + track_record_pts + safety_pts

        # 3. Overall PQM Composite Score
        pqm_composite = (price_score_raw * price_weight) + (quality_score_raw * quality_weight)

        scores.append({
            "bidder_id": b_id,
            "bidder_name": b_name,
            "uen": uen,
            "bca_grade": grade,
            "submitted_bid_sum": bid_sum,
            "scope_exclusion_adjustment_sgd": round(exposure, 2),
            "normalized_tender_sum_sgd": round(norm_bid_sum, 2),
            "variance_vs_pte_pct": round(((norm_bid_sum - pte) / pte) * 100.0, 2),
            "commercial_price_score": round(price_score_raw, 2),
            "technical_quality_score": round(quality_score_raw, 2),
            "conquas_subscore": round(conquas_pts, 2),
            "track_record_subscore": round(track_record_pts, 2),
            "safety_subscore": round(safety_pts, 2),
            "pqm_composite_score": round(pqm_composite, 2),
            "commercial_risk_status": alt_flag
        })

    # Sort descending by PQM Composite Score
    scores.sort(key=lambda x: x["pqm_composite_score"], reverse=True)

    for rank, item in enumerate(scores, 1):
        item["pqm_rank"] = rank

    return {
        "status": "SUCCESS",
        "tender_id": tender_id,
        "pte_client_estimate_sgd": round(pte, 2),
        "evaluation_weights": {
            "price_weight": price_weight,
            "quality_weight": quality_weight
        },
        "pqm_leaderboard": scores
    }


@mcp.tool()
def generate_tender_evaluation_report(
    db_path: Optional[str] = None,
    tender_id: str = "TND-WHC-2026-001"
) -> dict:
    """Generate comprehensive authoritative evaluation dossier integrating all four forensic checks.
    """
    if db_path and db_path.startswith("TND-"):
        tender_id = db_path
        db_path = None

    con = get_connection(db_path)
    validate_tender(con, tender_id)
    con.close()

    leveling = audit_rate_leveling(tender_id=tender_id, db_path=db_path)
    frontloading = detect_front_loading(tender_id=tender_id, db_path=db_path)
    exclusions = check_scope_exclusions(tender_id=tender_id, db_path=db_path)
    pqm = evaluate_pqm_score(db_path=db_path, tender_id=tender_id)

    # Synthesize recommendations
    leader = pqm["pqm_leaderboard"][0]

    return {
        "tender_id": tender_id,
        "project_name": "Woodlands Health Campus Acute Care Wing",
        "benchmark_pte_sgd": pqm["pte_client_estimate_sgd"],
        "rate_leveling_anomalies_count": leveling["total_anomalies_flagged"],
        "top_ranked_for_committee_review": {
            "rank": 1,
            "bidder_id": leader["bidder_id"],
            "bidder_name": leader["bidder_name"],
            "pqm_composite_score": leader["pqm_composite_score"],
            "submitted_bid_sum": leader["submitted_bid_sum"],
            "normalized_tender_sum_sgd": leader.get("normalized_tender_sum_sgd", leader["submitted_bid_sum"])
        },
        "pqm_ranked_winner": {  # Preserved as backward compatibility alias
            "rank": 1,
            "bidder_id": leader["bidder_id"],
            "bidder_name": leader["bidder_name"],
            "pqm_composite_score": leader["pqm_composite_score"],
            "submitted_bid_sum": leader["submitted_bid_sum"]
        },
        "detailed_results": {
            "pqm_rankings": pqm["pqm_leaderboard"],
            "front_loading_findings": frontloading["front_loading_analysis"],
            "scope_exclusion_findings": exclusions["exclusions"]
        }
    }


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Running ACIP S02 Deterministic Bid Evaluation Self-Test Diagnostic...")
        res = generate_tender_evaluation_report()
        import json
        print(json.dumps(res, indent=2))
    else:
        # Run FastMCP server over stdio for agent client consumption
        try:
            mcp.run()
        except RuntimeError as err:
            print(f"Notice: {err}")
            print("Falling back to self-test diagnostic report:")
            res = generate_tender_evaluation_report()
            import json
            print(json.dumps(res, indent=2))
