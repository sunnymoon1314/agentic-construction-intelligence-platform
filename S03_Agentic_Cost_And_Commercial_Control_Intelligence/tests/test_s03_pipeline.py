#!/usr/bin/env python3
"""
S03: Automated Test Suite for Cost & Commercial Control Intelligence
Module: ACIP S03 (Agentic Cost & Commercial Control Platform)
File: tests/test_s03_pipeline.py

Comprehensive test suite verifying:
1. DuckDB OLAP Columnar & Apache Parquet Lakehouse Parity (7 Tables)
2. Forensic Variation Order Audit Engine (PSSCOC Cl 19.1 28-Day Timebars & Star Rate Anti-Fraud)
3. openBIM 5D Quantity Takeoff Reconciliation (IFC Volume Discrepancy > 2.0%)
4. Statutory SOPA Section 11 Payment Response Engine (Withholding Grounds & Net Payable)
5. Statutory SOPA Deadline Clock & Singapore Public Holiday Calendar Engine
6. Predictive EVM & Contingency Velocity Depletion Radar
7. Multi-Agent Commercial Intelligence Pipeline (QS, Legal Counsel, Director Consensus)
8. Dashboard REST API Endpoints (/api/projects, /api/commercial-analytics, /api/health)
"""

import os
import sys
import unittest
import duckdb
from datetime import date

S03_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S03_ROOT)

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
from dashboard.server import get_full_project_analytics

DB_PATH = os.path.join(S03_ROOT, "data", "commercial_control.duckdb")
PARQUET_DIR = os.path.join(S03_ROOT, "data", "parquet")


class TestS03CommercialControlPipeline(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.exists(DB_PATH), f"Database not found at {DB_PATH}")
        self.assertTrue(os.path.exists(PARQUET_DIR), f"Parquet directory not found at {PARQUET_DIR}")

    def test_01_duckdb_and_parquet_lakehouse_parity(self):
        """Verify all 7 tables exist in DuckDB and Parquet lakehouse directory."""
        tables = [
            "projects", "schedule_of_rates", "interim_claims",
            "claim_items", "variation_orders", "site_safety_incidents",
            "cost_forecast_eac"
        ]
        con = duckdb.connect(DB_PATH, read_only=True)
        for tbl in tables:
            cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            self.assertGreater(cnt, 0, f"Table {tbl} is empty in DuckDB")

            pq_path = os.path.join(PARQUET_DIR, f"{tbl}.parquet")
            self.assertTrue(os.path.exists(pq_path), f"Parquet table missing: {pq_path}")
            pq_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pq_path}')").fetchone()[0]
            self.assertEqual(cnt, pq_cnt, f"Row count mismatch between DuckDB and Parquet for {tbl}")
        con.close()

    def test_02_variation_order_audit_and_28day_timebar(self):
        """Verify PSSCOC Clause 19.1 28-day notice timebar and Star Rate duplication detection."""
        # 1. Test VO-WHC-005 (Timebar Expired: 69 days > 28 days)
        vo5 = audit_variation_order(
            project_id="PRJ-WHC-COM-001",
            vo_id="VO-WHC-005",
            instruction_date="2026-07-15",
            claim_notice_date="2026-09-22",
            proposed_rate=85.00,
            proposed_tier="TIER_4_DAYWORK"
        )
        self.assertEqual(vo5["status"], "COMPLETED")
        self.assertEqual(vo5["timebar_validation"]["timebar_status"], "TIMEBAR_EXPIRED_CLAIM_WAIVED")
        self.assertEqual(vo5["valuation_waterfall"]["applied_tier"], "DISALLOWED_TIMEBAR")
        self.assertEqual(vo5["valuation_waterfall"]["certified_amount"], 0.0)
        self.assertEqual(vo5["valuation_waterfall"]["deduction_disallowed"], 10200.0)

        # 2. Test VO-WHC-001 (Star Rate Duplication Fraud -> Fallback to Tier 1 SOR S$240/m3)
        vo1 = audit_variation_order(
            project_id="PRJ-WHC-COM-001",
            vo_id="VO-WHC-001",
            instruction_date="2026-08-10",
            claim_notice_date="2026-08-25",
            proposed_rate=380.00,
            proposed_tier="TIER_3_STAR_RATE"
        )
        self.assertEqual(vo1["status"], "COMPLETED")
        self.assertEqual(vo1["timebar_validation"]["timebar_status"], "TIMEBAR_COMPLIANT")
        self.assertEqual(vo1["valuation_waterfall"]["fraud_flag"], "RATE_DUPLICATION_DETECTED")
        self.assertEqual(vo1["valuation_waterfall"]["applied_tier"], "TIER_1_SOR")
        self.assertEqual(vo1["valuation_waterfall"]["authoritative_rate_applied"], 240.0)
        self.assertEqual(vo1["valuation_waterfall"]["deduction_disallowed"], 49000.0)

    def test_03_openbim_quantity_reconciliation(self):
        """Verify physical openBIM takeoff comparison against contractor claim."""
        # Test STR-02-004: Claimed 7800 m3 vs Verified 6500 m3 (Shortfall 1300 m3)
        res = reconcile_progress_valuation(
            project_id="PRJ-WHC-COM-001",
            claim_id="CLM-WHC-008",
            item_code="STR-02-004",
            contractor_claimed_qty=7800.0
        )
        recon = res["reconciliation"]
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(recon["discrepancy_status"], "FLAGGED_OVER_CERTIFICATION")
        self.assertEqual(recon["disallowed_qty"], 1300.0)
        self.assertEqual(recon["disallowed_amount"], 312000.0)
        self.assertGreater(recon["variance_percentage"], 2.0)

        # Test CIV-01-001: Claimed 12000 m3 vs Verified 11850 m3 (Within 2.0% tolerance)
        civ = reconcile_progress_valuation(
            project_id="PRJ-WHC-COM-001",
            claim_id="CLM-WHC-008",
            item_code="CIV-01-001",
            contractor_claimed_qty=12000.0
        )
        self.assertEqual(civ["reconciliation"]["discrepancy_status"], "WITHIN_TOLERANCE")

    def test_04_statutory_sopa_response_generation(self):
        """Verify SOPA Section 11 response calculations, deductions, and statutory markdown."""
        sopa = generate_sopa_response("PRJ-WHC-COM-001", "CLM-WHC-008")
        self.assertEqual(sopa["status"], "COMPLETED")

        fin = sopa["financial_summary"]
        self.assertEqual(fin["claimed_gross_this_period"], 4850000.0)
        self.assertEqual(fin["openbim_verified_gross"], 3687500.0)
        self.assertEqual(fin["openbim_disallowance"], 1162500.0)
        self.assertEqual(fin["statutory_safety_set_off"], 55000.0)
        self.assertEqual(fin["net_payable_certified_this_period"], 3632500.0)

        # Verify dossier text
        self.assertIn("FORMAL STATUTORY PAYMENT RESPONSE", sopa["dossier_markdown"])
        self.assertIn("SECTION 11 OF THE BUILDING & CONSTRUCTION INDUSTRY SOPA", sopa["dossier_markdown"])
        self.assertIn("PART A: OPENBIM PHYSICAL TAKE-OFF QUANTITY RECONCILIATION", sopa["dossier_markdown"])
        self.assertIn("PART B: VARIATION ORDER VALUATION & STATUTORY TIMEBAR WATERFALL", sopa["dossier_markdown"])
        self.assertIn("PART C: MINISTRY OF MANPOWER (MOM) SAFETY INFRACTIONS SET-OFFS", sopa["dossier_markdown"])

    def test_05_statutory_sopa_deadline_clock(self):
        """Verify SOPA Section 2 deadline engine omits Sundays and Public Holidays."""
        # Claim served 2026-10-01, 14 statutory days ceiling
        clock = serve_sopa_deadline_clock("2026-10-01", 14)
        self.assertEqual(clock["status"], "COMPLETED")
        self.assertEqual(clock["statutory_response_deadline"], "2026-10-17")
        self.assertIn("business_days_remaining", clock["countdown"])
        self.assertIn("traffic_light", clock["countdown"])

    def test_06_predictive_evm_and_contingency_radar(self):
        """Verify EVM cost forecasting, CPI, and Month 10 contingency breach prediction."""
        eac = get_predictive_eac("PRJ-WHC-COM-001", current_month="2026-10")
        self.assertEqual(eac["status"], "COMPLETED")

        evm = eac["earned_value_metrics"]
        self.assertEqual(evm["bac_budget_at_completion"], 52380952.38)
        self.assertEqual(evm["bcwp_earned_value"], 28450000.0)
        self.assertEqual(evm["acwp_actual_cost"], 30150000.0)
        self.assertAlmostEqual(evm["cpi_cost_performance_index"], 0.9436, places=3)
        self.assertAlmostEqual(evm["base_eac"], 55511818.0, places=0)
        self.assertAlmostEqual(evm["risk_adjusted_eac"], 56795528.79, places=0)

        radar = eac["contingency_velocity_radar"]
        self.assertEqual(radar["forecasted_breach_month_index"], 10)
        self.assertEqual(radar["monthly_burn_velocity"], 231250.0)

    def test_07_multi_agent_commercial_pipeline(self):
        """Verify collaborative multi-agent pipeline execution and consensus across all projects."""
        pipeline = MultiAgentCommercialPipeline()
        audit = pipeline.run_full_audit("PRJ-WHC-COM-001", "CLM-WHC-008")

        self.assertEqual(audit["project_id"], "PRJ-WHC-COM-001")
        self.assertEqual(audit["statutory_response_deadline"], "2026-10-17")
        self.assertEqual(len(audit["agent_findings"]), 3)
        self.assertIn("LEGAL DISPUTE NARRATIVE", audit["dispute_narrative"])
        self.assertIn("EXECUTIVE BRIEFING MEMORANDUM", audit["executive_memo"])

    def test_08_dashboard_analytics_payload(self):
        """Verify full analytics payload delivered to interactive web cockpit."""
        payload = get_full_project_analytics("PRJ-WHC-COM-001")
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["project"]["project_id"], "PRJ-WHC-COM-001")
        self.assertEqual(len(payload["openbim_takeoff_items"]), 5)
        self.assertEqual(len(payload["variation_orders"]), 12)
        self.assertIn("predictive_eac", payload)
        self.assertIn("sopa_countdown_clock", payload)
        self.assertIn("statutory_dossier_markdown", payload)

    def test_09_end_to_end_financial_reconciliation_invariants(self):
        """Verify strict financial reconciliation invariants across line items, deductions, and net payable."""
        sopa = generate_sopa_response("PRJ-WHC-COM-001", "CLM-WHC-008")
        fin = sopa["financial_summary"]

        # 1. Fetch individual source rows to verify row-level pricing formulas
        con = get_connection()
        ci_source = get_table_source("claim_items")
        rows = con.execute(f"""
            SELECT 
                item_code,
                contract_unit_rate,
                contractor_claimed_cumulative_qty,
                contractor_claimed_cumulative_amount,
                ifc_openbim_verified_qty,
                ifc_openbim_verified_amount,
                discrepancy_amount
            FROM {ci_source}
            WHERE claim_id = 'CLM-WHC-008'
            ORDER BY item_code
        """).fetchall()
        con.close()

        self.assertEqual(len(rows), 5, "Expected exactly 5 claim items for CLM-WHC-008")

        calc_sum_claimed = 0.0
        calc_sum_verified = 0.0
        calc_sum_disallowed = 0.0

        for r in rows:
            item_code, rate, claim_qty, claim_amt, ver_qty, ver_amt, disallow_amt = r
            
            # Row-level invariant: Claimed Value = Claimed Qty * Contract Unit Rate
            expected_claim = round(claim_qty * rate, 2)
            self.assertAlmostEqual(claim_amt, expected_claim, places=2,
                msg=f"{item_code}: claimed amount does not equal qty * rate")

            # Row-level invariant: Verified Value = Verified Qty * Contract Unit Rate
            expected_ver = round(ver_qty * rate, 2)
            self.assertAlmostEqual(ver_amt, expected_ver, places=2,
                msg=f"{item_code}: verified amount does not equal qty * rate")

            # Row-level invariant: Disallowance = Claimed Value - Verified Value
            expected_disallow = round(claim_amt - ver_amt, 2)
            self.assertAlmostEqual(disallow_amt, expected_disallow, places=2,
                msg=f"{item_code}: disallowance does not equal claimed - verified")

            calc_sum_claimed += claim_amt
            calc_sum_verified += ver_amt
            calc_sum_disallowed += disallow_amt

        # Invariant 1: Dynamic sum of claimed rows equals published gross claimed
        self.assertAlmostEqual(calc_sum_claimed, fin["claimed_gross_this_period"], places=2)
        self.assertAlmostEqual(calc_sum_claimed, 4850000.00, places=2)

        # Invariant 2: Dynamic sum of verified rows equals published gross verified
        self.assertAlmostEqual(calc_sum_verified, fin["openbim_verified_gross"], places=2)
        self.assertAlmostEqual(calc_sum_verified, 3687500.00, places=2)

        # Invariant 3: Dynamic sum of disallowances equals published openBIM disallowance
        self.assertAlmostEqual(calc_sum_disallowed, fin["openbim_disallowance"], places=2)
        self.assertAlmostEqual(calc_sum_disallowed, 1162500.00, places=2)

        # Invariant 4: Gross Claimed minus Disallowances equals Verified Gross
        self.assertAlmostEqual(
            fin["claimed_gross_this_period"] - fin["openbim_disallowance"],
            fin["openbim_verified_gross"],
            places=2
        )

        # Invariant 5: Verified Gross minus Safety Deductions equals Net Payable
        self.assertAlmostEqual(
            fin["openbim_verified_gross"] - fin["statutory_safety_set_off"],
            fin["net_payable_certified_this_period"],
            places=2
        )
        self.assertAlmostEqual(fin["net_payable_certified_this_period"], 3632500.00, places=2)

    def test_10_negative_and_edge_case_validations(self):
        """Verify negative test cases: nonexistent records, invalid rates, and timebar breaches."""
        # Case A: Nonexistent variation order raises ValueError
        with self.assertRaises(ValueError):
            audit_variation_order(
                project_id="PRJ-WHC-COM-001",
                vo_id="VO-NONEXISTENT-999",
                instruction_date="2026-08-10",
                claim_notice_date="2026-08-25",
                proposed_rate=240.0,
                proposed_tier="TIER_1_SOR"
            )

        # Case B: Nonexistent openBIM item raises ValueError
        with self.assertRaises(ValueError):
            reconcile_progress_valuation(
                project_id="PRJ-WHC-COM-001",
                claim_id="CLM-WHC-008",
                item_code="INVALID-CODE-999",
                contractor_claimed_qty=500.0
            )

        # Case C: PSSCOC Clause 19.1 28-day notice timebar breach correctly triggers TIMEBAR_EXPIRED
        vo_timebarred = audit_variation_order(
            project_id="PRJ-WHC-COM-001",
            vo_id="VO-WHC-005",
            instruction_date="2026-06-01",
            claim_notice_date="2026-07-15",  # 44 days elapsed > 28 days
            proposed_rate=85.0,
            proposed_tier="TIER_3_STAR_RATE"
        )
        self.assertEqual(
            vo_timebarred["timebar_validation"]["timebar_status"],
            "TIMEBAR_EXPIRED_CLAIM_WAIVED"
        )
        self.assertEqual(vo_timebarred["valuation_waterfall"]["certified_amount"], 0.0)


if __name__ == "__main__":
    print("=" * 70)
    print("Running ACIP S03 Commercial Control Automated Test Suite")
    print("=" * 70)
    unittest.main()
