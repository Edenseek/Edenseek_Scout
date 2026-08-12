"""Tests for scout_discovery (Phase 2 · Increment 5b — publisher-wide Discovery, read-only).

Discovery enumerates auditable issues (those with an ``approved/published.json`` marker) in the
Publisher bucket and produces one IssueContext each, using the shared bucket+region config. It derives
no state and persists nothing; correctness comes from the certified resolve/rebuild pipeline. These
tests pin enumeration, context production, config fail-loud, malformed-prefix skipping, read-only
behavior, and — the point of Discovery — feeding the certified rebuild to produce a publisher-wide
Registry.
"""
import io
import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_discovery as disc  # noqa: E402
import scout_context as sc  # noqa: E402
import scout_registry as reg  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

PUB = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues"
I1, I2 = f"{PUB}/issue_001", f"{PUB}/issue_002"
REV1, REV2 = "rev_" + "1" * 64, "rev_" + "2" * 64
RID1, RID2 = "rev_" + "1" * 12, "rev_" + "2" * 12
ENV = {sc.APPROVED_BUCKET_ENV: "edenseek-publishing", sc.SCOUT_BUCKET_ENV: "edenseek-scout",
       sc.APPROVED_REGION_ENV: "us-west-2", sc.SCOUT_REGION_ENV: "us-west-2"}


class FakeS3:
    def __init__(self, store=None):
        self.store = dict(store or {})
        self.puts = []

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.puts.append((Bucket, Key))
        self.store[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.encode()
        return {"VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


class TestContextForPrefix(unittest.TestCase):
    """SXI-2a: reconstruct a single issue's context from its prefix WITHOUT re-listing S3."""

    def test_reconstructs_identity_and_prefixes(self):
        ctx = disc.context_for_prefix(I1, env=ENV)
        self.assertEqual(ctx.scout_prefix, I1)
        self.assertEqual(ctx.approved_prefix, f"{I1}/approved")
        self.assertEqual((ctx.publisher_id, ctx.title_group_id, ctx.series_id, ctx.issue_id),
                         ("edenseek", "society_universe", "society_of_killers", "issue_001"))
        self.assertEqual((ctx.approved_bucket, ctx.scout_bucket),
                         ("edenseek-publishing", "edenseek-scout"))

    def test_equals_discover_contexts_construction(self):
        # The reconstructed context must be identical to the one Discovery builds for that prefix,
        # so scoping a read to a prefix reads exactly the surface Discovery/Registry would.
        s3 = FakeS3({("edenseek-publishing", f"{I1}/approved/published.json"): b"{}"})
        [dctx] = disc.discover_contexts(client=s3, env=ENV)
        rctx = disc.context_for_prefix(dctx.scout_prefix, env=ENV)
        self.assertEqual(rctx.identity, dctx.identity)
        self.assertEqual((rctx.scout_bucket, rctx.scout_prefix, rctx.approved_bucket, rctx.approved_prefix),
                         (dctx.scout_bucket, dctx.scout_prefix, dctx.approved_bucket, dctx.approved_prefix))

    def test_malformed_prefix_raises_context_error(self):
        with self.assertRaises(sc.IssueContextError):
            disc.context_for_prefix("publishers/edenseek/title_groups/tg/series/s", env=ENV)  # no issue

    def test_unconfigured_raises_discovery_error(self):
        with self.assertRaises(disc.ScoutDiscoveryError):
            disc.context_for_prefix(I1, env={})


def _pointer(rev):
    return json.dumps({"published_pointer_version": "v1", "revision_id": rev,
                       "revision_key": f"x/{rev}/snap.json"}).encode()


def _pa(state="edenseek_approved"):
    return json.dumps({"platform_approval_version": "v1", "canonical_dataset_state": state}).encode()


def _index(rev, run_seq):
    e = {"published_revision_id": rev, "run_seq": run_seq, "run_id": f"run_{run_seq}",
         "report_id": f"rep{run_seq}"}
    return json.dumps({"report_index_version": "v1", "count": 1,
                       "latest": {"run_seq": run_seq}, "entries": [e]}).encode()


def _markers_only():
    # two auditable issues + a non-marker object (ignored)
    return FakeS3({
        ("edenseek-publishing", f"{I1}/approved/published.json"): _pointer(REV1),
        ("edenseek-publishing", f"{I2}/approved/published.json"): _pointer(REV2),
        ("edenseek-publishing", f"{I1}/approved/approved_dataset.json"): b"[]",  # not a marker
    })


def _full_store():
    return FakeS3({
        ("edenseek-publishing", f"{I1}/approved/published.json"): _pointer(REV1),
        ("edenseek-publishing", f"{I2}/approved/published.json"): _pointer(REV2),
        ("edenseek-publishing", f"{I1}/reviews/{RID1}/platform_approval.json"): _pa(),
        ("edenseek-publishing", f"{I2}/reviews/{RID2}/platform_approval.json"): _pa(),
        ("edenseek-scout", f"{I1}/reports/report_index.json"): _index(REV1, 1),
        ("edenseek-scout", f"{I2}/reports/report_index.json"): _index(REV2, 1),
    })


class EnumerationTest(unittest.TestCase):
    def test_discover_issue_prefixes_finds_published_issues(self):
        prefixes = disc.discover_issue_prefixes(_markers_only(), "edenseek-publishing")
        self.assertEqual(prefixes, sorted([I1, I2]))

    def test_empty_when_no_markers(self):
        self.assertEqual(disc.discover_issue_prefixes(FakeS3(), "edenseek-publishing"), [])


class ContextsTest(unittest.TestCase):
    def test_discover_contexts_builds_one_per_issue(self):
        contexts = disc.discover_contexts(client=_markers_only(), env=ENV)
        self.assertEqual([c.issue_id for c in contexts], ["issue_001", "issue_002"])
        c1 = contexts[0]
        self.assertEqual(c1.approved_bucket, "edenseek-publishing")
        self.assertEqual(c1.approved_prefix, f"{I1}/approved")
        self.assertEqual(c1.scout_bucket, "edenseek-scout")
        self.assertEqual(c1.scout_prefix, I1)
        self.assertEqual(c1.publisher_id, "edenseek")

    def test_config_missing_fails_loud(self):
        with self.assertRaises(disc.ScoutDiscoveryError):
            disc.discover_contexts(client=_markers_only(), env={})

    def test_malformed_prefix_is_skipped(self):
        s3 = _markers_only()
        s3.store[("edenseek-publishing", "publishers/rogue/approved/published.json")] = _pointer(REV1)
        contexts = disc.discover_contexts(client=s3, env=ENV)
        self.assertEqual([c.issue_id for c in contexts], ["issue_001", "issue_002"])  # rogue skipped

    def test_discovery_is_read_only(self):
        s3 = _markers_only()
        disc.discover_contexts(client=s3, env=ENV)
        self.assertEqual(s3.puts, [])  # enumeration writes nothing


class FeedsRebuildTest(unittest.TestCase):
    """Discovery feeding the certified rebuild pipeline -> publisher-wide Registry (tree-of-two)."""

    def test_discover_then_rebuild_registry(self):
        s3 = _full_store()
        contexts = disc.discover_contexts(client=s3, env=ENV)
        reg.rebuild_registry(contexts, client=s3, generated_at="t1")   # certified resolve+persist
        registry = reg.load_registry(client=s3, context=contexts[0])
        self.assertEqual(registry["count"], 2)
        self.assertEqual(set(registry["entries"]), {I1, I2})
        # correctness derived by the certified pipeline, per issue
        self.assertEqual(registry["entries"][I1]["publication"]["published_revision_id"], REV1)
        self.assertEqual(registry["entries"][I1]["publication"]["state"], "edenseek_approved")
        self.assertEqual(registry["entries"][I1]["audit"]["audit_state"], reg.AUDIT_AUDITED)
        self.assertEqual(registry["entries"][I2]["publication"]["published_revision_id"], REV2)
        # the tree view now has two issues under the one series (D6 rollup view)
        issues = reg.tree_view(registry)["edenseek"]["title_groups"]["society_universe"]["series"][
            "society_of_killers"]["issues"]
        self.assertEqual(set(issues), {"issue_001", "issue_002"})
        # only the Registry object was written to the Scout bucket (resolution was read-only)
        self.assertEqual([k for (b, k) in s3.puts], ["registry/registry.json"])
        self.assertTrue(all(b == "edenseek-scout" for (b, _k) in s3.puts))


class RebuildDiscoveredTest(unittest.TestCase):
    """The governed publisher-wide one-shot: scout_registry.rebuild_discovered (Discovery -> rebuild)."""

    def test_rebuild_discovered_publisher_wide(self):
        s3 = _full_store()
        with mock.patch.dict(os.environ, ENV, clear=True):
            out = reg.rebuild_discovered(client=s3, generated_at="t1")
            registry = reg.load_registry(client=s3)             # env target (scout bucket)
        self.assertEqual(out["discovered"], 2)
        self.assertEqual(out["count"], 2)
        self.assertEqual(set(registry["entries"]), {I1, I2})
        # every entry's truth derived by the certified pipeline
        self.assertEqual(registry["entries"][I1]["publication"]["published_revision_id"], REV1)
        self.assertEqual(registry["entries"][I1]["audit"]["audit_state"], reg.AUDIT_AUDITED)
        self.assertEqual(registry["entries"][I2]["publication"]["state"], "edenseek_approved")
        # single write: the Registry object only (resolution read-only)
        self.assertEqual([k for (b, k) in s3.puts], ["registry/registry.json"])

    def test_rebuild_discovered_empty_when_no_issues(self):
        s3 = FakeS3()  # no published markers
        with mock.patch.dict(os.environ, ENV, clear=True):
            out = reg.rebuild_discovered(client=s3, generated_at="t1")
        self.assertEqual(out["discovered"], 0)
        self.assertEqual(out["count"], 0)


if __name__ == "__main__":
    unittest.main()
