import sqlite3
import os
import sys

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("Enterprise Contractor Compliance MCP")
except ImportError:
    # Allow testing and standalone imports without mcp package installed
    class FastMCP:
        def __init__(self, name):
            self.name = name
        def tool(self):
            def decorator(f):
                return f
            return decorator
        def run(self, *args, **kwargs):
            sys.stderr.write(f"FastMCP server '{self.name}' dummy run called.\n")
    mcp = FastMCP("Enterprise Contractor Compliance MCP")


def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'contractors_registry.db')
    return sqlite3.connect(db_path)

@mcp.tool()
def query_contractor_profile(uen_or_name: str) -> str:
    """Query a contractor profile by UEN (Unique Entity Number) or registered company name.
    Returns BCA CRS registration grade, workheads, tendering limits, and track record.
    """
    conn = get_db_connection()
    c = conn.cursor()
    query = """
        SELECT c.uen, c.name, c.crs_grade, c.workheads, c.tendering_limit_sgd,
               c.paid_up_capital_sgd, c.net_worth_sgd, c.track_record_3yr_sgd, c.status,
               t.completed_projects_count, t.avg_conquas_score, t.on_time_completion_pct,
               t.open_defect_notices, t.dfma_adoption_score
        FROM contractors c
        LEFT JOIN track_record_conquas t ON c.uen = t.uen
        WHERE UPPER(c.uen) = UPPER(?) OR UPPER(c.name) LIKE UPPER(?)
    """
    c.execute(query, (uen_or_name.strip(), f"%{uen_or_name.strip()}%"))
    row = c.fetchone()
    conn.close()

    if not row:
        return f"No contractor profile found matching '{uen_or_name}' in the BCA CRS Registry."

    uen, name, grade, workheads, limit, paid_up, net_worth, track_3yr, status, \
        completed_cnt, avg_conquas, on_time, defects, dfma = row

    limit_str = "Unlimited" if limit >= 999999999 else f"S${limit:,.2f}"

    return (
        f"--- BCA CONTRACTOR REGISTRATION DOSSIER ---\n"
        f"Company Name: {name}\n"
        f"UEN: {uen}\n"
        f"Registration Status: {status}\n"
        f"BCA CRS Grade: {grade} (Tendering Limit: {limit_str})\n"
        f"Registered Workheads: {workheads}\n"
        f"Paid-Up Capital: S${paid_up:,.2f}\n"
        f"Audited Net Worth: S${net_worth:,.2f}\n"
        f"3-Year Proven Track Record: S${track_3yr:,.2f}\n"
        f"--- HISTORICAL PERFORMANCE METRICS ---\n"
        f"Completed Projects: {completed_cnt or 0}\n"
        f"Average CONQUAS Score: {avg_conquas or 0:.1f} / 100\n"
        f"On-Time Completion Rate: {on_time or 0:.1f}%\n"
        f"Open Defect Notices: {defects or 0}\n"
        f"DfMA Productivity Score: {dfma or 0:.1f} / 100\n"
    )

@mcp.tool()
def verify_safety_compliance(uen: str) -> str:
    """Audit contractor statutory safety records against Ministry of Manpower (MOM) regulations.
    Checks Safety Demerit Points (SDP threshold of 25 demerits), bizSAFE accreditation, and Stop Work Orders.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.name, s.mom_sdp, s.bizsafe_level, s.mom_debarred, s.ggbs_rating,
               s.fatalities_past_18m, s.stop_work_orders_past_18m, s.last_audit_date
        FROM safety_compliance s
        JOIN contractors c ON s.uen = c.uen
        WHERE UPPER(s.uen) = UPPER(?) OR UPPER(c.name) LIKE UPPER(?)
    """, (uen.strip(), f"%{uen.strip()}%"))
    row = c.fetchone()
    conn.close()

    if not row:
        return f"No safety records found for contractor UEN '{uen}'."

    name, sdp, bizsafe, debarred, ggbs, fatalities, swo, audit_date = row

    compliance_status = "COMPLIANT"
    reasons = []

    # MOM 25 Demerit Points Rule and Debarment
    if sdp >= 25 and debarred:
        compliance_status = "CRITICAL STATUTORY BAR & DEBARRED (DISQUALIFIED)"
        reasons.append(
            f"Accumulated {sdp} Safety Demerit Points (exceeds MOM legal threshold of 25 within 18 months). "
            f"Contractor is barred from hiring new foreign manpower and statutorily disqualified from public/tier-1 tenders."
        )
        reasons.append("Active Ministry of Manpower statutory debarment order on record.")
    elif sdp >= 25:
        compliance_status = "CRITICAL STATUTORY BAR (DISQUALIFIED)"
        reasons.append(
            f"Accumulated {sdp} Safety Demerit Points (exceeds MOM legal threshold of 25 within 18 months). "
            f"Contractor is barred from hiring new foreign manpower and statutorily disqualified from public/tier-1 tenders."
        )
    elif debarred:
        compliance_status = "STATUTORILY DEBARRED"
        reasons.append("Active Ministry of Manpower statutory debarment order on record.")
    elif sdp >= 15:
        compliance_status = "HIGH SAFETY RISK"
        reasons.append(f"Elevated Safety Demerit Points ({sdp} points). Nearing statutory suspension threshold.")

    if fatalities > 0:
        reasons.append(f"Reported {fatalities} workplace fatality in the preceding 18-month audit period.")

    if "bizSAFE STAR" not in bizsafe and "Level 3" not in bizsafe:
        compliance_status = "NON-COMPLIANT CERTIFICATION"
        reasons.append(f"Current certification '{bizsafe}' fails minimum bizSAFE Level 3 threshold for public procurement.")

    findings_str = "\n- ".join(reasons) if reasons else "Full safety compliance confirmed. No debarment or critical demerits."

    return (
        f"--- MOM STATUTORY SAFETY COMPLIANCE REPORT ---\n"
        f"Contractor: {name} (UEN: {uen})\n"
        f"Compliance Verdict: {compliance_status}\n"
        f"MOM Safety Demerit Points (SDP): {sdp} / 25 Threshold\n"
        f"bizSAFE Status: {bizsafe}\n"
        f"Green & Gracious Builder (GGBS): {ggbs}\n"
        f"Workplace Fatalities (Past 18 Months): {fatalities}\n"
        f"Stop Work Orders (SWO) Issued: {swo}\n"
        f"Last Regulatory Audit: {audit_date}\n"
        f"Key Compliance Observations:\n- {findings_str}\n"
    )

@mcp.tool()
def assess_financial_solvency(uen: str, tender_value_sgd: float) -> str:
    """Conduct financial solvency and liquidity due diligence for a prospective tender.
    Computes Current Ratio (> 1.2), Quick Ratio (> 1.0), Debt-to-Equity, Net Working Capital,
    and validates Banker Guarantee / Performance Bond capacity (5% to 10% of tender value).
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.name, f.fy_year, f.current_assets_sgd, f.current_liabilities_sgd,
               f.quick_assets_sgd, f.cash_reserves_sgd, f.total_debt_sgd,
               f.total_equity_sgd, f.credit_line_facility_sgd
        FROM financial_statements f
        JOIN contractors c ON f.uen = c.uen
        WHERE UPPER(f.uen) = UPPER(?) OR UPPER(c.name) LIKE UPPER(?)
        ORDER BY f.fy_year DESC LIMIT 1
    """, (uen.strip(), f"%{uen.strip()}%"))
    row = c.fetchone()
    conn.close()

    if not row:
        return f"No audited financial statements found for contractor '{uen}'."

    name, fy, ca, cl, qa, cash, debt, equity, credit = row

    current_ratio = ca / cl if cl > 0 else 0.0
    quick_ratio = qa / cl if cl > 0 else 0.0
    debt_equity = debt / equity if equity > 0 else 999.0
    net_working_capital = ca - cl

    # Standard performance bond requirement: 10% for large public works, 5% minimum
    bond_10_pct = tender_value_sgd * 0.10
    bond_capacity_sufficient = credit >= bond_10_pct

    flags = []
    verdict = "FINANCIALLY SOLVENT"

    if current_ratio < 1.0:
        verdict = "INSOLVENT / HIGH RISK (FAILED)"
        flags.append(f"Deficient Current Ratio ({current_ratio:.2f} < 1.0 threshold). Current liabilities exceed assets.")
    elif current_ratio < 1.2:
        verdict = "MARGINAL LIQUIDITY (WARNING)"
        flags.append(f"Sub-optimal Current Ratio ({current_ratio:.2f} < 1.2 target). Tight working capital buffer.")

    if quick_ratio < 1.0:
        flags.append(f"Quick Ratio ({quick_ratio:.2f} < 1.0). High dependency on illiquid inventories or contract work-in-progress.")

    if debt_equity > 1.5:
        flags.append(f"High Financial Leverage (Debt-to-Equity = {debt_equity:.2f} > 1.5). Vulnerable to interest rate volatility.")

    if not bond_capacity_sufficient:
        verdict = "FAILED BOND CAPACITY"
        flags.append(
            f"Available bank credit facility (S${credit:,.2f}) is insufficient to secure the required 10% Performance Bond "
            f"(S${bond_10_pct:,.2f}) for tender value of S${tender_value_sgd:,.2f}."
        )

    observations = "\n- ".join(flags) if flags else "Financial statements indicate solid liquidity, conservative leverage, and strong bonding headroom."

    return (
        f"--- FINANCIAL SOLVENCY & LIQUIDITY AUDIT (FY{fy}) ---\n"
        f"Contractor: {name} (UEN: {uen})\n"
        f"Tender Benchmark Value: S${tender_value_sgd:,.2f}\n"
        f"Overall Solvency Verdict: {verdict}\n"
        f"Current Ratio: {current_ratio:.2f} (Standard Benchmark: > 1.20)\n"
        f"Quick Ratio: {quick_ratio:.2f} (Standard Benchmark: > 1.00)\n"
        f"Debt-to-Equity Ratio: {debt_equity:.2f} (Standard Benchmark: < 1.50)\n"
        f"Net Working Capital: S${net_working_capital:,.2f}\n"
        f"Cash Reserves: S${cash:,.2f}\n"
        f"Available Bank Credit Facility: S${credit:,.2f}\n"
        f"Required 10% Banker's Guarantee / Bond: S${bond_10_pct:,.2f} "
        f"({'ADEQUATE' if bond_capacity_sufficient else 'DEFICIENT'})\n"
        f"Financial Due Diligence Observations:\n- {observations}\n"
    )

@mcp.tool()
def evaluate_pqm_score(uen: str, bid_price_sgd: float, tender_benchmark_sgd: float, quality_weight: float = 0.3) -> str:
    """Calculate the Price-Quality Method (PQM) composite score for a contractor bid
    in accordance with Singapore BCA public sector procurement guidelines.
    quality_weight defaults to 0.3 (Price 70%, Quality 30%).
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.name, t.avg_conquas_score, t.on_time_completion_pct,
               t.open_defect_notices, t.dfma_adoption_score, s.mom_sdp
        FROM contractors c
        LEFT JOIN track_record_conquas t ON c.uen = t.uen
        LEFT JOIN safety_compliance s ON c.uen = s.uen
        WHERE UPPER(c.uen) = UPPER(?) OR UPPER(c.name) LIKE UPPER(?)
    """, (uen.strip(), f"%{uen.strip()}%"))
    row = c.fetchone()
    conn.close()

    if not row:
        return f"Unable to retrieve track record and safety metrics for contractor '{uen}'."

    name, conquas, on_time, defects, dfma, sdp = row
    conquas = conquas or 75.0
    on_time = on_time or 80.0
    defects = defects or 0
    dfma = dfma or 50.0
    sdp = sdp or 0

    price_weight = 1.0 - quality_weight

    # 1. Price Score Calculation (Standard BCA PQM formula relative to benchmark)
    price_deviation = (bid_price_sgd - tender_benchmark_sgd) / tender_benchmark_sgd
    if price_deviation <= 0:
        # Competitive bid below or equal to benchmark
        raw_price_score = max(0.0, 100.0 - abs(price_deviation) * 50.0)
    else:
        # Bid higher than benchmark
        raw_price_score = max(0.0, 100.0 - price_deviation * 120.0)

    # 2. Quality Score Breakdown (Out of 100 points)
    # - Past Quality (CONQUAS): 40%
    # - Delivery Track Record (On-Time & Defect free): 30%
    # - Safety Track Record (Penalized by SDP): 20%
    # - Productivity & DfMA Innovation: 10%
    q_conquas = (conquas / 100.0) * 40.0
    q_delivery = max(0.0, ((on_time / 100.0) * 20.0) - (defects * 2.0) + 10.0)
    q_safety = max(0.0, 20.0 - (sdp * 0.8))
    q_dfma = (dfma / 100.0) * 10.0

    raw_quality_score = q_conquas + q_delivery + q_safety + q_dfma

    # 3. Composite Weighted Score
    final_pqm_score = (raw_price_score * price_weight) + (raw_quality_score * quality_weight)

    return (
        f"--- BCA PRICE-QUALITY METHOD (PQM) EVALUATION ---\n"
        f"Tenderer: {name} (UEN: {uen})\n"
        f"Tender Benchmark Budget: S${tender_benchmark_sgd:,.2f}\n"
        f"Submitted Bid Price: S${bid_price_sgd:,.2f} (Variance: {price_deviation * 100:+.2f}%)\n"
        f"Evaluation Ratio: Price {price_weight * 100:.0f}% / Quality {quality_weight * 100:.0f}%\n"
        f"--------------------------------------------------\n"
        f"Raw Price Competitiveness Score: {raw_price_score:.2f} / 100\n"
        f"Raw Quality Attributes Score: {raw_quality_score:.2f} / 100\n"
        f"  - CONQUAS Quality Benchmark (40% max): {q_conquas:.2f}\n"
        f"  - Project Delivery & Defect Record (30% max): {q_delivery:.2f}\n"
        f"  - WSH Safety Compliance Factor (20% max): {q_safety:.2f} (SDP Penalty: -{sdp * 0.8:.1f})\n"
        f"  - DfMA & Productivity Adoption (10% max): {q_dfma:.2f}\n"
        f"--------------------------------------------------\n"
        f"FINAL COMPOSITE PQM SCORE: {final_pqm_score:.2f} / 100\n"
        f"Recommendation: {'HIGHLY RECOMMENDED FOR AWARD' if final_pqm_score >= 85 else 'COMPETITIVE' if final_pqm_score >= 70 else 'DEFICIENT BID QUALITY'}\n"
    )

@mcp.tool()
def audit_contract_risk(clause_text: str, contract_standard: str = "PSSCOC") -> str:
    """Analyze tender or contract clauses against Singapore legal standards
    (Security of Payment Act SOPA, PSSCOC 2020, SIA Form of Contract, REDAS).
    Detects void pay-when-paid clauses, onerous LAD rates, short variation notice periods,
    and uninsurable indemnities.
    """
    lower_clause = clause_text.lower()
    findings = []
    severity = "LOW RISK"

    # 1. Pay-When-Paid Clause Detection (Strict violation of SOPA Section 9)
    if "pay when paid" in lower_clause or "pay if paid" in lower_clause or \
       ("payment" in lower_clause and "received from employer" in lower_clause and "condition precedent" in lower_clause):
        severity = "ILLEGAL / UNENFORCEABLE (SOPA BREACH)"
        findings.append(
            "CRITICAL STATUTORY VIOLATION: Clause contains a 'Pay-When-Paid' or contingent payment provision. "
            "Under Section 9 of the Singapore Building and Construction Industry Security of Payment Act (SOPA), "
            "any term making payment contingent on receipt of third-party funds is statutorily void and unenforceable."
        )

    # 2. Variation Claim Notice Periods
    if "notice" in lower_clause and "variation" in lower_clause:
        if any(term in lower_clause for term in ["7 days", "3 days", "48 hours", "5 days"]):
            severity = "HIGH CONTRACTUAL RISK"
            findings.append(
                "ONEROUS NOTICE PERIOD: The clause imposes an unusually short notice period (< 14 days) "
                "as a strict condition precedent for variation claims. Under standard PSSCOC Clause 23, "
                "contractors are granted 28 days to submit formal variation details. A 3-to-7 day requirement "
                "is an onerous contractor risk that frequently bars valid claims."
            )

    # 3. Liquidated Damages Rate
    if "liquidated damages" in lower_clause or "lad" in lower_clause:
        if any(term in lower_clause for term in ["50,000", "100,000", "without limit", "unlimited"]):
            severity = "HIGH RISK"
            findings.append(
                "EXCESSIVE LIQUIDATED DAMAGES: Liquidated Ascertained Damages (LAD) exceed industry norms or lack an aggregate cap. "
                "Ensure LAD represents a genuine pre-estimate of loss under common law, otherwise it risks being challenged as a penalty clause."
            )

    # 4. Indemnity & Consequential Loss
    if "indemnify" in lower_clause and ("consequential" in lower_clause or "loss of profit" in lower_clause or "indirect" in lower_clause):
        severity = "HIGH RISK"
        findings.append(
            "UNINSURABLE INDEMNITY: Clause exposes the party to indirect or consequential damages (loss of profit/revenue). "
            "Standard PSSCOC/SIA contracts exclude consequential losses and limit contractor liability to direct physical damages covered by CAR/TPL insurance."
        )

    if not findings:
        findings.append(
            f"No fatal statutory defects detected under Singapore {contract_standard} guidelines. "
            f"Clause structure aligns with standard risk allocation conventions."
        )

    return (
        f"--- STATUTORY & CONTRACTUAL RISK AUDIT REPORT ---\n"
        f"Governing Standard: Singapore {contract_standard} / SOPA\n"
        f"Overall Risk Rating: {severity}\n"
        f"Clause Analyzed:\n\"{clause_text.strip()}\"\n\n"
        f"Detailed Legal & Commercial Findings:\n- " + "\n- ".join(findings) + "\n"
    )

@mcp.tool()
def list_sample_tenders() -> str:
    """List benchmark public and private sector tender projects available for pre-qualification vetting."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT tender_id, title, developer_type, contract_form, estimated_budget_sgd,
               required_workhead, min_crs_grade, max_mom_sdp, min_bizsafe, performance_bond_pct
        FROM sample_tenders
    """)
    rows = c.fetchall()
    conn.close()

    output = ["--- BENCHMARK TENDER PACKAGES AVAILABLE ---"]
    for r in rows:
        tid, title, dev, c_form, budget, wh, grade, sdp, biz, bond = r
        output.append(
            f"Tender ID: {tid}\n"
            f"Title: {title}\n"
            f"Client: {dev} | Contract Form: {c_form}\n"
            f"Estimated Budget: S${budget:,.2f}\n"
            f"PQQ Requirements: Workhead {wh}, Min Grade {grade}, Max MOM SDP {sdp}, Min {biz}, {bond}% Performance Bond\n"
            f"--------------------------------------------------"
        )
    return "\n".join(output)

@mcp.tool()
def simulate_contractor_monte_carlo_risk(uen: str, tender_value_sgd: float, iterations: int = 500000) -> str:
    """Execute a 500,000-iteration quantitative Monte Carlo risk simulation
    modeling material price volatility (concrete/steel), adverse monsoon weather extensions,
    and Liquidated Ascertained Damages (LAD) liquidity exhaustion.
    Connects to the Rust Axum risk sidecar if active, with instant vectorized fallback.
    """
    import urllib.request
    import json
    import time

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT c.uen, c.name, c.crs_grade,
               f.current_assets_sgd, f.current_liabilities_sgd, f.credit_line_facility_sgd
        FROM contractors c
        LEFT JOIN financial_statements f ON c.uen = f.uen AND f.fy_year = 2025
        WHERE UPPER(c.uen) = UPPER(?) OR UPPER(c.name) LIKE UPPER(?)
    """, (uen.strip(), f"%{uen.strip()}%"))
    row = c.fetchone()
    conn.close()

    if not row:
        return f"Unable to find contractor with UEN or name '{uen}' for Monte Carlo quantitative risk simulation."

    actual_uen, name, grade, curr_a, curr_l, credit_fac = row
    curr_a = curr_a or 0.0
    curr_l = curr_l or 0.0
    credit_fac = credit_fac or 0.0
    working_capital = max(0.0, curr_a - curr_l)
    total_liquidity_buffer = working_capital + credit_fac
    lad_daily_rate = max(10000.0, tender_value_sgd * 0.00025)

    # 1. Attempt connection to Rust Axum quantitative sidecar
    payload = {
        "uen": uen.strip(),
        "tender_value_sgd": float(tender_value_sgd),
        "iterations": int(iterations),
        "available_working_capital_sgd": float(working_capital),
        "available_credit_line_sgd": float(credit_fac),
        "lad_daily_rate_sgd": float(lad_daily_rate)
    }

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8080/simulate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=0.25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            engine_source = "Rust / Axum Microservice Sidecar (tokio + rayon)"
            var_95 = data["var_95_sgd"]
            cvar_95 = data["cvar_95_sgd"]
            max_loss = data["max_loss_sgd"]
            default_prob = data["default_probability_pct"]
            cushion = data["liquidity_cushion_sgd"]
            risk_rating = data["risk_rating"]
            exec_time = data["execution_time_ms"]
            rec = data["recommendation"]
    except Exception:
        # 2. Vectorized NumPy Simulation Fallback
        import numpy as np
        t0 = time.time()
        n = min(max(int(iterations), 1000), 500000)
        mat_baseline = tender_value_sgd * 0.40
        mat_shocks = np.maximum(0.0, mat_baseline * (np.random.lognormal(0.0, 0.09, n) - 1.0))
        delays = np.maximum(0.0, np.random.normal(18.0, 8.0, n)) * lad_daily_rate
        sub_shocks = np.where(np.random.random(n) < 0.04, tender_value_sgd * np.random.uniform(0.02, 0.05, n), 0.0)

        total_losses = mat_shocks + delays + sub_shocks
        var_95 = float(np.percentile(total_losses, 95))
        cvar_95 = float(np.mean(total_losses[total_losses >= var_95]))
        max_loss = float(np.max(total_losses))
        default_prob = float(np.mean(total_losses > total_liquidity_buffer) * 100.0)
        cushion = float(total_liquidity_buffer - var_95)
        exec_time = round((time.time() - t0) * 1000.0, 2)
        engine_source = "Fast Vectorized NumPy Quantitative Engine (SIMD Fallback)"

        if default_prob > 5.0 or cushion < 0.0:
            risk_rating = "CRITICAL DEFAULT RISK"
            rec = "Disqualify or mandate 15% cash-backed retention escrow"
        elif default_prob > 1.0 or cushion < tender_value_sgd * 0.05:
            risk_rating = "MODERATE VOLATILITY RISK"
            rec = "Approved conditional on 10% On-Demand Performance Bond"
        else:
            risk_rating = "PRUDENT & LOW RISK"
            rec = "Unconditional clearance for tender award"

    return (
        f"--- QUANTITATIVE MONTE CARLO RISK DOSSIER ---\n"
        f"Contractor: {name} (UEN: {uen}, Grade: {grade})\n"
        f"Tender Package Value: S${tender_value_sgd:,.2f}\n"
        f"Simulation Engine: {engine_source}\n"
        f"Iterations Executed: {iterations:,} runs in {exec_time} ms\n"
        f"--------------------------------------------------\n"
        f"Value-at-Risk (VaR 95%): S${var_95:,.2f}\n"
        f"Conditional VaR (CVaR 95%): S${cvar_95:,.2f}\n"
        f"Worst-Case Simulated Loss: S${max_loss:,.2f}\n"
        f"Available Liquidity Buffer: S${total_liquidity_buffer:,.2f} (WC: S${working_capital:,.2f} + Credit: S${credit_fac:,.2f})\n"
        f"Net Liquidity Cushion post-VaR: S${cushion:,.2f}\n"
        f"Insolvency / Default Probability: {default_prob:.2f}%\n"
        f"Overall Quantitative Rating: {risk_rating}\n"
        f"Recommendation: {rec}\n"
    )

if __name__ == "__main__":
    mcp.run(transport='stdio')
