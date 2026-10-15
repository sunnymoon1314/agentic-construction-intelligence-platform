#!/usr/bin/env python3
"""
ACIP S04: Increment 4 Automated Verification & Field-Ready Cockpit Suite
Module: ACIP S04 - Agentic Progress & Delay Intelligence (Module Code: S04)
File: tests/test_s04_increment_4.py

Verification Targets for Increment 4:
1. TEST-01: SRE Health Probes Contract & Liveness (/livez, /readyz, /healthz, version 1.4.0).
2. TEST-02: Project Profile Registry Governance & Track Isolation (All 4 tracks + 404 guardrail).
3. TEST-03: Authoritative Parquet-backed Schedule Endpoint & Discrete-Day CPM Floats.
4. TEST-04: Delay Events Registry & Multi-Agent Claims Lifecycle Governance.
5. TEST-05: Contemporaneous Site Radar Weather Telemetry & Discrepancy Detection.
6. TEST-06: Deterministic TIA Fragnet Simulation Engine (Zero-LLM Math, PSSCOC/SIA Risk Rules).
7. TEST-07: Multi-Agent Deliberation Consensus Endpoint & 3-Agent Turn Signatures.
8. TEST-08: Universal ACIP Data Dictionary Bundle API & Canonical Fallback Resilience.
9. TEST-09: Cockpit Static Assets & SVG MIME Type Compliance.
10. TEST-10: SRE Fail-Closed Behavior on Malformed JSON Payloads.
11. TEST-11: FastMCP TIA Engine Failure Transparency, Stack Trace Logging & Discrete-Day Fallback (F11, F13, F14).
12. TEST-12: Multi-Track Contract Governance (PSSCOC, SIA 9th Ed, LTA Civil Standard) & Benchmark Boundaries (F10, F13).
13. TEST-13: Schedule Parquet Relationship Fallback on Missing/Unreadable Source (F12, F15, F22).
14. TEST-14: Legacy ai_consensus Alias Retirement & Zero Synthetic Multi-Model Claims Contract (F16, F25).
15. TEST-15: Canonical 6-Activity Schedule Parquet Alignment, Milestone Verification, and Baseline Invariance.
16. TEST-16: Multi-Stage Delay Lifecycle Governance, Contemporaneous Hearing Fragnet, and 3-Agent Turn Signatures.
17. TEST-17: TIA Fragnet Simulator Working Calendar Arithmetic, Residual LD Formula, and Parquet State-Isolation.
18. TEST-18: Cross-View Contract Consistency, Canonical Event Naming, Deliberation Terminology, and Negative Cases.
19. TEST-19: Deliberation Pipeline and API Cross-Path Parity, Correlated Identity, and Strict Tier Derivation.
"""

from datetime import date, datetime, timezone
import json
import os
import socketserver
import sys
import threading
import unittest
import urllib.request
import urllib.error

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from dashboard.server import ACIPS04DashboardHandler, PROJECT_PROFILES, DELAY_EVENTS_DATA


class TestS04Increment4(unittest.TestCase):
    """Automated unit and integration test suite for Increment 4 Cockpit."""

    @classmethod
    def setUpClass(cls):
        # Spawn ephemeral TCP server on OS-assigned free port (0)
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), ACIPS04DashboardHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=3)

    def _get_json(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data), resp.headers

    def _post_json(self, path: str, payload: dict):
        url = f"{self.base_url}{path}"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data), resp.headers

    def test_01_sre_health_probes_liveness_readiness_versioning(self):
        """TEST-01: Verify SRE Health Probes (/livez, /readyz, /healthz) and failure-path decoupling."""
        # 1. /livez (Happy path)
        status, data, _ = self._get_json("/livez")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ALIVE")
        self.assertIn("timestamp", data)

        # 2. /readyz (Happy path)
        status, data, _ = self._get_json("/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "READY")

        # 3. /healthz (Happy path)
        status, data, _ = self._get_json("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "HEALTHY")
        self.assertEqual(data.get("version"), "1.4.0")
        self.assertIn("active_milestone", data)
        self.assertIn("Increment 4", data["active_milestone"])
        self.assertEqual(data.get("port"), 8087)
        self.assertEqual(data["sre_metrics"]["cpm_engine_status"], "OPERATIONAL")
        self.assertEqual(data["sre_metrics"]["multi_agent_deliberation"], "OPERATIONAL")

        # 4. Failure-path decoupling test: Simulate unready state
        orig_profiles = dict(PROJECT_PROFILES)
        try:
            PROJECT_PROFILES.clear()
            try:
                self._get_json("/readyz")
                self.fail("Expected HTTP 503 when profiles uninitialized")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 503)
                err_data = json.loads(e.read().decode("utf-8"))
                self.assertIn("error", err_data)
                self.assertEqual(err_data.get("status"), 503)

            # Decoupled liveness: /livez MUST still return 200 ALIVE when downstream readiness fails
            l_status, l_data, _ = self._get_json("/livez")
            self.assertEqual(l_status, 200)
            self.assertEqual(l_data.get("status"), "ALIVE")
        finally:
            PROJECT_PROFILES.update(orig_profiles)

        # Confirm restored readiness
        status_restored, r_data, _ = self._get_json("/readyz")
        self.assertEqual(status_restored, 200)
        self.assertEqual(r_data.get("status"), "READY")

    def test_02_project_profiles_registry_across_all_four_tracks(self):
        """TEST-02: Verify project profile registry across 4 tracks and 404 guardrail."""
        status, projects, _ = self._get_json("/api/projects")
        self.assertEqual(status, 200)
        self.assertIsInstance(projects, list)
        self.assertEqual(len(projects), 4)

        expected_ids = {"PRJ-WHC-COM-001", "PRJ-JID-ATP-004", "PRJ-TWRP-002", "PRJ-T5-003"}
        retrieved_ids = {p["project_id"] for p in projects}
        self.assertEqual(expected_ids, retrieved_ids)

        # Query single project
        status, p_whc, _ = self._get_json("/api/projects?id=PRJ-WHC-COM-001")
        self.assertEqual(status, 200)
        self.assertEqual(p_whc["project_name"], "Woodlands Health Campus Commercial Annex")
        self.assertEqual(p_whc["contractor"], "WinningPine Construction Pte Ltd")
        self.assertEqual(p_whc["contract_sum_sgd"], 55000000.0)
        self.assertEqual(p_whc["liquidated_damages_daily_sgd"], 15000.0)

        # Negative test: Unknown project returns 404
        try:
            self._get_json("/api/projects?id=PRJ-NONEXISTENT-999")
            self.fail("Expected HTTP 404 error for non-existent project")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        # Negative test: Unknown project returns 404 on /api/deliberation/consensus
        try:
            self._get_json("/api/deliberation/consensus?project_id=PRJ-NONEXISTENT-999&event_id=DLY-2026-001")
            self.fail("Expected HTTP 404 for non-existent project in /api/deliberation/consensus")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            data_err = json.loads(e.read().decode("utf-8"))
            self.assertEqual(data_err.get("status"), 404)
            self.assertIn("Project not found", data_err.get("error", ""))

    def test_03_authoritative_schedule_endpoint_critical_path_and_floats(self):
        """TEST-03: Verify Parquet-backed schedule endpoint and discrete CPM float math."""
        status, data, _ = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status, 200)
        self.assertEqual(data["project_id"], "PRJ-WHC-COM-001")
        self.assertEqual(data.get("schedule_version", data.get("baseline_id")), "BL-01")

        activities = data["activities"]
        self.assertEqual(len(activities), 6)

        # Assert critical path logic: TF == 0 -> is_critical == True
        for act in activities:
            if act["total_float"] == 0:
                self.assertTrue(act["is_critical"], f"Activity {act['activity_id']} with TF=0 must be critical")
            else:
                self.assertFalse(act["is_critical"], f"Activity {act['activity_id']} with TF>0 must not be critical")

        # Specific milestone verification
        act01 = next(a for a in activities if a["activity_id"] == "ACT-01")
        self.assertEqual(act01["early_start"], "2026-11-02")
        self.assertEqual(act01["duration_workdays"], 0)
        # Assert Parquet lineage, stored baseline mode, and authoritative fixture flag (F1, F12, F18)
        self.assertTrue(data.get("is_parquet_backed"), "WHC schedule must be backed by schedule_activities.parquet")
        self.assertEqual(data.get("activities_lineage"), "data/parquet/schedule_activities.parquet")
        self.assertEqual(data.get("relationships_lineage"), "data/parquet/schedule_relationships.parquet")
        self.assertFalse(data.get("is_fallback_schedule"))
        self.assertEqual(data.get("calculation_type"), "STORED_SCHEDULE_BASELINE_PARQUET")
        self.assertEqual(data.get("recalculation_mode"), "STORED_INGESTION_BASELINE_SERVED")
        self.assertTrue(data.get("is_authoritative_fixture"))
        self.assertEqual(len(data["relationships"]), 6)
        self.assertTrue(data["relationships"][0]["is_driving"])

        # Assert non-WHC benchmark isolation (F4, F12)
        status_jid, data_jid, _ = self._get_json("/api/schedule?project_id=PRJ-JID-ATP-004")
        self.assertEqual(status_jid, 200)
        self.assertTrue(data_jid.get("is_benchmark_illustrative"))
        self.assertFalse(data_jid.get("is_authoritative_fixture"))
        self.assertFalse(data_jid.get("is_parquet_backed"))
        self.assertTrue(data_jid.get("is_fallback_schedule"))
        self.assertEqual(data_jid.get("activities_lineage"), "CROSS_PROJECT_BENCHMARK_FIXTURE")
        self.assertEqual(data_jid.get("relationships_lineage"), "CROSS_PROJECT_BENCHMARK_FIXTURE")
        self.assertIn("Benchmark illustrative", data_jid.get("track_note", ""))

        # Negative test: Unknown project ID returns 404
        try:
            self._get_json("/api/schedule?project_id=PRJ-NONEXISTENT-999")
            self.fail("Expected HTTP 404 for unknown project in /api/schedule")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_04_delay_events_registry_lifecycle_and_notice_compliance(self):
        """TEST-04: Verify delay events registry, notice compliance, and project isolation."""
        status, data, _ = self._get_json("/api/delay_events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total_events"], 1)

        dly01 = next(e for e in data["delay_events"] if e["event_id"] == "DLY-2026-001")
        self.assertEqual(dly01["revision_stage"], "CONTRACTOR_CLAIM")
        self.assertEqual(dly01["cause_category"], "WEATHER_FORCE_MAJEURE")
        self.assertTrue(dly01["is_notice_compliant"])
        self.assertEqual(dly01["claimed_eot_workdays"], 4)
        self.assertIn("Clause 23.1", dly01["clause_citation"])
        # Assert neutral evaluation_note and deterministic_evaluation fields (F16)
        self.assertIn("evaluation_note", dly01)
        self.assertIn("deterministic_evaluation", dly01)
        self.assertIn("DETERMINISTIC EVALUATION", dly01["evaluation_note"])

        # Negative test: Unknown project ID returns 404
        try:
            self._get_json("/api/delay_events?project_id=PRJ-NONEXISTENT-999")
            self.fail("Expected HTTP 404 for unknown project in /api/delay_events")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_05_site_radar_weather_telemetry_discrepancy_detection(self):
        """TEST-05: Verify site radar weather discrepancy scoring and project isolation."""
        status, data, _ = self._get_json("/api/site_radar?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["records_count"], 4)

        # Check for corroboration on Nov 5 (heavy rain) and discrepancy on Nov 7 (zero rain claim)
        nov5 = next(r for r in data["site_records"] if r["date"] == "2026-11-05")
        self.assertEqual(nov5["status"], "CORROBORATED_HEAVY_RAIN")
        self.assertGreater(nov5["weather_station_rain_mm"], 20.0)

        nov7 = next(r for r in data["site_records"] if r["date"] == "2026-11-07")
        self.assertEqual(nov7["status"], "DISCREPANCY_FLAGGED")
        self.assertEqual(nov7["weather_station_rain_mm"], 0.0)
        self.assertGreater(nov7["contractor_rain_claim_hrs"], 0.0)

        # Negative test: Unknown project ID returns 404
        try:
            self._get_json("/api/site_radar?project_id=PRJ-NONEXISTENT-999")
            self.fail("Expected HTTP 404 for unknown project in /api/site_radar")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_06_tia_fragnet_simulation_deterministic_calendar_cpm(self):
        """TEST-06: Verify deterministic TIA fragnet simulator with CPM float sensitivity."""
        # 1. Critical path insertion on ACT-03 (TF=0): Net critical shift = 3 workdays
        payload_act03 = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Unforeseen Groundwater Pit Pumping",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 3,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        status, data_act03, _ = self._post_json("/api/tia/simulate", payload_act03)
        self.assertEqual(status, 200)
        self.assertEqual(data_act03["critical_path_shift_workdays"], 3)
        self.assertEqual(data_act03["baseline_completion_date"], "2026-11-19")
        self.assertEqual(data_act03["impacted_completion_date"], "2026-11-24")
        self.assertEqual(data_act03["liquidated_damages_rate_daily_sgd"], 15000.0)
        self.assertIn("CPM", data_act03["calculation_engine"])
        self.assertIn(data_act03["engine_mode"], ["GENUINE_CPM_TIA_ENGINE", "DETERMINISTIC_DISCRETE_DAY_FALLBACK"])
        self.assertEqual(data_act03["agentic_synthesis"]["consensus_status"], "DETERMINISTIC_MATHEMATICAL_CALCULATION")
        self.assertFalse(data_act03["agentic_synthesis"]["llm_inference_used"])
        self.assertNotIn("models_aligned", data_act03["agentic_synthesis"])
        # Assert contract-aware evidence-qualified governing rules on WHC (F10, F17, F26)
        self.assertIn("RECORDED_COMPLIANT", data_act03["governing_rules"]["notice_compliance"])
        self.assertIn("point-of-use notice verification pending", data_act03["governing_rules"]["notice_compliance"])
        self.assertIn("REGISTERED_PROFILE_MATCH", data_act03["governing_rules"]["contract_guardrail"])
        self.assertIn("physical deed verification pending", data_act03["governing_rules"]["contract_guardrail"])

        # 2. Non-critical path insertion on ACT-04: Network float absorption verification
        payload_act04 = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Ground Anchor Equipment Fault",
            "inserted_after_activity_id": "ACT-04",
            "fragnet_duration_days": 3,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        status, data_act04, _ = self._post_json("/api/tia/simulate", payload_act04)
        self.assertEqual(status, 200)
        self.assertEqual(data_act04["critical_path_shift_workdays"], 2)
        self.assertEqual(data_act04["impacted_completion_date"], "2026-11-23")

        # 3. Boundary test: Minimum duration = 1 workday (Valid)
        payload_dur1 = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Single Day Boundary Check",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 1,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        status_d1, data_d1, _ = self._post_json("/api/tia/simulate", payload_dur1)
        self.assertEqual(status_d1, 200)
        self.assertEqual(data_d1["critical_path_shift_workdays"], 1)

        # 4. Boundary test: Maximum duration = 60 workdays (Valid)
        payload_dur60 = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Max Workday Boundary Check",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 60,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        status_d60, data_d60, _ = self._post_json("/api/tia/simulate", payload_dur60)
        self.assertEqual(status_d60, 200)
        self.assertEqual(data_d60["critical_path_shift_workdays"], 60)

        # 5. Boundary rejections: 0 and 61
        for invalid_dur in [0, 61]:
            try:
                self._post_json("/api/tia/simulate", {
                    "project_id": "PRJ-WHC-COM-001",
                    "inserted_after_activity_id": "ACT-03",
                    "fragnet_duration_days": invalid_dur
                })
                self.fail(f"Expected HTTP 400 for boundary duration {invalid_dur}")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 400)

        # 6. Type rejections: Booleans and Fractional floats
        for invalid_type_dur in [True, False, 3.5]:
            try:
                self._post_json("/api/tia/simulate", {
                    "project_id": "PRJ-WHC-COM-001",
                    "inserted_after_activity_id": "ACT-03",
                    "fragnet_duration_days": invalid_type_dur
                })
                self.fail(f"Expected HTTP 400 for invalid duration type {invalid_type_dur}")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 400)

    def test_07_multi_agent_deliberation_consensus_endpoint(self):
        """TEST-07: Verify multi-agent adversarial deliberation consensus endpoint."""
        status, data, _ = self._get_json("/api/deliberation/consensus?project_id=PRJ-WHC-COM-001&event_id=DLY-2026-001")
        self.assertEqual(status, 200)
        self.assertEqual(data["project_id"], "PRJ-WHC-COM-001")
        self.assertEqual(data["event_id"], "DLY-2026-001")
        self.assertIn("turns", data)
        self.assertEqual(len(data["turns"]), 3)

        agent_names = [t["agent_name"] for t in data["turns"]]
        self.assertIn("Contractor Claims Agent", agent_names)
        self.assertIn("Employer QS Agent", agent_names)
        self.assertIn("Superintending Officer Agent", agent_names)

        self.assertIn("determination_tier", data)
        self.assertIn("adjudication_disclaimer", data)
        self.assertIn("SOPA", data["adjudication_disclaimer"])

    def test_08_universal_data_dictionary_bundle(self):
        """TEST-08: Verify universal data dictionary lookup bundle."""
        status, data, _ = self._get_json("/api/dictionary")
        self.assertEqual(status, 200)
        self.assertIn("by_id", data)

        # Check required canonical terms
        by_id = data["by_id"]
        expected_terms = [
            "ACIP-S04-CPM-CRITICAL_PATH",
            "ACIP-S04-CPM-TOTAL_FLOAT",
            "ACIP-S04-CPM-FREE_FLOAT",
            "ACIP-CORE-EXTENSION_OF_TIME"
        ]
        for term in expected_terms:
            self.assertIn(term, by_id, f"Dictionary must contain canonical term {term}")
            self.assertIn("plain_english_definition", by_id[term])

    def test_09_static_asset_serving_and_html_sanitization(self):
        """TEST-09: Verify cockpit static asset delivery and HTML sanitization."""
        # 1. Root / index.html
        url_root = f"{self.base_url}/"
        with urllib.request.urlopen(url_root, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            content_type = resp.headers.get("Content-Type", "")
            self.assertIn("text/html", content_type)
            body = resp.read().decode("utf-8")
            self.assertIn("ACIP Forensics", body)
            self.assertIn("S04 COCKPIT", body)

        # 2. HTML Sanitization Regression Test (R2)
        # Verify escapeHtml is defined and called across dynamic interpolation sites in index.html
        self.assertIn("function escapeHtml(str)", body, "index.html must define escapeHtml()")
        self.assertIn("escapeHtml(act.wbs_code)", body, "Schedule rows must escape WBS code")
        self.assertIn("escapeHtml(evt.event_id)", body, "Delay event rows must escape event ID")
        self.assertIn("escapeHtml(rec.status)", body, "Site radar cards must escape status")
        self.assertIn("escapeHtml(t.agent_name)", body, "Deliberation cards must escape agent name")
        self.assertIn("escapeHtml(title)", body, "Forensic drawer must escape drawer title")

        # Prove inertness against malicious payload: <img src=x onerror=alert(1)>
        xss_payload = "<img src=x onerror=alert(1)>"
        # Mirror JavaScript escapeHtml algorithm in Python to verify exact transformed string
        sanitized_payload = (
            xss_payload
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
        # 4. Zero-Value Preservation Contract (F6)
        # JavaScript escapeHtml guard: if (str === null || str === undefined) return '';
        def js_escape_html(v):
            if v is None:
                return ''
            return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

        self.assertEqual(js_escape_html(0), "0", "Numeric 0 must be preserved as '0' and not dropped")
        self.assertEqual(js_escape_html(False), "False")
        self.assertEqual(js_escape_html(None), "")
        self.assertIn("if (str === null || str === undefined) return '';", body, "index.html must check null/undefined, not falsy !str")

    def test_10_sre_fail_closed_and_malformed_payload_rejection(self):
        """TEST-10: Verify SRE fail-closed rejection on invalid payloads and parameters."""
        # 1. Malformed JSON string
        url = f"{self.base_url}/api/tia/simulate"
        req = urllib.request.Request(
            url,
            data=b"INVALID_MALFORMED_JSON_STRING",
            headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Expected HTTP 400 Bad Request for malformed payload")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

        # 2. Unknown Project ID in TIA simulate -> 404
        try:
            self._post_json("/api/tia/simulate", {
                "project_id": "PRJ-NONEXISTENT-999",
                "fragnet_duration_days": 3
            })
            self.fail("Expected HTTP 404 for unknown project in /api/tia/simulate")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        # 3. Invalid Activity ID -> 400
        try:
            self._post_json("/api/tia/simulate", {
                "project_id": "PRJ-WHC-COM-001",
                "inserted_after_activity_id": "ACT-DOES-NOT-EXIST-999",
                "fragnet_duration_days": 3
            })
            self.fail("Expected HTTP 400 for invalid activity ID in /api/tia/simulate")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

        # 4. Invalid Duration (non-positive or too large) -> 400
        try:
            self._post_json("/api/tia/simulate", {
                "project_id": "PRJ-WHC-COM-001",
                "fragnet_duration_days": -5
            })
            self.fail("Expected HTTP 400 for negative duration in /api/tia/simulate")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

        # 5. Invalid Risk Allocation -> 400
        try:
            self._post_json("/api/tia/simulate", {
                "project_id": "PRJ-WHC-COM-001",
                "risk_allocation": "UNKNOWN_RISK_CATEGORY"
            })
            self.fail("Expected HTTP 400 for invalid risk allocation in /api/tia/simulate")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

        # Confirm server remains alive and healthy after fault injections
        status, health, _ = self._get_json("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "HEALTHY")

    def test_11_tia_engine_failure_fallback_transparency_and_logging(self):
        """TEST-11: Verify that FastMCP engine failures activate discrete-day fallback with logging and transparency (F11, F13, F14)."""
        import dashboard.server as dserver
        orig_engine = dserver.s04_simulate_tia_fragnet

        def mock_failing_engine(**kwargs):
            raise RuntimeError("Simulated FastMCP Graph Kernel Fault for failure transparency test")

        try:
            dserver.s04_simulate_tia_fragnet = mock_failing_engine
            payload = {
                "project_id": "PRJ-WHC-COM-001",
                "fragnet_name": "Simulated Fault Injection Fragnet",
                "inserted_after_activity_id": "ACT-03",
                "fragnet_duration_days": 4,
                "risk_allocation": "EMPLOYER_RISK"
            }
            with self.assertLogs("acip.s04.dashboard", level="WARNING") as log_capture:
                status, data, _ = self._post_json("/api/tia/simulate", payload)
                self.assertEqual(status, 200)
                self.assertEqual(data["engine_mode"], "DETERMINISTIC_DISCRETE_DAY_FALLBACK")
                self.assertTrue(data["is_fallback_calculation"])
                self.assertEqual(data["calculation_engine"], "Deterministic Discrete-Day CPM Fallback")
                self.assertEqual(data["critical_path_shift_workdays"], 4)
                self.assertEqual(data["compensable_eot_workdays"], 4)
                self.assertEqual(data["contractor_culpable_workdays"], 0)

            # Assert log message was emitted and includes failure details (F14)
            self.assertTrue(any("TIA FastMCP engine calculation failed" in msg for msg in log_capture.output),
                            "Expected logger.warning with failure message")
            self.assertTrue(any("Simulated FastMCP Graph Kernel Fault" in msg for msg in log_capture.output),
                            "Expected stack trace message in logs")
        finally:
            dserver.s04_simulate_tia_fragnet = orig_engine

    def test_12_non_whc_project_contract_and_benchmark_boundaries(self):
        """TEST-12: Verify contract-aware governing rules and benchmark disclaimers across non-WHC tracks (F10, F13)."""
        # 1. Test PRJ-MBF-FIT-002 (SIA Measurement 9th Ed)
        payload_sia = {
            "project_id": "PRJ-MBF-FIT-002",
            "fragnet_name": "Architect Disruption Benchmark",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 5,
            "risk_allocation": "EMPLOYER_RISK"
        }
        status_sia, data_sia, _ = self._post_json("/api/tia/simulate", payload_sia)
        self.assertEqual(status_sia, 200)
        self.assertTrue(data_sia["is_benchmark_illustrative"])
        self.assertEqual(data_sia["track_scope"], "BENCHMARK_ILLUSTRATIVE_NETWORK")
        self.assertIn("ILLUSTRATIVE_NOT_EVALUATED", data_sia["governing_rules"]["notice_compliance"])
        self.assertIn("SIA Measurement 9th Ed", data_sia["governing_rules"]["contract_guardrail"])
        self.assertTrue(data_sia["agentic_synthesis"]["synthesis_summary"].startswith("[BENCHMARK DEMO:"))

        # 2. Test PRJ-CRL-CR108 (LTA Civil Standard)
        payload_lta = {
            "project_id": "PRJ-CRL-CR108",
            "fragnet_name": "LTA Utility Clash Benchmark",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 2,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        status_lta, data_lta, _ = self._post_json("/api/tia/simulate", payload_lta)
        self.assertEqual(status_lta, 200)
        self.assertTrue(data_lta["is_benchmark_illustrative"])
        self.assertIn("LTA Civil Standard", data_lta["governing_rules"]["contract_guardrail"])
        self.assertIn("ILLUSTRATIVE_NOT_EVALUATED", data_lta["governing_rules"]["notice_compliance"])

    def test_13_schedule_parquet_relationship_fallback_on_missing_file(self):
        """TEST-13: Verify that missing or unreadable relationship Parquet isolates relationship fallback while activity Parquet loads (F12, F15, F22)."""
        import dashboard.server as dserver
        orig_rel_path = dserver.SCHEDULE_RELATIONSHIPS_PARQUET_PATH

        try:
            dserver.SCHEDULE_RELATIONSHIPS_PARQUET_PATH = "/nonexistent/schedule_relationships.parquet"
            status, data, _ = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001")
            self.assertEqual(status, 200)
            # Activities load from genuine Parquet!
            self.assertEqual(data.get("activities_lineage"), "data/parquet/schedule_activities.parquet")
            self.assertEqual(len(data.get("activities", [])), 6)
            # Relationships specifically fall back to fixture!
            self.assertEqual(data.get("relationships_lineage"), "IN_MEMORY_FIXTURE_FALLBACK")
            self.assertEqual(len(data.get("relationships", [])), 6)
            # Overall status reflects mixed-source fallback:
            self.assertFalse(data.get("is_parquet_backed"))
            self.assertTrue(data.get("is_fallback_schedule"))
            self.assertFalse(data.get("is_authoritative_fixture"))
        finally:
            dserver.SCHEDULE_RELATIONSHIPS_PARQUET_PATH = orig_rel_path

    def test_14_ai_consensus_alias_sunset_contract_and_zero_synthetic_claims(self):
        """TEST-14: Assert legacy ai_consensus alias sunset contract and zero synthetic cross-model claims (F16, F25)."""
        forbidden_tokens = ["Claude", "Sonnet", "GPT-4o", "Gemini", "CROSS-MODEL AGREEMENT", "CROSS-MODEL"]

        # 1. Full raw payload scan of GET /api/delay_events
        url = f"{self.base_url}/api/delay_events?project_id=PRJ-WHC-COM-001"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            raw_delay_events_body = resp.read().decode("utf-8")

        # Must contain zero synthetic cross-model claims anywhere in entire raw response
        for token in forbidden_tokens:
            self.assertNotIn(token, raw_delay_events_body, f"Forbidden model token '{token}' detected in /api/delay_events payload")

        # Parse and verify alias contract semantics
        data = json.loads(raw_delay_events_body)
        events = data.get("delay_events", [])
        self.assertGreater(len(events), 0)

        for evt in events:
            # Must provide neutral evaluation_note and deterministic_evaluation
            self.assertIn("evaluation_note", evt)
            self.assertIn("deterministic_evaluation", evt)
            self.assertIn("ai_consensus", evt)
            # Assert backwards-compatibility parity
            self.assertEqual(evt["ai_consensus"], evt["evaluation_note"])
            self.assertEqual(evt["ai_consensus"], evt["deterministic_evaluation"])
            self.assertTrue(evt["ai_consensus"].startswith("DETERMINISTIC EVALUATION"))

        # 2. Full raw payload scan of POST /api/tia/simulate
        sim_payload = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Unforeseen Groundwater Pit Pumping",
            "inserted_after_activity_id": "ACT-03",
            "fragnet_duration_days": 3,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE"
        }
        sim_req = urllib.request.Request(
            f"{self.base_url}/api/tia/simulate",
            data=json.dumps(sim_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(sim_req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            raw_tia_body = resp.read().decode("utf-8")

        for token in forbidden_tokens:
            self.assertNotIn(token, raw_tia_body, f"Forbidden model token '{token}' detected in /api/tia/simulate payload")

        # 3. UI Consumer Verification: Inspect dashboard/index.html template
        index_html_path = os.path.join(MODULE_ROOT, "dashboard", "index.html")
        self.assertTrue(os.path.exists(index_html_path), "index.html not found")
        with open(index_html_path, "r", encoding="utf-8") as f:
            index_html_content = f.read()

        for token in forbidden_tokens:
            self.assertNotIn(token, index_html_content, f"Forbidden model token '{token}' rendered in dashboard/index.html")

        # Ensure ai_consensus is not used or bound as model consensus in UI
        self.assertNotIn("ai_consensus", index_html_content, "Deprecated alias 'ai_consensus' exposed in UI template")

        # 4. Sunset Contract in server.py Verification
        server_py_path = os.path.join(MODULE_ROOT, "dashboard", "server.py")
        with open(server_py_path, "r", encoding="utf-8") as f:
            server_content = f.read()

        self.assertIn("DEPRECATED COMPATIBILITY ALIAS SUNSET CONTRACT (F25)", server_content)
        self.assertIn("Release 2.0.0", server_content)
        self.assertIn("Technical Ownership", server_content)
        self.assertIn("Migration Directive", server_content)

    def test_15_forensic_reconciliation_authoritative_milestone_and_forecast_dates(self):
        """TEST-15 (F-01/F-05): Reconcile authoritative project completion milestone contract and forecast dates.
        Asserts ACT-06 is the contractual terminal milestone, BL-01 planned finish is 2026-11-19,
        and Contemporaneous Progress Update UP-01 forecast finish is 2026-11-24 (+3 workdays / 5 calendar days).
        """
        # 1. Verify /api/schedule endpoint exposes explicit milestone completion metadata
        status_sched, sched_data, _ = self._get_json("/api/schedule?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_sched, 200)
        self.assertEqual(sched_data["completion_milestone_id"], "ACT-06")
        self.assertEqual(sched_data["completion_milestone_name"], "Substructure Complete Milestone")
        self.assertEqual(sched_data["milestone_role"], "CONTRACT_PACKAGE_PRACTICAL_COMPLETION")
        self.assertEqual(sched_data["baseline_completion_date"], "2026-11-19")
        self.assertEqual(sched_data["forecast_completion_date"], "2026-11-24")
        self.assertEqual(sched_data["schedule_variance_workdays"], 3)
        self.assertEqual(sched_data["schedule_variance_calendar_days"], 5)

        # 2. Verify all six activities' durations, dates, floats, and critical statuses (F-REV-01)
        acts = {a["activity_id"]: a for a in sched_data["activities"]}
        self.assertEqual(len(acts), 6, "Authoritative network must contain exactly 6 activities")

        # ACT-01
        self.assertEqual(acts["ACT-01"]["duration_workdays"], 0)
        self.assertEqual(acts["ACT-01"]["early_start"], "2026-11-02")
        self.assertEqual(acts["ACT-01"]["early_finish"], "2026-11-02")
        self.assertTrue(acts["ACT-01"]["is_critical"])
        self.assertTrue(acts["ACT-01"]["is_milestone"])

        # ACT-02
        self.assertEqual(acts["ACT-02"]["duration_workdays"], 5)
        self.assertEqual(acts["ACT-02"]["early_start"], "2026-11-02")
        self.assertEqual(acts["ACT-02"]["early_finish"], "2026-11-06")
        self.assertTrue(acts["ACT-02"]["is_critical"])

        # ACT-03 (Canonical: 4 workdays, 2026-11-09 to 2026-11-12)
        self.assertEqual(acts["ACT-03"]["duration_workdays"], 4)
        self.assertEqual(acts["ACT-03"]["early_start"], "2026-11-09")
        self.assertEqual(acts["ACT-03"]["early_finish"], "2026-11-12")
        self.assertTrue(acts["ACT-03"]["is_critical"])

        # ACT-04 (Canonical: 6 workdays, TF = 5d, Non-Critical)
        self.assertEqual(acts["ACT-04"]["duration_workdays"], 6)
        self.assertEqual(acts["ACT-04"]["early_start"], "2026-11-04")
        self.assertEqual(acts["ACT-04"]["early_finish"], "2026-11-11")
        self.assertEqual(acts["ACT-04"]["late_finish"], "2026-11-18")
        self.assertEqual(acts["ACT-04"]["total_float"], 5)
        self.assertFalse(acts["ACT-04"]["is_critical"])

        # ACT-05 (Canonical: 5 workdays, 2026-11-13 to 2026-11-19)
        self.assertEqual(acts["ACT-05"]["duration_workdays"], 5)
        self.assertEqual(acts["ACT-05"]["early_start"], "2026-11-13")
        self.assertEqual(acts["ACT-05"]["early_finish"], "2026-11-19")
        self.assertTrue(acts["ACT-05"]["is_critical"])

        # ACT-06 (Terminal Milestone, 0 workdays)
        act06 = acts["ACT-06"]
        self.assertTrue(act06["is_milestone"])
        self.assertEqual(act06["duration_workdays"], 0)
        self.assertEqual(act06["early_start"], "2026-11-19")
        self.assertEqual(act06["early_finish"], "2026-11-19")
        self.assertEqual(act06["late_finish"], "2026-11-19")
        self.assertEqual(act06["total_float"], 0)
        self.assertTrue(act06["is_critical"])
        self.assertEqual(act06.get("milestone_role"), "CONTRACT_PACKAGE_PRACTICAL_COMPLETION")
        self.assertEqual(act06.get("forecast_finish"), "2026-11-24")
        self.assertEqual(act06.get("variance_workdays"), 3)

        # 3. Verify relationships chain in schedule response
        rels = sched_data.get("relationships", [])
        self.assertGreaterEqual(len(rels), 5)
        driving_pairs = [(r["pred"], r["succ"], r["type"]) for r in rels if r.get("is_driving")]
        self.assertIn(("ACT-01", "ACT-02", "FS"), driving_pairs)
        self.assertIn(("ACT-02", "ACT-03", "FS"), driving_pairs)
        self.assertIn(("ACT-03", "ACT-05", "FS"), driving_pairs)
        self.assertIn(("ACT-05", "ACT-06", "FS"), driving_pairs)

        # 3. Verify Executive Profile /api/projects agrees with typed scope distinction
        status_proj, proj_whc, _ = self._get_json("/api/projects?id=PRJ-WHC-COM-001")
        self.assertEqual(status_proj, 200)
        self.assertEqual(proj_whc["original_completion_date"], "2026-11-19")
        self.assertEqual(proj_whc["current_forecast_completion_date"], "2026-11-24")
        self.assertEqual(proj_whc["net_delay_days"], 3)
        self.assertEqual(proj_whc["net_delay_unit"], "workdays")
        self.assertEqual(proj_whc["completion_milestone_id"], "ACT-06")
        self.assertEqual(proj_whc["baseline_completion_date"], "2026-11-19")
        self.assertEqual(proj_whc["forecast_completion_date"], "2026-11-24")
        self.assertEqual(proj_whc["schedule_variance_workdays"], 3)
        self.assertEqual(proj_whc["schedule_variance_calendar_days"], 5)

    def test_16_forensic_reconciliation_dly_001_lifecycle_and_employer_contestation_provenance(self):
        """TEST-16 (F-02/F-04): Reconcile DLY-2026-001 across claims ledger, AI consensus audit, and party positions.
        Asserts versioned provenance explaining S$60,000 initial claim demand vs S$45,000 hearing demand,
        S$30,000 SO approved ledger determination, and S$0 advisory ruling under SCL Principle 10.
        """
        # 1. Verify /api/delay_events contains lifecycle stages and multi-tier provenance
        status_dly, dly_data, _ = self._get_json("/api/delay_events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_dly, 200)
        dly01 = next(e for e in dly_data["delay_events"] if e["event_id"] == "DLY-2026-001")
        self.assertEqual(dly01["claimed_eot_workdays"], 4)
        self.assertEqual(dly01.get("employer_claim_demand_sgd"), 60000.0)
        self.assertEqual(dly01.get("employer_hearing_demand_sgd"), 45000.0)
        self.assertEqual(dly01.get("approved_eot_workdays"), 2)
        self.assertEqual(dly01.get("culpable_delay_workdays"), 2)
        self.assertEqual(dly01.get("liquidated_damages_sgd"), 30000.0)
        self.assertEqual(dly01.get("so_advisory_eot_workdays"), 3)
        self.assertEqual(dly01.get("so_advisory_ld_sgd"), 0.0)

        # Assert lifecycle stages list
        stages = dly01.get("event_lifecycle_stages", [])
        self.assertGreaterEqual(len(stages), 3)
        rev1 = next(s for s in stages if s.get("revision") == 1)
        self.assertEqual(rev1["stage"], "CONTRACTOR_CLAIM")
        self.assertEqual(rev1["claimed_eot_days"], 4)
        self.assertEqual(rev1["employer_demand_sgd"], 60000.0)

        rev2 = next(s for s in stages if s.get("revision") == 2)
        self.assertEqual(rev2["stage"], "SUPERINTENDING_OFFICER_ASSESSMENT")
        self.assertEqual(rev2["approved_eot_days"], 2)
        self.assertEqual(rev2["culpable_days"], 2)
        self.assertEqual(rev2["assessed_ld_sgd"], 30000.0)

        rev3 = next(s for s in stages if s.get("revision") == "DELIB-01")
        self.assertEqual(rev3["stage"], "AI_CONSENSUS_DELIBERATION_HEARING")
        self.assertEqual(rev3["deliberated_eot_days"], 3)
        self.assertEqual(rev3["advisory_ld_sgd"], 0.0)
        self.assertEqual(rev3["employer_hearing_demand_sgd"], 45000.0)

        # 2. Verify /api/deliberation/consensus live hearing returns traceable turns
        status_delib, delib_data, _ = self._get_json(
            "/api/deliberation/consensus?project_id=PRJ-WHC-COM-001&event_id=DLY-2026-001"
        )
        self.assertEqual(status_delib, 200)
        self.assertEqual(delib_data["net_critical_delay_workdays"], 3.0)
        self.assertEqual(delib_data["candidate_eot_relief_days"], 3.0)
        self.assertEqual(delib_data["contractor_culpable_days"], 0.0)
        self.assertEqual(delib_data["liquidated_damages_exposure_sgd"], 0.0)

        # Inspect Employer QS Respondent turn
        resp_turn = next(t for t in delib_data["turns"] if t["agent_role"] == "RESPONDENT")
        self.assertIn("S$ 60,000.00", resp_turn["position_statement"])
        self.assertIn("S$ 45,000.00", resp_turn["position_statement"])
        self.assertEqual(resp_turn["recommended_ld_exposure_sgd"], 45000.0)

        # Inspect Superintending Officer Arbitrator turn
        arb_turn = next(t for t in delib_data["turns"] if t["agent_role"] == "ARBITRATOR")
        self.assertIn("Principle 10", arb_turn["position_statement"])
        self.assertEqual(arb_turn["recommended_eot_days"], 3.0)
        self.assertEqual(arb_turn["recommended_ld_exposure_sgd"], 0.0)

    def test_17_forensic_reconciliation_tia_arithmetic_working_calendar_and_state_isolation(self):
        """TEST-17 (F-03/F-06): Verify TIA fragnet simulator arithmetic, working calendar, and state isolation (E-04).
        Asserts 3-workday fragnet inserted at ACT-01 shifts completion by exactly +3 workdays (Nov 19 to Nov 24),
        verifies formula residual_culpable_days * daily_rate = 0 * 15,000 = S$0.00,
        and cryptographically proves zero mutation to Parquet lakehouse, delay ledger, and executive KPIs.
        """
        import hashlib
        parquet_dir = os.path.join(MODULE_ROOT, "data", "parquet")
        tables_to_check = [
            "schedule_activities.parquet",
            "schedule_versions.parquet",
            "schedule_relationships.parquet",
            "delay_events.parquet",
            "contract_parameters.parquet",
        ]

        def get_disk_hashes():
            hashes = {}
            for t in tables_to_check:
                p = os.path.join(parquet_dir, t)
                if os.path.exists(p):
                    with open(p, "rb") as f:
                        hashes[t] = hashlib.sha256(f.read()).hexdigest()
            return hashes

        # Pre-execution snapshot
        pre_hashes = get_disk_hashes()
        status_pre_kpi, pre_kpi, _ = self._get_json("/api/projects?id=PRJ-WHC-COM-001")
        self.assertEqual(status_pre_kpi, 200)
        status_pre_dly, pre_dly, _ = self._get_json("/api/delay_events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_pre_dly, 200)

        # Execute TIA Fragnet Simulation at ACT-01
        payload = {
            "project_id": "PRJ-WHC-COM-001",
            "fragnet_name": "Neutral Force Majeure Rain Ingress on Notice to Proceed",
            "inserted_after_activity_id": "ACT-01",
            "fragnet_duration_days": 3,
            "risk_allocation": "NEUTRAL_FORCE_MAJEURE",
            "cause_category": "WEATHER_FORCE_MAJEURE"
        }
        status_tia, tia_res, _ = self._post_json("/api/tia/simulate", payload)
        self.assertEqual(status_tia, 200)

        # 1. Verify exact calendar arithmetic
        self.assertEqual(tia_res["baseline_completion_date"], "2026-11-19")
        self.assertEqual(tia_res["impacted_completion_date"], "2026-11-24")
        self.assertEqual(tia_res["critical_path_shift_workdays"], 3)
        self.assertIn("Standard 5-Day Singapore Construction Calendar", tia_res.get("working_calendar", ""))
        self.assertEqual(tia_res["entitled_eot_workdays"], 3)
        self.assertEqual(tia_res["residual_culpable_delay_workdays"], 0)
        self.assertEqual(tia_res["calculated_liquidated_damages_exposure_sgd"], 0.0)
        self.assertIn("residual_culpable_workdays (0)", tia_res.get("scenario_ld_formula", ""))
        self.assertIn("S$0.00", tia_res.get("scenario_ld_formula", ""))
        self.assertIn("VERIFIED_ZERO_MUTATION", tia_res.get("scenario_state_isolation", ""))

        # 2. State-Isolation Assertion (E-04): Verify zero disk mutation
        post_hashes = get_disk_hashes()
        for t, h in pre_hashes.items():
            self.assertEqual(
                h, post_hashes[t],
                f"E-04 Violation: Parquet file '{t}' was mutated during what-if TIA simulation!"
            )

        # 3. State-Isolation Assertion (E-04): Verify zero API state mutation
        status_post_kpi, post_kpi, _ = self._get_json("/api/projects?id=PRJ-WHC-COM-001")
        self.assertEqual(status_post_kpi, 200)
        self.assertEqual(pre_kpi, post_kpi, "E-04 Violation: Executive KPI profile mutated by TIA simulation!")

        status_post_dly, post_dly, _ = self._get_json("/api/delay_events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_post_dly, 200)
        self.assertEqual(pre_dly, post_dly, "E-04 Violation: Delay events ledger mutated by TIA simulation!")

    def test_18_forensic_reconciliation_cross_view_contract_consistency_and_negative_cases(self):
        """TEST-18 (F-REV-02/F-REV-03/F-REV-04/F-REV-07): Verify cross-view contract consistency,
        canonical event naming, deliberation terminology, and negative/fallback cases.
        """
        # 1. Verify Canonical and Alias Project Profile endpoints return identical payloads
        status_canon, proj_canon, _ = self._get_json("/api/projects?id=PRJ-WHC-COM-001")
        self.assertEqual(status_canon, 200)
        status_alias, proj_alias, _ = self._get_json("/api/project-profile?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_alias, 200)
        self.assertEqual(proj_canon["original_completion_date"], proj_alias["original_completion_date"])
        self.assertEqual(proj_canon["current_forecast_completion_date"], proj_alias["current_forecast_completion_date"])
        self.assertEqual(proj_canon["net_delay_days"], proj_alias["net_delay_days"])
        self.assertEqual(proj_canon["ld_exposure_sgd"], proj_alias["ld_exposure_sgd"])

        # 2. Verify Canonical and Alias Delay Events endpoints
        status_dly_canon, dly_canon, _ = self._get_json("/api/delay_events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_dly_canon, 200)
        status_dly_alias, dly_alias, _ = self._get_json("/api/delay-events?project_id=PRJ-WHC-COM-001")
        self.assertEqual(status_dly_alias, 200)
        self.assertEqual(dly_canon["total_events"], dly_alias["total_events"])

        # 3. Verify Canonical Event Naming and Aliases (F-REV-04)
        evt = dly_canon["delay_events"][0]
        self.assertEqual(evt["event_id"], "DLY-2026-001")
        self.assertEqual(evt["canonical_event_name"], "Groundwater Ingress & Pumping Stoppage")
        self.assertEqual(evt["event_title"], "Groundwater Ingress & Pumping Stoppage")
        self.assertEqual(evt["event_name"], "Groundwater Ingress & Pumping Stoppage")
        self.assertEqual(evt["location_detail"], "Basement 2 North Pit")

        # 4. Verify Deliberation Terminology and Counts (F-REV-03)
        status_delib, delib_data, _ = self._get_json(
            "/api/deliberation/consensus?project_id=PRJ-WHC-COM-001&event_id=DLY-2026-001"
        )
        self.assertEqual(status_delib, 200)
        self.assertEqual(delib_data["deliberation_round_count"], 1)
        self.assertEqual(delib_data["agent_turn_count"], 3)
        self.assertEqual(delib_data["hearing_phase"], "FORMAL_HEARING_ROUND_1")
        self.assertEqual(delib_data["canonical_event_name"], "Groundwater Ingress & Pumping Stoppage")

        # Also verify /api/deliberate alias
        status_delib_alias, delib_alias, _ = self._get_json(
            "/api/deliberate?project_id=PRJ-WHC-COM-001&event_id=DLY-2026-001"
        )
        self.assertEqual(status_delib_alias, 200)
        self.assertEqual(delib_alias["session_id"], delib_data["session_id"])

        # 5. Negative Cases: Missing/Unknown IDs return 404 (F-REV-07)
        try:
            self._get_json("/api/projects?id=PRJ-UNKNOWN-999")
            self.fail("Expected 404 for unknown project in /api/projects")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        try:
            self._get_json("/api/schedule?project_id=PRJ-UNKNOWN-999")
            self.fail("Expected 404 for unknown project in /api/schedule")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        try:
            self._get_json("/api/delay_events?project_id=PRJ-UNKNOWN-999")
            self.fail("Expected 404 for unknown project in /api/delay_events")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        try:
            self._get_json("/api/deliberation/consensus?project_id=PRJ-WHC-COM-001&event_id=DLY-UNKNOWN-999")
            self.fail("Expected 404 for unknown event in /api/deliberation/consensus")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_19_deliberation_pipeline_and_api_cross_path_parity(self):
        """TEST-19 (F-REV-03/F-REV-07/A4): Verify deliberation pipeline and API cross-path parity,
        traceable correlation identity, and strict determination tier derivation.
        """
        from agent_client.deliberation_pipeline import DeliberationPipeline, DeliberationInputError

        pipeline = DeliberationPipeline()
        corr_session_id = f"DELIB-CORR-PRJ-WHC-COM-001-DLY-2026-001-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        canonical_event = DELAY_EVENTS_DATA["PRJ-WHC-COM-001"][0].copy()
        canonical_event["is_contract_verified"] = True
        canonical_event["verification_record_id"] = "DOC-VERIF-TRUSTED-PSSCOC-2026"

        # 1. Live Deliberation Pipeline Execution with Lakehouse Persistence
        pipeline_res = pipeline.run_deliberation(
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data=canonical_event,
            persist_log=True,
            session_id=corr_session_id
        )

        # 2. Correlated API Call
        status, api_payload, _ = self._get_json(
            f"/api/deliberation/consensus?project_id=PRJ-WHC-COM-001&event_id=DLY-2026-001&session_id={corr_session_id}"
        )
        self.assertEqual(status, 200)

        # 3. Cross-Path Exact Parity Assertions
        self.assertEqual(pipeline_res.session_id, corr_session_id)
        self.assertEqual(api_payload["session_id"], corr_session_id)
        self.assertEqual(pipeline_res.candidate_eot_relief_days, 3.0)
        self.assertEqual(api_payload["candidate_eot_relief_days"], 3.0)
        self.assertEqual(pipeline_res.contractor_culpable_days, 0.0)
        self.assertEqual(api_payload["contractor_culpable_days"], 0.0)
        self.assertEqual(pipeline_res.liquidated_damages_exposure_sgd, 0.0)
        self.assertEqual(api_payload["liquidated_damages_exposure_sgd"], 0.0)
        self.assertEqual(pipeline_res.determination_tier, "DETERMINISTIC_ADVISORY_ASSESSMENT")
        self.assertEqual(api_payload["determination_tier"], "DETERMINISTIC_ADVISORY_ASSESSMENT")
        self.assertEqual(pipeline_res.contract_verification_status, "VERIFIED")
        self.assertEqual(api_payload["contract_verification_status"], "VERIFIED")
        self.assertEqual(pipeline_res.contract_verification_record_id, "DOC-VERIF-TRUSTED-PSSCOC-2026")
        self.assertEqual(api_payload["contract_verification_record_id"], "DOC-VERIF-TRUSTED-PSSCOC-2026")
        self.assertEqual(api_payload["canonical_event_name"], "Groundwater Ingress & Pumping Stoppage")
        self.assertEqual(len(pipeline_res.turns), len(api_payload["turns"]))

        # 4. Same-Session Lakehouse Parquet Log Read-Back Assertion
        log_path = os.path.join(MODULE_ROOT, "data", "parquet", "audit_deliberation_log.parquet")
        self.assertTrue(os.path.exists(log_path), "audit_deliberation_log.parquet must exist")
        import duckdb
        con = duckdb.connect()
        try:
            log_df = con.execute(
                f"SELECT session_id, turn_id, agent_role, recommended_eot_days FROM read_parquet('{log_path}') WHERE session_id = $1",
                [corr_session_id]
            ).fetch_df()
            self.assertEqual(len(log_df), 3, "Lakehouse audit log must contain exactly 3 turns for session")
            so_log = log_df[log_df["agent_role"] == "ARBITRATOR"].iloc[0]
            self.assertEqual(float(so_log["recommended_eot_days"]), 3.0, "Lakehouse audit log must record 3.0d EOT")
        finally:
            con.close()

        # 5. Negative Test: Strict Enforcement of Verification Guardrail (Unverified -> UNVERIFIED_ADVISORY_SIMULATION)
        unverified_event = canonical_event.copy()
        unverified_event["is_contract_verified"] = False
        unverified_event.pop("verification_record_id", None)
        unverified_res = pipeline.run_deliberation(
            project_id="PRJ-WHC-COM-001",
            event_id="DLY-2026-001",
            event_data=unverified_event,
            persist_log=False
        )
        self.assertEqual(unverified_res.determination_tier, "UNVERIFIED_ADVISORY_SIMULATION")
        self.assertEqual(unverified_res.contract_verification_status, "UNVERIFIED")
        self.assertEqual(unverified_res.contract_verification_record_id, "UNVERIFIED_NO_RECORD")

        # 5. Negative Test: Truthy Spoofing Rejection (R1 Rule)
        spoofed_event = canonical_event.copy()
        spoofed_event["is_contract_verified"] = "True"  # String instead of strict boolean
        with self.assertRaises(DeliberationInputError):
            pipeline.run_deliberation(
                project_id="PRJ-WHC-COM-001",
                event_id="DLY-2026-001",
                event_data=spoofed_event,
                persist_log=False
            )


if __name__ == "__main__":
    unittest.main()

