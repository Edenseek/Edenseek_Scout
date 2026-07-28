"""Focused tests for the deterministic metadata revision-distance classifier (Increment 1).

Covers category boundaries (minor edit vs complete replacement stay distinct), numerator/denominator
preservation, weighted intervention score, references-and-hashes-only (no raw content stored),
determinism, unsupported-schema handling, and integration into the report/index/comparability
contracts.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _delta_fixtures as fx  # noqa: E402
import delta_metadata_revision as dmr  # noqa: E402
from review_contract_adapter import adapt_review  # noqa: E402
from delta_auditor import run_delta_audit  # noqa: E402
import scout_delta_audit as sda  # noqa: E402
import scout_report_index as sri  # noqa: E402

_ALLOWED_RECORD_KEYS = {"artifact_id", "field", "category", "distance", "generated_sha256",
                        "approved_sha256", "generated_empty", "approved_empty", "measures"}
_ALLOWED_MEASURE_KEYS = {"char_levenshtein", "char_levenshtein_norm", "token_jaccard_distance",
                         "set_jaccard_distance", "len_ratio", "structural_equal",
                         "generated_type", "approved_type"}


class TestClassifier(unittest.TestCase):
    def test_category_boundaries(self):
        base = "x" * 100                                   # deterministic normalized distances
        self.assertEqual(dmr._classify(base, base)[0], "accepted_unchanged")                # d 0
        self.assertEqual(dmr._classify(base, base + "y")[0], "minor_wording_edit")          # ~0.01
        self.assertEqual(dmr._classify(base, "x" * 80 + "y" * 20)[0], "moderate_rewrite")   # 0.20
        self.assertEqual(dmr._classify(base, "x" * 50 + "y" * 50)[0], "major_rewrite")      # 0.50
        self.assertEqual(dmr._classify(base, "y" * 100)[0], "complete_replacement")         # 1.00
        self.assertEqual(dmr._classify(None, "new value")[0], "added")
        self.assertEqual(dmr._classify("old value", None)[0], "removed")
        self.assertEqual(dmr._classify(None, None)[0], "abstention")

    def test_minor_edit_distinct_from_replacement(self):
        minor_cat, minor_d, _ = dmr._classify("The cat sat on the mat quietly.",
                                              "The cat sat on the mat quietly!")
        repl_cat, repl_d, _ = dmr._classify("The cat sat on the mat.", "Total war erupts downtown.")
        self.assertEqual(minor_cat, "minor_wording_edit")
        self.assertEqual(repl_cat, "complete_replacement")
        self.assertLess(minor_d, repl_d)
        self.assertLess(dmr.WEIGHTS[minor_cat], dmr.WEIGHTS[repl_cat])

    def test_dict_vs_list_tags_is_high_distance(self):
        cat, d, m = dmr._classify({"action": "smoking", "mood": "edgy", "setting": "design"},
                                  ["character design"])
        self.assertIn(cat, ("major_rewrite", "complete_replacement"))
        self.assertIsNotNone(m["set_jaccard_distance"])   # structural measure preserved for lists/dicts

    def test_benchmark_over_fixture(self):
        b = dmr.compute_metadata_benchmark(adapt_review(fx.review_generated()))
        self.assertTrue(b["applicable"])
        self.assertEqual(b["version"], "v1")
        g = b["global"]
        # numerators/denominators preserved, not just rates
        self.assertIn("numerator", g["accepted_unchanged_rate"])
        self.assertIn("denominator", g["unchanged_metadata_rate"])
        self.assertIn("numerator", g["weighted_editorial_intervention_score"])
        # every field/artifact classified; counts sum to fields evaluated
        total = sum(g["counts"].values())
        self.assertEqual(total, b["comparable_artifacts"] * len(dmr.FIELDS)
                         + sum(g["counts"][c] for c in ("unsupported_schema",)) * 0)  # comparable here
        self.assertEqual(len(b["per_field"]), 4)
        self.assertTrue(0.0 <= g["average_revision_distance"] <= 1.0)
        self.assertTrue(0.0 <= g["weighted_editorial_intervention_score"]["score"] <= 1.0)

    def test_records_are_references_and_hashes_only(self):
        b = dmr.compute_metadata_benchmark(adapt_review(fx.review_generated()))
        self.assertTrue(b["records"])
        for r in b["records"]:
            self.assertTrue(set(r).issubset(_ALLOWED_RECORD_KEYS), set(r) - _ALLOWED_RECORD_KEYS)
            self.assertEqual(len(r["generated_sha256"]), 64)
            self.assertEqual(len(r["approved_sha256"]), 64)
            if r["measures"] is not None:
                self.assertTrue(set(r["measures"]).issubset(_ALLOWED_MEASURE_KEYS))
        # no raw metadata text leaked anywhere in the benchmark
        blob = json.dumps(b, ensure_ascii=False)
        self.assertNotIn("Astrid St. James", blob)
        self.assertNotIn("Get back!", blob)

    def test_deterministic(self):
        c = adapt_review(fx.review_generated())
        a = json.dumps(dmr.compute_metadata_benchmark(c), sort_keys=True)
        b = json.dumps(dmr.compute_metadata_benchmark(c), sort_keys=True)
        self.assertEqual(a, b)

    def test_unsupported_schema_abstains(self):
        r = fx.review_generated()
        r["approved_metadata"]["llm_enrichment_output_version"] = "v2"   # skew -> all unsupported
        b = dmr.compute_metadata_benchmark(adapt_review(r))
        self.assertEqual(b["comparable_artifacts"], 0)
        # fixture has 3 common artifacts -> all 3*4 fields land in unsupported_schema
        self.assertEqual(b["global"]["counts"]["unsupported_schema"], 3 * len(dmr.FIELDS))
        self.assertEqual(b["global"]["comparable_fields"], 0)

    def test_manual_not_applicable(self):
        b = dmr.compute_metadata_benchmark(adapt_review(fx.review_manual()))
        self.assertFalse(b["applicable"])


class TestIntegration(unittest.TestCase):
    def test_report_includes_metadata_benchmark_and_axis(self):
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        self.assertTrue(rep["metadata_benchmark"]["applicable"])
        self.assertEqual(rep["provenance"]["metadata_revision_distance_version"], "v1")

    def test_report_body_headline_and_comparability(self):
        # a minimal view around the fixture delta, exercising build_report_body's headline path
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        view = {
            "audit_timestamp": "2026-07-28T00:00:00Z", "publisher_commit": "p", "scout_commit": "s",
            "evidence": {"issue_identity": fx.IDENTITY, "summary": {}, "objects": [],
                         "manifest_version": "v1", "publisher_provenance": {}},
            "findings": [{"code": "x", "severity": "PASS", "title": "t", "detail": "d"}],
            "delta_summary": {"geometry": {"status": "computed", "precision": 1.0, "recall": 0.5,
                                           "split_rate": 0, "merge_rate": 0, "missing": 0,
                                           "spread_missing": 1, "false": 0},
                              "metadata": {"status": "computed", "compared": 2}},
            "delta_report": rep, "delta_report_sha256": "x",
        }
        body = sda.build_report_body(view)
        self.assertTrue(body["metadata_metrics"]["applicable"])
        self.assertIn("weighted_editorial_intervention_score", body["metadata_metrics"])
        # metadata revision-distance version is a metadata comparability axis
        axes = sri.metadata_axes(body)
        self.assertEqual(axes["metadata_revision_distance_version"], "v1")
        entry = sri.build_index_entry({**body, "run_id": "r", "run_seq": 1, "report_id": "x"})
        self.assertTrue(entry["metadata_metrics"]["applicable"])


if __name__ == "__main__":
    unittest.main()
