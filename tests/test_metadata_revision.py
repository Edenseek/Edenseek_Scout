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
                        "approved_sha256", "generated_empty", "approved_empty",
                        "generated_disposition", "measures"}

# A fresh per-output generation_provenance (Publisher enhancement #1), sibling of `output`.
_FRESH_PROV = {"model": "gpt-4.1-mini", "prompt_version": "v1",
               "prompt_sha256": "sha256:3b5dea34", "temperature": 0, "mode": "text"}
_ALLOWED_MEASURE_KEYS = {"char_levenshtein", "char_levenshtein_norm", "token_jaccard_distance",
                         "set_jaccard_distance", "len_ratio", "structural_equal",
                         "generated_type", "approved_type"}


def _generated_with_prov(dispositions=None, provenance_by_id=None):
    """``fx.review_generated()`` with per-output ``generation_provenance`` + disposition injected on
    every generated output. ``dispositions``/``provenance_by_id`` override per artifact_id; defaults
    are all-``fresh`` with ``_FRESH_PROV``."""
    r = fx.review_generated()
    for o in r["generated_metadata"]["llm_enrichment_outputs"]:
        aid = o["artifact_id"]
        o["generation_provenance"] = (provenance_by_id or {}).get(aid, _FRESH_PROV)
        o["metadata_generation_provenance"] = (dispositions or {}).get(aid, "fresh")
    return r


def _report_body(rep):
    """Wrap a delta report into the minimal view build_report_body needs (mirrors TestIntegration)."""
    view = {
        "audit_timestamp": "2026-07-31T00:00:00Z", "publisher_commit": "p", "scout_commit": "s",
        "evidence": {"issue_identity": fx.IDENTITY, "summary": {}, "objects": [],
                     "manifest_version": "v1", "publisher_provenance": {}},
        "findings": [{"code": "x", "severity": "PASS", "title": "t", "detail": "d"}],
        "delta_summary": {"geometry": {"status": "computed", "precision": 1.0, "recall": 0.5,
                                       "split_rate": 0, "merge_rate": 0, "missing": 0,
                                       "spread_missing": 1, "false": 0},
                          "metadata": {"status": "computed", "compared": 2}},
        "delta_report": rep, "delta_report_sha256": "x",
    }
    return sda.build_report_body(view)


class TestProvenanceV2(unittest.TestCase):
    """Publisher enhancement #1 (model/prompt provenance) + #2 (fresh/preserved flag) → adapter v2."""

    def test_adapter_tolerates_and_reads_provenance_siblings(self):
        # The additive sibling keys must NOT trip fail-fast, and must not change compared content.
        c = adapt_review(_generated_with_prov())
        base = adapt_review(fx.review_generated())
        aid = "society_of_killers_1_3::p1"
        self.assertEqual(c["generated"]["metadata"][aid]["fields"],
                         base["generated"]["metadata"][aid]["fields"])
        self.assertEqual(c["generated"]["metadata"][aid]["generation_disposition"], "fresh")

    def test_provenance_identity_from_fresh_outputs(self):
        mp = adapt_review(_generated_with_prov())["metadata_provenance"]
        self.assertEqual(mp["model"], "gpt-4.1-mini")
        self.assertEqual(mp["prompt_version"], "v1")
        self.assertEqual(mp["prompt_sha256"], "sha256:3b5dea34")
        self.assertEqual(mp["provenance_source"], "per_output_fresh")
        self.assertFalse(mp["provenance_heterogeneous"])

    def test_legacy_revision_yields_null_provenance(self):
        mp = adapt_review(fx.review_generated())["metadata_provenance"]   # no provenance emitted
        self.assertIsNone(mp["model"])
        self.assertIsNone(mp["prompt_version"])
        self.assertIsNone(mp["prompt_sha256"])
        self.assertEqual(mp["provenance_source"], "legacy_or_absent")
        self.assertEqual(mp["fresh_output_count"], 0)

    def test_heterogeneous_fresh_provenance_is_surfaced_not_collapsed(self):
        prov_b = dict(_FRESH_PROV, model="gpt-4o")
        mp = adapt_review(_generated_with_prov(
            provenance_by_id={"society_of_killers_1_3::p1": prov_b}))["metadata_provenance"]
        # disagreeing models -> a deterministic mixed marker (NOT None, so the axis key stays distinct)
        self.assertTrue(mp["model"].startswith("mixed:"))
        self.assertTrue(mp["provenance_heterogeneous"])
        self.assertEqual(mp["prompt_version"], "v1")    # prompt_version still agrees -> resolved

    def test_heterogeneous_mixes_get_distinct_axis_keys(self):
        # Same mix -> same marker; a DIFFERENT mix -> a different marker. Two heterogeneous reports
        # must never silently share a comparability key.
        m1 = adapt_review(_generated_with_prov(provenance_by_id={
            "society_of_killers_1_3::p1": dict(_FRESH_PROV, model="gpt-4o")}))["metadata_provenance"]["model"]
        m1b = adapt_review(_generated_with_prov(provenance_by_id={
            "society_of_killers_1_3::p1": dict(_FRESH_PROV, model="gpt-4o")}))["metadata_provenance"]["model"]
        m2 = adapt_review(_generated_with_prov(provenance_by_id={
            "society_of_killers_1_3::p1": dict(_FRESH_PROV, model="claude-3")}))["metadata_provenance"]["model"]
        self.assertEqual(m1, m1b)          # deterministic per mix
        self.assertNotEqual(m1, m2)        # different mix -> different marker

    def test_headline_is_fresh_only_and_self_consistent(self):
        # Reviewer finding #1: with a preserved output present, EVERY headline rate must be fresh-only,
        # so accepted_unchanged_rate == the acceptance headline and comparable_fields == its denominator.
        aid = "society_of_killers_1_10::p1"
        b = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov(
            dispositions={aid: "preserved_approved"})))
        h = dmr.benchmark_headline(b)
        ma = b["metadata_accuracy"]
        self.assertEqual(h["accepted_unchanged_rate"], ma["acceptance"]["rate"])
        self.assertEqual(h["unchanged_metadata_rate"], ma["acceptance"]["rate"])
        self.assertEqual(h["comparable_fields"], ma["acceptance"]["denominator"])
        # the surfaced `global` is now fresh-only (== the headline denominator), and DIFFERS from the
        # retained all-common descriptive block — proving no inflated surface survives.
        self.assertEqual(h["comparable_fields"], b["global"]["comparable_fields"])
        self.assertNotEqual(h["comparable_fields"], b["global_all_common"]["comparable_fields"])

    def test_body_metadata_benchmark_is_fresh_only(self):
        # Reviewer finding A: the field the index entry + Metadata Intelligence trend consume
        # (body["metadata_benchmark"], spread from mb["global"]) must be fresh-only, not preserved-inflated.
        import scout_delta_audit as sda2
        aid = "society_of_killers_1_10::p1"
        rep = run_delta_audit(_generated_with_prov(dispositions={aid: "preserved_approved"}),
                              fx.platform_approval())
        mb = rep["metadata_benchmark"]
        self.assertEqual(mb["global"]["comparable_fields"], mb["metadata_accuracy"]["acceptance"]["denominator"])
        self.assertNotEqual(mb["global"]["comparable_fields"], mb["global_all_common"]["comparable_fields"])
        body = _report_body(rep)
        self.assertEqual(body["metadata_benchmark"]["comparable_fields"],
                         mb["metadata_accuracy"]["acceptance"]["denominator"])

    def test_all_preserved_withholds_target(self):
        # Reviewer finding B: a zero-fresh revision must not read as "0% accepted / target failed".
        r = _generated_with_prov(dispositions={a: "preserved_approved" for a in
                                               ("society_of_killers_1_10::p1", "society_of_killers_1_3::p1",
                                                "society_of_killers_1_7::p1")})
        ma = dmr.compute_metadata_benchmark(adapt_review(r))["metadata_accuracy"]
        self.assertEqual(ma["acceptance"]["denominator"], 0)
        self.assertIsNone(ma["meets_target"])
        self.assertFalse(ma["provisional"])            # coverage is "all", not partial
        self.assertEqual(ma["disposition_coverage"], "all")

    def test_partial_coverage_is_provisional_and_target_withheld(self):
        # Reviewer finding #2: an under-flagged (contract-violating) revision must not emit a trustworthy
        # meets_target. Flag every output except the fully-accepted one.
        r = fx.review_generated()
        for o in r["generated_metadata"]["llm_enrichment_outputs"]:
            o["generation_provenance"] = _FRESH_PROV
            if o["artifact_id"] != "society_of_killers_1_10::p1":
                o["metadata_generation_provenance"] = "fresh"
        b = dmr.compute_metadata_benchmark(adapt_review(r))
        ma = b["metadata_accuracy"]
        self.assertEqual(ma["disposition_coverage"], "partial")
        self.assertTrue(ma["provisional"])
        self.assertIsNone(ma["meets_target"])
        self.assertIsNone(dmr.benchmark_headline(b)["metadata_accuracy_meets_target"])

    def test_preserved_provenance_ignored_for_axis(self):
        # A preserved output keeps a PRIOR run's model; it must not drive this run's axis.
        prov_old = {"model": "old-model", "prompt_version": "v0", "prompt_sha256": "sha256:old"}
        mp = adapt_review(_generated_with_prov(
            dispositions={"society_of_killers_1_3::p1": "preserved_approved"},
            provenance_by_id={"society_of_killers_1_3::p1": prov_old}))["metadata_provenance"]
        self.assertEqual(mp["model"], "gpt-4.1-mini")   # from the fresh outputs only
        self.assertEqual(mp["prompt_version"], "v1")

    def test_prompt_sha256_is_a_metadata_axis(self):
        self.assertIn("metadata_prompt_sha256", sri.METADATA_AXES)
        body = _report_body(run_delta_audit(_generated_with_prov(), fx.platform_approval()))
        axes = sri.metadata_axes(body)
        self.assertEqual(axes["metadata_prompt_sha256"], "sha256:3b5dea34")
        self.assertEqual(axes["metadata_model"], "gpt-4.1-mini")
        self.assertEqual(axes["metadata_prompt_version"], "v1")

    def test_v2_excludes_preserved_from_denominator(self):
        aid = "society_of_killers_1_10::p1"   # 4 scored fields: tags/chars/summary accepted, dialogue added
        base = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov()))["metadata_accuracy"]
        ma = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov(
            dispositions={aid: "preserved_approved"})))["metadata_accuracy"]
        self.assertEqual(ma["excluded_preserved_artifacts"], [aid])
        self.assertEqual(ma["excluded_preserved_field_count"], 4)
        self.assertEqual(ma["acceptance"]["denominator"], base["acceptance"]["denominator"] - 4)
        self.assertEqual(ma["acceptance"]["numerator"], base["acceptance"]["numerator"] - 3)

    def test_preserved_prior_success_also_excluded(self):
        aid = "society_of_killers_1_10::p1"
        ma = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov(
            dispositions={aid: "preserved_prior_success"})))["metadata_accuracy"]
        self.assertIn(aid, ma["excluded_preserved_artifacts"])

    def test_v2_all_fresh_equals_legacy_number(self):
        # v2 is backward-identical: explicit-all-fresh == no-flags-at-all.
        a = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov()))["metadata_accuracy"]
        b = dmr.compute_metadata_benchmark(adapt_review(fx.review_generated()))["metadata_accuracy"]
        self.assertEqual(a["acceptance"], b["acceptance"])

    def test_disposition_coverage_signal(self):
        legacy = dmr.compute_metadata_benchmark(adapt_review(fx.review_generated()))["metadata_accuracy"]
        self.assertEqual(legacy["disposition_coverage"], "none")
        allflagged = dmr.compute_metadata_benchmark(adapt_review(_generated_with_prov()))["metadata_accuracy"]
        self.assertEqual(allflagged["disposition_coverage"], "all")
        # a contract-violating partial emission (flag on some outputs, absent on others) is surfaced
        r = fx.review_generated()
        outs = r["generated_metadata"]["llm_enrichment_outputs"]
        outs[0]["metadata_generation_provenance"] = "fresh"   # only one output flagged
        partial = dmr.compute_metadata_benchmark(adapt_review(r))["metadata_accuracy"]
        self.assertEqual(partial["disposition_coverage"], "partial")


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

    def test_metadata_accuracy_v2(self):
        b = dmr.compute_metadata_benchmark(adapt_review(fx.review_generated()))
        ma = b["metadata_accuracy"]
        self.assertEqual(ma["version"], "v2")
        self.assertEqual(ma["denominator_basis"], "fresh_generated_outputs_only")
        # BACKWARD-IDENTICAL on all-fresh data: with no disposition flag every scored field is fresh,
        # so v2's fresh-only acceptance equals the global accepted/comparable (the v1 number).
        self.assertEqual(ma["acceptance"]["numerator"], b["global"]["counts"]["accepted_unchanged"])
        self.assertEqual(ma["acceptance"]["denominator"], b["global"]["comparable_fields"])
        self.assertEqual(ma["excluded_preserved_field_count"], 0)
        self.assertEqual(ma["excluded_preserved_artifacts"], [])
        self.assertEqual(ma["disposition_coverage"], "none")   # legacy fixture: no flags
        self.assertFalse(ma["provisional"])
        self.assertEqual(ma["meets_target"], ma["acceptance"]["rate"] >= 0.75)
        # per-field editorial burden covers all fields and is ranked by edits (where the work is)
        self.assertEqual(set(ma["per_field"]), set(dmr.FIELDS))
        edits = [x["edited"] for x in ma["editorial_burden"]]
        self.assertEqual(edits, sorted(edits, reverse=True))
        self.assertEqual(sum(x["edited"] for x in ma["editorial_burden"]), ma["total_edited_fields"])
        # effort method is data-driven: a list field edited -> set_jaccard; text field -> token_jaccard
        chars = ma["per_field"]["entities.characters"]
        if chars["edited"]:
            self.assertEqual(chars["effort_method"], "set_jaccard")

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

    def test_revision_id_field_names_aligned(self):
        # The delta report exposes the revision under BOTH the canonical `published_revision_id` and the
        # `publisher_revision_id` alias (retrieval-report name), both populated and equal — no null field.
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
        prov = sda.build_report_body(view)["provenance"]
        self.assertEqual(prov["publisher_revision_id"], prov["published_revision_id"])
        self.assertIsNotNone(prov["published_revision_id"])


if __name__ == "__main__":
    unittest.main()
