"""Daemon + processed-revision ledger tests (Increment 2).

In-memory S3 fake; Publisher reads (resolve + build_audit_review) are mocked so nothing touches the
Publisher repository. Covers first-time processing, duplicate suppression, retry after failure,
partial-persistence failure, hash mismatch, changed comparability context, dataset-audit
preservation, and no-Publisher-writes.
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
import scout_revision_ledger as ledger  # noqa: E402
import scout_delta_audit as sda  # noqa: E402
import scout_watch  # noqa: E402
import scout_context  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

REPO_PREFIX = "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001"
IDENT = {"publisher_id": "edenseek", "title_group_id": "society_universe",
         "series_id": "society_of_killers", "issue_id": "issue_001"}


class FakeS3:
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

    def history_count(self):
        return len([k for (b, k) in self.store if "/history/scout_delta_report_" in k])


def _env():
    return {srp.BUCKET_ENV: "edenseek-scout", srp.PREFIX_ENV: REPO_PREFIX,
            srp.REGION_ENV: "us-west-2"}


def _view(published="rev_pub_1", generated="rev_gen_1"):
    prov = {"published_revision_id": published, "generated_snapshot_revision_id": generated,
            "source_versions": {"review_report_version": "v1", "platform_approval_version": "v1",
                                "generated_snapshot_version": None,
                                "generated_metadata_version": "v1.1", "approved_metadata_version": "v1.1"},
            "normalization_version": "v1", "metadata_revision_distance_version": "v1",
            "geometry_detector": {"match_version": "v1", "iou_threshold": 0.5},
            "metadata_provenance": {"generated_schema_version": "v1.1", "approved_schema_version": "v1.1",
                                    "prompt_version": None, "model": None}}
    delta = {"review_id": "rev_pub_1"[:12], "applicability": "generated_publication", "provenance": prov,
             "geometry_delta": {"applicable": True, "benchmark": {}}, "metadata_delta": {"applicable": True},
             "metadata_benchmark": {"applicable": False}, "correction_ledger": [],
             "publisher_certified_state": {"canonical_dataset_state": "edenseek_approved"}}
    return {
        "audit_timestamp": "2026-07-28T12:00:00Z", "publisher_commit": published, "scout_commit": "s1",
        "evidence": {"issue_identity": IDENT, "summary": {}, "objects": [], "manifest_version": "v1",
                     "publisher_provenance": {}},
        "findings": [{"code": "evidence.loaded", "severity": "PASS", "title": "t", "detail": "d"}],
        "delta_summary": {"geometry": {"status": "computed", "precision": 0.9, "recall": 0.6,
                                       "split_rate": 0, "merge_rate": 0, "missing": 0,
                                       "spread_missing": 0, "false": 0},
                          "metadata": {"status": "abstained", "compared": 0}},
        "delta_report": delta, "delta_report_sha256": "sha",
    }


def _pointer(published="rev_pub_1"):
    return {"key": f"{REPO_PREFIX}/approved/published.json", "version_id": "pv",
            "revision_id": published, "revision_key": f"{REPO_PREFIX}/.../snap.json"}


class _Base(unittest.TestCase):
    def run_agent(self, s3, view, published="rev_pub_1", force=False, trigger="manual"):
        with mock.patch.dict("os.environ", _env(), clear=False), \
                mock.patch.object(sda.audit_s3_source, "resolve_current_revision",
                                  return_value=_pointer(published)), \
                mock.patch.object(sda.audit_review, "build_audit_review", return_value=view):
            return sda.audit_current_revision(client=s3, force=force, trigger=trigger)

    def load_ledger(self, s3):
        with mock.patch.dict("os.environ", _env(), clear=False):
            return ledger.load_ledger(s3)

    def load_index(self, s3):
        with mock.patch.dict("os.environ", _env(), clear=False):
            return sri.load_index(s3)


class TestLifecycle(_Base):
    def test_first_time_processing(self):
        s3 = FakeS3()
        r = self.run_agent(s3, _view())
        self.assertEqual(r["status"], "persisted")
        self.assertEqual(r["run_seq"], 1)
        self.assertEqual(self.load_index(s3)["count"], 1)
        led = self.load_ledger(s3)
        self.assertEqual(led["count"], 1)
        entry = next(iter(led["entries"].values()))
        self.assertEqual(entry["status"], "processed")
        self.assertEqual(entry["run_seq"], 1)
        self.assertEqual(entry["revision_id"], "rev_pub_1")
        self.assertEqual(s3.history_count(), 1)

    def test_duplicate_revision_suppressed(self):
        s3 = FakeS3()
        self.run_agent(s3, _view())
        r2 = self.run_agent(s3, _view())          # same revision + context
        self.assertEqual(r2["status"], "skipped")
        self.assertEqual(r2["reason"], "already_processed")
        self.assertEqual(s3.history_count(), 1)   # no duplicate report
        self.assertEqual(self.load_index(s3)["count"], 1)

    def test_changed_comparability_context_reaudits(self):
        s3 = FakeS3()
        self.run_agent(s3, _view())
        with mock.patch.object(sda, "DELTA_ALGORITHM_VERSION", "v2"):   # methodology bump
            r2 = self.run_agent(s3, _view())
        self.assertEqual(r2["status"], "persisted")
        self.assertEqual(r2["run_seq"], 2)                              # a new logical run
        self.assertEqual(self.load_index(s3)["count"], 2)
        self.assertEqual(self.load_ledger(s3)["count"], 2)             # two context fingerprints


class TestFailures(_Base):
    def test_retry_after_failure(self):
        s3 = FakeS3()
        bad = _view()
        bad["delta_report"] = None                 # contract-not-adapted -> incomplete
        r1 = self.run_agent(s3, bad)
        self.assertEqual(r1["status"], "failed")
        self.assertEqual(r1["stage"], "assemble")
        led = self.load_ledger(s3)
        self.assertEqual(next(iter(led["entries"].values()))["status"], "failed")
        self.assertEqual(s3.history_count(), 0)
        # retry succeeds
        r2 = self.run_agent(s3, _view())
        self.assertEqual(r2["status"], "persisted")
        self.assertEqual(next(iter(self.load_ledger(s3)["entries"].values()))["status"], "processed")
        self.assertEqual(s3.history_count(), 1)

    def test_partial_persistence_failure_then_retry_no_duplicate(self):
        s3 = FakeS3()
        calls = {"n": 0}
        real_update = sri.update_index

        def flaky_update(entry, client=None, context=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise sri.ScoutReportIndexError("simulated index write failure")
            return real_update(entry, client=client, context=context)

        with mock.patch.object(sri, "update_index", side_effect=flaky_update):
            r1 = self.run_agent(s3, _view())
            self.assertEqual(r1["status"], "failed")
            self.assertEqual(r1["stage"], "index")
            self.assertEqual(s3.history_count(), 1)          # report persisted, just not indexed
            entry = next(iter(self.load_ledger(s3)["entries"].values()))
            self.assertEqual(entry["status"], "failed")
            r2 = self.run_agent(s3, _view())                 # retry
        self.assertEqual(r2["status"], "reconciled")         # idempotent — no new logical report
        self.assertEqual(s3.history_count(), 1)              # still one snapshot
        self.assertEqual(self.load_index(s3)["count"], 1)
        self.assertEqual(next(iter(self.load_ledger(s3)["entries"].values()))["status"], "processed")

    def test_hash_mismatch_records_failure_not_processed(self):
        s3 = FakeS3()
        calls = {"n": 0}
        real_verify = srp._verify_readback

        def flaky_verify(client, bucket, key, expected):
            calls["n"] += 1
            if calls["n"] == 1:                              # first verify (the report) fails
                raise srp.ScoutReportPublishError("simulated sha256 read-back mismatch")
            return real_verify(client, bucket, key, expected)

        with mock.patch.object(srp, "_verify_readback", side_effect=flaky_verify):
            r = self.run_agent(s3, _view())
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["stage"], "persist_verify")
        entry = next(iter(self.load_ledger(s3)["entries"].values()))
        self.assertEqual(entry["status"], "failed")
        self.assertNotEqual(entry["status"], "processed")
        # index never advanced past empty on a verify failure
        with mock.patch.dict("os.environ", _env(), clear=False):
            self.assertEqual(sri.load_index(s3)["count"], 0)


class TestBoundaries(_Base):
    def test_no_publisher_writes(self):
        s3 = FakeS3()
        self.run_agent(s3, _view())
        # every write went to Scout's own bucket; nothing to edenseek-publishing
        self.assertTrue(s3.store)
        self.assertEqual({b for (b, _k) in s3.store}, {"edenseek-scout"})

    def test_dataset_audit_preserved_and_both_run(self):
        # run_cycle runs the existing dataset audit (unchanged) AND the delta agent; a delta failure
        # does not stop the dataset audit.
        with mock.patch.object(scout_watch, "check_and_audit",
                               return_value={"status": "unchanged"}) as ds, \
                mock.patch.object(scout_watch.scout_delta_audit, "audit_current_revision",
                                  return_value={"status": "skipped"}) as delta:
            out = scout_watch.run_cycle()
        ds.assert_called_once()
        delta.assert_called_once()
        self.assertEqual(out["dataset"]["status"], "unchanged")
        self.assertEqual(out["delta"]["status"], "skipped")


class TestLedgerIssueContextThreading(unittest.TestCase):
    """Increment 3: an explicit IssueContext drives the ledger identically to the env default.

    Timestamps (`_now`) are pinned so the env-vs-context comparison is a true byte-for-byte check
    of the persisted ledger object rather than being defeated by wall-clock differences.
    """

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=REPO_PREFIX + "/approved",
            scout_bucket="edenseek-scout", scout_prefix=REPO_PREFIX)

    def _mark_processed(self, client, context=None):
        return ledger.mark_processed(
            "rev_pub_1", "fp_1", run_id="run_x", run_seq=1, report_id="rid",
            completed_at="2026-07-14T00:00:00Z", generated_snapshot_revision_id="rev_gen_1",
            comparability={"geometry": "cmp_g", "metadata": "cmp_m"}, trigger="manual",
            client=client, context=context)

    def test_mark_processed_context_equals_env(self):
        a, b = FakeS3(), FakeS3()
        with mock.patch.object(ledger, "_now", return_value="2026-07-14T00:00:00Z"):
            with mock.patch.dict("os.environ", _env(), clear=False):
                self._mark_processed(a)
            with mock.patch.dict("os.environ", {}, clear=True):  # env cleared → context-driven
                self._mark_processed(b, context=self._ctx())
        self.assertEqual(a.store, b.store)  # byte-identical ledger object at identical key

    def test_mark_failed_context_equals_env(self):
        a, b = FakeS3(), FakeS3()
        with mock.patch.object(ledger, "_now", return_value="2026-07-14T00:00:00Z"):
            with mock.patch.dict("os.environ", _env(), clear=False):
                ledger.mark_failed("rev_pub_1", "fp_1", stage="persist_verify",
                                   error_codes=["Boom"], trigger="manual", client=a)
            with mock.patch.dict("os.environ", {}, clear=True):
                ledger.mark_failed("rev_pub_1", "fp_1", stage="persist_verify",
                                   error_codes=["Boom"], trigger="manual", client=b, context=self._ctx())
        self.assertEqual(a.store, b.store)

    def test_load_ledger_context_equals_env(self):
        s3 = FakeS3()
        with mock.patch.dict("os.environ", _env(), clear=False):
            self._mark_processed(s3)
            led_env = ledger.load_ledger(s3)
        with mock.patch.dict("os.environ", {}, clear=True):
            led_ctx = ledger.load_ledger(s3, context=self._ctx())
        self.assertEqual(led_env, led_ctx)

    def test_context_ledger_writes_only_scout(self):
        s3 = FakeS3()
        with mock.patch.dict("os.environ", {}, clear=True):
            self._mark_processed(s3, context=self._ctx())
        self.assertTrue(all(bkt == "edenseek-scout" for (bkt, _k) in s3.store))
        self.assertTrue(all("issues/issue_001/" in k for (_b, k) in s3.store))


class TestRunnerIssueContextThreading(_Base):
    """Increment 4b: audit_current_revision forwards an explicit IssueContext through the WHOLE delta
    transaction (resolve -> evidence -> persist -> index -> ledger). With the environment CLEARED,
    the run must still succeed and be byte-identical to the env-driven run — which can only happen if
    the runner forwards the context to every downstream write."""

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=REPO_PREFIX + "/approved",
            scout_bucket="edenseek-scout", scout_prefix=REPO_PREFIX)

    def _run_ctx(self, s3, view, published="rev_pub_1"):
        # resolve + build_audit_review are mocked; env is cleared, so the persistence/index/ledger
        # writes survive ONLY because audit_current_revision threads the context to them.
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(sda.audit_s3_source, "resolve_current_revision",
                                  return_value=_pointer(published)), \
                mock.patch.object(sda.audit_review, "build_audit_review", return_value=view):
            return sda.audit_current_revision(client=s3, context=self._ctx())

    def test_audit_current_revision_context_equals_env(self):
        with mock.patch.object(ledger, "_now", return_value="2026-07-14T00:00:00Z"):
            a = FakeS3()
            res_env = self.run_agent(a, _view())          # env-driven (env set)
            b = FakeS3()
            res_ctx = self._run_ctx(b, _view())            # context-driven (env cleared)
        self.assertEqual(res_env["status"], "persisted")
        self.assertEqual(res_env, res_ctx)                 # identical runner result
        self.assertEqual(a.store, b.store)                 # byte-identical report + index + ledger

    def test_context_run_writes_only_scout_repo(self):
        with mock.patch.object(ledger, "_now", return_value="2026-07-14T00:00:00Z"):
            b = FakeS3()
            self._run_ctx(b, _view())
        self.assertTrue(all(bkt == "edenseek-scout" for (bkt, _k) in b.store))
        self.assertTrue(all("issues/issue_001/" in k for (_b, k) in b.store))


if __name__ == "__main__":
    unittest.main()
