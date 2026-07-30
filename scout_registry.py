"""scout_registry.py — the Scout Registry (ADR-0001 D3/D6).

A **derived, rebuildable projection** of the Publisher repository hierarchy, stored as **flat,
hierarchy-keyed per-issue entries**. The publisher/series/issue "tree" is a query/rollup VIEW over
that flat model — never a nested-storage commitment.

Phase 2 (behavior-neutral so far). Increment 1 introduced the Registry **data model + pure
projection/view functions**. Increment 2 adds **read-only resolvers** (``resolve_entry`` /
``resolve_registry``) that derive a Registry from authoritative Publisher objects (current revision +
platform-approval state) and Scout's own index/ledger (audit linkage). There is still **no
persistence and no production consumer** — nothing in the running pipeline reads, resolves, or
persists a Registry. Later increments (per ADR-0001 D7) persist the Registry (tree-of-one), then add
Discovery to populate it publisher-wide, then point the scheduler at it. Introducing this changes no
production behavior.

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

import json
from typing import Any, Mapping, Optional

import audit_s3_source
import scout_report_index
import scout_revision_ledger
from scout_context import IssueContext  # leaf import (scout_context depends on nothing Scout-side)

REGISTRY_VERSION = "v1"

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
