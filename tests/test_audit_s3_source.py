"""Mocked-S3 tests for the canonical Approved-Dataset read adapter.

Covers the certified "Option B" consumption path (Week 10 Day 18): resolve the
mutable ``approved/published.json`` pointer, fetch the immutable content-addressed
``processing_snapshot.json`` it names, verify the snapshot content hash equals the
pointer's ``revision_id``, and extract the three embedded contract files. Also
covers fail-loud on unconfigured/unreachable sources, content-hash mismatch,
missing embedded files, and the ownership/scope boundaries (approved-only entry
prefix, GET-only — never Put/Delete).
"""
import base64
import hashlib
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
import scout_context  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

APPROVED_PREFIX = (
    "publishers/edenseek/title_groups/society_universe/series/"
    "society_of_killers/issues/issue_001/approved"
)
REVISION_KEY = (
    "publishers/edenseek/title_groups/society_universe/series/"
    "society_of_killers/issues/issue_001/processing/workspace/"
    "rev_<hash>/processing_snapshot.json"
)

# The certified shapes: two bare lists + one wrapped object (matches live data).
CONTRACT_PAYLOADS = {
    "approved_dataset.json": [{"artifact_id": "a1"}],
    "approved_llm_outputs.json": {"llm_enrichment_outputs": [{"artifact_id": "o1"}]},
    "retrieval_evidence_packets.json": [{"scope": "p1"}],
}


def _build_snapshot(payloads=None, omit=()):
    """Build a processing snapshot embedding the contract files, plus its rev id.

    Returns ``(snapshot_bytes, revision_id, revision_key)``. ``omit`` drops named
    contract files from the snapshot to exercise the missing-file path.
    """
    payloads = payloads if payloads is not None else CONTRACT_PAYLOADS
    artifacts = []
    for name, doc in payloads.items():
        if name in omit:
            continue
        raw = json.dumps(doc).encode("utf-8")
        artifacts.append({
            "path": name,
            "content_b64": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        })
    snapshot = {
        "processing_snapshot_version": "v1",
        "pal_state": "processing",
        "binary_assets": [],
        "artifacts": artifacts,
    }
    snapshot_bytes = json.dumps(snapshot).encode("utf-8")
    revision_id = "rev_" + hashlib.sha256(snapshot_bytes).hexdigest()
    revision_key = REVISION_KEY.replace("<hash>", revision_id)
    return snapshot_bytes, revision_id, revision_key


class _FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def _fake_client(snapshot_bytes=None, revision_id=None, revision_key=None,
                 pointer_override=None, missing=False, corrupt_snapshot=False):
    """Build a Mock S3 client serving the pointer then the named snapshot."""
    if snapshot_bytes is None:
        snapshot_bytes, revision_id, revision_key = _build_snapshot()
    if corrupt_snapshot:
        snapshot_bytes = snapshot_bytes + b" tampered"
    pointer = pointer_override if pointer_override is not None else {
        "published_pointer_version": "v1",
        "revision_id": revision_id,
        "revision_key": revision_key,
    }
    client = mock.Mock()

    def get_object(Bucket, Key):  # noqa: N803 (boto3 kwarg names)
        if missing:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        if Key.endswith("published.json"):
            body = json.dumps(pointer).encode("utf-8")
        elif Key == revision_key:
            body = snapshot_bytes
        else:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        return {"Body": _FakeBody(body), "VersionId": "ver-" + Key.rsplit("/", 1)[-1]}

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

    def test_resolve_pointer_reconstruct_and_load(self):
        client = _fake_client()
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            dest = audit_s3_source.materialize_approved_contract(dest_root=root)

            # The three embedded contract files were reconstructed to disk.
            for name in audit_s3_source.CONTRACT_FILES:
                self.assertTrue((Path(dest) / name).is_file())
            # Exactly two reads: the pointer, then the one snapshot it names.
            self.assertEqual(client.get_object.call_count, 2)

            # The existing deterministic loader consumes the reconstructed dir,
            # accepting both bare-list and wrapped certified shapes.
            data = audit_inputs.load_inputs(dest)
            self.assertEqual(len(data["approved_artifacts"]), 1)
            self.assertEqual(len(data["llm_outputs"]), 1)
            self.assertEqual(len(data["packets"]), 1)
            self.assertTrue(data["dataset_id"].endswith("society_of_killers/issue_001"))

    def test_pointer_resolved_dynamically_never_pinned(self):
        # A different revision id in the pointer is followed without config change.
        snap, rev, key = _build_snapshot()
        client = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            audit_s3_source.materialize_approved_contract(dest_root=root)
        # The snapshot fetched is exactly the key the pointer named.
        fetched = [c.kwargs.get("Key") or c.args[1] for c in client.get_object.call_args_list]
        self.assertIn(key, fetched)

    def test_content_hash_mismatch_fails_loud(self):
        client = _fake_client(corrupt_snapshot=True)
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract(dest_root=root)

    def test_missing_embedded_contract_file_fails_loud(self):
        snap, rev, key = _build_snapshot(omit=("retrieval_evidence_packets.json",))
        client = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract(dest_root=root)

    def test_pointer_missing_revision_fields_fails_loud(self):
        client = _fake_client(pointer_override={"published_pointer_version": "v1"})
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract(dest_root=root)

    def test_ownership_get_only_never_writes(self):
        client = _fake_client()
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            audit_s3_source.materialize_approved_contract(dest_root=root)
        client.put_object.assert_not_called()
        client.delete_object.assert_not_called()
        client.delete_object_version.assert_not_called()

    def test_unconfigured_source_fails_loud(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(audit_s3_source.is_configured())
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract()

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

    def test_unreachable_pointer_fails_loud(self):
        client = _fake_client(missing=True)
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            with self.assertRaises(audit_s3_source.ScoutS3SourceError):
                audit_s3_source.materialize_approved_contract(dest_root=root)


class TestIssueContextThreading(unittest.TestCase):
    """Increment 2: an explicit IssueContext drives the read path identically to the env default.

    The context path must (a) produce byte-identical S3 access + outputs to the env path, and
    (b) be fully self-contained — it works with the environment *cleared*, and it *overrides* the
    environment when both are present.
    """

    SCOUT_PREFIX = ("publishers/edenseek/title_groups/society_universe/series/"
                    "society_of_killers/issues/issue_001")

    def _env(self, **overrides):
        env = {
            audit_s3_source.BUCKET_ENV: "edenseek-publishing",
            audit_s3_source.PREFIX_ENV: APPROVED_PREFIX,
            audit_s3_source.REGION_ENV: "us-west-2",
        }
        env.update(overrides)
        return env

    def _ctx(self):
        return scout_context.IssueContext.for_prefixes(
            approved_bucket="edenseek-publishing", approved_prefix=APPROVED_PREFIX,
            scout_bucket="edenseek-scout", scout_prefix=self.SCOUT_PREFIX)

    @staticmethod
    def _keys(client):
        return [c.kwargs.get("Key") or c.args[1] for c in client.get_object.call_args_list]

    def test_resolve_current_revision_context_equals_env(self):
        snap, rev, key = _build_snapshot()
        client_env = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client_env):
            ptr_env = audit_s3_source.resolve_current_revision()
        # Context path with the environment CLEARED — proves it is context-driven, not env-driven.
        client_ctx = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client_ctx):
            ptr_ctx = audit_s3_source.resolve_current_revision(context=self._ctx())
        self.assertEqual(ptr_env, ptr_ctx)
        self.assertEqual(self._keys(client_env), self._keys(client_ctx))

    def test_materialize_context_equals_env(self):
        snap, rev, key = _build_snapshot()
        client_env = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with tempfile.TemporaryDirectory() as root_env, \
                mock.patch.dict("os.environ", self._env(), clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client_env):
            dest_env = audit_s3_source.materialize_approved_contract(dest_root=root_env)
            rel_env = Path(dest_env).relative_to(root_env).as_posix()
            prov_env = (Path(dest_env) / audit_s3_source.PROVENANCE_FILE).read_text(encoding="utf-8")
        client_ctx = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        with tempfile.TemporaryDirectory() as root_ctx, \
                mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client_ctx):
            dest_ctx = audit_s3_source.materialize_approved_contract(
                dest_root=root_ctx, context=self._ctx())
            rel_ctx = Path(dest_ctx).relative_to(root_ctx).as_posix()
            prov_ctx = (Path(dest_ctx) / audit_s3_source.PROVENANCE_FILE).read_text(encoding="utf-8")
        # Same dest path (series/issue), same S3 keys read, byte-identical provenance.
        self.assertEqual(rel_env, rel_ctx)
        self.assertEqual(self._keys(client_env), self._keys(client_ctx))
        self.assertEqual(prov_env, prov_ctx)

    def test_context_overrides_environment(self):
        # Environment points at a different (wrong) issue; the context must win.
        snap, rev, key = _build_snapshot()
        client = _fake_client(snapshot_bytes=snap, revision_id=rev, revision_key=key)
        wrong = self._env(**{audit_s3_source.PREFIX_ENV:
                             "publishers/x/title_groups/y/series/z/issues/issue_999/approved"})
        with mock.patch.dict("os.environ", wrong, clear=False), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            audit_s3_source.resolve_current_revision(context=self._ctx())
        self.assertTrue(all(k.startswith(APPROVED_PREFIX) for k in self._keys(client)))

    def test_context_never_writes(self):
        client = _fake_client()
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(audit_s3_source, "_s3_client", return_value=client):
            audit_s3_source.materialize_approved_contract(dest_root=root, context=self._ctx())
        client.put_object.assert_not_called()
        client.delete_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
