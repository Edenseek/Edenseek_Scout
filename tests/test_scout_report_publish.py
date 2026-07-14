"""Mocked-S3 tests for the consolidated Scout Report publication (Week 10 Day 18).

Covers: provenance tied to the exact Publisher Approved Dataset revision, the
machine-readable + Markdown artifacts written to the Scout Repository, append-only
history sequencing, read-back verification (pass + fail-loud on mismatch), and the
repository boundary (writes only to edenseek-scout; never the Publisher Repository;
no deletes; unconfigured fails loud).
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_inputs  # noqa: E402
import audit_scoring  # noqa: E402
import dataset_auditor  # noqa: E402
import scout_report_publisher as srp  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "dataset" / "society_of_killers" / "issue_1"
ISSUE_PREFIX = (
    "publishers/edenseek/title_groups/society_universe/series/"
    "society_of_killers/issues/issue_001"
)
PROVENANCE = {
    "source": "publisher_approved_dataset_s3",
    "source_bucket": "edenseek-publishing",
    "publisher_pointer_key": f"{ISSUE_PREFIX}/approved/published.json",
    "publisher_pointer_version_id": "ptr-ver-1",
    "publisher_revision_id": "rev_abc123",
    "publisher_revision_key": f"{ISSUE_PREFIX}/processing/workspace/rev_abc123/processing_snapshot.json",
    "publisher_snapshot_version_id": "snap-ver-1",
}


class _Body:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class _FakeS3:
    """Minimal in-memory S3 supporting put/get/list, with optional corrupt read-back."""

    def __init__(self, corrupt_readback=False):
        self.store = {}
        self.corrupt = corrupt_readback
        self.deleted = []

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.store[(Bucket, Key)] = Body
        return {}

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        data = self.store[(Bucket, Key)]
        if self.corrupt:
            data = data + b" tampered"
        return {"Body": _Body(data)}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):  # noqa: N803
        keys = [k for (b, k) in self.store if b == Bucket and k.startswith(Prefix)]
        return {"Contents": [{"Key": k} for k in keys], "IsTruncated": False}

    def delete_object(self, **kwargs):
        self.deleted.append(kwargs)


def _make_result():
    result = audit_scoring.run_audit(audit_inputs.load_inputs(FIXTURE_DIR))
    dataset_auditor._derive_core_blocks(result)
    return result


def _env(**overrides):
    env = {
        srp.BUCKET_ENV: "edenseek-scout",
        srp.PREFIX_ENV: ISSUE_PREFIX,
        srp.REGION_ENV: "us-west-2",
    }
    env.update(overrides)
    return env


class TestScoutReportPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = _make_result()

    def test_publishes_consolidated_report_with_provenance(self):
        client = _FakeS3()
        with mock.patch.dict("os.environ", _env(), clear=False):
            out = srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", PROVENANCE, client=client)

        # report_id ties the artifact to the exact revision + issue + run.
        self.assertIn("rev_abc123", out["report_id"])
        self.assertIn("issue_001", out["report_id"])

        # Both machine-readable and Markdown, at latest + history keys.
        for key in out["keys"].values():
            self.assertIn(("edenseek-scout", key), client.store)
        self.assertTrue(out["keys"]["latest_json"].endswith("reports/scout_report.json"))
        self.assertTrue(out["keys"]["history_json"].endswith("history/scout_report_000001.json"))
        self.assertTrue(out["keys"]["latest_md"].endswith("reports/scout_report.md"))

        # Envelope carries provenance, audit results, findings, recommendations, evidence.
        env = json.loads(client.store[("edenseek-scout", out["keys"]["latest_json"])])
        self.assertEqual(env["provenance"]["publisher_revision_id"], "rev_abc123")
        self.assertEqual(env["provenance"]["publisher_pointer_key"], PROVENANCE["publisher_pointer_key"])
        self.assertEqual(env["scout_version"], srp.SCOUT_VERSION)
        self.assertEqual(env["report_version"], srp.SCOUT_REPORT_VERSION)
        self.assertEqual(env["audit_results"]["quality_score"], self.result["quality_score"])
        self.assertIsInstance(env["findings"], list)
        self.assertIsInstance(env["recommendations"], list)
        self.assertIn("retrieval_packets_evaluated", env["evidence_references"])

    def test_history_is_append_only_and_sequenced(self):
        client = _FakeS3()
        with mock.patch.dict("os.environ", _env(), clear=False):
            first = srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", PROVENANCE, client=client)
            second = srp.publish_scout_report(self.result, "2026-07-14T01:00:00Z", PROVENANCE, client=client)
        self.assertEqual(first["run_seq"], 1)
        self.assertEqual(second["run_seq"], 2)
        # Both history snapshots survive (append-only); latest was overwritten in place.
        self.assertIn(("edenseek-scout", f"{ISSUE_PREFIX}/history/scout_report_000001.json"), client.store)
        self.assertIn(("edenseek-scout", f"{ISSUE_PREFIX}/history/scout_report_000002.json"), client.store)

    def test_readback_mismatch_fails_loud(self):
        client = _FakeS3(corrupt_readback=True)
        with mock.patch.dict("os.environ", _env(), clear=False):
            with self.assertRaises(srp.ScoutReportPublishError):
                srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", PROVENANCE, client=client)

    def test_boundary_scout_repo_only_no_publisher_no_delete(self):
        client = _FakeS3()
        with mock.patch.dict("os.environ", _env(), clear=False):
            srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", PROVENANCE, client=client)
        # Every write landed in edenseek-scout; nothing touched the Publisher bucket.
        self.assertTrue(all(bucket == "edenseek-scout" for (bucket, _key) in client.store))
        self.assertFalse(any("edenseek-publishing" in key for (_b, key) in client.store))
        self.assertEqual(client.deleted, [])

    def test_unconfigured_fails_loud(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(srp.ScoutReportPublishError):
                srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", PROVENANCE, client=_FakeS3())

    def test_provenance_absent_still_publishes(self):
        # Local/fixture runs carry no revision provenance; the report still persists.
        client = _FakeS3()
        with mock.patch.dict("os.environ", _env(), clear=False):
            out = srp.publish_scout_report(self.result, "2026-07-14T00:00:00Z", None, client=client)
        env = json.loads(client.store[("edenseek-scout", out["keys"]["latest_json"])])
        self.assertEqual(env["provenance"], {"source": "local_or_explicit_dir"})
        self.assertIn("local", out["report_id"])


if __name__ == "__main__":
    unittest.main()
