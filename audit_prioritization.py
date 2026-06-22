"""Deterministic review prioritization and page rollup for Phase 2.

Pure computation over the per-artifact assessments produced by
``audit_scoring`` — no I/O, no network, no LLM, no randomness, no time. Outputs
are advisory only: Scout ranks and recommends; it never approves, rejects,
locks, routes, or modifies datasets (Charter §4). Impact is reported as a
qualitative band (high/medium/low), never a numeric prediction.
"""
from audit_scoring import SEVERITY_RANK

# Qualitative impact band derived from a weakness severity.
IMPACT_BY_SEVERITY = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "low",
}
_IMPACT_RANK = {"high": 3, "medium": 2, "low": 1}

# Artifacts with no derivable page sort after all numbered pages.
_UNPAGED_SENTINEL = 10 ** 9


def _impact(severity):
    return IMPACT_BY_SEVERITY.get(severity, "low")


def _page_sort_key(page):
    return _UNPAGED_SENTINEL if not isinstance(page, int) else page


def prioritize(artifacts):
    """Rank weak artifacts into an advisory review worklist.

    Ordering (Option B — publisher workflow efficiency):
      severity desc  →  page asc (unpaged last)  →  effort asc  →  artifact_id asc.
    The artifact_id tiebreak makes this a strict, input-order-independent total
    order.
    """
    weak = [a for a in artifacts if a["weak"]]
    ordered = sorted(weak, key=lambda a: (
        -SEVERITY_RANK.get(a["severity"], 0),
        _page_sort_key(a["page"]),
        a["effort"],
        str(a["artifact_id"]),
    ))

    queue = []
    by_impact = {"high": 0, "medium": 0, "low": 0}
    for rank, a in enumerate(ordered, start=1):
        impact = _impact(a["severity"])
        by_impact[impact] += 1
        queue.append({
            "priority_rank": rank,
            "artifact_id": a["artifact_id"],
            "page": a["page"],
            "severity": a["severity"],
            "estimated_impact": impact,
            "effort": a["effort"],
            "blocking_issues": a["blocking_issues"],
            "primary_weakness": a["primary_weakness"],
            "suggested_action": a["suggested_action"],
        })
    return {"total": len(queue), "by_impact": by_impact, "queue": queue}


def build_page_heatmap(artifacts):
    """Aggregate weak signals per page; non-page ids go to an 'unpaged' bucket."""
    pages = {}
    for a in artifacts:
        key = a["page"] if isinstance(a["page"], int) else "unpaged"
        bucket = pages.setdefault(key, {
            "page": key,
            "artifact_count": 0,
            "weak_count": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        })
        bucket["artifact_count"] += 1
        if a["weak"]:
            bucket["weak_count"] += 1
            if a["severity"] in bucket["by_severity"]:
                bucket["by_severity"][a["severity"]] += 1

    rows = list(pages.values())
    for row in rows:
        worst = next((s for s in ("critical", "high", "medium", "low")
                      if row["by_severity"][s] > 0), None)
        row["page_impact"] = _impact(worst)

    rows.sort(key=lambda r: (
        -_IMPACT_RANK.get(r["page_impact"], 0),
        -r["weak_count"],
        _page_sort_key(r["page"]),
    ))

    unpaged_count = next((r["artifact_count"] for r in rows if r["page"] == "unpaged"), 0)
    return {"pages": rows, "unpaged_count": unpaged_count}
