"""
ACIP S04: Central Data & Application Dictionary Engine
Module: ACIP S04 - Agentic Progress & Delay Intelligence
File: engine/dictionary_engine.py

Provides validation, querying, and UI tooltip export for the ACIP-wide
Data & Application Dictionary:
1. Validates dictionary entries against JSON schema (draft 2020-12).
2. Provides term lookup by term_id, display_label, or module_scope.
3. Exports lightweight tooltip lookup bundles for UI components.
"""
import json
import os
from typing import Dict, List, Optional
import jsonschema

S04_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(S04_ROOT, "data", "dictionary", "acip_dictionary_schema.json")
DICTIONARY_PATH = os.path.join(S04_ROOT, "data", "dictionary", "acip_dictionary.json")


class DictionaryValidationError(Exception):
    """Raised when dictionary JSON violates schema or term invariants."""
    pass


class ACIPDictionaryEngine:
    """Manages validation, lookup, and UI tooltip generation for ACIP terms."""

    def __init__(self, dictionary_path: str = DICTIONARY_PATH, schema_path: str = SCHEMA_PATH):
        self.dictionary_path = dictionary_path
        self.schema_path = schema_path
        self.raw_data = self._load_json(self.dictionary_path)
        self.schema = self._load_json(self.schema_path)
        self._term_by_id: Dict[str, dict] = {}
        self._term_by_label: Dict[str, dict] = {}
        self._index_terms()

    def _load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _index_terms(self) -> None:
        terms = self.raw_data.get("terms", [])
        for term in terms:
            tid = term.get("term_id")
            label = term.get("display_label")
            if tid:
                self._term_by_id[tid] = term
            if label:
                self._term_by_label[label.lower()] = term

    def validate(self) -> bool:
        """Validates all terms against the JSON schema."""
        terms = self.raw_data.get("terms", [])
        if not terms:
            raise DictionaryValidationError("Dictionary contains no terms.")

        for i, term in enumerate(terms):
            try:
                jsonschema.validate(instance=term, schema=self.schema)
            except jsonschema.ValidationError as err:
                raise DictionaryValidationError(
                    f"Term at index {i} ('{term.get('term_id', 'UNKNOWN')}') failed schema validation: {err.message}"
                )

        # Check unique term_ids
        seen_ids = set()
        for term in terms:
            tid = term["term_id"]
            if tid in seen_ids:
                raise DictionaryValidationError(f"Duplicate term_id detected: {tid}")
            seen_ids.add(tid)

        return True

    def get_term_by_id(self, term_id: str) -> Optional[dict]:
        return self._term_by_id.get(term_id)

    def get_term_by_label(self, label: str) -> Optional[dict]:
        return self._term_by_label.get(label.strip().lower())

    def get_terms_by_module(self, module_code: str) -> List[dict]:
        return [
            term for term in self.raw_data.get("terms", [])
            if module_code in term.get("module_scope", [])
        ]

    def export_ui_tooltip_bundle(self, output_path: Optional[str] = None) -> dict:
        """
        Exports a lightweight JSON mapping for web dashboard tooltips:
        {
          "by_id": { term_id: { label, tooltip, definition, category, why_it_matters } },
          "by_label": { display_label_lowercase: term_id }
        }
        """
        bundle = {
            "dictionary_version": self.raw_data.get("dictionary_version", "1.0.0"),
            "by_id": {},
            "by_label": {}
        }

        for term in self.raw_data.get("terms", []):
            tid = term["term_id"]
            label = term["display_label"]
            bundle["by_id"][tid] = {
                "display_label": label,
                "short_tooltip": term.get("short_tooltip", ""),
                "plain_english_definition": term.get("plain_english_definition", ""),
                "category": term.get("category", ""),
                "why_it_matters": term.get("why_it_matters", ""),
                "calculation_rule": term.get("calculation_rule"),
                "limitations": term.get("limitations_and_boundaries", ""),
                "action": term.get("recommended_user_action", "")
            }
            bundle["by_label"][label.lower()] = tid

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(bundle, f, indent=2)

        return bundle


if __name__ == "__main__":
    engine = ACIPDictionaryEngine()
    engine.validate()
    out_bundle = os.path.join(S04_ROOT, "data", "dictionary", "acip_ui_tooltip_bundle.json")
    engine.export_ui_tooltip_bundle(out_bundle)
    print(f"Dictionary validated successfully: {len(engine._term_by_id)} terms.")
    print(f"UI tooltip bundle exported to: {out_bundle}")
