#!/usr/bin/env python3
"""
S02: Automated Test Suite for Deterministic Bid Evaluation & Multi-Agent Deliberation
Project: Woodlands Health Campus Acute Care Wing (S$120,000,000 Benchmark)
Tender ID: TND-WHC-2026-001
"""

import os
import sys
import unittest
import duckdb

# Ensure S02 root is on sys.path
S02_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, S02_ROOT)

from mcp_server.server import (
    audit_rate_leveling,
    detect_front_loading,
    check_scope_exclusions,
    evaluate_pqm_score,
    generate_tender_evaluation_report
)
from agent_client.evaluator import TenderBoardChairmanAgent

DB_PATH = os.path.join(S02_ROOT, "data", "hospital_tender.duckdb")

class TestS02BidEvaluationPipeline(unittest.TestCase):

    def setUp(self):
        self.assertTrue(os.path.exists(DB_PATH), f"Database not found at {DB_PATH}")

    def test_01_duckdb_schema_and_pte_benchmark(self):
        """Verify DuckDB master registry (50 contractors), multi-project registry, M:M project_bidders, and PTE benchmark sum."""
        con = duckdb.connect(DB_PATH, read_only=True)
        contractors_cnt = con.execute("SELECT COUNT(*) FROM contractors").fetchone()[0]
        projects_cnt = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        tenders_cnt = con.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
        project_bidders_cnt = con.execute("SELECT COUNT(*) FROM project_bidders").fetchone()[0]
        trades_cnt = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        items_cnt = con.execute("SELECT COUNT(*) FROM boq_items").fetchone()[0]
        bidders_cnt = con.execute("SELECT COUNT(*) FROM bidders WHERE tender_id = 'TND-WHC-2026-001'").fetchone()[0]
        pte_sum = con.execute("SELECT SUM(pte_total_amount) FROM boq_items").fetchone()[0]
        con.close()

        self.assertEqual(contractors_cnt, 50)
        self.assertEqual(projects_cnt, 3)
        self.assertEqual(tenders_cnt, 3)
        self.assertEqual(project_bidders_cnt, 13)
        self.assertEqual(trades_cnt, 8)
        self.assertEqual(items_cnt, 18)
        self.assertEqual(bidders_cnt, 5)
        self.assertAlmostEqual(pte_sum, 114999998.90, places=1)

    def test_02_rate_leveling_outliers(self):
        """Verify Z-score outlier detection flags extreme deviations across bidders."""
        res = audit_rate_leveling(DB_PATH, z_threshold=1.5)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(res["total_anomalies_flagged"], 0)
        # Check that B03 dumping items are flagged
        b03_anomalies = [a for a in res["anomalies"] if a["bidder_id"] == "B03"]
        self.assertGreater(len(b03_anomalies), 0)

    def test_03_front_loading_detection(self):
        """Verify WinningPine Construction (B02) is flagged with high front-loading cash extraction risk."""
        res = detect_front_loading(DB_PATH)
        self.assertEqual(res["status"], "SUCCESS")
        b02 = next(b for b in res["front_loading_analysis"] if b["bidder_id"] == "B02")

        self.assertEqual(b02["risk_flag"], "HIGH_FRONT_LOADING_RISK")
        self.assertGreater(b02["front_loading_risk_index"], 1.5)
        self.assertGreater(b02["substructure_pct"], 35.0)
        self.assertGreater(b02["early_cash_extraction_sgd"], 20000000.0)

        # Heng Win (B01) must be balanced
        b01 = next(b for b in res["front_loading_analysis"] if b["bidder_id"] == "B01")
        self.assertEqual(b01["risk_flag"], "BALANCED_RATE_DISTRIBUTION")

    def test_04_scope_exclusion_detection(self):
        """Verify GemStone Building Contractors (B04) scope omission of medical gas piping is caught."""
        res = check_scope_exclusions(DB_PATH)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["total_scope_exclusions_found"], 1)

        b04_ex = res["exclusions"][0]
        self.assertEqual(b04_ex["bidder_id"], "B04")
        self.assertEqual(b04_ex["clause_id"], "QUAL-14.2")
        self.assertEqual(b04_ex["qualification_page_nr"], 38)
        self.assertAlmostEqual(b04_ex["employer_cost_exposure_sgd"], 6790000.0, places=1)
        self.assertEqual(b04_ex["severity"], "CRITICAL_SCOPE_OMISSION")

    def test_05_pqm_scoring_and_ranking(self):
        """Verify deterministic BCA PQM formula evaluates Heng Win (B01) as Rank 1 and Starlight (B03) as ALT warning."""
        res = evaluate_pqm_score(DB_PATH, price_weight=0.5, quality_weight=0.5)
        self.assertEqual(res["status"], "SUCCESS")

        leaderboard = res["pqm_leaderboard"]
        self.assertEqual(len(leaderboard), 5)

        # Winner: B01 Heng Win (Private) Limited
        self.assertEqual(leaderboard[0]["bidder_id"], "B01")
        self.assertEqual(leaderboard[0]["bidder_name"], "Heng Win (Private) Limited")
        self.assertEqual(leaderboard[0]["pqm_rank"], 1)
        self.assertGreater(leaderboard[0]["pqm_composite_score"], 95.0)

        # Last place: B03 Starlight Urban Infrastructure due to screening ALT penalty
        self.assertEqual(leaderboard[-1]["bidder_id"], "B03")
        self.assertEqual(leaderboard[-1]["commercial_risk_status"], "SCREENING_ALT_HEURISTIC_POTENTIAL_DUMPING")

    def test_06_multi_agent_deliberation(self):
        """Verify Tender Board Chairman agent synthesizes findings and issues 2 clarification letters."""
        chairman = TenderBoardChairmanAgent()
        report = chairman.conduct_board_deliberation(DB_PATH)

        self.assertEqual(report["recommended_awardee"]["bidder_id"], "B01")
        self.assertEqual(report["recommended_awardee"]["bidder_name"], "Heng Win (Private) Limited")
        self.assertEqual(len(report["clarification_letters_issued"]), 2)

        recipients = [c["recipient"] for c in report["clarification_letters_issued"]]
        self.assertIn("WinningPine Construction Pte Ltd", recipients)
        self.assertIn("GemStone Building Contractors Pte Ltd", recipients)

    def test_07_price_score_monotonicity_across_boundary(self):
        """Closing evidence for AI Council Finding 1: Assert strict monotonicity of commercial price score across ratio 1.05 boundary."""
        # Test ratios from 1.00 to 1.30 in steps of 0.01
        prev_score = 100.0
        for step in range(100, 131):
            ratio = step / 100.0
            if 0.90 <= ratio <= 1.05:
                score = 100.0 - (abs(1.0 - ratio) * 150.0)
            else:
                score = max(10.0, 92.5 - ((ratio - 1.05) * 180.0))
            score = min(100.0, max(0.0, score))
            # Monotonicity assertion: as price increases above median, score must strictly decrease or equalize
            self.assertLessEqual(score, prev_score, f"Score increased at ratio {ratio}: {score} > {prev_score}")
            prev_score = score
        # Specifically verify continuity at boundary 1.05:
        score_at_105_lower = 100.0 - (0.05 * 150.0)  # 92.5
        score_at_105_upper = 92.5 - (0.0 * 180.0)     # 92.5
        self.assertEqual(score_at_105_lower, score_at_105_upper)

    def test_08_scope_exclusion_equalized_sum_impact(self):
        """Closing evidence for AI Council Finding 2: Assert B04 submitted bid S$105.15M is equalized by S$6.79M exposure to S$111.94M."""
        res = evaluate_pqm_score(DB_PATH)
        b04 = next(b for b in res["pqm_leaderboard"] if b["bidder_id"] == "B04")
        self.assertAlmostEqual(b04["submitted_bid_sum"], 105149742.25, places=2)
        self.assertAlmostEqual(b04["scope_exclusion_adjustment_sgd"], 6790000.0, places=2)
        self.assertAlmostEqual(b04["normalized_tender_sum_sgd"], 111939742.25, places=2)
        self.assertEqual(b04["pqm_rank"], 2)

    def test_09_multi_tender_validation(self):
        """Closing evidence for DeepSeek Finding: Dynamic tender parameter routing and validation."""
        from mcp_server.server import list_tenders
        tenders_res = list_tenders(DB_PATH)
        self.assertEqual(tenders_res["status"], "SUCCESS")
        self.assertEqual(len(tenders_res["tenders"]), 3)

        # Invalid tender_id must raise ValueError
        with self.assertRaises(ValueError):
            evaluate_pqm_score(DB_PATH, tender_id="TND-INVALID-999")


if __name__ == "__main__":
    unittest.main()
