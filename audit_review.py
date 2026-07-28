"""Read-only Audit-Review evidence service (Scout UI, Slice 1).

Assembles the **Consumed-Evidence Manifest** for the currently-configured issue and its current
certified revision: every Publisher S3 object Scout consumes for the generated-vs-approved delta,
with its exact key, load status, size, sha256, version id, revision id, and schema version — plus
permanent audit metadata (``publisher_commit``, ``scout_commit``, ``audit_timestamp``) and a
top-level ``summary`` block the future UI renders directly, without recomputing.

This is the evidentiary core the founder verifies visually: that Publisher evidence is read
correctly and normalized correctly, before any delta is computed or persisted.

Boundaries (Charter §4; Repository Ownership Principle):
  * **Read-only** on ``edenseek-publishing`` — GetObject only, via the least-privilege
    ``edenseek-scout-app`` identity. This module writes nothing anywhere; a per-object failure is
    *recorded* (status ``missing``/``denied``/``error``), never mutating and never masked.
  * Reuses the existing read path (``audit_s3_source``) and the anti-corruption boundary's
    supported-version sets (``review_contract_adapter``); no Publisher-shape logic is duplicated
    here.
  * No LLM / vision / external-service calls; deterministic over the frozen, content-addressed
    Publisher inputs (aside from ``audit_timestamp`` / ``scout_commit``, which are envelope audit
    metadata — like the report's ``created_at`` — not part of any deterministic delta body).

The manifest metadata shape is itself versioned (``manifest_version``) so it can become permanent,
reproducible audit metadata carried into the persisted Scout delta report (Slice 3).
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import audit_s3_source
from review_contract_adapter import (
    SUPPORTED_REVIEW_REPORT_VERSIONS,
    SUPPORTED_PLATFORM_APPROVAL_VERSIONS,
)
from logging_config import logger

MANIFEST_VERSION = "v1"
_HERE = Path(__file__).resolve().parent


class AuditReviewError(Exception):
    """Raised only for whole-manifest configuration errors (unconfigured source, unresolvable
    pointer). Per-object read failures are recorded in the manifest, not raised."""


def _derive_review_id(published_revision_id):
    """``review_id = "rev_" + <sha256 of published revision>[:12]`` — the same deterministic
    derivation Scout uses to address the ``reviews/{review_id}/`` certification artifacts."""
    return "rev_" + published_revision_id.split("_", 1)[1][:12]


def _scout_commit():
    """Scout's own git HEAD (with a ``+dirty`` suffix if the tree has uncommitted changes) — the
    code version that produced this manifest, for report reproducibility. Fail-soft to ``None``
    (a missing git context must not break a read-only endpoint)."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=_HERE,
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if not sha:
            return None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=_HERE,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return None


def _schema_version(role, parsed):
    """Extract the Publisher-declared schema version for a parsed object, or ``None``. The
    content-addressed processing snapshot has no schema version — its identity is its revision
    hash, captured separately as ``revision_id``."""
    if not isinstance(parsed, dict):
        return None
    return {
        "approved_pointer": parsed.get("published_pointer_version"),
        "review_report": parsed.get("review_report_version"),
        "platform_approval": parsed.get("platform_approval_version"),
    }.get(role)


def build_evidence_manifest(client=None):
    """Build the read-only Consumed-Evidence Manifest for the configured issue + current revision.

    Resolves the published pointer, derives ``review_id``, and probes the four Publisher objects
    Scout consumes for the delta (approved pointer, processing snapshot, review report, platform
    approval). Returns a manifest dict with permanent audit metadata + a ``summary`` health block.
    Fail-loud only on whole-manifest config/resolution errors; per-object issues are recorded.
    """
    bucket = os.getenv(audit_s3_source.BUCKET_ENV)
    prefix = os.getenv(audit_s3_source.PREFIX_ENV)
    if not bucket or not prefix:
        raise AuditReviewError(
            "Approved-Dataset S3 source is not configured: set "
            f"{audit_s3_source.BUCKET_ENV} and {audit_s3_source.PREFIX_ENV}.")

    segments = audit_s3_source._require_approved_prefix(prefix)
    normalized = "/".join(segments)
    issue_root = normalized[: -len("/approved")]
    _series_id, issue_id = audit_s3_source._derive_identity_tail(segments)

    client = client or audit_s3_source.s3_client()

    # Resolve the mutable pointer (fail-loud — without it there is no revision to review).
    try:
        pointer = audit_s3_source.resolve_current_revision(client)
    except audit_s3_source.ScoutS3SourceError as e:
        raise AuditReviewError(f"Unable to resolve the current certified revision: {e}") from e

    published_revision_id = pointer["revision_id"]
    review_id = _derive_review_id(published_revision_id)

    # The four objects Scout consumes for the generated-vs-approved delta, in read order.
    roles = [
        ("approved_pointer", pointer["key"], published_revision_id, True),
        ("processing_snapshot", pointer["revision_key"], published_revision_id, False),
        ("review_report", f"{issue_root}/reviews/{review_id}/review_report.json", review_id, True),
        ("platform_approval", f"{issue_root}/reviews/{review_id}/platform_approval.json", review_id, True),
    ]

    objects = []
    parsed_by_role = {}
    for role, key, revision_id, parse in roles:
        probe = audit_s3_source.probe_object(client, bucket, key)
        parsed = None
        if probe["status"] == "read" and parse:
            try:
                parsed = json.loads(probe["body"])
                parsed_by_role[role] = parsed
            except json.JSONDecodeError:
                parsed = None
        objects.append({
            "role": role,
            "key": key,
            "status": probe["status"],
            "size": probe["size"],
            "sha256": probe["sha256"],
            "version_id": probe["version_id"],
            "revision_id": revision_id,
            "schema_version": _schema_version(role, parsed),
        })

    # --- summary health block (permanent; rendered directly, never recomputed) ---
    loaded = sum(1 for o in objects if o["status"] == "read")
    expected = len(objects)
    rr_ok = _schema_version("review_report", parsed_by_role.get("review_report")) \
        in SUPPORTED_REVIEW_REPORT_VERSIONS
    pa_ok = _schema_version("platform_approval", parsed_by_role.get("platform_approval")) \
        in SUPPORTED_PLATFORM_APPROVAL_VERSIONS
    audit_ready = (loaded == expected) and rr_ok and pa_ok

    rr_prov = (parsed_by_role.get("review_report") or {}).get("provenance") or {}
    publisher_commit = rr_prov.get("published_revision_id") or published_revision_id

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "audit_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scout_commit": _scout_commit(),
        "publisher_commit": publisher_commit,
        "issue_id": issue_id,
        "review_id": review_id,
        "bucket": bucket,
        "objects": objects,
        "summary": {
            "objects_expected": expected,
            "objects_loaded": loaded,
            "objects_missing": expected - loaded,
            "publisher_mutation": "none",  # GetObject-only identity; writes IAM-denied (Phase B v5)
            "audit_ready": audit_ready,
        },
        "publisher_provenance": {
            "chain_id": rr_prov.get("chain_id"),
            "published_at": rr_prov.get("published_at"),
            "initiating_user": rr_prov.get("initiating_user"),
        },
    }
    logger.info(
        "Audit-review evidence manifest: issue=%s review_id=%s loaded=%d/%d audit_ready=%s",
        issue_id, review_id, loaded, expected, audit_ready,
    )
    return manifest


def _load_dotenv(path=None):
    """Minimal .env loader for the CLI verification path only (the app/systemd supplies env)."""
    path = Path(path or (_HERE / ".env"))
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    # Verification entry point: `python audit_review.py` prints the live manifest as JSON.
    _load_dotenv()
    os.environ.pop("AWS_PROFILE", None)
    print(json.dumps(build_evidence_manifest(), indent=2, ensure_ascii=False))
