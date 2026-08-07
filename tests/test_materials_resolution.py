"""Track A — resolved-graph material auditor tests.

Covers the v1 cascade mirror (inheritance, most-specific-on-collision, retirement + edition eligibility
DURING the union, explicit supersession, approved-only terminal), the Publisher cross-check (matches /
only_scout / only_publisher / file-revision mismatch / version skew), the authoring invariants (dangling
supersedes, multiple-active-approved-per-lineage, superseded-still-approved), the version pin fail-fast,
determinism, and identifiers-only.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import materials_resolution_audit as mra  # noqa: E402

CONTRACT = {"resolution_contract_version": "v1",
            "cascade_levels": ["issue", "series", "title_group", "publisher"],
            "resolution_order": ["retirement_exclusion", "edition_filter",
                                 "inheritance_union_supplement_by_default",
                                 "rank_aware_explicit_supersession", "lifecycle_publisher_approved_only"]}


def _rec(material_id, level, status="publisher_approved", edition_id=None, supersedes=None, file_id="f1",
         revision="rev_1"):
    r = {"material_id": material_id, "category": "reference", "subtype": "style_guide",
         "scope": {"level": level}, "title": material_id, "status": status, "version": 1,
         "files": [{"file_id": file_id, "role": "primary", "artifact_ref": {"stage": "reference",
                                                                            "sub": "materials", "revision": revision}}]}
    if edition_id is not None:
        r["scope"]["edition_id"] = edition_id
    if supersedes is not None:
        r["relationships"] = [{"rel": "supersedes", "target": {"kind": "material", "id": supersedes}}]
    return r


def _index(level, records):
    return {"material_index_version": "v1", "scope": {"level": level}, "records": records}


def _resolved(entries, cver="v1", edition_id=None):
    return {"resolved_materials_version": "v1", "resolution_contract_version": cver,
            "resolution": "context_builder_view",
            "target": {"property_id": "society_of_killers", "issue_number": 1, "edition_id": edition_id},
            "resolved": entries}


def _res_entry(material_id, scope_level="issue", revision="rev_1", file_id="f1"):
    return {"material_id": material_id, "category": "reference", "subtype": "style_guide",
            "scope_level": scope_level, "edition_id": None, "status": "publisher_approved",
            "files": [{"file_id": file_id, "revision": revision}]}


class TestResolveMirror(unittest.TestCase):
    def test_inheritance_union_across_scopes(self):
        recs = [_rec("m_issue", "issue"), _rec("m_series", "series"),
                _rec("m_tg", "title_group"), _rec("m_pub", "publisher")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertEqual(eff, ["m_issue", "m_pub", "m_series", "m_tg"])   # all inherited, approved

    def test_retirement_excluded(self):
        recs = [_rec("m_a", "issue"), _rec("m_r", "series", status="retired")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertEqual(eff, ["m_a"])

    def test_edition_eligibility_during_union(self):
        recs = [_rec("m_agnostic", "issue"),
                _rec("m_ed1", "issue", edition_id="ed_1"),
                _rec("m_ed2", "issue", edition_id="ed_2")]
        # target edition ed_1 -> agnostic + ed_1 only
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs, target_edition_id="ed_1")]
        self.assertEqual(eff, ["m_agnostic", "m_ed1"])
        # target null -> only edition-agnostic
        eff0 = [r["material_id"] for r in mra.resolve_effective_materials(recs, target_edition_id=None)]
        self.assertEqual(eff0, ["m_agnostic"])

    def test_most_specific_on_collision(self):
        # same material_id at issue + series -> issue (narrower) wins
        recs = [_rec("m_x", "series", revision="rev_series"), _rec("m_x", "issue", revision="rev_issue")]
        eff = mra.resolve_effective_materials(recs)
        self.assertEqual(len(eff), 1)
        self.assertEqual((eff[0].get("scope") or {}).get("level"), "issue")

    def test_explicit_supersession_removes_target(self):
        recs = [_rec("m_old", "issue", status="superseded"),
                _rec("m_new", "issue", supersedes="m_old")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertEqual(eff, ["m_new"])

    def test_ineligible_record_never_suppresses(self):
        # m_new supersedes m_old but m_new is RETIRED (ineligible) -> it can't suppress; m_old survives
        recs = [_rec("m_old", "issue", status="publisher_approved"),
                _rec("m_new", "issue", status="retired", supersedes="m_old")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertEqual(eff, ["m_old"])

    def test_terminal_approved_only(self):
        recs = [_rec("m_draft", "issue", status="draft"), _rec("m_ok", "issue")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertEqual(eff, ["m_ok"])


class TestCrossCheck(unittest.TestCase):
    def _indexes(self, issue=None, series=None, tg=None, pub=None):
        return {"issue": _index("issue", issue or []), "series": _index("series", series or []),
                "title_group": _index("title_group", tg or []), "publisher": _index("publisher", pub or [])}

    def test_matches(self):
        idx = self._indexes(issue=[_rec("m_a", "issue")], series=[_rec("m_b", "series")])
        rm = _resolved([_res_entry("m_a"), _res_entry("m_b", scope_level="series")])
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertTrue(rep["applicable"])
        self.assertTrue(rep["cross_check"]["matches"])
        self.assertEqual(rep["cross_check"]["agree"], ["m_a", "m_b"])

    def test_only_scout_divergence(self):
        # Scout resolves m_a + m_b; Publisher's resolved has only m_a -> only_scout = [m_b]
        idx = self._indexes(issue=[_rec("m_a", "issue"), _rec("m_b", "issue")])
        rm = _resolved([_res_entry("m_a")])
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertFalse(rep["cross_check"]["matches"])
        self.assertEqual(rep["cross_check"]["only_scout"], ["m_b"])
        self.assertEqual(rep["cross_check"]["only_publisher"], [])

    def test_only_publisher_divergence(self):
        idx = self._indexes(issue=[_rec("m_a", "issue")])
        rm = _resolved([_res_entry("m_a"), _res_entry("m_z")])
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertEqual(rep["cross_check"]["only_publisher"], ["m_z"])

    def test_file_revision_mismatch(self):
        idx = self._indexes(issue=[_rec("m_a", "issue", revision="rev_1")])
        rm = _resolved([_res_entry("m_a", revision="rev_2")])   # same id, different file revision
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertFalse(rep["cross_check"]["matches"])
        self.assertEqual(rep["cross_check"]["file_revision_mismatches"], ["m_a"])

    def test_version_skew_abstains_match(self):
        idx = self._indexes(issue=[_rec("m_a", "issue")])
        rm = _resolved([_res_entry("m_a")], cver="v2")   # resolved snapshot on a different contract version
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertTrue(rep["version_skew"])
        self.assertFalse(rep["cross_check"]["matches"])

    def test_unsupported_contract_version_fail_fast(self):
        rep = mra.compute_resolution_audit({}, _resolved([]), {"resolution_contract_version": "v9"})
        self.assertFalse(rep["applicable"])
        self.assertEqual(rep["reason"], "unsupported_resolution_contract_version")


class TestAuthoringInvariants(unittest.TestCase):
    def _run(self, records):
        idx = {"issue": _index("issue", records)}
        return mra.compute_resolution_audit(idx, _resolved([]), CONTRACT)["authoring_findings"]

    def test_dangling_supersedes(self):
        f = self._run([_rec("m_new", "issue", supersedes="m_ghost")])
        self.assertTrue(any(x["code"] == "materials.dangling_supersedes" for x in f))

    def test_multiple_active_approved_per_lineage(self):
        # m_new supersedes m_old, but BOTH are publisher_approved -> FAIL
        f = self._run([_rec("m_old", "issue", status="publisher_approved"),
                       _rec("m_new", "issue", status="publisher_approved", supersedes="m_old")])
        codes = [x["code"] for x in f]
        self.assertIn("materials.multiple_active_approved", codes)
        self.assertIn("materials.superseded_still_approved", codes)

    def test_clean_lineage_no_findings(self):
        f = self._run([_rec("m_old", "issue", status="superseded"),
                       _rec("m_new", "issue", status="publisher_approved", supersedes="m_old")])
        self.assertEqual(f, [])


class TestGovernanceAndDeterminism(unittest.TestCase):
    def test_identifiers_only_no_material_text(self):
        idx = {"issue": _index("issue", [_rec("m_a", "issue")])}
        rep = mra.compute_resolution_audit(idx, _resolved([_res_entry("m_a")]), CONTRACT)
        blob = json.dumps(rep, ensure_ascii=False)
        # titles are the only text-ish field on a record; confirm the audit never copies record `title`/files bytes
        self.assertNotIn("style_guide_body", blob)   # no material content vector exists
        self.assertNotIn("\"files\"", blob)            # audit surfaces ids, not file objects

    def test_deterministic(self):
        idx = {"issue": _index("issue", [_rec("m_b", "issue"), _rec("m_a", "issue")]),
               "series": _index("series", [_rec("m_c", "series")])}
        rm = _resolved([_res_entry("m_a"), _res_entry("m_c", scope_level="series")])
        a = json.dumps(mra.compute_resolution_audit(idx, rm, CONTRACT), sort_keys=True)
        b = json.dumps(mra.compute_resolution_audit(idx, rm, CONTRACT), sort_keys=True)
        self.assertEqual(a, b)

    def test_missing_file_id_does_not_crash(self):
        # Review #1: a multi-file record with one missing file_id must not crash the sorted() in the key.
        rec = _rec("m_a", "issue")
        rec["files"].append({"role": "secondary", "artifact_ref": {"revision": "rev_2"}})  # no file_id
        idx = {"issue": {"records": [rec]}}
        rep = mra.compute_resolution_audit(idx, _resolved([_res_entry("m_a")]), CONTRACT)  # must not raise
        self.assertTrue(rep["applicable"])

    def test_shadowed_supersedes_edge_still_applied(self):
        # Review #3: a supersedes edge on a collision-shadowed record is still honored (collected from all
        # eligible records), so authoring and resolved layers don't contradict.
        recs = [_rec("m_x", "issue"),                                   # narrower m_x wins the collision
                _rec("m_x", "series", supersedes="m_y"),               # shadowed, but its edge must apply
                _rec("m_y", "issue", status="publisher_approved")]
        eff = [r["material_id"] for r in mra.resolve_effective_materials(recs)]
        self.assertNotIn("m_y", eff)                                   # m_y superseded, not in effective set

    def test_version_skew_blanks_divergence_lists(self):
        idx = {"issue": _index("issue", [_rec("m_a", "issue")])}
        rm = _resolved([_res_entry("m_z")], cver="v2")   # different id AND different version
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertTrue(rep["version_skew"])
        cc = rep["cross_check"]
        self.assertEqual(cc["only_scout"], [])           # not a meaningless cross-version delta
        self.assertEqual(cc["only_publisher"], [])
        self.assertFalse(cc["matches"])

    def test_duplicate_resolved_id_flagged_deterministically(self):
        idx = {"issue": _index("issue", [_rec("m_a", "issue")])}
        rm = _resolved([_res_entry("m_a", revision="rev_1"), _res_entry("m_a", revision="rev_2")])
        rep = mra.compute_resolution_audit(idx, rm, CONTRACT)
        self.assertEqual(rep["cross_check"]["duplicate_resolved_ids"], ["m_a"])
        self.assertFalse(rep["cross_check"]["matches"])   # a dup id is a divergence, not silently deduped

    def test_tolerant_index_wrapper(self):
        # accepts records under 'materials' as well as 'records'
        idx = {"issue": {"materials": [_rec("m_a", "issue")]}}
        rep = mra.compute_resolution_audit(idx, _resolved([_res_entry("m_a")]), CONTRACT)
        self.assertTrue(rep["cross_check"]["matches"])


if __name__ == "__main__":
    unittest.main()
