"""scout_observability.py — Health Projections (ADR-0001 D8).

A general, read-only **Health Projection** capability: deterministic views that derive operational
intelligence **solely from certified Registry data**. This is the substrate for a family of projections —
Issue / Series / Publisher / Cross-Series / Trend / Retrieval health — each a pure, read-only view over
the Registry. It introduces **no new data source**, performs **no Publisher read**, makes **no mutation**;
it is advisory only (Charter §4).

Increment 1 implements the first concrete projection, **Issue Health**, plus the shared primitives the
later projections reuse:
- ``assess_issue`` — the atomic per-issue health rule (the leaf assessment every projection starts from);
- ``roll_up`` — the parent-from-children rule (how Series/Publisher/Cross-Series health will aggregate);
- ``_summary`` — health counts; and a common projection envelope (``projection`` name + ``summary`` +
  ``records``) so future projections are uniform.

Series/Publisher/Cross-Series/Trend/Retrieval health are later additive increments that compose these
primitives over the Registry's ``rollup`` / ``tree_view`` — they need no change here beyond adding a new
projection function + (when a second projection exists) a routing refactor.

Layering: imports only the standard library. It consumes a Registry object (dict) — the caller loads it via
``scout_registry.load_registry()`` — so this module is a **leaf** with no Scout-module imports and no I/O.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

HEALTH_VERSION = "v1"

# --- Health states (advisory) ------------------------------------------------------------------
HEALTHY = "healthy"
ATTENTION = "attention"
UNKNOWN = "unknown"

# --- Machine-readable reasons attached to a non-healthy issue ----------------------------------
REASON_NOT_PLATFORM_APPROVED = "not_platform_approved"
REASON_AUDIT_FAILED = "audit_failed"
REASON_AUDIT_PENDING = "audit_pending"
REASON_NO_PUBLISHED_REVISION = "no_published_revision"

# The Publisher publication-state value that denotes platform approval. Mirrors
# ``review_contract_adapter.STATE_EDENSEEK_APPROVED`` (drift-guarded by test) to keep this module a leaf.
STATE_EDENSEEK_APPROVED = "edenseek_approved"
# Registry audit-linkage states — mirror ``scout_registry`` (drift-guarded by test).
AUDIT_AUDITED = "audited"
AUDIT_FAILED = "failed"


def assess_issue(entry: Mapping[str, Any]) -> tuple[str, list[str]]:
    """The atomic per-issue health rule over a Registry entry (pure). Returns ``(health, reasons)``.

    - **healthy** — platform-approved (``state == edenseek_approved``) AND Scout's audit is current
      (``audit_state == audited``).
    - **attention** — published, but not platform-approved and/or the audit failed / is pending — each
      condition adds a machine-readable ``reason``.
    - **unknown** — no published revision (nothing to assess yet).

    Every higher-level projection (series/publisher/…) starts from this leaf assessment.
    """
    pub = entry.get("publication") or {}
    aud = entry.get("audit") or {}
    revision = pub.get("published_revision_id")
    state = pub.get("state")
    audit_state = aud.get("audit_state")

    if not revision:
        return UNKNOWN, [REASON_NO_PUBLISHED_REVISION]

    reasons: list[str] = []
    if state != STATE_EDENSEEK_APPROVED:
        reasons.append(REASON_NOT_PLATFORM_APPROVED)
    if audit_state == AUDIT_FAILED:
        reasons.append(REASON_AUDIT_FAILED)
    elif audit_state != AUDIT_AUDITED:
        reasons.append(REASON_AUDIT_PENDING)

    return (HEALTHY if not reasons else ATTENTION), reasons


def roll_up(statuses: Iterable[str]) -> str:
    """Parent health from child health — the shared primitive for future rollup projections
    (series / publisher / cross-series). Problems surface; full confidence requires all-healthy:

    any ``attention`` -> ``attention``; else all ``healthy`` -> ``healthy``; else (some ``unknown``, no
    ``attention``) -> ``unknown``; empty -> ``unknown``.
    """
    s = list(statuses)
    if not s:
        return UNKNOWN
    if ATTENTION in s:
        return ATTENTION
    if all(x == HEALTHY for x in s):
        return HEALTHY
    return UNKNOWN


def _summary(healths: Iterable[str]) -> dict:
    counts = {HEALTHY: 0, ATTENTION: 0, UNKNOWN: 0}
    total = 0
    for h in healths:
        counts[h] = counts.get(h, 0) + 1
        total += 1
    counts["total"] = total
    return counts


def _issue_record(issue_prefix: str, entry: Mapping[str, Any]) -> dict:
    pub = entry.get("publication") or {}
    aud = entry.get("audit") or {}
    health, reasons = assess_issue(entry)
    return {
        "issue_prefix": issue_prefix,
        "publisher_id": entry.get("publisher_id"),
        "title_group_id": entry.get("title_group_id"),
        "series_id": entry.get("series_id"),
        "issue_id": entry.get("issue_id"),
        "publication_state": pub.get("state"),
        "published_revision_id": pub.get("published_revision_id"),
        "audit_state": aud.get("audit_state"),
        "health": health,
        "reasons": reasons,
    }


def issue_health(registry: Mapping[str, Any]) -> dict:
    """The **Issue Health** projection — a deterministic, read-only view over a Registry object.

    Pure: derives from the passed Registry (no I/O, no wall-clock). ``registry_generated_at`` is carried
    through so consumers can see the freshness of the underlying data. Records are sorted by issue prefix.
    """
    entries = registry.get("entries") or {}
    records = [_issue_record(prefix, entries[prefix]) for prefix in sorted(entries)]
    return {
        "projection": "issue_health",
        "health_version": HEALTH_VERSION,
        "registry_version": registry.get("registry_version"),
        "registry_generated_at": registry.get("generated_at"),
        "summary": _summary(r["health"] for r in records),
        "records": records,
    }
