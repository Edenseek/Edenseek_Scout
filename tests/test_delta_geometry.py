"""Geometry delta tests (Scout 6.3, Phase A) — real shapes; spreads + bounds."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import _delta_fixtures as fx  # noqa: E402
from review_contract_adapter import adapt_review  # noqa: E402
from delta_geometry import compute_geometry_delta  # noqa: E402


def _mk_review(gen_bounds_by_key, approved_geom, page_number=1):
    """Minimal generated-publication review with given generated bounds + approved geometry, all
    on one page. Synthetic approved keys carry no page in their id, so stamp ``page_number`` on
    each so the page-scoped matcher (v2) keeps them on the same page as the generated panels."""
    approved = {k: ({**v, "page_number": v.get("page_number", page_number)}
                    if isinstance(v, dict) and not v.get("isSpreadPanel") else v)
                for k, v in approved_geom.items()}
    return {
        "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
        "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 1,
                               "total_story_pages": 1, "total_panels": len(gen_bounds_by_key),
                               "panels": [{"panel_key": k, "page_number": page_number, "order": 1,
                                           "bbox": [0, 0, 1, 1], "bounds": b, "coordinate_space": "page"}
                                          for k, b in gen_bounds_by_key.items()]},
        "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
        "approved_geometry": approved,
        "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
        "provenance": {"published_revision_id": "rev_taaaa",
                       "generated_vs_approved": {"state": "generated_publication",
                                                 "generated_snapshot_revision_id": "rev_g"}},
    }


class TestGeometryDelta(unittest.TestCase):
    def test_real_fixture_page_and_spread_strata(self):
        d = compute_geometry_delta(adapt_review(fx.review_generated()))
        self.assertTrue(d["applicable"])
        # TOTAL (page + spread): 3 generated, 5 approved (4 page + 1 spread), 3 matched
        self.assertEqual(d["precision"], 1.0)
        self.assertEqual(d["recall"], 0.6)
        # page stratum: 3 of 4 page panels matched
        self.assertEqual(d["strata"]["page"]["recall"], 0.75)
        self.assertIn("11::NEW::1", d["missing_page_artifact_ids"])
        # spread stratum: the approved spread has no generated counterpart -> a real spread miss
        self.assertEqual(d["strata"]["spread"]["recall"], 0.0)
        self.assertEqual(d["spread_missing_artifact_ids"], ["spread_12_13::p1"])
        self.assertEqual(d["false_count"], 0)

    def test_spread_matches_in_spread_frame(self):
        """A generated spread and an approved spread on the same page_range that overlap are matched
        in the spread frame — not compared against page panels."""
        r = {
            "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
            "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 2,
                "total_story_pages": 2, "total_panels": 1, "panels": [
                    {"panel_key": "spread_4_5::p1", "page_number": 4, "page_range": [4, 5], "order": 1,
                     "bbox": [0, 0, 1, 1], "bounds": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5},
                     "coordinate_space": "spread"}]},
            "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "approved_geometry": {
                "spread_4_5::p1": {"isSpreadPanel": True, "page_range": [4, 5],
                                   "stage_geometry": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}}},
            "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "provenance": {"published_revision_id": "rev_taaaa",
                           "generated_vs_approved": {"state": "generated_publication",
                                                     "generated_snapshot_revision_id": "rev_g"}},
        }
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["strata"]["spread"]["precision"], 1.0)   # the generated spread matched
        self.assertEqual(d["strata"]["spread"]["recall"], 1.0)      # the approved spread matched
        self.assertEqual(d["spread_missing_artifact_ids"], [])
        self.assertEqual(d["strata"]["page"]["generated_panel_count"], 0)  # not in the page pool
        self.assertEqual(d["precision"], 1.0)                       # whole-issue total

    def test_split(self):
        r = _mk_review({"g1": {"x": 0, "y": 0, "width": 1, "height": 1},
                        "g2": {"x": 0, "y": 0, "width": 0.9, "height": 1}},
                       {"a1": {"x": 0, "y": 0, "width": 1, "height": 1}})
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["split_artifact_ids"], ["a1"])
        self.assertEqual(d["merge_artifact_ids"], [])

    def test_merge(self):
        r = _mk_review({"g1": {"x": 0, "y": 0, "width": 1, "height": 1}},
                       {"a1": {"x": 0, "y": 0, "width": 0.5, "height": 1},
                        "a2": {"x": 0.5, "y": 0, "width": 0.5, "height": 1}})
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["merge_artifact_ids"], ["g1"])

    def test_false_panel(self):
        r = _mk_review({"g1": {"x": 0, "y": 0, "width": 0.1, "height": 0.1}},
                       {"a1": {"x": 0.9, "y": 0.9, "width": 0.1, "height": 0.1}})
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["false_artifact_ids"], ["g1"])
        self.assertIn("a1", d["missing_page_artifact_ids"])

    def test_deleted_approved_excluded(self):
        r = fx.review_generated()
        r["approved_geometry"]["society_of_killers_1_3::p1"]["deleted"] = True
        d = compute_geometry_delta(adapt_review(r))
        # total benchmark set = 4 page + 1 spread = 5 -> 4 after deleting one page panel
        self.assertEqual(d["approved_panel_count"], 4)

    def test_reading_order_and_per_page_diagnostics(self):
        """Two matched panels the human RE-SEQUENCED (approved panel_order reversed) -> order
        agreement 0; the per-page diagnostics report density + the reading-order fidelity."""
        top = {"x": 0, "y": 0, "width": 1.0, "height": 0.5}
        bot = {"x": 0, "y": 0.5, "width": 1.0, "height": 0.5}
        r = {
            "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
            "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 1,
                "total_story_pages": 1, "total_panels": 2, "panels": [
                    {"panel_key": "society_of_killers_1_1::p1", "page_number": 1, "order": 1,
                     "bbox": [0, 0, 1, 1], "bounds": top, "coordinate_space": "page"},
                    {"panel_key": "society_of_killers_1_1::p2", "page_number": 1, "order": 2,
                     "bbox": [0, 0, 1, 1], "bounds": bot, "coordinate_space": "page"}]},
            "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "approved_geometry": {
                "society_of_killers_1_1::p1": {**top, "approved": True},
                "society_of_killers_1_1::p2": {**bot, "approved": True},
                # human-approved reading order is REVERSED vs automation
                "panel_order": {"1": ["society_of_killers_1_1::p2", "society_of_killers_1_1::p1"]}},
            "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "provenance": {"published_revision_id": "rev_taaaa",
                           "generated_vs_approved": {"state": "generated_publication",
                                                     "generated_snapshot_revision_id": "rev_g"}},
        }
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["precision"], 1.0)                       # both panels detected
        self.assertEqual(d["diagnostics"]["order"]["agreement"], 0.0)   # but the order is reversed
        self.assertEqual(d["diagnostics"]["order"]["discordant"], 1)
        pg = d["diagnostics"]["per_page"][0]
        self.assertEqual(pg["page_number"], 1)
        self.assertEqual(pg["density"], 2)
        self.assertEqual(pg["order_agreement"], 0.0)

    def test_manual_not_applicable(self):
        d = compute_geometry_delta(adapt_review(fx.review_manual()))
        self.assertFalse(d["applicable"])
        self.assertEqual(d["reason"], "manual_publication")

    def test_segmentation_accuracy_and_resize_diagnostics(self):
        """Quality-weighted E/(A+FP): a single page panel automation drew 50% too short (IoU 0.5)
        earns partial credit 0.5 of 1 approved panel -> accuracy 0.5; resize diagnostics expose it."""
        r = _mk_review(
            {"society_of_killers_1_1::p1": {"x": 0, "y": 0, "width": 1.0, "height": 0.5}},
            {"society_of_killers_1_1::p1": {"x": 0, "y": 0, "width": 1.0, "height": 1.0}})
        d = compute_geometry_delta(adapt_review(r))
        sa = d["segmentation_accuracy"]
        self.assertEqual(sa["numerator"], 0.5)          # earned credit = IoU 0.5 (partial)
        self.assertEqual(sa["denominator"], 1)          # 1 approved + 0 false
        self.assertEqual(sa["score"], 0.5)
        self.assertFalse(sa["meets_target"])            # 0.5 < 0.95
        pair = d["strata"]["page"]["matched_pairs"][0]
        self.assertEqual(pair["iou"], 0.5)
        self.assertEqual(pair["area_ratio"], 0.5)       # generated area 0.5 / approved 1.0
        self.assertEqual(pair["dh_pct"], -0.5)          # height 50% under approved
        self.assertEqual(pair["dw_pct"], 0.0)           # width exact

    def test_over_segmentation_penalizes_accuracy(self):
        """Automation drew TWO identical boxes for ONE approved panel (over-segmentation). The extra
        box earns no credit and enters the denominator, so accuracy is 0.5, not a false 1.0."""
        r = _mk_review(
            {"1::p1": {"x": 0, "y": 0, "width": 0.5, "height": 0.5},
             "1::p2": {"x": 0, "y": 0, "width": 0.5, "height": 0.5}},   # duplicate of p1
            {"1::p1": {"x": 0, "y": 0, "width": 0.5, "height": 0.5}})
        d = compute_geometry_delta(adapt_review(r))
        self.assertIn("1::p1", d["split_artifact_ids"])   # 1 approved <- 2 automated
        sa = d["segmentation_accuracy"]
        self.assertEqual(sa["numerator"], 1.0)            # best match is exact
        self.assertEqual(sa["denominator"], 2)            # 1 approved + 1 over-seg excess
        self.assertEqual(sa["false_or_excess"], 1)
        self.assertEqual(sa["score"], 0.5)

    def test_non_numeric_page_does_not_abort(self):
        """A 'cover' page id carries no numeric page — derivation falls back to the label as a scope
        and the delta still computes (one un-numbered page must not abort the whole issue)."""
        r = {
            "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
            "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 1,
                "total_story_pages": 1, "total_panels": 1, "panels": [
                    {"panel_key": "cover::p1", "order": 1, "bbox": [0, 0, 1, 1],
                     "bounds": {"x": 0, "y": 0, "width": 1.0, "height": 1.0}, "coordinate_space": "page"}]},
            "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "approved_geometry": {"cover::p1": {"x": 0, "y": 0, "width": 1.0, "height": 1.0}},
            "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "provenance": {"published_revision_id": "rev_taaaa",
                           "generated_vs_approved": {"state": "generated_publication",
                                                     "generated_snapshot_revision_id": "rev_g"}},
        }
        d = compute_geometry_delta(adapt_review(r))
        self.assertTrue(d["applicable"])          # did NOT abort on the non-numeric 'cover' page
        self.assertEqual(d["precision"], 1.0)     # matched within the 'cover' scope
        self.assertEqual(d["recall"], 1.0)

    def test_false_panel_penalizes_accuracy(self):
        """A false automated panel enters the denominator (A + FP): one perfect match + one false
        panel -> accuracy 1.0/(1+1) = 0.5."""
        r = _mk_review(
            {"1::p1": {"x": 0, "y": 0, "width": 0.4, "height": 0.4},
             "1::pX": {"x": 0.9, "y": 0.9, "width": 0.05, "height": 0.05}},   # no approved overlap
            {"1::p1": {"x": 0, "y": 0, "width": 0.4, "height": 0.4}})
        d = compute_geometry_delta(adapt_review(r))
        sa = d["segmentation_accuracy"]
        self.assertEqual(sa["numerator"], 1.0)          # the one match is exact
        self.assertEqual(sa["denominator"], 2)          # 1 approved + 1 false
        self.assertEqual(sa["score"], 0.5)

    def test_no_cross_page_match(self):
        """Regression for the cross-page matching defect (GEOMETRY_MATCH_VERSION v2): panels with
        identical per-page normalized coordinates on DIFFERENT pages must not match each other.
        Under v1 (no page scope) this produced phantom merges/splits and inflated precision."""
        box = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.5}
        r = {
            "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
            "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 2,
                "total_story_pages": 2, "total_panels": 2, "panels": [
                    {"panel_key": "society_of_killers_1_3::p1", "page_number": 3, "order": 1,
                     "bbox": [0, 0, 1, 1], "bounds": box, "coordinate_space": "page"},
                    {"panel_key": "society_of_killers_1_6::p1", "page_number": 6, "order": 1,
                     "bbox": [0, 0, 1, 1], "bounds": box, "coordinate_space": "page"}]},
            "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "approved_geometry": {
                "society_of_killers_1_3::p1": {**box, "approved": True},
                "society_of_killers_1_6::p1": {**box, "approved": True}},
            "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "provenance": {"published_revision_id": "rev_taaaa",
                           "generated_vs_approved": {"state": "generated_publication",
                                                     "generated_snapshot_revision_id": "rev_g"}},
        }
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["geometry_match_version"], "v3")
        self.assertEqual(d["precision"], 1.0)      # each gen matches exactly its own-page approved
        self.assertEqual(d["recall"], 1.0)
        self.assertEqual(d["split_artifact_ids"], [])   # no phantom split from the other page
        self.assertEqual(d["merge_artifact_ids"], [])   # no phantom merge from the other page
        self.assertEqual(d["false_count"], 0)

    def test_page_number_derived_when_uncarried(self):
        """Approved page panels carry no page_number in production; the adapter derives it from the
        id so matching can be page-scoped. A generated page-3 panel must not match an approved
        page-6 panel even at identical coordinates."""
        box = {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}
        r = {
            "review_report_version": "v1", "issue_identity": fx.IDENTITY, "review_id": "rev_t",
            "generated_geometry": {"property_id": "x", "issue_number": 1, "total_pages": 6,
                "total_story_pages": 6, "total_panels": 1, "panels": [
                    {"panel_key": "society_of_killers_1_3::p1", "page_number": 3, "order": 1,
                     "bbox": [0, 0, 1, 1], "bounds": box, "coordinate_space": "page"}]},
            "generated_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            # approved id encodes page 6, NO page_number field -> derived
            "approved_geometry": {"6::NEW::1": {**box, "isNew": True}},
            "approved_metadata": {"llm_enrichment_output_version": "v1.1", "llm_enrichment_outputs": []},
            "provenance": {"published_revision_id": "rev_taaaa",
                           "generated_vs_approved": {"state": "generated_publication",
                                                     "generated_snapshot_revision_id": "rev_g"}},
        }
        d = compute_geometry_delta(adapt_review(r))
        self.assertEqual(d["false_count"], 1)                 # gen page-3 panel matched nothing
        self.assertIn("6::NEW::1", d["missing_page_artifact_ids"])   # approved page-6 unmatched


if __name__ == "__main__":
    unittest.main()
