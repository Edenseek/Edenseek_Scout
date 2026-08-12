"""scout_discovery.py — publisher-wide Discovery (ADR-0001 D7 step 3).

A **READ-ONLY producer of ``IssueContext``s**. Discovery enumerates the issues Scout can audit by
scanning the Publisher repository for the authoritative "has a current published revision" marker
(``approved/published.json``), and builds one ``IssueContext`` per issue via
``IssueContext.for_prefixes`` using the shared Publisher/Scout **bucket + region** config (not the
single-issue PREFIX).

Discovery **only enumerates candidates** — it derives no state, resolves nothing, and persists nothing.
Registry correctness continues to come from the certified resolve/rebuild pipeline (``scout_registry``),
which resolves each discovered context from authoritative objects. Feeding ``discover_contexts()`` into
``scout_registry.rebuild_registry(...)`` generalizes the certified tree-of-one to publisher-wide without
changing how correctness is derived.

Layering: imports stdlib + ``scout_context`` (a leaf) + ``audit_s3_source`` (for the S3 client) — but
**not** ``scout_registry`` (Discovery produces contexts; the Registry consumes them). No import cycle.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import audit_s3_source
import scout_context
from scout_context import IssueContext


class ScoutDiscoveryError(Exception):
    """Raised when Discovery is unconfigured or the Publisher enumeration fails."""


# An issue is "auditable" iff it has a current published revision; ``approved/published.json`` is that
# authoritative marker (the same object ``resolve_current_revision`` reads).
_SCAN_ROOT = "publishers/"
_PUBLISHED_MARKER = "/approved/published.json"


def discover_issue_prefixes(client, bucket: str) -> list[str]:
    """List every issue with a current published revision in the Publisher ``bucket``.

    Read-only ``ListObjectsV2`` under ``publishers/`` collecting keys ending in the published-pointer
    marker; the issue ownership prefix is the key minus that marker. Returns a sorted, de-duplicated
    list. Fail-loud on a transport error.
    """
    prefixes, continuation = [], None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": _SCAN_ROOT}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        try:
            resp = client.list_objects_v2(**kwargs)
        except (ClientError, BotoCoreError) as e:
            raise ScoutDiscoveryError(
                f"Unable to enumerate issues under s3://{bucket}/{_SCAN_ROOT}: {e}") from e
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(_PUBLISHED_MARKER):
                prefixes.append(key[: -len(_PUBLISHED_MARKER)])
        if resp.get("IsTruncated"):
            continuation = resp.get("NextContinuationToken")
        else:
            break
    return sorted(set(prefixes))


def _config(env: Mapping[str, str]):
    """Resolve the publisher-wide bucket+region config (NOT the single-issue prefix)."""
    approved_bucket = env.get(scout_context.APPROVED_BUCKET_ENV)
    scout_bucket = env.get(scout_context.SCOUT_BUCKET_ENV)
    if not approved_bucket or not scout_bucket:
        raise ScoutDiscoveryError(
            "Discovery is not configured: set "
            f"{scout_context.APPROVED_BUCKET_ENV} and {scout_context.SCOUT_BUCKET_ENV}.")
    approved_region = env.get(scout_context.APPROVED_REGION_ENV, scout_context.DEFAULT_REGION)
    scout_region = env.get(scout_context.SCOUT_REGION_ENV, scout_context.DEFAULT_REGION)
    return approved_bucket, approved_region, scout_bucket, scout_region


def context_for_prefix(issue_prefix: str, *, env: Optional[Mapping[str, str]] = None) -> IssueContext:
    """Reconstruct the ``IssueContext`` for ONE discovered issue prefix WITHOUT re-listing S3.

    An issue's approved surface is always ``{issue}/approved`` and its Scout surface is ``{issue}``;
    the buckets/regions are shared config — the identical construction ``discover_contexts`` uses per
    enumerated issue, minus the enumeration. The multi-issue dashboard uses this to scope archive /
    report reads to a chosen issue. Raises ``IssueContextError`` (bad/malformed prefix) or
    ``ScoutDiscoveryError`` (unconfigured); callers translate these to 400 / 503.
    """
    env = os.environ if env is None else env
    approved_bucket, approved_region, scout_bucket, scout_region = _config(env)
    return IssueContext.for_prefixes(
        approved_bucket=approved_bucket, approved_prefix=f"{issue_prefix}/approved",
        scout_bucket=scout_bucket, scout_prefix=issue_prefix,
        approved_region=approved_region, scout_region=scout_region)


def discover_contexts(*, client=None, env: Optional[Mapping[str, str]] = None) -> list[IssueContext]:
    """Publisher-wide READ-ONLY enumeration → one ``IssueContext`` per discovered issue.

    Every issue's approved surface is ``{issue}/approved`` and its Scout surface is ``{issue}``; the
    buckets/regions are the shared config. Persists nothing and derives no state. A discovered prefix
    that is not a valid issue ownership chain is skipped (logged), never fatal. Feed the result to
    ``scout_registry.rebuild_registry(...)`` to materialize the publisher-wide Registry via the
    certified pipeline.
    """
    env = os.environ if env is None else env
    approved_bucket, approved_region, scout_bucket, scout_region = _config(env)
    client = client or audit_s3_source.s3_client(approved_region)

    contexts: list[IssueContext] = []
    for issue_prefix in discover_issue_prefixes(client, approved_bucket):
        try:
            contexts.append(IssueContext.for_prefixes(
                approved_bucket=approved_bucket, approved_prefix=f"{issue_prefix}/approved",
                scout_bucket=scout_bucket, scout_prefix=issue_prefix,
                approved_region=approved_region, scout_region=scout_region))
        except scout_context.IssueContextError as e:
            logger.warning("Discovery: skipping non-issue prefix %r: %s", issue_prefix, e)
    logger.info("Discovery: enumerated %d issue(s) under s3://%s/%s",
                len(contexts), approved_bucket, _SCAN_ROOT)
    return contexts
