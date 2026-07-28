"""Metadata delta tests (Scout 6.3, Phase A) — nested content, dict/list tags."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import _delta_fixtures as fx  # noqa: E402
from review_contract_adapter import adapt_review  # noqa: E402
from delta_metadata import compute_metadata_delta  # noqa: E402


class TestMetadataDelta(unittest.TestCase):
    def test_content_field_deltas(self):
        d = compute_metadata_delta(adapt_review(fx.review_generated()))
        self.assertTrue(d["applicable"])
        self.assertEqual(d["compared_artifact_count"], 3)
        # panel_10: tags/characters/summary accepted (dict==dict), dialogue added
        # panel_3: tags edited (rare dict->list), characters+summary edited
        # panel_7: tags null==null (no-op), characters+summary accepted
        self.assertGreater(d["acceptance_rate"], 0.0)
        self.assertGreater(d["edit_rate"], 0.0)
        self.assertGreater(d["addition_rate"], 0.0)
        # hallucination proxy (edit+delete over generated) >= edit rate
        self.assertGreaterEqual(d["hallucination_proxy_rate"], d["edit_rate"])
        # the drawn NEW + spread carry approved-only metadata (artifact-level additions)
        self.assertEqual(sorted(d["approved_only_artifact_ids"]), ["11::NEW::1", "spread_12_13::p1"])
        self.assertEqual(d["generated_only_artifact_ids"], [])

    def test_schema_version_mismatch_excluded(self):
        r = fx.review_generated()
        r["approved_metadata"]["llm_enrichment_output_version"] = "v2"
        d = compute_metadata_delta(adapt_review(r))
        self.assertEqual(sorted(d["schema_version_mismatch_artifact_ids"]),
                         ["society_of_killers_1_10::p1", "society_of_killers_1_3::p1",
                          "society_of_killers_1_7::p1"])
        self.assertEqual(d["compared_artifact_count"], 0)

    def test_manual_not_applicable(self):
        d = compute_metadata_delta(adapt_review(fx.review_manual()))
        self.assertFalse(d["applicable"])


if __name__ == "__main__":
    unittest.main()
