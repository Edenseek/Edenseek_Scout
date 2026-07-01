"""Mocked-S3 tests for the canonical Approved-Dataset read adapter (Week 10 Day 14).

Covers: successful read + materialization, fail-loud on unconfigured source and
on unreachable objects, and ownership/scope boundaries (approved-only prefix,
GET-only — never Put/Delete).
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import audit_s3_source  # noqa: E402
import audit_inputs  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

APPROVED_PREFIX = (
    "publishers/edenseek/title_groups/society_universe/series/"
    "society_of_killers/issues/issue_001/approved"
)

CONTRACT_PAYLOADS = {
    "approved_dataset.json": {"approved_dataset": [{"id": "a1"}]},
    "approved_llm_outputs.json": {"llm_enrichment_outputs": [{"id": "o1"}]},
    "retrieval_evidence_packets.json": {"retrieval_evidence_packets": [{"id": "p1"}]},
}


class _FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def _fake_client(payloads=None, missing=False):
    """Build a Mock S3 client whose get_object returns canned bytes."""
    payloads = payloads if payloads is not None else CONTRACT_PAYLOADS
    client = mock.Mock()

    def get_object(Bucket, Key):  # noqa: N803 (boto3 kwarg names)
        name = Key.rsplit("/", 1)[-1]
        if missing or name not in payloads:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        return {"Body": _FakeBody(json.dumps(payloads[name]).encode("utf-8"))}

    client.get_object.side_effect = get_object
    return client


class TestScoutS3Source(unittest.TestCase):
    def _env(self, **overrides):
        env = {
            audit_s3_source.BUCKET_ENV: "edenseek-publishing",
            audit_s3_source.PREFIX_ENV: APPROVED_PREFIX,
            audit_s3_source.REGION_ENV: "us-west-2",
        }
        env.update(overrides)
        return env

    def test_materialize_reads_contract_and_loads(self):
        client = _fake_client()
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            dest = audit_s3_source.materialize_approved_contract(dest_root=root)

            # All three contract files were fetched (GET only) and written locally.
            for name in audit_s3_source.CONTRACT_FILES:
                self.assertTrue((Path(dest) / name).is_file())
            self.assertEqual(client.get_object.call_count, 3)

            # The existing deterministic loader consumes the materialized dir unchanged.
            data = audit_inputs.load_inputs(dest)
            self.assertEqual(len(data["approved_artifacts"]), 1)
            self.assertEqual(len(data["llm_outputs"]), 1)
            self.assertEqual(len(data["packets"]), 1)
            # dataset_id stays joinable to the canonical issue.
            self.assertTrue(data["dataset_id"].endswith("society_of_killers/issue_001"))

    def test_ownership_get_only_never_writes(self):
        client = _fake_client()
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            audit_s3_source.materialize_approved_contract(dest_root=root)
        # No write/delete API was ever invoked against the Publishing Repository.
        client.put_object.assert_not_called()
        client.delete_object.assert_not_called()
        client.delete_object_version.assert_not_called()

    def test_unconfigured_source_fails_loud(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract()
        self.assertFalse(audit_s3_source.is_configured())

    def test_non_approved_prefix_refused(self):
        bad = self._env(
            **{audit_s3_source.PREFIX_ENV:
               "publishers/edenseek/title_groups/society_universe/series/"
               "society_of_killers/issues/issue_001/intake"}
        )
        with mock.patch.dict("os.environ", bad, clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client") as factory:
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract()
            # Refused before any S3 client was constructed or any object read.
            factory.assert_not_called()

    def test_missing_object_fails_loud(self):
        client = _fake_client(missing=True)
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract(dest_root=root)


if __name__ == "__main__":
    unittest.main()
