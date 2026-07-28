"""Tests for the Scout report index + comparability contract + delta-report persistence.

In-memory S3 fake (no network). Covers the comparability key/diff, the report projection, the
persist+index transaction, index rebuild from history, pure query filters, and metric-series
comparability boundaries.
"""
import io
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_report_publisher as srp  # noqa: E402
import scout_report_index as sri  # noqa: E402
import scout_delta_audit  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

REPO_PREFIX = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001"
IDENT = {"publisher_id": "edenseek", "title_group_id": "society_universe",
         "series_id": "society_of_killers", "issue_id": "issue_001"}


class FakeS3:
    """Minimal in-memory S3: put/get/list over a dict, with monotonic VersionIds."""
    def __init__(self):
        self.store = {}
        self._v = 0

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self._v += 1
        self.store[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.encode()
        return {"VersionId": f"v{self._v}"}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)]), "VersionId": "v"}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in sorted(keys)], "IsTruncated": False}


def _env():
    return {srp.BUCKET_ENV: "edenseek-scout", srp.PREFIX_ENV: REPO_PREFIX,
            srp.REGION_ENV: "us-west-2"}


def _view(precision=0.9, recall=0.6, meta_status="abstained", rr="v1", pa="v1", gs=None,
          published="rev_pub_aaaa", generated="rev_gen_bbbb"):
    """A synthetic build_audit_review() view."""
    return {
        "audit_timestamp": "2026-07-28T12:00:00Z",
        "publisher_commit": published, "scout_commit": "scoutsha1",
        "review_id": "rev_pub_aaaa"[:12],
        "evidence": {"issue_identity": IDENT, "summary": {"objects_loaded": 4, "audit_ready": True},
                     "objects": [{"role": "review_report", "key": "…/review_report.json",
                                  "status": "read", "size": 10, "sha256": "h", "schema_version": rr,
                                  "revision_id": "rev"}]},
        "findings": [{"code": "evidence.loaded", "severity": "PASS", "title": "x", "detail": "y"},
                     {"code": "metadata.comparability", "severity": "WARNING", "title": "x", "detail": "y"},
                     {"code": "geometry.false_panels", "severity": "WARNING", "title": "x", "detail": "y"}],
        "delta_summary": {
            "geometry": {"status": "computed", "precision": precision, "recall": recall,
                         "split_rate": 0.5, "merge_rate": 0.9, "missing": 4, "spread_missing": 34, "false": 3},
            "metadata": {"status": meta_status, "compared": (0 if meta_status == "abstained" else 5)},
        },
        "delta_report": {
            "review_id": "rev_pub_aaaa"[:12], "applicability": "generated_publication",
            "provenance": {"published_revision_id": published, "generated_snapshot_revision_id": generated,
                           "source_versions": {"review_report_version": rr,
                                               "platform_approval_version": pa,
                                               "generated_snapshot_version": gs}},
            "geometry_delta": {"applicable": True}, "metadata_delta": {"applicable": True},
            "correction_ledger": [], "publisher_certified_state": {"canonical_dataset_state": "edenseek_approved"},
        },
        "delta_report_sha256": "deadbeef",
    }


class TestComparability(unittest.TestCase):
    def test_key_stable_and_diff(self):
        a = {"report_version": "v1", "algorithm_version": "v1", "schema_version": "rr:v1|pa:v1|gs:-",
             "evaluation_version": "v1"}
        b = dict(a, algorithm_version="v2")
        self.assertEqual(sri.comparability_key(a), sri.comparability_key(a))
        self.assertNotEqual(sri.comparability_key(a), sri.comparability_key(b))
        self.assertEqual(sri.comparability_diff(a, b), ["algorithm_version"])
        self.assertEqual(sri.comparability_diff(a, a), [])


class TestPersistAndIndex(unittest.TestCase):
    def _run(self, client, view):
        with mock.patch.dict("os.environ", _env(), clear=False), \
                mock.patch.object(scout_delta_audit.audit_review, "build_audit_review", return_value=view):
            return scout_delta_audit.run_and_persist(client=client)

    def test_transaction_persists_report_and_updates_index(self):
        s3, view = FakeS3(), _view()
        res = self._run(s3, view)
        self.assertEqual(res["status"], "persisted")
        self.assertEqual(res["run_seq"], 1)
        # report persisted at both R1 keys, and the latest bytes hash matches the reported sha
        latest_key = f"{REPO_PREFIX}/reports/scout_delta_report.json"
        hist_key = f"{REPO_PREFIX}/history/scout_delta_report_000001.json"
        self.assertIn(("edenseek-scout", latest_key), s3.store)
        self.assertIn(("edenseek-scout", hist_key), s3.store)
        import hashlib
        self.assertEqual(hashlib.sha256(s3.store[("edenseek-scout", latest_key)]).hexdigest(),
                         res["report_sha256"])
        # index updated with one entry + latest pointer + searchable metadata
        with mock.patch.dict("os.environ", _env(), clear=False):
            idx = sri.load_index(s3)
        self.assertEqual(idx["count"], 1)
        self.assertEqual(idx["latest"]["run_seq"], 1)
        e = idx["entries"][0]
        self.assertEqual(e["issue_id"], "issue_001")
        self.assertEqual(e["publisher_id"], "edenseek")
        self.assertEqual(e["metrics"]["precision"], 0.9)
        self.assertEqual(e["schema_version"], "rr:v1|pa:v1|gs:-")
        self.assertEqual(e["finding_counts"], {"PASS": 1, "WARNING": 2, "FAIL": 0, "INFO": 0})
        self.assertEqual(e["worst_severity"], "WARNING")
        # per-task comparability keys + a deterministic logical run id
        self.assertTrue(e["geometry_comparability_key"].startswith("cmp_"))
        self.assertTrue(e["metadata_comparability_key"].startswith("cmp_"))
        self.assertNotEqual(e["geometry_comparability_key"], e["metadata_comparability_key"])
        self.assertTrue(e["run_id"].startswith("run_"))
        self.assertEqual(res["run_id"], e["run_id"])

    def test_newest_first_and_rebuild_matches(self):
        s3 = FakeS3()
        self._run(s3, _view(precision=0.9, published="rev_pub_1"))
        self._run(s3, _view(precision=0.8, published="rev_pub_2"))  # distinct publication -> run_seq 2
        with mock.patch.dict("os.environ", _env(), clear=False):
            idx = sri.load_index(s3)
            self.assertEqual([e["run_seq"] for e in idx["entries"]], [2, 1])  # newest first
            self.assertEqual(idx["latest"]["run_seq"], 2)
            rebuilt = sri.rebuild_index(s3)
        self.assertEqual([e["run_seq"] for e in rebuilt["entries"]], [2, 1])
        self.assertEqual(rebuilt["count"], 2)

    def test_retry_same_publication_is_idempotent(self):
        """Re-running the same publication under the same methodology must not create a duplicate
        logical run: same run_id, one history report, index count stays 1."""
        s3 = FakeS3()
        first = self._run(s3, _view(published="rev_pub_x"))
        second = self._run(s3, _view(precision=0.5, published="rev_pub_x"))  # retry, different metric
        self.assertEqual(first["status"], "persisted")
        self.assertEqual(second["status"], "reconciled")
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["run_seq"], 1)              # no new run_seq
        with mock.patch.dict("os.environ", _env(), clear=False):
            self.assertEqual(sri.load_index(s3)["count"], 1)
        # only one immutable history snapshot exists
        hist = [k for (b, k) in s3.store if "/history/scout_delta_report_" in k]
        self.assertEqual(len(hist), 1)

    def test_dry_run_writes_nothing(self):
        s3, view = FakeS3(), _view()
        with mock.patch.dict("os.environ", _env(), clear=False), \
                mock.patch.object(scout_delta_audit.audit_review, "build_audit_review", return_value=view):
            res = scout_delta_audit.run_and_persist(client=s3, dry_run=True)
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(s3.store, {})
        self.assertEqual(res["report_body"]["algorithm_version"], "v1")


class TestQueryAndSeries(unittest.TestCase):
    def _index(self, s3):
        with mock.patch.dict("os.environ", _env(), clear=False):
            return sri.load_index(s3)

    def _run(self, s3, view):
        with mock.patch.dict("os.environ", _env(), clear=False), \
                mock.patch.object(scout_delta_audit.audit_review, "build_audit_review", return_value=view):
            return scout_delta_audit.run_and_persist(client=s3)

    def test_query_filters(self):
        s3 = FakeS3()
        self._run(s3, _view(precision=0.95, published="rev_A"))
        self._run(s3, _view(precision=0.60, published="rev_B"))
        idx = self._index(s3)
        # numeric metric range
        self.assertEqual([e["run_seq"] for e in sri.query_index(idx, {"precision_min": 0.9})], [1])
        # revision match (approved side)
        self.assertEqual([e["run_seq"] for e in sri.query_index(idx, {"revision": "rev_B"})], [2])
        # severity presence + finding code
        self.assertEqual(len(sri.query_index(idx, {"severity": "WARNING"})), 2)
        self.assertEqual(len(sri.query_index(idx, {"finding_code": "geometry.false_panels"})), 2)
        self.assertEqual(sri.query_index(idx, {"finding_code": "nope"}), [])
        # commit substring
        self.assertEqual(len(sri.query_index(idx, {"commit": "scoutsha1"})), 2)

    def test_metric_series_marks_comparability_boundary(self):
        s3 = FakeS3()
        self._run(s3, _view(precision=0.9))                      # algorithm v1 (run 1)
        # a second run under a DIFFERENT algorithm version -> comparability boundary
        with mock.patch.object(scout_delta_audit, "DELTA_ALGORITHM_VERSION", "v2"):
            self._run(s3, _view(precision=0.8))                  # run 2
        idx = self._index(s3)
        series = sri.metric_series(idx, ["precision"])["precision"]
        self.assertEqual([p["value"] for p in series["points"]], [0.9, 0.8])   # oldest->newest
        self.assertEqual(len(series["segments"]), 2)             # split by comparability key
        self.assertEqual(series["boundaries"], [2])              # boundary at run_seq 2


if __name__ == "__main__":
    unittest.main()
