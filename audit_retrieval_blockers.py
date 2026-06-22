"""Deterministic retrieval-readiness blocker analysis (Phase 3B).

Evaluates how ready the dataset is for grounded retrieval / QA. **Assesses
readiness only** — it never performs, implements, or alters retrieval (Charter
§4). Pure: no I/O, no network, no LLM, no embeddings, no vision. Diagnostic, not
prescriptive; impact is a qualitative coverage band, never a numeric prediction.
"""
from audit_failure_analysis import _impact_band

# A non-empty summary shorter than this is a "thin" (weak) description (authored).
THIN_DESCRIPTION_CHARS = 40


def _missing_tag(a):
    return any(str(f).startswith("classification.tags.") for f in a["missing_fields"])


# Artifact-level retrieval blockers: (blocker_type, severity, predicate over an assessment).
_ARTIFACT_BLOCKERS = [
    ("no_grounding", "high", lambda a: a["summary_length"] == 0),
    ("thin_description", "medium", lambda a: 0 < a["summary_length"] < THIN_DESCRIPTION_CHARS),
    ("missing_characters", "medium", lambda a: not a["has_characters"]),
    ("missing_dialogue", "medium", lambda a: not a["has_dialogue"]),
    ("missing_page_linkage", "medium", lambda a: a["page"] is None),
    ("thin_metadata", "low", _missing_tag),
]


def build_retrieval_blockers(artifacts, retrieval_block):
    """Aggregate packet-level and artifact-level retrieval-readiness blockers."""
    n = len(artifacts)

    # ---- Packet coverage ----
    referenced = retrieval_block.get("artifacts_referenced", 0)
    coverage_percent = round(100 * referenced / n) if n else 0
    packet_coverage = {
        "packets_evaluated": retrieval_block.get("packets_evaluated", 0),
        "artifacts_referenced": referenced,
        "artifact_count": n,
        "coverage_percent": coverage_percent,
    }

    # ---- Packet blockers (from retrieval findings) ----
    packet_blockers = []
    by_gap = {}
    for f in retrieval_block.get("findings", []):
        gap = f.get("gap", "")
        entry = by_gap.setdefault(gap, {"blocker": gap, "severity": f.get("severity", "info"),
                                        "affected_packets": 0})
        entry["affected_packets"] += 1
    packet_blockers.extend(by_gap.values())
    if coverage_percent < 100:
        packet_blockers.append({
            "blocker": "low_packet_coverage",
            "severity": "high" if coverage_percent < 50 else "medium",
            "detail": f"Evidence packets reference only {referenced} of {n} artifacts "
                      f"({coverage_percent}%).",
            "affected_packets": packet_coverage["packets_evaluated"],
        })

    # ---- Artifact blockers (retrieval lens over per-artifact signals) ----
    artifact_blockers = []
    for blocker_type, severity, predicate in _ARTIFACT_BLOCKERS:
        count = sum(1 for a in artifacts if predicate(a))
        if not count:
            continue
        percent = round(100 * count / n) if n else 0
        artifact_blockers.append({
            "blocker_type": blocker_type,
            "severity": severity,
            "affected_count": count,
            "affected_percent": percent,
            "estimated_impact": _impact_band(percent),
        })
    artifact_blockers.sort(key=lambda b: (-b["affected_count"], b["blocker_type"]))

    return {
        "retrieval_readiness_score": retrieval_block.get("retrieval_readiness_score", 0),
        "packet_coverage": packet_coverage,
        "packet_blockers": packet_blockers,
        "artifact_blockers": artifact_blockers,
    }
