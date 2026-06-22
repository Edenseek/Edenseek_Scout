"""Scout Daily Digest (Phase D1) — a consolidated, de-duplicated summary.

A **pure projection** over existing Phase 1–5 report blocks: it selects and
de-duplicates fields, performing **no new intelligence computation**. Read-only,
deterministic, advisory; no recommendations, no predictions, no schema change
(Charter §4).
"""
from audit_reports import REPORT_FILES

TOP_REVIEW_ITEMS = 5
_REVIEW_FIELDS = ("priority_rank", "artifact_id", "page", "severity",
                  "estimated_impact", "primary_weakness")


def build_digest(blocks):
    """Assemble the daily digest from already-computed audit blocks."""
    dataset = blocks.get("dataset", {})
    highest_leverage = blocks.get("highest_leverage", {})
    readiness = blocks.get("retrieval_readiness", {})
    review = blocks.get("review_priority", {})
    historical = blocks.get("historical", {})
    delta = historical.get("delta")

    grounding = next((d for d in readiness.get("dimensions", [])
                      if d.get("dimension") == "grounding_quality"), None)

    top_items = [{k: q.get(k) for k in _REVIEW_FIELDS}
                 for q in review.get("queue", [])[:TOP_REVIEW_ITEMS]]

    changes = None
    if delta:
        changes = {
            "quality_change": delta.get("metrics", {}).get("quality_score"),
            "new_failures": delta.get("new_failures", []),
            "resolved_failures": delta.get("resolved_failures", []),
        }

    return {
        "dataset_id": dataset.get("dataset"),
        "quality_score": dataset.get("quality_score"),
        "quality_delta": (delta or {}).get("metrics", {}).get("quality_score") if delta else None,
        "trend": {"confidence": historical.get("confidence")},
        "readiness": {
            "verdict": readiness.get("verdict"),
            "score": readiness.get("readiness_score"),
            "grounding_status": grounding["status"] if grounding else None,
            "weaknesses": readiness.get("weaknesses", []),
        },
        "highest_leverage_failure": highest_leverage.get("highest_leverage_failure"),
        "review": {
            "total": review.get("total", 0),
            "by_impact": review.get("by_impact", {}),
            "top_items": top_items,
        },
        "changes_since_last_audit": changes,
        "stagnant_domains": [d["domain"] for d in historical.get("stagnant_domains", [])],
        "report_links": {k: f"{v[0]}/{v[1]}" for k, v in REPORT_FILES.items()},
        "note": "Consolidated read-only summary derived from existing audit reports. Advisory "
                "only; Scout makes no recommendations or predictions.",
    }
