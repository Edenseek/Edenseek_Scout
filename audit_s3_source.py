"""Read-only S3 source for the canonical Approved-Dataset contract (Week 10 Day 14).

Fetches the three Approved-Dataset contract files from the canonical Publishing
Repository ``approved/`` surface (S3) into a local transient directory, which the
existing deterministic loader (``audit_inputs.load_inputs``) then reads unchanged.

Boundaries (Charter §4; Repository Ownership Principle):
  * Scout is read-only on canonical data: this module performs S3 ``GetObject``
    only — never ``PutObject``/``DeleteObject``, and never writes to the
    Publishing Repository.
  * Scout only reads inside the configured ``approved/`` prefix; a prefix that is
    not an ``approved/`` surface is refused.
  * No LLM / vision / external-service calls; deterministic over a frozen source.

Fail-loud: if the canonical source is not configured, the prefix is not an
approved surface, or any contract file cannot be reached, this raises
``ScoutS3SourceError`` rather than falling back to local fixtures.
"""
import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger

# The three files that constitute the active Approved-Dataset contract.
CONTRACT_FILES = (
    "approved_dataset.json",
    "approved_llm_outputs.json",
    "retrieval_evidence_packets.json",
)

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

    Guarantees Scout never reads outside the approved contract surface. Returns
    the normalized path segments.
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


def materialize_approved_contract(dest_root=None):
    """Download the three contract files from the canonical ``approved/`` surface.

    Returns the local directory ``<dest_root>/<series_id>/<issue_id>`` containing
    the three files, suitable for ``audit_inputs.load_inputs``. Read-only on S3
    (``GetObject`` only). Raises ``ScoutS3SourceError`` (fail-loud) when the source
    is unconfigured or any file cannot be retrieved. Never falls back to fixtures.
    """
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

    dest_root = Path(dest_root) if dest_root else Path(tempfile.mkdtemp(prefix="scout_approved_"))
    dest_dir = dest_root / series_id / issue_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    client = _s3_client(region)
    for name in CONTRACT_FILES:
        key = f"{normalized_prefix}/{name}"
        try:
            obj = client.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
        except (ClientError, BotoCoreError) as e:
            raise ScoutS3SourceError(
                f"Unable to read canonical contract object s3://{bucket}/{key}: {e}"
            ) from e
        (dest_dir / name).write_bytes(body)

    logger.info(
        "Materialized canonical Approved-Dataset contract from "
        f"s3://{bucket}/{normalized_prefix}/ -> {dest_dir}"
    )
    return str(dest_dir)
