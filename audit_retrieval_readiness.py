"""Deterministic Retrieval Readiness Intelligence (Phase 5).

A synthesis layer that classifies the already-computed retrieval signals (Phase 1
retrieval block + Phase 3B Retrieval Blockers, with the optional Phase 4
retrieval-readiness trend) into four named readiness dimensions and an overall
verdict. **Assesses readiness only — never performs, implements, or alters
retrieval; no search, embeddings, LLM, or vision.** Read-only, deterministic,
fully derived (no new stored data). Diagnostic: no recommendations, no
predictions (Charter §4).
"""

# Status bands over measured percentages (authored, static).
STRONG_MIN = 80
ADEQUATE_MIN = 40


def _status(percent):
    if percent >= STRONG_MIN:
        return "strong"
    if percent >= ADEQUATE_MIN:
        return "adequate"
    return "weak"


def _pct(numer, denom):
    return round(100 * numer / denom) if denom else 0


def build_retrieval_readiness(retrieval_block, retrieval_blockers, retrieval_trend=None,
                              dataset_id=None):
    """Classify retrieval readiness into dimensions and a verdict (grounding is hard-stop)."""
    n_packets = retrieval_block.get("packets_evaluated", 0)
    findings = retrieval_block.get("findings", [])

    confidence_unscored = set()
    untraceable = set()
    for f in findings:
        pid = f.get("packet_id")
        gap = (f.get("gap") or "").lower()
        if "confidence" in gap:
            confidence_unscored.add(pid)
        if "matched_fields" in gap or "scope" in gap or "approved" in gap:
            untraceable.add(pid)

    coverage = retrieval_blockers.get("packet_coverage", {})
    coverage_pct = coverage.get("coverage_percent", 0)
    grounding_pct = _pct(n_packets - len(confidence_unscored), n_packets)
    traceability_pct = _pct(n_packets - len(untraceable), n_packets)

    no_grounding = next((b for b in retrieval_blockers.get("artifact_blockers", [])
                         if b.get("blocker_type") == "no_grounding"), None)
    boundaries_pct = 100 - (no_grounding["affected_percent"] if no_grounding else 0)

    packet_blocker_names = [pb.get("blocker", "") for pb in retrieval_blockers.get("packet_blockers", [])]

    def _contrib(keys):
        return [b for b in packet_blocker_names if any(k in b.lower() for k in keys)]

    dimensions = [
        _dim("coverage", coverage_pct,
             f"{coverage.get('artifacts_referenced', 0)} of {coverage.get('artifact_count', 0)} "
             f"artifacts referenced by evidence packets",
             ["low_packet_coverage"] if any("coverage" in b.lower() for b in packet_blocker_names) else []),
        _dim("grounding_quality", grounding_pct,
             f"{n_packets - len(confidence_unscored)} of {n_packets} packets have scored confidence",
             _contrib(["confidence"])),
        _dim("traceability", traceability_pct,
             f"{n_packets - len(untraceable)} of {n_packets} packets have matched fields, scope, "
             f"and approved artifacts",
             _contrib(["matched", "scope", "approved"])),
        _dim("confidence_boundaries", boundaries_pct,
             f"{boundaries_pct}% of artifacts carry a grounding description",
             ["no_grounding"] if no_grounding else []),
    ]

    grounding_status = next(d["status"] for d in dimensions if d["dimension"] == "grounding_quality")
    any_weak = any(d["status"] == "weak" for d in dimensions)
    if grounding_status == "weak":
        verdict = "not_ready"            # grounding is the hard-stop dimension
    elif any_weak:
        verdict = "partially_ready"
    else:
        verdict = "ready"

    strengths = [d["dimension"] for d in dimensions if d["status"] == "strong"]
    weaknesses = [d["dimension"] for d in dimensions if d["status"] == "weak"]
    explanation = verdict.replace("_", " ") + ": " + ", ".join(
        f"{d['dimension']} {d['status']} ({d['measured_percent']}%)" for d in dimensions) + "."

    return {
        "dataset_id": dataset_id,
        "verdict": verdict,
        "readiness_score": retrieval_block.get("retrieval_readiness_score", 0),
        "dimensions": dimensions,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "trend": retrieval_trend,
        "explanation": explanation,
        "note": "Assesses readiness only; Scout never performs or implements retrieval, and makes "
                "no recommendations or predictions.",
    }


def _dim(dimension, percent, evidence, contributing):
    return {
        "dimension": dimension,
        "status": _status(percent),
        "measured_percent": percent,
        "evidence": evidence,
        "contributing_blockers": contributing,
    }
