"""Tests for scout_registry (Phase 2 · Increment 1 — behavior-neutral Registry model).

The Registry is a pure, derived projection: flat hierarchy-keyed entries (D6) with rollup/tree VIEWS,
built from supplied facts (no I/O). These tests pin the entry shape, the flat keying + idempotent
rebuild, the context seam, the rollup/tree views, and the fact/observation separation. Nothing in
production consumes the Registry yet.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_registry as reg  # noqa: E402
import scout_context as sc  # noqa: E402

PUB = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues"
P1 = f"{PUB}/issue_001"
P2 = f"{PUB}/issue_002"
IDENT1 = {"publisher_id": "edenseek", "title_group_id": "society_universe",
          "series_id": "society_of_killers", "issue_id": "issue_001"}
IDENT2 = {**IDENT1, "issue_id": "issue_002"}


class BuildEntryTest(unittest.TestCase):
    def test_flat_entry_shape_and_identity(self):
        e = reg.build_entry(issue_prefix=P1, identity=IDENT1,
                            published_revision_id="rev_x", review_id="rev_x"[:12],
                            publication_state="edenseek_approved", resolved_at="t0")
        self.assertEqual(e["issue_prefix"], P1)
        for k, v in IDENT1.items():
            self.assertEqual(e[k], v)
        self.assertEqual(e["publication"], {"published_revision_id": "rev_x",
                                            "review_id": "rev_x"[:12], "state": "edenseek_approved"})
        self.assertEqual(e["resolved_at"], "t0")

    def test_defaults_are_fact_free_and_unprocessed(self):
        e = reg.build_entry(issue_prefix=P1, identity=IDENT1)
        self.assertEqual(e["publication"]["state"], reg.STATE_UNKNOWN)
        self.assertIsNone(e["publication"]["published_revision_id"])
        self.assertEqual(e["audit"]["audit_state"], reg.AUDIT_UNPROCESSED)
        self.assertIsNone(e["audit"]["run_seq"])

    def test_audit_observation_recorded_separately(self):
        audit = {"audit_state": reg.AUDIT_AUDITED, "run_seq": 3, "run_id": "run_abc",
                 "report_id": "scoutdelta::issue_001::rev::run000003"}
        e = reg.build_entry(issue_prefix=P1, identity=IDENT1, audit=audit)
        self.assertEqual(e["audit"], audit)
        # the passed audit dict is copied, not aliased
        audit["run_seq"] = 999
        self.assertEqual(e["audit"]["run_seq"], 3)

    def test_entry_from_context_uses_context_identity_and_prefix(self):
        ctx = sc.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=P1 + "/approved",
            scout_bucket="edenseek-scout", scout_prefix=P1)
        e = reg.entry_from_context(ctx, published_revision_id="rev_ctx",
                                   publication_state="edenseek_approved")
        self.assertEqual(e["issue_prefix"], P1)
        self.assertEqual({k: e[k] for k in IDENT1}, IDENT1)
        self.assertEqual(e["publication"]["published_revision_id"], "rev_ctx")


class BuildRegistryTest(unittest.TestCase):
    def _reg(self):
        return reg.build_registry(
            [reg.build_entry(issue_prefix=P1, identity=IDENT1, publication_state="edenseek_approved"),
             reg.build_entry(issue_prefix=P2, identity=IDENT2)],
            generated_at="t1")

    def test_flat_keyed_projection(self):
        r = self._reg()
        self.assertEqual(r["registry_version"], reg.REGISTRY_VERSION)
        self.assertEqual(r["generated_at"], "t1")
        self.assertEqual(r["count"], 2)
        self.assertEqual(set(r["entries"].keys()), {P1, P2})

    def test_rebuild_is_idempotent_by_key(self):
        # the same issue seen twice -> one entry (a re-scan converges), last one wins
        e_old = reg.build_entry(issue_prefix=P1, identity=IDENT1, published_revision_id="rev_old")
        e_new = reg.build_entry(issue_prefix=P1, identity=IDENT1, published_revision_id="rev_new")
        r = reg.build_registry([e_old, e_new])
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["entries"][P1]["publication"]["published_revision_id"], "rev_new")

    def test_get(self):
        r = self._reg()
        self.assertEqual(reg.get(r, P1)["issue_id"], "issue_001")
        self.assertIsNone(reg.get(r, "publishers/none/issues/none"))


class ViewsTest(unittest.TestCase):
    def _reg(self):
        return reg.build_registry([
            reg.build_entry(issue_prefix=P1, identity=IDENT1),
            reg.build_entry(issue_prefix=P2, identity=IDENT2),
        ])

    def test_rollup_by_series_groups_both_issues(self):
        v = reg.rollup(self._reg(), "series_id")
        self.assertEqual(v["level"], "series_id")
        self.assertEqual(v["group_count"], 1)                     # one series
        self.assertEqual(sorted(v["groups"]["society_of_killers"]), sorted([P1, P2]))
        self.assertEqual(v["issue_count"], 2)

    def test_rollup_by_publisher(self):
        v = reg.rollup(self._reg(), "publisher_id")
        self.assertEqual(v["groups"]["edenseek"], [P1, P2])

    def test_rollup_rejects_issue_leaf_and_bad_level(self):
        with self.assertRaises(ValueError):
            reg.rollup(self._reg(), "issue_id")
        with self.assertRaises(ValueError):
            reg.rollup(self._reg(), "nope")

    def test_tree_view_is_a_view_over_flat_entries(self):
        tree = reg.tree_view(self._reg())
        issues = tree["edenseek"]["title_groups"]["society_universe"]["series"]["society_of_killers"]["issues"]
        self.assertEqual(issues, {"issue_001": P1, "issue_002": P2})

    def test_tree_of_one(self):
        r = reg.build_registry([reg.build_entry(issue_prefix=P1, identity=IDENT1)])
        tree = reg.tree_view(r)
        self.assertEqual(list(tree.keys()), ["edenseek"])
        self.assertEqual(
            list(tree["edenseek"]["title_groups"]["society_universe"]["series"]
                 ["society_of_killers"]["issues"]),
            ["issue_001"])


if __name__ == "__main__":
    unittest.main()
