"""Tests for the read-only Audit-Review evidence manifest (Scout UI, Slice 1).

Stubbed S3 (no network). Verifies the consumed-object manifest, the permanent audit metadata
(publisher_commit/scout_commit/audit_timestamp), and the summary health block
(objects_expected/loaded/missing, publisher_mutation, audit_ready) across happy-path,
missing-object, and unsupported-schema cases.
"""
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_s3_source  # noqa: E402
import audit_review  # noqa: E402
import scout_context  # noqa: E402
import _delta_fixtures as fx  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

APPROVED_PREFIX = (
    "publishers/edenseek/title_groups/society_universe/series/"
    "society_of_killers/issues/issue_001/approved"
)
ISSUE_ROOT = APPROVED_PREFIX[: -len("/approved")]
REVISION_ID = "rev_a8c65a83a196" + "0" * 52  # rev_ + 64 hex
REVISION_KEY = f"{ISSUE_ROOT}/processing/workspace/{REVISION_ID}/processing_snapshot.json"
REVIEW_ID = "rev_a8c65a83a196"


class _FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def _bodies(review_report_version="v1", platform_approval_version="v1"):
    pointer = {"published_pointer_version": "v1", "revision_id": REVISION_ID,
               "revision_key": REVISION_KEY}
    snapshot = {"processing_snapshot_version": "v1", "artifacts": []}
    review_report = {
        "review_report_version": review_report_version,
        "review_id": REVIEW_ID,
        "provenance": {"published_revision_id": REVISION_ID,
                       "chain_id": "sha256:deadbeef", "published_at": "2026-07-27T17:07:57Z",
                       "initiating_user": "Derek"},
    }
    platform_approval = {"platform_approval_version": platform_approval_version,
                         "canonical_dataset_state": "edenseek_approved"}
    return {
        f"{APPROVED_PREFIX}/published.json": json.dumps(pointer).encode(),
        REVISION_KEY: json.dumps(snapshot).encode(),
        f"{ISSUE_ROOT}/reviews/{REVIEW_ID}/review_report.json": json.dumps(review_report).encode(),
        f"{ISSUE_ROOT}/reviews/{REVIEW_ID}/platform_approval.json": json.dumps(platform_approval).encode(),
    }


def _fake_client(bodies=None, missing_keys=()):
    bodies = bodies if bodies is not None else _bodies()
    client = mock.Mock()

    def get_object(Bucket, Key):  # noqa: N803
        if Key in missing_keys or Key not in bodies:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": _FakeBody(bodies[Key]), "VersionId": "ver-" + Key.rsplit("/", 1)[-1]}

    client.get_object.side_effect = get_object
    return client


class TestAuditReview(unittest.TestCase):
    def _env(self, **ov):
        env = {audit_s3_source.BUCKET_ENV: "edenseek-publishing",
               audit_s3_source.PREFIX_ENV: APPROVED_PREFIX,
               audit_s3_source.REGION_ENV: "us-west-2"}
        env.update(ov)
        return env

    def _manifest(self, client):
        with mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_review, "_scout_commit", return_value="testsha"):
            return audit_review.build_evidence_manifest(client=client)

    def test_happy_path_manifest_and_summary(self):
        m = self._manifest(_fake_client())
        self.assertEqual(m["manifest_version"], "v1")
        self.assertEqual(m["issue_id"], "issue_001")
        self.assertEqual(m["review_id"], REVIEW_ID)                 # derived from pointer
        self.assertEqual(m["publisher_commit"], REVISION_ID)       # from review_report provenance
        self.assertEqual(m["scout_commit"], "testsha")
        self.assertTrue(m["audit_timestamp"].endswith("Z"))
        roles = [o["role"] for o in m["objects"]]
        self.assertEqual(roles, ["approved_pointer", "processing_snapshot",
                                 "review_report", "platform_approval"])
        self.assertTrue(all(o["status"] == "read" for o in m["objects"]))
        self.assertTrue(all(o["sha256"] and o["size"] for o in m["objects"]))
        # schema versions extracted; snapshot is content-addressed (no schema version)
        by_role = {o["role"]: o for o in m["objects"]}
        self.assertEqual(by_role["review_report"]["schema_version"], "v1")
        self.assertEqual(by_role["platform_approval"]["schema_version"], "v1")
        self.assertIsNone(by_role["processing_snapshot"]["schema_version"])
        self.assertEqual(by_role["processing_snapshot"]["revision_id"], REVISION_ID)
        self.assertEqual(m["summary"], {
            "objects_expected": 4, "objects_loaded": 4, "objects_missing": 0,
            "publisher_mutation": "none", "audit_ready": True})
        self.assertEqual(m["publisher_provenance"]["chain_id"], "sha256:deadbeef")

    def test_missing_platform_approval_marks_not_ready(self):
        missing = f"{ISSUE_ROOT}/reviews/{REVIEW_ID}/platform_approval.json"
        m = self._manifest(_fake_client(missing_keys=(missing,)))
        by_role = {o["role"]: o for o in m["objects"]}
        self.assertEqual(by_role["platform_approval"]["status"], "missing")
        self.assertIsNone(by_role["platform_approval"]["sha256"])
        self.assertEqual(m["summary"]["objects_loaded"], 3)
        self.assertEqual(m["summary"]["objects_missing"], 1)
        self.assertFalse(m["summary"]["audit_ready"])

    def test_denied_object_recorded_not_raised(self):
        client = mock.Mock()

        def get_object(Bucket, Key):  # noqa: N803
            if Key.endswith("platform_approval.json"):
                raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
            return {"Body": _FakeBody(_bodies()[Key]), "VersionId": "v"}

        client.get_object.side_effect = get_object
        m = self._manifest(client)
        by_role = {o["role"]: o for o in m["objects"]}
        self.assertEqual(by_role["platform_approval"]["status"], "denied")
        self.assertFalse(m["summary"]["audit_ready"])

    def test_unsupported_schema_not_ready(self):
        m = self._manifest(_fake_client(_bodies(review_report_version="v99")))
        # object still loads, but the schema is not one Scout understands
        by_role = {o["role"]: o for o in m["objects"]}
        self.assertEqual(by_role["review_report"]["status"], "read")
        self.assertEqual(by_role["review_report"]["schema_version"], "v99")
        self.assertEqual(m["summary"]["objects_missing"], 0)
        self.assertFalse(m["summary"]["audit_ready"])

    def test_unconfigured_source_raises(self):
        with mock.patch.dict("os.environ", {audit_s3_source.BUCKET_ENV: "",
                                            audit_s3_source.PREFIX_ENV: ""}, clear=False):
            with self.assertRaises(audit_review.AuditReviewError):
                audit_review.build_evidence_manifest(client=_fake_client())


# --- Slice 2: live delta + state comparison + findings (delta fixtures as review bodies) ---

def _delta_bodies(rr_version="v1", approved_meta_version="v1.1"):
    """Serve the real delta fixtures as the review_report/platform_approval bodies so the audit
    view runs an actual delta."""
    pointer = {"published_pointer_version": "v1", "revision_id": REVISION_ID,
               "revision_key": REVISION_KEY}
    rr = fx.review_generated()
    rr["review_report_version"] = rr_version
    rr["approved_metadata"]["llm_enrichment_output_version"] = approved_meta_version
    return {
        f"{APPROVED_PREFIX}/published.json": json.dumps(pointer).encode(),
        REVISION_KEY: json.dumps({"artifacts": []}).encode(),
        f"{ISSUE_ROOT}/reviews/{REVIEW_ID}/review_report.json": json.dumps(rr).encode(),
        f"{ISSUE_ROOT}/reviews/{REVIEW_ID}/platform_approval.json":
            json.dumps(fx.platform_approval()).encode(),
    }


class TestAuditReviewDelta(unittest.TestCase):
    def _env(self):
        return {audit_s3_source.BUCKET_ENV: "edenseek-publishing",
                audit_s3_source.PREFIX_ENV: APPROVED_PREFIX,
                audit_s3_source.REGION_ENV: "us-west-2"}

    def _view(self, bodies):
        with mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_review, "_scout_commit", return_value="testsha"):
            return audit_review.build_audit_review(client=_fake_client(bodies))

    def _by_code(self, view):
        return {f["code"]: f for f in view["findings"]}

    def test_delta_computes_and_projects(self):
        # both sides v1.1 -> metadata computes; contract adapts cleanly
        v = self._view(_delta_bodies(approved_meta_version="v1.1"))
        self.assertEqual(v["audit_review_version"], "v1")
        self.assertEqual(len(v["delta_report_sha256"]), 64)
        self.assertIsNotNone(v["state_comparison"])
        self.assertEqual(v["state_comparison"]["publisher_certified"]["canonical_dataset_state"],
                         "edenseek_approved")
        self.assertEqual(v["delta_summary"]["geometry"]["status"], "computed")
        self.assertEqual(v["delta_summary"]["metadata"]["status"], "computed")
        fbc = self._by_code(v)
        self.assertEqual(fbc["contract.adapted"]["severity"], "PASS")
        self.assertEqual(fbc["metadata.comparability"]["severity"], "PASS")
        self.assertEqual(fbc["delta.deterministic"]["severity"], "PASS")
        self.assertEqual(fbc["evidence.loaded"]["severity"], "PASS")

    def test_metadata_schema_skew_warns(self):
        # generated v1.1 vs approved v1 -> metadata abstains -> WARNING, not FAIL
        v = self._view(_delta_bodies(approved_meta_version="v1"))
        self.assertEqual(v["delta_summary"]["metadata"]["status"], "abstained")
        self.assertEqual(self._by_code(v)["metadata.comparability"]["severity"], "WARNING")
        self.assertFalse(any(f["severity"] == "FAIL" for f in v["findings"]))

    def test_unsupported_contract_version_fails(self):
        v = self._view(_delta_bodies(rr_version="v99"))
        self.assertIsNone(v["delta_report"])
        self.assertIsNone(v["state_comparison"])
        self.assertEqual(self._by_code(v)["contract.adapted"]["severity"], "FAIL")


class TestAuditReviewIssueContextThreading(unittest.TestCase):
    """Increment 4: an explicit IssueContext drives the evidence read layer identically to the env
    default. `datetime` is pinned so the audit_timestamp cannot mask a real diff."""

    APPROVED_ENV = {audit_s3_source.BUCKET_ENV: "edenseek-publishing",
                    audit_s3_source.PREFIX_ENV: APPROVED_PREFIX,
                    audit_s3_source.REGION_ENV: "us-west-2"}

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=APPROVED_PREFIX,
            scout_bucket="edenseek-scout", scout_prefix=ISSUE_ROOT)

    def test_evidence_manifest_context_equals_env(self):
        fixed = datetime(2026, 7, 14, tzinfo=timezone.utc)
        with mock.patch.object(audit_review, "_scout_commit", return_value="testsha"), \
                mock.patch.object(audit_review, "datetime") as dt:
            dt.now.return_value = fixed
            with mock.patch.dict("os.environ", self.APPROVED_ENV, clear=False):
                m_env = audit_review.build_evidence_manifest(client=_fake_client())
            with mock.patch.dict("os.environ", {}, clear=True):  # env cleared → context-driven
                m_ctx = audit_review.build_evidence_manifest(client=_fake_client(), context=self._ctx())
        self.assertEqual(m_env, m_ctx)

    def test_audit_review_view_context_equals_env(self):
        fixed = datetime(2026, 7, 14, tzinfo=timezone.utc)
        bodies = _delta_bodies()
        with mock.patch.object(audit_review, "_scout_commit", return_value="testsha"), \
                mock.patch.object(audit_review, "datetime") as dt:
            dt.now.return_value = fixed
            with mock.patch.dict("os.environ", self.APPROVED_ENV, clear=False):
                v_env = audit_review.build_audit_review(client=_fake_client(bodies))
            with mock.patch.dict("os.environ", {}, clear=True):
                v_ctx = audit_review.build_audit_review(client=_fake_client(bodies), context=self._ctx())
        self.assertEqual(v_env, v_ctx)


if __name__ == "__main__":
    unittest.main()
