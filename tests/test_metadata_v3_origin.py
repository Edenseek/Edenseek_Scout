"""Metadata Accuracy v3 — REVISION-AWARE acceptance denominator (origin-composite).

On a revision, metadata is INHERITED but keeps its original `metadata_generation_provenance`, so a rev-1
`fresh` output still reads `fresh` in rev 2 though no LLM ran. v3 counts only content an LLM produced THIS
revision, discriminated by the PRESENCE of the Publisher `origin` field (written only on the inheritance path):
  origin ABSENT  -> generation path -> v2 fresh-only filter (byte-identical on first publications);
  origin PRESENT -> revision-inherited -> count only generated/regenerated; exclude carried_forward /
                    confirmed / null (empty add-split-merge class).
"""
import copy
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _delta_fixtures as fx  # noqa: E402
import delta_metadata_revision as dmr  # noqa: E402
from review_contract_adapter import adapt_review  # noqa: E402

A1, A2, A3 = "society_of_killers_1_10::p1", "society_of_killers_1_3::p1", "society_of_killers_1_7::p1"


def _with_origin(origins):
    """fx.review_generated() with `origin` set on the named GENERATED outputs. A key present with value None
    is the empty class; an artifact absent from `origins` leaves `origin` absent (generation path)."""
    r = copy.deepcopy(fx.review_generated())
    for o in r["generated_metadata"]["llm_enrichment_outputs"]:
        if o["artifact_id"] in origins:
            o["origin"] = origins[o["artifact_id"]]
    return r


def _all_accepted_review():
    """Generated == approved (byte-identical) -> 0 edits -> rate 1.0 over the common artifacts."""
    r = copy.deepcopy(fx.review_generated())
    appr = []
    for o in r["generated_metadata"]["llm_enrichment_outputs"]:
        a = copy.deepcopy(o)
        a["metadata_review_state"] = "approved"
        a["metadata_locked"] = True
        appr.append(a)
    r["approved_metadata"]["llm_enrichment_outputs"] = appr
    return r


def _ma(review):
    return dmr.compute_metadata_benchmark(adapt_review(review))["metadata_accuracy"]


class TestV3RevisionAware(unittest.TestCase):
    def test_version_and_basis(self):
        ma = _ma(fx.review_generated())
        self.assertEqual(ma["version"], "v3")
        self.assertEqual(ma["denominator_basis"], "llm_generated_this_revision_only")

    def test_first_publication_origin_absent_counts(self):
        # origin absent on every output -> generation path -> fresh fields counted (v2-identical)
        ma = _ma(fx.review_generated())
        self.assertGreater(ma["acceptance"]["denominator"], 0)
        self.assertEqual(ma["excluded_preserved_field_count"], 0)

    def test_confirmed_is_the_trap_excluded(self):
        # THE trap: metadata_generation_provenance == "fresh" beside origin == "confirmed" -> EXCLUDED
        # (no LLM ran this revision). All three -> denominator 0, meets_target withheld.
        ma = _ma(_with_origin({A1: "confirmed", A2: "confirmed", A3: "confirmed"}))
        self.assertEqual(ma["acceptance"]["denominator"], 0)
        self.assertEqual(ma["acceptance"]["numerator"], 0)
        self.assertIsNone(ma["meets_target"])            # 0 denominator -> withheld, not a false pass
        self.assertEqual(set(ma["excluded_preserved_artifacts"]), {A1, A2, A3})
        self.assertGreater(ma["excluded_preserved_field_count"], 0)

    def test_carried_forward_excluded(self):
        ma = _ma(_with_origin({A1: "carried_forward"}))
        self.assertIn(A1, ma["excluded_preserved_artifacts"])

    def test_empty_class_origin_null_excluded(self):
        # origin present + null (added/split/merged empty class) -> excluded
        ma = _ma(_with_origin({A1: None}))
        self.assertIn(A1, ma["excluded_preserved_artifacts"])

    def test_generated_origin_included(self):
        # hypothetical in-revision regeneration emitting origin="generated" -> counted
        ma = _ma(_with_origin({A1: "generated", A2: "generated", A3: "generated"}))
        self.assertGreater(ma["acceptance"]["denominator"], 0)
        self.assertEqual(ma["excluded_preserved_field_count"], 0)

    def test_mixed_only_generation_path_counts(self):
        # A1/A3 confirmed (excluded), A2 origin-absent-fresh (counted)
        ma = _ma(_with_origin({A1: "confirmed", A3: "confirmed"}))
        self.assertEqual(set(ma["excluded_preserved_artifacts"]), {A1, A3})
        self.assertGreater(ma["acceptance"]["denominator"], 0)   # A2 fresh fields still counted

    def test_zero_denominator_all_inherited_is_correct_not_failure(self):
        # rev-2 all-inherited, editor regenerated nothing -> 0 comparable fields -> correct answer
        ma = _ma(_with_origin({A1: "confirmed", A2: "carried_forward", A3: "confirmed"}))
        self.assertEqual(ma["acceptance"]["denominator"], 0)
        self.assertEqual(ma["acceptance"]["rate"], 0.0)
        self.assertIsNone(ma["meets_target"])
        self.assertFalse(ma["low_confidence_no_inspection"])     # no marker on an empty denominator

    def test_low_confidence_no_inspection_marker(self):
        ma = _ma(_all_accepted_review())                          # rate 1.0, 0 edits
        self.assertEqual(ma["acceptance"]["rate"], 1.0)
        self.assertEqual(ma["total_edited_fields"], 0)
        self.assertTrue(ma["low_confidence_no_inspection"])

    def test_low_confidence_marker_false_when_edits_present(self):
        ma = _ma(fx.review_generated())                           # the fixture has real edits
        self.assertLess(ma["acceptance"]["rate"], 1.0)
        self.assertFalse(ma["low_confidence_no_inspection"])


if __name__ == "__main__":
    unittest.main()
