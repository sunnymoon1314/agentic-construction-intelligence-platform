"""
ACIP S04: Unit Test Suite for Data & Application Dictionary Engine
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: tests/test_dictionary_engine.py
"""
import copy
import json
import os
import sys
import unittest

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if S04_ROOT not in sys.path:
    sys.path.insert(0, S04_ROOT)

from engine.dictionary_engine import ACIPDictionaryEngine, DictionaryValidationError


class TestACIPDictionaryEngine(unittest.TestCase):
    """Verifies schema conformance, indexing, taxonomy, and UI bundle generation."""

    def setUp(self):
        self.engine = ACIPDictionaryEngine()

    def test_01_dictionary_schema_validation(self):
        """Asserts all dictionary terms pass formal JSON schema validation."""
        self.assertTrue(self.engine.validate())
        self.assertGreaterEqual(len(self.engine._term_by_id), 30)

    def test_02_term_lookup_by_id_and_label(self):
        """Asserts lookups by canonical ID and lowercase display label succeed."""
        term = self.engine.get_term_by_id("ACIP-S04-CPM-TOTAL_FLOAT")
        self.assertIsNotNone(term)
        self.assertEqual(term["canonical_name"], "Total Float")

        # By label (case insensitive)
        term_by_lbl = self.engine.get_term_by_label("total float (tf)")
        self.assertIsNotNone(term_by_lbl)
        self.assertEqual(term_by_lbl["term_id"], "ACIP-S04-CPM-TOTAL_FLOAT")

    def test_03_taxonomy_coverage(self):
        """Asserts terms cover all 5 evidence-first taxonomy tiers."""
        expected_categories = {
            "CONSTRUCTION_DOMAIN_STANDARD",
            "DETERMINISTIC_CALCULATION",
            "OBSERVED_SITE_EVIDENCE",
            "FORECAST_PROJECTION",
            "AI_AGENTIC_INTERPRETATION"
        }
        present_categories = {term["category"] for term in self.engine.raw_data["terms"]}
        self.assertTrue(expected_categories.issubset(present_categories))

    def test_04_cross_module_filtering(self):
        """Asserts terms can be filtered by module scope (S04, S02, S06, CORE)."""
        s04_terms = self.engine.get_terms_by_module("S04")
        core_terms = self.engine.get_terms_by_module("CORE")
        s06_terms = self.engine.get_terms_by_module("S06")

        self.assertGreater(len(s04_terms), 0)
        self.assertGreater(len(core_terms), 0)
        self.assertGreater(len(s06_terms), 0)

    def test_05_ui_tooltip_bundle_export(self):
        """Asserts exported UI tooltip bundle matches lightweight contract."""
        out_path = os.path.join(S04_ROOT, "data", "dictionary", "acip_ui_tooltip_bundle.json")
        bundle = self.engine.export_ui_tooltip_bundle(out_path)

        self.assertIn("by_id", bundle)
        self.assertIn("by_label", bundle)
        self.assertIn("ACIP-S04-CPM-CRITICAL_PATH", bundle["by_id"])

        entry = bundle["by_id"]["ACIP-S04-CPM-CRITICAL_PATH"]
        self.assertIn("short_tooltip", entry)
        self.assertIn("plain_english_definition", entry)
        self.assertIn("why_it_matters", entry)
        self.assertIn("category", entry)

    def test_06_validation_failure_on_missing_required_property(self):
        """Asserts that invalid dictionary structure raises DictionaryValidationError fail-closed."""
        bad_engine = ACIPDictionaryEngine()
        bad_engine.raw_data = copy.deepcopy(self.engine.raw_data)
        # Remove required property from first term
        del bad_engine.raw_data["terms"][0]["plain_english_definition"]

        with self.assertRaises(DictionaryValidationError):
            bad_engine.validate()


if __name__ == "__main__":
    unittest.main()
