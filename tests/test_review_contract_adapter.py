"""Anti-corruption adapter tests (Scout 6.3, Phase A) — grounded on real emitted shapes."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import _delta_fixtures as fx  # noqa: E402
from review_contract_adapter import (  # noqa: E402
    adapt_review, ReviewContractError,
    APPLICABILITY_GENERATED, APPLICABILITY_MANUAL,
    STATE_CREATOR_APPROVED, STATE_EDENSEEK_APPROVED,
)


class TestAdapter(unittest.TestCase):
    def test_generated_geometry_uses_bounds_not_bbox(self):
        c = adapt_review(fx.review_generated(), fx.platform_approval())
        self.assertEqual(c["applicability"], APPLICABILITY_GENERATED)
        # normalized from `bounds` (0..1), NOT the pixel `bbox` [0,0,2063,2864]
        self.assertEqual(c["generated"]["geometry"]["society_of_killers_1_10::p1"]["bbox"],
                         (0.0, 0.0, 1.0, 0.9092))
        self.assertEqual(c["approved"]["geometry"]["society_of_killers_1_10::p1"]["bbox"],
                         (0.0, 0.0, 1.0, 0.9999))
        self.assertEqual(c["publisher_certified"]["canonical_dataset_state"], STATE_EDENSEEK_APPROVED)

    def test_spread_uses_stage_geometry_and_flag(self):
        c = adapt_review(fx.review_generated())
        spread = c["approved"]["geometry"]["spread_12_13::p1"]
        self.assertTrue(spread["flags"]["is_spread"])
        self.assertEqual(spread["bbox"], (0.006, 0.057, 0.247, 0.385))  # from stage_geometry
        self.assertEqual(spread["coordinate_space"], "spread")
        self.assertEqual(spread["page_range"], [12, 13])

    def test_structural_keys_skipped_not_treated_as_panels(self):
        """approved_geometry carries structural siblings (panel_order, spread_artifacts) among
        the artifact entries; the adapter must skip them, never compare them as panels."""
        c = adapt_review(fx.review_generated())
        geom = c["approved"]["geometry"]
        self.assertNotIn("panel_order", geom)
        self.assertNotIn("spread_artifacts", geom)
        # the real artifacts survive
        self.assertIn("society_of_killers_1_10::p1", geom)
        self.assertIn("spread_12_13::p1", geom)

    def test_new_on_spread_entry_handled_as_spread(self):
        """A ``<page>::NEW::N`` drawn-on-spread entry (degenerate page coords + stage_geometry)
        is handled identically to a ``spread_*`` entry."""
        r = fx.review_generated()
        r["approved_geometry"]["12::NEW::1"] = {
            "isSpreadPanel": True, "isNew": True, "deleted": False, "page_range": [12, 13],
            "x": 0, "y": 0, "width": 0.01, "height": 0.01,
            "stage_geometry": {"x": 0.239, "y": 0.084, "width": 0.274, "height": 0.366}}
        entry = adapt_review(r)["approved"]["geometry"]["12::NEW::1"]
        self.assertTrue(entry["flags"]["is_spread"])
        self.assertEqual(entry["bbox"], (0.239, 0.084, 0.274, 0.366))  # stage_geometry, not page 0.01

    def test_unknown_non_artifact_member_fails_fast(self):
        """An unrecognized non-artifact member (not a known structural key, not a panel) must
        fail loud rather than be silently reinterpreted."""
        r = fx.review_generated()
        r["approved_geometry"]["some_future_summary"] = {"totally": "unknown"}
        with self.assertRaises(ReviewContractError):
            adapt_review(r)

    def test_metadata_extracts_four_nested_content_fields(self):
        c = adapt_review(fx.review_generated())
        fields = c["approved"]["metadata"]["society_of_killers_1_10::p1"]["fields"]
        self.assertEqual(sorted(fields),
                         ["classification.tags", "entities.characters",
                          "narrative.dialogue", "narrative.summary"])
        # provenance excluded
        self.assertNotIn("geometry_source", fields)
        self.assertNotIn("context_source", fields)

    def test_tags_taken_as_is_across_all_shapes(self):
        """The adapter passes tags through untouched — dict (the norm), the rare list, and null —
        so the delta, not the boundary, decides accept/edit."""
        c = adapt_review(fx.review_generated())

        def tags(side, aid):
            return c[side]["metadata"][aid]["fields"]["classification.tags"]

        # norm: dict on both sides (an accept downstream)
        self.assertIsInstance(tags("generated", "society_of_killers_1_10::p1"), dict)
        self.assertIsInstance(tags("approved", "society_of_killers_1_10::p1"), dict)
        # rare outlier: dict generated, list approved (an edit downstream)
        self.assertIsInstance(tags("generated", "society_of_killers_1_3::p1"), dict)
        self.assertIsInstance(tags("approved", "society_of_killers_1_3::p1"), list)
        # null path: null on both sides (a no-op downstream)
        self.assertIsNone(tags("generated", "society_of_killers_1_7::p1"))
        self.assertIsNone(tags("approved", "society_of_killers_1_7::p1"))

    def test_manual_sentinel_not_applicable(self):
        c = adapt_review(fx.review_manual())
        self.assertEqual(c["applicability"], APPLICABILITY_MANUAL)
        self.assertIsNone(c["generated"])

    def test_absence_of_D_is_creator_approved(self):
        c = adapt_review(fx.review_generated(), None)
        self.assertEqual(c["publisher_certified"]["canonical_dataset_state"], STATE_CREATOR_APPROVED)

    def test_fail_fast_generated_missing_bounds(self):
        r = fx.review_generated()
        del r["generated_geometry"]["panels"][0]["bounds"]
        with self.assertRaises(ReviewContractError):
            adapt_review(r)

    def test_fail_fast_spread_missing_stage_geometry(self):
        r = fx.review_generated()
        del r["approved_geometry"]["spread_12_13::p1"]["stage_geometry"]
        with self.assertRaises(ReviewContractError):
            adapt_review(r)

    def test_fail_fast_unknown_review_version(self):
        r = fx.review_generated(); r["review_report_version"] = "v2"
        with self.assertRaises(ReviewContractError):
            adapt_review(r)

    def test_fail_fast_unknown_platform_version(self):
        d = fx.platform_approval(); d["platform_approval_version"] = "v2"
        with self.assertRaises(ReviewContractError):
            adapt_review(fx.review_generated(), d)

    def test_fail_fast_unknown_link_shape(self):
        r = fx.review_generated(); r["provenance"]["generated_vs_approved"] = {"state": "weird"}
        with self.assertRaises(ReviewContractError):
            adapt_review(r)


if __name__ == "__main__":
    unittest.main()
