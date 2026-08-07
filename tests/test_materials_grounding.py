"""Tests for the CBI-2b materials-grounding benchmark (generated-vs-approved grounding delta).

Covers: off-by-default -> not-applicable (byte-identical baseline); the change categories
(accepted/added/removed/revision_changed/replaced); fresh-only acceptance (preserved excluded);
version-pin skew abstains; identifiers-only (no material bytes/text); determinism; manual not-applicable.
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
import delta_materials_grounding as dmg  # noqa: E402
from review_contract_adapter import adapt_review  # noqa: E402
from delta_auditor import run_delta_audit  # noqa: E402

_PIN = {"materials_grounding_version": "v1", "resolution_contract_version": "v1"}


def _sm(material_id, revision, category="reference", subtype="style_guide", file_id="f1", edition_id=None):
    """A supporting_material context_source entry."""
    return {"kind": "supporting_material", "material_id": material_id, "category": category,
            "subtype": subtype, "edition_id": edition_id,
            "files": [{"file_id": file_id, "revision": revision}]}


def _grounded_review(gen_ctx, app_ctx, gen_pin=_PIN, app_pin=_PIN, dispositions=None):
    """v1.1 review with per-output context_source grounding injected on the 3 common panels.
    gen_ctx/app_ctx: {artifact_id: [context_source entries]}. dispositions: {artifact_id: fresh|preserved_*}."""
    r = copy.deepcopy(fx.review_generated())
    for side, ctx in (("generated_metadata", gen_ctx), ("approved_metadata", app_ctx)):
        for o in r[side]["llm_enrichment_outputs"]:
            aid = o["artifact_id"]
            if aid in ctx:
                o["context_source"] = ctx[aid]
            if side == "generated_metadata" and dispositions and aid in dispositions:
                o["metadata_generation_provenance"] = dispositions[aid]
    if gen_pin is not None:
        r["generated_metadata"]["materials_grounding"] = gen_pin
    if app_pin is not None:
        r["approved_metadata"]["materials_grounding"] = app_pin
    return r


A1, A2, A3 = "society_of_killers_1_10::p1", "society_of_killers_1_3::p1", "society_of_killers_1_7::p1"


class TestMaterialsGrounding(unittest.TestCase):
    def test_off_by_default_not_applicable(self):
        # the base fixture has no context_source grounding -> nothing to audit (byte-identical baseline)
        b = dmg.compute_materials_grounding_benchmark(adapt_review(fx.review_generated()))
        self.assertFalse(b["applicable"])
        self.assertEqual(b["reason"], "no_materials_grounding")

    def test_accepted_unchanged(self):
        g = {A1: [_sm("mat_a", "rev_1")]}
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(g, g)))
        self.assertTrue(b["applicable"])
        self.assertEqual(b["counts"]["accepted_unchanged"], 1)
        self.assertEqual(b["grounding_acceptance"]["rate"], 1.0)
        self.assertEqual(b["grounding_edits"], 0)

    def test_added_removed_revised_replaced(self):
        gen = {A1: [_sm("mat_a", "rev_1")],                 # approval ADDS mat_b -> grounding_added
               A2: [_sm("mat_c", "rev_1")],                 # approval REMOVES -> grounding_removed
               A3: [_sm("mat_d", "rev_1")]}                 # same id, new rev -> revision_changed
        app = {A1: [_sm("mat_a", "rev_1"), _sm("mat_b", "rev_1")],
               A2: [],
               A3: [_sm("mat_d", "rev_2")]}
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(gen, app)))
        self.assertEqual(b["counts"]["grounding_added"], 1)
        self.assertEqual(b["counts"]["grounding_removed"], 1)
        self.assertEqual(b["counts"]["revision_changed"], 1)
        self.assertEqual(b["grounding_edits"], 3)
        self.assertEqual(b["grounding_acceptance"]["denominator"], 3)
        self.assertEqual(b["grounding_acceptance"]["numerator"], 0)

    def test_replaced(self):
        gen = {A1: [_sm("mat_a", "rev_1")]}
        app = {A1: [_sm("mat_b", "rev_1")]}                 # add mat_b + remove mat_a -> replaced
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(gen, app)))
        self.assertEqual(b["counts"]["grounding_replaced"], 1)

    def test_fresh_only_excludes_preserved(self):
        g = {A1: [_sm("mat_a", "rev_1")], A2: [_sm("mat_b", "rev_1")]}
        # A2 preserved -> excluded from the acceptance denominator even though it grounds
        b = dmg.compute_materials_grounding_benchmark(
            adapt_review(_grounded_review(g, g, dispositions={A2: "preserved_approved"})))
        self.assertEqual(b["grounding_acceptance"]["denominator"], 1)   # only A1 fresh+comparable

    def test_version_skew_abstains(self):
        g = {A1: [_sm("mat_a", "rev_1")]}
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(
            g, g, app_pin={"materials_grounding_version": "v2", "resolution_contract_version": "v1"})))
        self.assertTrue(b["version_skew"])
        self.assertEqual(b["counts"]["unsupported_version"], b["artifacts_common"])
        self.assertEqual(b["grounding_acceptance"]["denominator"], 0)

    def test_identifiers_only_no_material_text(self):
        g = {A1: [_sm("mat_secret", "rev_1", subtype="character_bible")]}
        app = {A1: [_sm("mat_secret", "rev_1", subtype="character_bible")]}
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(g, app)))
        blob = json.dumps(b, ensure_ascii=False)
        # ids/subtypes are references and may appear; assert no file-content-ish leakage vector exists —
        # records carry only id lists + detail id lists, never a 'text'/'content'/'bytes' field.
        for rec in b["records"]:
            self.assertEqual(set(rec) - {"artifact_id", "category", "generated_material_ids",
                                         "approved_material_ids", "detail", "generated_disposition"}, set())

    def test_deterministic(self):
        g = {A1: [_sm("mat_a", "rev_1"), _sm("mat_b", "rev_2")]}
        c = adapt_review(_grounded_review(g, g))
        a = json.dumps(dmg.compute_materials_grounding_benchmark(c), sort_keys=True)
        b = json.dumps(dmg.compute_materials_grounding_benchmark(c), sort_keys=True)
        self.assertEqual(a, b)

    def test_manual_not_applicable(self):
        b = dmg.compute_materials_grounding_benchmark(adapt_review(fx.review_manual()))
        self.assertFalse(b["applicable"])
        self.assertEqual(b["reason"], "manual_publication")

    def test_registry_entities_are_not_materials(self):
        # a registry_entity kind in context_source must be ignored (materials audit filters by kind)
        gen = {A1: [{"kind": "registry_entity", "entity_id": "e1"}, _sm("mat_a", "rev_1")]}
        b = dmg.compute_materials_grounding_benchmark(adapt_review(_grounded_review(gen, gen)))
        self.assertEqual(b["records"][0]["generated_material_ids"], ["mat_a"])


class TestIntegration(unittest.TestCase):
    def test_report_carries_materials_grounding_benchmark(self):
        g = {A1: [_sm("mat_a", "rev_1")]}
        rep = run_delta_audit(_grounded_review(g, g), fx.platform_approval())
        self.assertTrue(rep["materials_grounding_benchmark"]["applicable"])
        self.assertEqual(rep["provenance"]["materials_grounding_version"], "v1")

    def test_report_baseline_not_applicable_when_off(self):
        rep = run_delta_audit(fx.review_generated(), fx.platform_approval())
        self.assertFalse(rep["materials_grounding_benchmark"]["applicable"])


if __name__ == "__main__":
    unittest.main()
