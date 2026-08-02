"""Adapter v3 — Panel Intelligence v2 metadata field contract (llm_enrichment_output_version v2).

Exercises the v2 path the v1.1 suite can't: per-leaf field set (tags decomposed to facets, environment,
objects, shot_type, weather, time_of_day), structured `narrative.dialogue`, `field_sources`-marker exclusion
of computed `colors` + `publisher_notes`, the recall-counter metric, and the both-sides-unsupported guard.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _delta_fixtures as fx  # noqa: E402
import delta_metadata_revision as dmr  # noqa: E402
from review_contract_adapter import adapt_review, ReviewContractError  # noqa: E402
from delta_metadata_revision import V2_LLM_LEAVES  # noqa: E402

_PROV = {"model": "gpt-4o-mini", "prompt_version": "v2", "prompt_sha256": "sha256:v2hash",
         "temperature": 0, "mode": "vision"}


def _v2_out(aid, *, characters, objects, environment, summary, dialogue, shot_type,
            mood, action, weather, time_of_day, colors, notes=None, disposition="fresh",
            gen_count=1, review_state="unreviewed"):
    """One v2 metadata output (nested output.* + record-level field_sources/provenance/notes)."""
    out = {
        "artifact_id": aid, "input_ref": aid, "version": "v2",
        "metadata_locked": review_state == "approved", "metadata_review_state": review_state,
        "output": {
            "entities": {"characters": characters, "objects": objects, "environment": environment},
            "narrative": {"summary": summary, "dialogue": dialogue},
            "classification": {"shot_type": shot_type, "colors": colors,
                               "tags": {"mood": mood, "action": action,
                                        "weather": weather, "time_of_day": time_of_day}},
        },
        "field_sources": {"output.classification.colors": "computed"},
        "generation_provenance": dict(_PROV, generation_count=gen_count),
        "metadata_generation_provenance": disposition,
    }
    if notes is not None:
        out["publisher_notes"] = notes
        out["field_sources"]["publisher_notes"] = "publisher"
    return out


def _v2_review():
    """A v2 generated-publication review: geometry reused from the v1.1 fixture; metadata replaced with the
    v2 shape for the 3 common page panels. 1_10 fully accepted; 1_3 edits (characters/dialogue/environment);
    1_7 accepted but colors differs (must NOT count) + carries publisher_notes."""
    r = copy.deepcopy(fx.review_generated())

    def blk(outs):
        return {"llm_enrichment_output_version": "v2", "llm_enrichment_outputs": outs}

    dlg = [{"type": "Speech", "speaker": "Astrid", "text": "Stay back."}]
    gen = [
        _v2_out("society_of_killers_1_10::p1", characters=["Quentin"], objects=["cage"],
                environment="holding pen", summary="Guards around a cage.", dialogue=dlg,
                shot_type="wide", mood="tense", action="observation", weather="clear",
                time_of_day="night", colors=["#111111"], gen_count=1),
        _v2_out("society_of_killers_1_3::p1", characters=["Astrid"], objects=[],
                environment="studio", summary="Astrid, stylized.", dialogue=dlg,
                shot_type="close-up", mood="edgy", action="smoking", weather="clear",
                time_of_day="day", colors=["#222222"], gen_count=2),
        _v2_out("society_of_killers_1_7::p1", characters=["Marlowe"], objects=[],
                environment="room", summary="A quiet room.", dialogue=[],
                shot_type="medium", mood="calm", action="waiting", weather="clear",
                time_of_day="day", colors=["#333333"], gen_count=1),
    ]
    appr = [
        _v2_out("society_of_killers_1_10::p1", characters=["Quentin"], objects=["cage"],
                environment="holding pen", summary="Guards around a cage.", dialogue=dlg,
                shot_type="wide", mood="tense", action="observation", weather="clear",
                time_of_day="night", colors=["#111111"], review_state="approved"),
        # 1_3: characters + dialogue speaker + environment edited
        _v2_out("society_of_killers_1_3::p1", characters=["Samara"], objects=[],
                environment="alley", summary="Astrid, stylized.",
                dialogue=[{"type": "Speech", "speaker": "Samara", "text": "Stay back."}],
                shot_type="close-up", mood="edgy", action="smoking", weather="clear",
                time_of_day="day", colors=["#222222"], review_state="approved"),
        # 1_7: all editorial accepted, but colors DIFFERS (must be excluded) + publisher_notes present
        _v2_out("society_of_killers_1_7::p1", characters=["Marlowe"], objects=[],
                environment="room", summary="A quiet room.", dialogue=[],
                shot_type="medium", mood="calm", action="waiting", weather="clear",
                time_of_day="day", colors=["#999999"], notes="cover panel",
                review_state="approved"),
    ]
    r["generated_metadata"] = blk(gen)
    r["approved_metadata"] = blk(appr)
    return r


class TestV2FieldContract(unittest.TestCase):
    def test_v2_field_set_and_leaves(self):
        b = dmr.compute_metadata_benchmark(adapt_review(_v2_review()))
        self.assertTrue(b["applicable"])
        self.assertEqual(b["field_set_version"], "v2")
        self.assertEqual(set(b["fields"]), set(V2_LLM_LEAVES))
        # colors + publisher_notes are NOT compared leaves
        self.assertNotIn("classification.colors", b["fields"])
        self.assertNotIn("publisher_notes", b["fields"])
        self.assertEqual(len(b["fields"]), 10)

    def test_colors_and_notes_excluded_recorded_as_hash(self):
        b = dmr.compute_metadata_benchmark(adapt_review(_v2_review()))
        # colors differs on 1_7 but is NOT an edit anywhere in the compared records
        for r in b["records"]:
            self.assertNotEqual(r["field"], "classification.colors")
            self.assertNotEqual(r["field"], "publisher_notes")
        # recorded as hashes on the generated side
        ne = b["non_editorial"]["society_of_killers_1_7::p1"]
        self.assertIn("classification.colors", ne)
        self.assertIn("publisher_notes", ne)
        self.assertEqual(len(ne["publisher_notes"]["approved"]), 64)   # sha256, approved-side authored
        # colors differs gen vs approved on 1_7 (recorded, but never an editorial edit)
        self.assertNotEqual(ne["classification.colors"]["generated"], ne["classification.colors"]["approved"])
        # raw note text never leaks into the benchmark
        self.assertNotIn("cover panel", json.dumps(b, ensure_ascii=False))

    def test_v2_edits_land_on_the_right_leaves(self):
        b = dmr.compute_metadata_benchmark(adapt_review(_v2_review()))
        edited = {(r["field"]) for r in b["records"]
                  if r["category"] in dmr._EDIT_CATEGORIES}
        # 1_3 edited characters, environment, and dialogue (speaker change)
        self.assertIn("entities.characters", edited)
        self.assertIn("entities.environment", edited)
        self.assertIn("narrative.dialogue", edited)

    def test_v2_acceptance_denominator_excludes_non_editorial(self):
        b = dmr.compute_metadata_benchmark(adapt_review(_v2_review()))
        ma = b["metadata_accuracy"]
        # 3 artifacts x 10 leaves = 30 candidate; abstentions (empty both sides, e.g. objects/dialogue on
        # some) reduce comparable. colors/notes are NOT in the 30 at all.
        self.assertEqual(ma["denominator_basis"], "fresh_generated_outputs_only")
        self.assertTrue(0 < ma["acceptance"]["denominator"] <= 30)
        self.assertGreater(ma["total_edited_fields"], 0)

    def test_dialogue_structured_change_is_an_edit(self):
        # speaker change
        g = [{"type": "Speech", "speaker": "A", "text": "Hi"}]
        a = [{"type": "Speech", "speaker": "B", "text": "Hi"}]
        self.assertIn(dmr._classify(g, a)[0], dmr._EDIT_CATEGORIES)
        # add element
        self.assertIn(dmr._classify(g, g + [{"type": "SFX", "speaker": "", "text": "BOOM"}])[0],
                      dmr._EDIT_CATEGORIES)
        # reorder (two distinct elements swapped) is an edit via order-sensitive char distance
        two = [{"type": "Speech", "speaker": "A", "text": "Hi"},
               {"type": "Speech", "speaker": "B", "text": "Bye"}]
        self.assertIn(dmr._classify(two, list(reversed(two)))[0], dmr._EDIT_CATEGORIES)
        # identical dialogue accepts
        self.assertEqual(dmr._classify(g, copy.deepcopy(g))[0], "accepted_unchanged")

    def test_recall_counter_metric(self):
        b = dmr.compute_metadata_benchmark(adapt_review(_v2_review()))
        calls = b["llm_calls_per_panel"]
        self.assertEqual(calls["panels_with_count"], 3)
        self.assertEqual(calls["total_calls"], 1 + 2 + 1)
        self.assertEqual(calls["recalled_panels"], 1)   # 1_3 had generation_count 2
        self.assertEqual(calls["max_calls"], 2)

    def test_recall_metric_absent_when_no_counts(self):
        r = _v2_review()
        for o in r["generated_metadata"]["llm_enrichment_outputs"]:
            o["generation_provenance"].pop("generation_count", None)
        b = dmr.compute_metadata_benchmark(adapt_review(r))
        self.assertIsNone(b["llm_calls_per_panel"])

    def test_both_sides_unsupported_version_fails(self):
        r = _v2_review()
        r["generated_metadata"]["llm_enrichment_output_version"] = "v9"
        r["approved_metadata"]["llm_enrichment_output_version"] = "v9"
        with self.assertRaises(ReviewContractError):
            adapt_review(r)

    def test_version_skew_abstains_not_fails(self):
        # generated v2 vs approved v1.1 -> skew -> unsupported_schema (no raise)
        r = _v2_review()
        r["approved_metadata"]["llm_enrichment_output_version"] = "v1.1"
        b = dmr.compute_metadata_benchmark(adapt_review(r))   # must not raise
        self.assertEqual(b["comparable_artifacts"], 0)
        self.assertEqual(b["global"]["comparable_fields"], 0)

    def test_field_sources_marker_excludes_generically(self):
        # marking a normally-editorial leaf as non-llm removes it from the compared set
        r = _v2_review()
        for o in r["generated_metadata"]["llm_enrichment_outputs"]:
            o["field_sources"]["output.classification.shot_type"] = "computed"
        for o in r["approved_metadata"]["llm_enrichment_outputs"]:
            o["field_sources"]["output.classification.shot_type"] = "computed"
        b = dmr.compute_metadata_benchmark(adapt_review(r))
        for rec in b["records"]:
            self.assertNotEqual(rec["field"], "classification.shot_type")
        self.assertIn("classification.shot_type",
                      b["non_editorial"]["society_of_killers_1_10::p1"])

    def test_v2_deterministic(self):
        c = adapt_review(_v2_review())
        a = json.dumps(dmr.compute_metadata_benchmark(c), sort_keys=True)
        b = json.dumps(dmr.compute_metadata_benchmark(c), sort_keys=True)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
