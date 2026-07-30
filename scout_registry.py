"""scout_registry.py — the Scout Registry (ADR-0001 D3/D6).

A **derived, rebuildable projection** of the Publisher repository hierarchy, stored as **flat,
hierarchy-keyed per-issue entries**. The publisher/series/issue "tree" is a query/rollup VIEW over
that flat model — never a nested-storage commitment.

Phase 2 (behavior-neutral so far). Increment 1 introduced the Registry **data model + pure
projection/view functions**. Increment 2 added **read-only resolvers** (``resolve_entry`` /
``resolve_registry``). Increment 3 adds **persistence** (``persist_registry`` / ``load_registry`` /
``rebuild_registry``) of the derived projection to a single latest-state object at the Scout-bucket
root ``registry/registry.json`` (like the benchmark platform projection) — overwrite + readback
SHA-256 verified, rebuildable by re-resolving. Increment 4 exposed a read-only ``GET /registry``.
Increment 5a adds the **governed one-shot rebuild trigger** ``rebuild_current`` (+ a CLI) that
materializes the persisted Registry for the env-configured single issue (tree-of-one) from
authoritative Publisher data. This is the first use of ``IssueContext.from_env()`` in a real entry
point — but it is a **separate, human-run operational tool**, NOT the certified audit path (which is
untouched and still runs its ``context=None`` env branches). Later increments (per ADR-0001 D7) add
Discovery to populate the Registry publisher-wide, then point the scheduler at it.

Invariants this module must always uphold (ADR-0001):
- **D3 — derived projection.** A Registry is rebuildable from the Publisher's authoritative objects
  (``approved/published.json`` -> revision; ``reviews/{id}/platform_approval.json`` presence -> state)
  plus Scout's own index/ledger. It is **never** a second source of truth, and is **never** derived
  from the stale Publisher ``dataset_registry.json``.
- **D6 — flat, hierarchy-keyed.** Entries are keyed by the issue ownership prefix
  (``publishers/{pub}/title_groups/{tg}/series/{series}/issues/{issue}``); ``rollup`` / ``tree_view``
  are pure VIEWS over the flat entries.
- **Facts vs. observations (Principle P1).** Publisher publication facts (revision / review / state)
  are recorded verbatim; Scout's audit linkage is an observation over Scout's own ledger/index.
- **Layering.** The pure model depends only on the standard library + ``scout_context`` (a leaf). The
  Increment-2 resolvers additionally read via ``audit_s3_source`` + ``scout_report_index`` +
  ``scout_revision_ledger`` — none of which import the Registry, so there is no import cycle. The
  Registry sits above the Audit-layer readers.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import audit_s3_source
import scout_report_index
import scout_report_publisher
import scout_revision_ledger
from scout_context import IssueContext  # leaf import (scout_context depends on nothing Scout-side)


class ScoutRegistryError(Exception):
    """Raised when the Registry cannot be configured, read, or persisted."""


REGISTRY_VERSION = "v1"

# The Registry is a platform-wide flat projection -> a single latest-state object at the Scout-bucket
# root (peer of ``benchmark/platform.json``), NOT per-issue and NOT immutable history.
REGISTRY_ARTIFACT_KEY = "registry/registry.json"

# Publisher publication state is a Publisher FACT that Scout records verbatim; Scout never invents it.
STATE_UNKNOWN = "unknown"
# Published but no platform_approval.json present yet (mirrors review_contract_adapter semantics).
STATE_CREATOR_APPROVED = "creator_approved"

# Scout-derived audit-linkage state — an observation over Scout's own ledger/index for the issue.
AUDIT_UNPROCESSED = "unprocessed"
AUDIT_AUDITED = "audited"
AUDIT_FAILED = "failed"

# Canonical ownership-identity fields (leaf = issue_id); the flat key is the issue ownership prefix.
_IDENTITY_FIELDS = ("publisher_id", "title_group_id", "series_id", "issue_id")
_ROLLUP_LEVELS = ("publisher_id", "title_group_id", "series_id")


def _empty_audit() -> dict:
    return {"audit_state": AUDIT_UNPROCESSED, "run_seq": None, "run_id": None, "report_id": None}


def build_entry(*, issue_prefix: str, identity: Mapping[str, Optional[str]],
                published_revision_id: Optional[str] = None, review_id: Optional[str] = None,
                publication_state: str = STATE_UNKNOWN,
                audit: Optional[Mapping[str, Any]] = None,
                resolved_at: Optional[str] = None) -> dict:
    """One flat Registry entry for a single issue (D6 flat, keyed by ``issue_prefix``).

    The ``publication`` block holds Publisher facts (revision / review / state) recorded verbatim; the
    ``audit`` block holds Scout's observation of its own index/ledger for this issue. Pure — no I/O;
    ``resolved_at`` is supplied by the caller (a later I/O increment stamps it), never wall-clock here.
    """
    ident = {k: identity.get(k) for k in _IDENTITY_FIELDS}
    return {
        "issue_prefix": issue_prefix,
        **ident,
        "publication": {
            "published_revision_id": published_revision_id,
            "review_id": review_id,
            "state": publication_state,
        },
        "audit": dict(audit) if audit is not None else _empty_audit(),
        "resolved_at": resolved_at,
    }


def entry_from_context(context: IssueContext, *,
                       published_revision_id: Optional[str] = None, review_id: Optional[str] = None,
                       publication_state: str = STATE_UNKNOWN,
                       audit: Optional[Mapping[str, Any]] = None,
                       resolved_at: Optional[str] = None) -> dict:
    """Build an entry from an ``IssueContext`` — identity + the flat key (``scout_prefix``) come from
    the context. This is the seam a future Discovery/Registry-seed increment uses per enumerated issue."""
    return build_entry(
        issue_prefix=context.scout_prefix, identity=context.identity,
        published_revision_id=published_revision_id, review_id=review_id,
        publication_state=publication_state, audit=audit, resolved_at=resolved_at)


def build_registry(entries, *, generated_at: Optional[str] = None) -> dict:
    """Assemble the flat Registry projection: entries keyed by ``issue_prefix`` (D6).

    Idempotent-by-key: a later entry for the same issue prefix replaces the earlier one, so a rebuild
    from a re-scan converges. Pure — ``generated_at`` is supplied, never wall-clock here.
    """
    keyed: dict[str, dict] = {}
    for e in entries:
        keyed[e["issue_prefix"]] = e
    return {
        "registry_version": REGISTRY_VERSION,
        "generated_at": generated_at,
        "count": len(keyed),
        "entries": keyed,
    }


def get(registry: Mapping[str, Any], issue_prefix: str) -> Optional[dict]:
    """The Registry entry for one issue prefix, or ``None``."""
    return (registry.get("entries") or {}).get(issue_prefix)


def rollup(registry: Mapping[str, Any], level: str) -> dict:
    """Group the flat entries by a hierarchy level — a pure VIEW over the flat model (D6).

    ``level`` is one of ``publisher_id`` / ``title_group_id`` / ``series_id`` (not the ``issue_id``
    leaf). Returns ``{level, groups: {value: [issue_prefix, ...]}, group_count, issue_count}``.
    """
    if level not in _ROLLUP_LEVELS:
        raise ValueError(f"rollup level must be one of {_ROLLUP_LEVELS}: {level!r}")
    groups: dict[Optional[str], list] = {}
    for prefix, e in (registry.get("entries") or {}).items():
        groups.setdefault(e.get(level), []).append(prefix)
    return {"level": level, "groups": groups, "group_count": len(groups),
            "issue_count": sum(len(v) for v in groups.values())}


def tree_view(registry: Mapping[str, Any]) -> dict:
    """The publisher -> title_group -> series -> issue nesting as a pure rollup VIEW over the flat
    entries (D6: the tree is a view, not storage). Tree-of-one today; generalizes as issues accumulate."""
    tree: dict = {}
    for prefix, e in (registry.get("entries") or {}).items():
        pub = tree.setdefault(e.get("publisher_id"),
                              {"publisher_id": e.get("publisher_id"), "title_groups": {}})
        tg = pub["title_groups"].setdefault(
            e.get("title_group_id"), {"title_group_id": e.get("title_group_id"), "series": {}})
        ser = tg["series"].setdefault(
            e.get("series_id"), {"series_id": e.get("series_id"), "issues": {}})
        ser["issues"][e.get("issue_id")] = prefix
    return tree


# --------------------------------------------------------------------------- #
# Resolution (Phase 2 · Increment 2): resolve a Registry entry from AUTHORITATIVE objects + Scout's
# own index/ledger. READ-ONLY; no persistence; no production consumer yet.
# --------------------------------------------------------------------------- #
def _resolve_review_id(published_revision_id: str) -> str:
    """The deterministic ``reviews/{review_id}/`` address for a published revision.

    Mirrors ``audit_review._derive_review_id`` (drift-guarded by test) so the resolved
    ``platform_approval.json`` key matches the one Scout's evidence layer reads.
    """
    return "rev_" + published_revision_id.split("_", 1)[1][:12]


def _resolve_publication_state(client, context: IssueContext, review_id: str) -> str:
    """Resolve the Publisher publication-state FACT from ``platform_approval.json`` (authoritative).

    Records the verbatim ``canonical_dataset_state`` when present (Principle P1). A missing
    platform_approval ⇒ published-but-not-platform-approved (``creator_approved``);
    denied/error/unparseable ⇒ ``unknown``. Tolerant — never raises.
    """
    issue_root = context.approved_prefix[: -len("/approved")]
    key = f"{issue_root}/reviews/{review_id}/platform_approval.json"
    probe = audit_s3_source.probe_object(client, context.approved_bucket, key)
    if probe["status"] == "missing":
        return STATE_CREATOR_APPROVED
    if probe["status"] != "read":
        return STATE_UNKNOWN
    try:
        return json.loads(probe["body"]).get("canonical_dataset_state") or STATE_UNKNOWN
    except (json.JSONDecodeError, TypeError, AttributeError):
        return STATE_UNKNOWN


def _resolve_audit_linkage(client, context: IssueContext, published_revision_id: Optional[str]) -> dict:
    """Resolve Scout's OWN audit linkage for the issue from the index (+ ledger) — an observation,
    kept separate from Publisher facts. Read-only; tolerant of an absent index/ledger."""
    try:
        index = scout_report_index.load_index(client, context=context)
    except scout_report_index.ScoutReportIndexError:
        return _empty_audit()
    cur = next((e for e in (index.get("entries") or [])
                if e.get("published_revision_id") == published_revision_id), None)
    if cur is not None:
        return {"audit_state": AUDIT_AUDITED, "run_seq": cur.get("run_seq"),
                "run_id": cur.get("run_id"), "report_id": cur.get("report_id")}
    # Not audited under the current revision — was the last attempt on it a recorded failure?
    try:
        led = scout_revision_ledger.load_ledger(client, context=context)
    except scout_revision_ledger.ScoutRevisionLedgerError:
        return _empty_audit()
    for e in (led.get("entries") or {}).values():
        if (e.get("revision_id") == published_revision_id
                and e.get("status") == scout_revision_ledger.STATUS_FAILED):
            return {"audit_state": AUDIT_FAILED, "run_seq": e.get("run_seq"),
                    "run_id": e.get("run_id"), "report_id": e.get("report_id")}
    return _empty_audit()


def resolve_entry(context: IssueContext, *, client=None, resolved_at: Optional[str] = None) -> dict:
    """Resolve one issue's Registry entry from authoritative objects (current revision + platform-
    approval state) and Scout's own index/ledger (audit linkage). **READ-ONLY.**

    A resolvable-but-unpublished issue (no current pointer) yields a fact-free entry (revision
    ``None``, state ``unknown``, audit ``unprocessed``) rather than raising. The derived projection is
    rebuildable by re-resolving.
    """
    client = client or audit_s3_source.s3_client(context.approved_region)
    try:
        pointer = audit_s3_source.resolve_current_revision(client, context=context)
        revision_id = pointer["revision_id"]
    except audit_s3_source.ScoutS3SourceError:
        return build_entry(issue_prefix=context.scout_prefix, identity=context.identity,
                           resolved_at=resolved_at)
    review_id = _resolve_review_id(revision_id)
    state = _resolve_publication_state(client, context, review_id)
    audit = _resolve_audit_linkage(client, context, revision_id)
    return build_entry(issue_prefix=context.scout_prefix, identity=context.identity,
                       published_revision_id=revision_id, review_id=review_id,
                       publication_state=state, audit=audit, resolved_at=resolved_at)


def resolve_registry(contexts, *, client=None, generated_at: Optional[str] = None) -> dict:
    """Resolve a flat Registry over the given issue contexts (tree-of-one today = a one-element list).
    READ-ONLY; the derived projection (D3), rebuildable by re-resolving."""
    entries = [resolve_entry(c, client=client) for c in contexts]
    return build_registry(entries, generated_at=generated_at)


# --------------------------------------------------------------------------- #
# Persistence (Phase 2 · Increment 3): write/read the derived projection to a single Scout-bucket-root
# object. Latest-state (overwrite) + readback SHA-256 verified; rebuildable. No production consumer yet.
# --------------------------------------------------------------------------- #
def _target(client, context: Optional[IssueContext]):
    """Resolve ``(client, bucket)`` for the Scout-bucket-root Registry object.

    The Registry is platform-wide, so only the Scout bucket + region are needed (no per-issue prefix).
    An explicit context supplies both; otherwise they come from the environment (byte-for-byte the
    ``scout_benchmark`` env pattern).
    """
    if context is not None:
        bucket, region = context.scout_bucket, context.scout_region
    else:
        bucket = os.getenv(scout_report_publisher.BUCKET_ENV)
        if not bucket:
            raise ScoutRegistryError(
                f"Scout Repository bucket not configured: set {scout_report_publisher.BUCKET_ENV}.")
        region = os.getenv(scout_report_publisher.REGION_ENV, scout_report_publisher.DEFAULT_REGION)
    client = client or scout_report_publisher._s3_client(region)
    return client, bucket


def persist_registry(registry: Mapping[str, Any], *, client=None,
                     context: Optional[IssueContext] = None) -> dict:
    """Write the derived Registry projection to ``registry/registry.json`` (latest-state overwrite),
    then read it back and byte-verify. Writes only ``edenseek-scout``. Returns the write summary."""
    client, bucket = _target(client, context)
    body = scout_report_publisher._dumps(registry)
    scout_report_publisher._put(client, bucket, REGISTRY_ARTIFACT_KEY, body, "application/json")
    scout_report_publisher._verify_readback(client, bucket, REGISTRY_ARTIFACT_KEY, body)
    logger.info("Registry persisted + verified: s3://%s/%s (%d issue(s))",
                bucket, REGISTRY_ARTIFACT_KEY, registry.get("count", 0))
    return {"bucket": bucket, "key": REGISTRY_ARTIFACT_KEY,
            "sha256": hashlib.sha256(body).hexdigest(), "count": registry.get("count", 0)}


def load_registry(*, client=None, context: Optional[IssueContext] = None) -> dict:
    """Read the persisted Registry (read-only). Returns an empty Registry when none exists yet."""
    client, bucket = _target(client, context)
    try:
        body = client.get_object(Bucket=bucket, Key=REGISTRY_ARTIFACT_KEY)["Body"].read()
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            return build_registry([])
        raise ScoutRegistryError(
            f"Unable to read Registry s3://{bucket}/{REGISTRY_ARTIFACT_KEY}: {e}") from e
    except BotoCoreError as e:
        raise ScoutRegistryError(
            f"Unable to read Registry s3://{bucket}/{REGISTRY_ARTIFACT_KEY}: {e}") from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ScoutRegistryError(
            f"Registry is not valid JSON (s3://{bucket}/{REGISTRY_ARTIFACT_KEY}): {e}") from e


def rebuild_registry(contexts, *, client=None, generated_at: Optional[str] = None) -> dict:
    """Resolve the Registry over ``contexts`` and persist it — the derived, rebuildable projection end
    to end. The persist target (bucket/region) comes from the first context (all share the Scout bucket)."""
    registry = resolve_registry(contexts, client=client, generated_at=generated_at)
    target_context = contexts[0] if contexts else None
    return persist_registry(registry, client=client, context=target_context)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rebuild_current(*, client=None, generated_at: Optional[str] = None) -> dict:
    """Governed one-shot: rebuild + persist the Registry for the env-configured single issue
    (tree-of-one). Builds the ``IssueContext`` from the environment (``IssueContext.from_env``), resolves
    it from authoritative Publisher data + Scout's index/ledger, and persists ``registry/registry.json``.

    Read-only on the Publisher; writes only ``edenseek-scout``. This is a **separate operational tool** —
    it is NOT part of the certified audit path. Returns the persist summary + the resolved entries.
    """
    context = IssueContext.from_env()
    generated_at = generated_at or _now_iso()
    registry = resolve_registry([context], client=client, generated_at=generated_at)
    summary = persist_registry(registry, client=client, context=context)
    return {**summary, "generated_at": generated_at, "entries": registry["entries"]}


def main(argv=None) -> int:
    """CLI trigger for the governed one-shot rebuild — the same entry a future scheduler would call."""
    import audit_review  # local import: the .env loader lives with the evidence layer
    audit_review._load_dotenv()
    # Prefer explicit access-key creds from .env; otherwise keep AWS_PROFILE (the VM's named profile).
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        os.environ.pop("AWS_PROFILE", None)
    try:
        summary = rebuild_current()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:  # noqa: BLE001 — CLI boundary; fail-loud with a log + exit 1
        logger.exception("Registry rebuild failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
