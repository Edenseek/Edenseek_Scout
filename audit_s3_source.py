"""Read-only S3 source for the canonical Approved-Dataset contract.

Scout consumes the frozen Publisher Repository contract as a pure reader. The
certified model ("Option B", Week 10 Day 18) is a **content-addressed processing
revision**, not three loose files under ``approved/``:

  1. ``approved/published.json`` is a small **mutable pointer** carrying
     ``revision_id`` (a ``rev_<sha256>`` content hash) and ``revision_key``
     (the full S3 key of the immutable snapshot for that revision).
  2. That ``revision_key`` resolves to ``processing/workspace/<rev>/
     processing_snapshot.json`` — an immutable snapshot whose ``artifacts`` list
     embeds every issue file as ``{path, content_b64, sha256, size}``.
  3. The three Approved-Dataset contract files
     (``approved_dataset.json``, ``approved_llm_outputs.json``,
     ``retrieval_evidence_packets.json``) are embedded artifacts inside that
     snapshot; Scout extracts them and hands the reconstructed directory to the
     existing deterministic loader (``audit_inputs.load_inputs``) unchanged.

Invariants (enforced here):
  * **Resolve the pointer every run** — the revision id is never pinned in config;
    a new approval simply moves the pointer and Scout follows it.
  * **Version-pin each S3 read** — the S3 ``VersionId`` returned for the pointer
    and the snapshot is captured and logged as run provenance so the audit records
    exactly which object versions it consumed.
  * **Verify content integrity** — ``sha256(snapshot_bytes)`` must equal the
    pointer's ``revision_id``; each extracted file must match its embedded
    ``sha256``. Any mismatch fails loud.
  * **Fail loud, no fixture fallback** — if the canonical source is unconfigured
    or any object cannot be reached, this raises ``ScoutS3SourceError``.

Boundaries (Charter §4; Repository Ownership Principle):
  * Scout is read-only on canonical data: ``GetObject`` only — never
    ``PutObject``/``DeleteObject``. Scout writes only to its own report space.
  * Scout enters only through a configured ``approved/`` surface; the
    ``processing/`` snapshot it follows is named by the pointer the Publisher
    published, never guessed.
  * No LLM / vision / external-service calls; deterministic over a frozen source.
"""
import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger

# The three files that constitute the active Approved-Dataset contract, embedded
# by ``path`` inside the certified processing snapshot's ``artifacts`` list.
CONTRACT_FILES = (
    "approved_dataset.json",
    "approved_llm_outputs.json",
    "retrieval_evidence_packets.json",
)

# The mutable pointer object that lives on the ``approved/`` surface.
POINTER_FILE = "published.json"

# Scout-internal provenance sidecar written into the materialized directory. It
# records exactly which Publisher Approved Dataset revision (and S3 object
# versions) this run consumed, so the persisted Scout Report can cite the source.
# Named with a leading underscore so it never collides with a contract file.
PROVENANCE_FILE = "_scout_source.json"

# Explicit canonical S3 source configuration (no defaults that point at fixtures).
BUCKET_ENV = "SCOUT_APPROVED_S3_BUCKET"
PREFIX_ENV = "SCOUT_APPROVED_S3_PREFIX"
REGION_ENV = "SCOUT_APPROVED_S3_REGION"
DEFAULT_REGION = "us-west-2"


class ScoutS3SourceError(Exception):
    """Raised when the canonical Approved-Dataset S3 source is unconfigured or unreachable."""


def is_configured():
    """True only when an explicit canonical S3 source is configured."""
    return bool(os.getenv(BUCKET_ENV) and os.getenv(PREFIX_ENV))


def _s3_client(region):
    # Isolated for test injection. Credentials resolve through the standard AWS
    # chain — the least-privilege, read-only ``edenseek-scout-app`` identity.
    return boto3.client("s3", region_name=region)


def _require_approved_prefix(prefix):
    """Enforce that the configured prefix is an ``approved/`` surface.

    Guarantees Scout enters the contract only through the approved surface it is
    scoped to. Returns the normalized path segments.
    """
    segments = prefix.strip().strip("/").split("/")
    if not segments or segments[-1] != "approved":
        raise ScoutS3SourceError(
            f"Refusing non-approved S3 prefix (must end with 'approved/'): {prefix!r}"
        )
    return segments


def _derive_identity_tail(segments):
    """Derive ``(series_id, issue_id)`` from the canonical ownership chain.

    Keeps the audit's ``dataset_id`` stable and joinable to the canonical issue.
    """
    try:
        series_id = segments[segments.index("series") + 1]
        issue_id = segments[segments.index("issues") + 1]
    except (ValueError, IndexError):
        raise ScoutS3SourceError(
            "Approved prefix missing the canonical series/issues chain: "
            f"{'/'.join(segments)!r}"
        )
    return series_id, issue_id


def _get_object(client, bucket, key):
    """Read one object (GET only) and return ``(body_bytes, version_id)``.

    Version-pin provenance: the S3 ``VersionId`` is captured so the run records
    exactly which object version it consumed. Fail-loud on any transport error.
    """
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
    except (ClientError, BotoCoreError) as e:
        raise ScoutS3SourceError(
            f"Unable to read canonical object s3://{bucket}/{key}: {e}"
        ) from e
    return body, obj.get("VersionId")


def s3_client(region=None):
    """Public read-only S3 client factory on the least-privilege ``edenseek-scout-app``
    identity (standard AWS chain). Thin wrapper so callers (e.g. the audit-review manifest)
    do not reach into module internals."""
    return _s3_client(region or os.getenv(REGION_ENV, DEFAULT_REGION))


def probe_object(client, bucket, key):
    """Read-only probe of one object for the evidence manifest — GET only, and **tolerant**:
    a missing or access-denied object is *recorded*, never raised, so a manifest can report
    pipeline health rather than crash.

    Returns ``{status, size, sha256, version_id, body}`` where ``status`` is one of
    ``read`` / ``missing`` / ``denied`` / ``error``. On a non-``read`` status ``size``/``sha256``/
    ``version_id``/``body`` are ``None``. Never writes anything.
    """
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        status = ("missing" if code in ("NoSuchKey", "404", "NotFound")
                  else "denied" if code in ("AccessDenied", "403", "AccessDeniedException")
                  else "error")
        return {"status": status, "size": None, "sha256": None, "version_id": None, "body": None}
    except BotoCoreError:
        return {"status": "error", "size": None, "sha256": None, "version_id": None, "body": None}
    return {
        "status": "read",
        "size": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "version_id": obj.get("VersionId"),
        "body": body,
    }


def _resolve_published_pointer(client, bucket, approved_prefix):
    """Resolve the mutable ``approved/published.json`` pointer for this run.

    Returns a dict with ``revision_id``, ``revision_key``, and the pointer's own
    S3 ``version_id``. Fail-loud if the pointer is missing, unparseable, or does
    not carry both fields.
    """
    key = f"{approved_prefix}/{POINTER_FILE}"
    body, version_id = _get_object(client, bucket, key)
    try:
        pointer = json.loads(body)
    except json.JSONDecodeError as e:
        raise ScoutS3SourceError(
            f"Published pointer is not valid JSON (s3://{bucket}/{key}): {e}"
        ) from e
    revision_id = pointer.get("revision_id")
    revision_key = pointer.get("revision_key")
    if not revision_id or not revision_key:
        raise ScoutS3SourceError(
            "Published pointer missing 'revision_id'/'revision_key' "
            f"(s3://{bucket}/{key})"
        )
    return {
        "key": key,
        "version_id": version_id,
        "revision_id": revision_id,
        "revision_key": revision_key,
    }


def _verify_revision_hash(snapshot_bytes, revision_id):
    """Assert the snapshot's content hash equals the pointer's ``revision_id``.

    The revision id is content-addressed: ``rev_<sha256(snapshot_bytes)>``. A
    mismatch means the pointer and the snapshot disagree — fail loud.
    """
    computed = f"rev_{hashlib.sha256(snapshot_bytes).hexdigest()}"
    if computed != revision_id:
        raise ScoutS3SourceError(
            "Snapshot content hash does not match the published pointer: "
            f"computed {computed} != revision_id {revision_id}"
        )


def _extract_contract_files(snapshot_bytes, revision_id):
    """Extract the three embedded contract files from the certified snapshot.

    Each snapshot ``artifacts`` entry is ``{path, content_b64, sha256, size}``.
    Returns ``{filename: raw_bytes}`` for the three contract files, verifying each
    file's embedded ``sha256``. Fail-loud if a required file is absent or its
    content is corrupt.
    """
    try:
        snapshot = json.loads(snapshot_bytes)
    except json.JSONDecodeError as e:
        raise ScoutS3SourceError(
            f"processing_snapshot.json is not valid JSON for {revision_id}: {e}"
        ) from e

    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, list):
        raise ScoutS3SourceError(
            f"Certified revision {revision_id} snapshot has no 'artifacts' list"
        )
    by_path = {a.get("path"): a for a in artifacts if isinstance(a, dict)}

    extracted = {}
    for name in CONTRACT_FILES:
        entry = by_path.get(name)
        if entry is None:
            raise ScoutS3SourceError(
                f"Certified revision {revision_id} does not embed required "
                f"contract file {name!r}"
            )
        content_b64 = entry.get("content_b64")
        if content_b64 is None:
            raise ScoutS3SourceError(
                f"Embedded contract file {name!r} has no 'content_b64' "
                f"in revision {revision_id}"
            )
        try:
            raw = base64.b64decode(content_b64, validate=True)
        except (ValueError, TypeError) as e:
            raise ScoutS3SourceError(
                f"Embedded contract file {name!r} is not valid base64 "
                f"in revision {revision_id}: {e}"
            ) from e
        expected_sha = entry.get("sha256")
        if expected_sha is not None:
            actual_sha = hashlib.sha256(raw).hexdigest()
            if actual_sha != expected_sha:
                raise ScoutS3SourceError(
                    f"Embedded contract file {name!r} sha256 mismatch in "
                    f"revision {revision_id}: {actual_sha} != {expected_sha}"
                )
        extracted[name] = raw
    return extracted


def materialize_approved_contract(dest_root=None, context=None):
    """Reconstruct the certified Approved-Dataset contract from S3, read-only.

    Resolves the published pointer, fetches the immutable content-addressed
    revision snapshot, verifies its content hash, extracts the three embedded
    contract files, and writes them to ``<dest_root>/<series_id>/<issue_id>`` —
    a directory ``audit_inputs.load_inputs`` consumes unchanged. ``GetObject``
    only; never writes to the Publishing Repository. Raises ``ScoutS3SourceError``
    (fail-loud) when the source is unconfigured, the pointer/snapshot is
    unreachable, or content integrity fails. Never falls back to fixtures.
    """
    if context is not None:
        # Explicit context: the approved surface + identity are already resolved and normalized
        # (IssueContext.from_env reproduces this env derivation byte-for-byte — Increment 1).
        bucket = context.approved_bucket
        normalized_prefix = context.approved_prefix
        region = context.approved_region
        series_id, issue_id = context.series_id, context.issue_id
    else:
        # Environment path — unchanged (byte-for-byte with the certified single-issue behavior).
        bucket = os.getenv(BUCKET_ENV)
        prefix = os.getenv(PREFIX_ENV)
        if not bucket or not prefix:
            raise ScoutS3SourceError(
                "Canonical Approved-Dataset S3 source is not configured: set "
                f"{BUCKET_ENV} and {PREFIX_ENV} (there is no fixture fallback)."
            )

        region = os.getenv(REGION_ENV, DEFAULT_REGION)
        segments = _require_approved_prefix(prefix)
        normalized_prefix = "/".join(segments)
        series_id, issue_id = _derive_identity_tail(segments)

    client = _s3_client(region)

    # 1. Resolve the mutable pointer dynamically — never pin a revision id.
    pointer = _resolve_published_pointer(client, bucket, normalized_prefix)

    # 2. Fetch the immutable, content-addressed revision snapshot the pointer names.
    snapshot_bytes, snapshot_version = _get_object(client, bucket, pointer["revision_key"])

    # 3. Verify the snapshot's content hash equals the pointer's revision_id.
    _verify_revision_hash(snapshot_bytes, pointer["revision_id"])

    # 4. Extract (and per-file verify) the three embedded contract files.
    extracted = _extract_contract_files(snapshot_bytes, pointer["revision_id"])

    dest_root = Path(dest_root) if dest_root else Path(tempfile.mkdtemp(prefix="scout_approved_"))
    dest_dir = dest_root / series_id / issue_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, raw in extracted.items():
        # Write the certified bytes verbatim so the on-disk copy stays hash-verifiable.
        (dest_dir / name).write_bytes(raw)

    # Record run provenance alongside the contract files so the Scout Report can
    # tie its findings to the exact Publisher Approved Dataset revision analyzed.
    provenance = {
        "source": "publisher_approved_dataset_s3",
        "source_bucket": bucket,
        "publisher_pointer_key": pointer["key"],
        "publisher_pointer_version_id": pointer["version_id"],
        "publisher_revision_id": pointer["revision_id"],
        "publisher_revision_key": pointer["revision_key"],
        "publisher_snapshot_version_id": snapshot_version,
    }
    (dest_dir / PROVENANCE_FILE).write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    logger.info(
        "Reconstructed canonical Approved-Dataset contract "
        f"revision={pointer['revision_id']} from s3://{bucket}/{normalized_prefix}/ "
        f"(pointer VersionId={pointer['version_id']}, "
        f"snapshot VersionId={snapshot_version}) -> {dest_dir}"
    )
    return str(dest_dir)


def resolve_current_revision(client=None, context=None):
    """Resolve the current Approved Dataset revision from the pointer only.

    A cheap, read-only ``GetObject`` on ``approved/published.json`` (the mutable
    pointer) — it does **not** download the immutable revision snapshot. Used by the
    revision watcher to detect change without materializing or auditing anything.
    Returns the pointer dict (``key``, ``version_id``, ``revision_id``,
    ``revision_key``). Fail-loud (``ScoutS3SourceError``) when unconfigured or
    unreachable; no fixture fallback.
    """
    if context is not None:
        # Explicit context: already-normalized approved surface (byte-for-byte with the env path).
        bucket = context.approved_bucket
        normalized_prefix = context.approved_prefix
        region = context.approved_region
    else:
        # Environment path — unchanged.
        bucket = os.getenv(BUCKET_ENV)
        prefix = os.getenv(PREFIX_ENV)
        if not bucket or not prefix:
            raise ScoutS3SourceError(
                "Canonical Approved-Dataset S3 source is not configured: set "
                f"{BUCKET_ENV} and {PREFIX_ENV} (there is no fixture fallback)."
            )
        region = os.getenv(REGION_ENV, DEFAULT_REGION)
        normalized_prefix = "/".join(_require_approved_prefix(prefix))
    client = client or _s3_client(region)
    return _resolve_published_pointer(client, bucket, normalized_prefix)


def load_source_provenance(input_dir):
    """Return the read-path provenance for ``input_dir``, or ``None`` if absent.

    Present only for directories materialized from the Publisher Approved Dataset
    S3 source (see ``PROVENANCE_FILE``); an explicit ``SCOUT_DATASET_DIR`` / local
    fixture directory has no revision provenance and yields ``None``.
    """
    path = Path(input_dir) / PROVENANCE_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
