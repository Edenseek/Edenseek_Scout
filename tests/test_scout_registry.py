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

import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from unittest import mock  # noqa: E402
import scout_registry as reg  # noqa: E402
import scout_context as sc  # noqa: E402
import scout_report_publisher as srp  # noqa: E402
import scout_revision_ledger as srl  # noqa: E402
import audit_review  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

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


REVISION_ID = "rev_0be8dc342ab3aaaaaaaaaaaa"
REVIEW_ID = "rev_0be8dc342ab3"  # == audit_review._derive_review_id(REVISION_ID); drift-guarded below


class _RegFakeS3:
    """Minimal read-only in-memory S3: get_object over a {(bucket,key): bytes} store."""
    def __init__(self, store=None):
        self.store = dict(store or {})

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.store[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.encode()
        return {"VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


def _ctx():
    return sc.IssueContext.for_prefixes(
        approved_bucket="edenseek-publishing", approved_prefix=P1 + "/approved",
        scout_bucket="edenseek-scout", scout_prefix=P1)


def _pointer_bytes():
    return json.dumps({"published_pointer_version": "v1", "revision_id": REVISION_ID,
                       "revision_key": f"{P1}/processing/workspace/{REVISION_ID}/snap.json"}).encode()


def _pa_bytes(state="edenseek_approved"):
    return json.dumps({"platform_approval_version": "v1", "canonical_dataset_state": state}).encode()


def _index_bytes(entries):
    return json.dumps({"report_index_version": "v1", "issue_prefix": P1,
                       "latest": {"run_seq": entries[-1]["run_seq"]} if entries else {},
                       "count": len(entries), "entries": entries}).encode()


class ResolveTest(unittest.TestCase):
    def test_review_id_matches_audit_review(self):  # drift guard
        self.assertEqual(reg._resolve_review_id(REVISION_ID),
                         audit_review._derive_review_id(REVISION_ID))
        self.assertEqual(reg._resolve_review_id(REVISION_ID), REVIEW_ID)

    def _full_store(self):
        entry = {"published_revision_id": REVISION_ID, "run_seq": 3, "run_id": "run_x",
                 "report_id": "scoutdelta::issue_001::rev::run000003"}
        return {
            ("edenseek-publishing", f"{P1}/approved/published.json"): _pointer_bytes(),
            ("edenseek-publishing", f"{P1}/reviews/{REVIEW_ID}/platform_approval.json"): _pa_bytes(),
            ("edenseek-scout", f"{P1}/reports/report_index.json"): _index_bytes([entry]),
        }

    def test_resolve_entry_full_authoritative(self):
        e = reg.resolve_entry(_ctx(), client=_RegFakeS3(self._full_store()), resolved_at="t0")
        self.assertEqual(e["issue_prefix"], P1)
        self.assertEqual(e["publication"]["published_revision_id"], REVISION_ID)
        self.assertEqual(e["publication"]["review_id"], REVIEW_ID)
        self.assertEqual(e["publication"]["state"], "edenseek_approved")  # verbatim Publisher fact
        self.assertEqual(e["audit"], {"audit_state": reg.AUDIT_AUDITED, "run_seq": 3,
                                      "run_id": "run_x",
                                      "report_id": "scoutdelta::issue_001::rev::run000003"})
        self.assertEqual(e["resolved_at"], "t0")

    def test_missing_platform_approval_is_creator_approved(self):
        store = self._full_store()
        del store[("edenseek-publishing", f"{P1}/reviews/{REVIEW_ID}/platform_approval.json")]
        e = reg.resolve_entry(_ctx(), client=_RegFakeS3(store))
        self.assertEqual(e["publication"]["state"], reg.STATE_CREATOR_APPROVED)

    def test_audit_unprocessed_when_no_index_entry(self):
        store = {k: v for k, v in self._full_store().items()
                 if k != ("edenseek-scout", f"{P1}/reports/report_index.json")}
        e = reg.resolve_entry(_ctx(), client=_RegFakeS3(store))
        self.assertEqual(e["audit"]["audit_state"], reg.AUDIT_UNPROCESSED)

    def test_audit_failed_from_ledger(self):
        store = {k: v for k, v in self._full_store().items()
                 if k != ("edenseek-scout", f"{P1}/reports/report_index.json")}
        store[("edenseek-scout", f"{P1}/reports/report_index.json")] = _index_bytes([])
        store[("edenseek-scout", f"{P1}/ledger/processed_revisions.json")] = json.dumps(
            {"entries": {"k": {"revision_id": REVISION_ID, "status": srl.STATUS_FAILED,
                               "run_seq": None, "run_id": None, "report_id": None}}}).encode()
        e = reg.resolve_entry(_ctx(), client=_RegFakeS3(store))
        self.assertEqual(e["audit"]["audit_state"], reg.AUDIT_FAILED)

    def test_unpublished_when_no_pointer(self):
        e = reg.resolve_entry(_ctx(), client=_RegFakeS3({}))  # no published.json
        self.assertIsNone(e["publication"]["published_revision_id"])
        self.assertEqual(e["publication"]["state"], reg.STATE_UNKNOWN)
        self.assertEqual(e["audit"]["audit_state"], reg.AUDIT_UNPROCESSED)
        self.assertEqual(e["issue_prefix"], P1)  # still a tree-of-one entry

    def test_resolve_registry_flat_tree_of_one(self):
        r = reg.resolve_registry([_ctx()], client=_RegFakeS3(self._full_store()), generated_at="t1")
        self.assertEqual(r["count"], 1)
        self.assertIn(P1, r["entries"])
        self.assertEqual(r["entries"][P1]["publication"]["state"], "edenseek_approved")


class PersistTest(unittest.TestCase):
    REGISTRY_KEY = ("edenseek-scout", "registry/registry.json")

    def _registry(self):
        return reg.build_registry(
            [reg.build_entry(issue_prefix=P1, identity=IDENT1, publication_state="edenseek_approved")],
            generated_at="t1")

    def test_persist_and_load_roundtrip(self):
        s3 = _RegFakeS3()
        registry = self._registry()
        out = reg.persist_registry(registry, client=s3, context=_ctx())
        self.assertEqual(out["key"], "registry/registry.json")
        self.assertEqual(out["count"], 1)
        self.assertIn(self.REGISTRY_KEY, s3.store)
        self.assertEqual(reg.load_registry(client=s3, context=_ctx()), registry)  # byte-faithful roundtrip

    def test_load_absent_returns_empty_registry(self):
        empty = reg.load_registry(client=_RegFakeS3(), context=_ctx())
        self.assertEqual(empty["count"], 0)
        self.assertEqual(empty["entries"], {})
        self.assertEqual(empty["registry_version"], reg.REGISTRY_VERSION)

    def test_rebuild_registry_end_to_end(self):
        # seed authoritative sources so resolve produces a real entry, then rebuild persists it.
        store = {
            ("edenseek-publishing", f"{P1}/approved/published.json"): _pointer_bytes(),
            ("edenseek-publishing", f"{P1}/reviews/{REVIEW_ID}/platform_approval.json"): _pa_bytes(),
            ("edenseek-scout", f"{P1}/reports/report_index.json"): _index_bytes(
                [{"published_revision_id": REVISION_ID, "run_seq": 3, "run_id": "run_x",
                  "report_id": "rep3"}]),
        }
        s3 = _RegFakeS3(store)
        reg.rebuild_registry([_ctx()], client=s3, generated_at="t1")
        loaded = reg.load_registry(client=s3, context=_ctx())
        self.assertEqual(loaded["count"], 1)
        e = loaded["entries"][P1]
        self.assertEqual(e["publication"]["published_revision_id"], REVISION_ID)
        self.assertEqual(e["publication"]["state"], "edenseek_approved")
        self.assertEqual(e["audit"]["audit_state"], reg.AUDIT_AUDITED)

    def test_persist_writes_only_scout_bucket(self):
        s3 = _RegFakeS3()
        reg.persist_registry(self._registry(), client=s3, context=_ctx())
        self.assertTrue(all(bkt == "edenseek-scout" for (bkt, _k) in s3.store))
        self.assertEqual(set(s3.store), {self.REGISTRY_KEY})

    def test_persist_context_equals_env(self):
        registry = self._registry()
        a = _RegFakeS3()
        with mock.patch.dict(os.environ, {srp.BUCKET_ENV: "edenseek-scout",
                                          srp.REGION_ENV: "us-west-2"}, clear=False):
            reg.persist_registry(registry, client=a)                       # env target
        b = _RegFakeS3()
        with mock.patch.dict(os.environ, {}, clear=True):                  # env cleared
            reg.persist_registry(registry, client=b, context=_ctx())       # context target
        self.assertEqual(a.store, b.store)  # byte-identical object at the same key


if __name__ == "__main__":
    unittest.main()
