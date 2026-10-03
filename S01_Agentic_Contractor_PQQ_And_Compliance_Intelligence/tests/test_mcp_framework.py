import unittest
import sys
import os

# Add mcp_server to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mcp_server')))

from server import (
    query_contractor_profile,
    verify_safety_compliance,
    assess_financial_solvency,
    evaluate_pqm_score,
    audit_contract_risk,
    list_sample_tenders,
    simulate_contractor_monte_carlo_risk
)

class TestMCPComplianceServer(unittest.TestCase):

    def test_query_contractor_profile_valid(self):
        result = query_contractor_profile("Heng Win")
        self.assertIn("Heng Win (Private) Limited", result)
        self.assertIn("BCA CRS Grade: A1", result)
        self.assertIn("CW01", result)
        self.assertIn("Unlimited", result)

    def test_query_contractor_profile_not_found(self):
        result = query_contractor_profile("NonExistentCorp999")
        self.assertIn("No contractor profile found", result)

    def test_verify_safety_compliance_compliant(self):
        result = verify_safety_compliance("197600888B")
        self.assertIn("COMPLIANT", result)
        self.assertIn("MOM Safety Demerit Points (SDP): 0 / 25 Threshold", result)
        self.assertIn("bizSAFE STAR", result)

    def test_verify_safety_compliance_debarred_sdp_breach(self):
        result = verify_safety_compliance("Titan Piling")
        self.assertIn("CRITICAL STATUTORY BAR", result)
        self.assertIn("28", result)
        self.assertIn("exceeds MOM legal threshold of 25", result)

    def test_assess_financial_solvency_strong(self):
        result = assess_financial_solvency("Heng Win", 120000000.0)
        self.assertIn("FINANCIALLY SOLVENT", result)
        self.assertIn("Current Ratio: 1.96", result)
        self.assertIn("ADEQUATE", result)

    def test_assess_financial_solvency_distressed(self):
        result = assess_financial_solvency("Starlight Urban", 35000000.0)
        self.assertTrue("INSOLVENT / HIGH RISK (FAILED)" in result or "FAILED BOND CAPACITY" in result)
        self.assertIn("Current Ratio: 0.85", result)

    def test_evaluate_pqm_score(self):
        result = evaluate_pqm_score("Heng Win", 118000000.0, 120000000.0, 0.3)
        self.assertIn("FINAL COMPOSITE PQM SCORE", result)
        self.assertIn("CONQUAS Quality Benchmark", result)

    def test_audit_contract_risk_sopa_violation(self):
        clause = "Subcontractor will be paid within 14 days after main contractor receives payment from the Employer (pay when paid)."
        result = audit_contract_risk(clause, "PSSCOC")
        self.assertIn("SOPA BREACH", result)
        self.assertIn("Section 9 of the Singapore Building and Construction Industry Security of Payment Act", result)

    def test_audit_contract_risk_short_notice(self):
        clause = "The contractor must give written notice of any variation claim within 3 days of the event, failing which all entitlement is forfeited."
        result = audit_contract_risk(clause, "PSSCOC")
        self.assertIn("ONEROUS NOTICE PERIOD", result)
        self.assertIn("< 14 days", result)

    def test_list_sample_tenders(self):
        result = list_sample_tenders()
        self.assertIn("Woodlands Health Campus", result)
        self.assertIn("TND-2026-SG-001", result)

    def test_simulate_contractor_monte_carlo_risk_prudent(self):
        result = simulate_contractor_monte_carlo_risk("Heng Win", 120000000.0, 10000)
        self.assertIn("QUANTITATIVE MONTE CARLO RISK DOSSIER", result)
        self.assertIn("Value-at-Risk (VaR 95%)", result)
        self.assertIn("PRUDENT & LOW RISK", result)

    def test_simulate_contractor_monte_carlo_risk_critical_default(self):
        result = simulate_contractor_monte_carlo_risk("Starlight Urban", 35000000.0, 10000)
        self.assertIn("QUANTITATIVE MONTE CARLO RISK DOSSIER", result)
        self.assertIn("CRITICAL DEFAULT RISK", result)
        self.assertIn("Insolvency / Default Probability", result)

if __name__ == '__main__':
    unittest.main()
