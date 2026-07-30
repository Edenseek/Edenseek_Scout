"""scout_observability.py — Health Projections (ADR-0001 D8).

A general, read-only **Health Projection** capability: deterministic views that derive operational
intelligence **solely from certified Registry data**. This is the substrate for a family of projections —
Issue / Series / Publisher / Cross-Series / Trend / Retrieval health — each a pure, read-only view over
the Registry. It introduces **no new data source**, performs **no Publisher read**, makes **no mutation**;
it is advisory only (Charter §4).

The projections form a hierarchy where **each level is a deterministic projection computed SOLELY from the
level beneath it** — Issue Health is the primitive; Series Health aggregates Issue Health; Publisher Health
aggregates Series Health; later levels (Cross-Series / Trend / Recommendations) build on those certified
projections. ``roll_up`` is a monotone max over ``attention > unknown > healthy``, so it is associative:
composing the levels yields the same result as rolling the leaves directly — the hierarchy is coherent by
construction.

Increment 1 implemented **Issue Health**; Increment 2 adds **Series Health** and **Publisher Health** as
aggregations. All share the primitives:
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


def _envelope(projection: str, registry: Mapping[str, Any], records: list) -> dict:
    return {
        "projection": projection,
        "health_version": HEALTH_VERSION,
        "registry_version": registry.get("registry_version"),
        "registry_generated_at": registry.get("generated_at"),
        "summary": _summary(r["health"] for r in records),
        "records": records,
    }


def _series_prefix(publisher_id, title_group_id, series_id) -> str:
    return f"publishers/{publisher_id}/title_groups/{title_group_id}/series/{series_id}"


def series_health(registry: Mapping[str, Any]) -> dict:
    """**Series Health** — a deterministic aggregation *of Issue Health*.

    Composes the level beneath (``issue_health``), groups the issue records by
    ``(publisher_id, title_group_id, series_id)``, and ``roll_up``s each group's issue healths into the
    series health (+ child issue counts). Pure; no new input beyond the Registry.
    """
    issue = issue_health(registry)
    groups: dict[tuple, list] = {}
    for rec in issue["records"]:
        key = (rec.get("publisher_id"), rec.get("title_group_id"), rec.get("series_id"))
        groups.setdefault(key, []).append(rec)

    records = []
    for (pub, tg, series), issues in sorted(groups.items(), key=lambda kv: tuple(x or "" for x in kv[0])):
        healths = [i["health"] for i in issues]
        records.append({
            "series_prefix": _series_prefix(pub, tg, series),
            "publisher_id": pub, "title_group_id": tg, "series_id": series,
            "health": roll_up(healths),
            "issue_counts": _summary(healths),
            "issues": [i["issue_id"] for i in issues],
        })
    return _envelope("series_health", registry, records)


def publisher_health(registry: Mapping[str, Any]) -> dict:
    """**Publisher Health** — a deterministic aggregation *of Series Health*.

    Composes the level beneath (``series_health``), groups the series records by ``publisher_id``, and
    ``roll_up``s each publisher's series healths into the publisher health (+ series counts, and a rollup of
    issue counts for visibility). Because ``roll_up`` is associative, this equals rolling all a publisher's
    issues directly — the hierarchy is coherent.
    """
    series = series_health(registry)
    groups: dict[str, list] = {}
    for rec in series["records"]:
        groups.setdefault(rec.get("publisher_id"), []).append(rec)

    records = []
    for pub, series_recs in sorted(groups.items(), key=lambda kv: kv[0] or ""):
        series_healths = [s["health"] for s in series_recs]
        issue_counts = {HEALTHY: 0, ATTENTION: 0, UNKNOWN: 0, "total": 0}
        for s in series_recs:
            for k in issue_counts:
                issue_counts[k] += s["issue_counts"].get(k, 0)
        records.append({
            "publisher_id": pub,
            "health": roll_up(series_healths),
            "series_counts": _summary(series_healths),
            "issue_counts": issue_counts,
            "series": [s["series_id"] for s in series_recs],
        })
    return _envelope("publisher_health", registry, records)
