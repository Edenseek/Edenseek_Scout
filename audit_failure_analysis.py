"""Deterministic dataset failure analysis (Phase 3A).

Pure aggregation over the per-artifact assessments from ``audit_scoring`` — no
I/O, no network, no LLM, no randomness. Diagnostic only: it identifies and
explains *why* the dataset is failing and where failures cluster. It does NOT
prescribe engineering actions, approve/reject anything, or predict numeric score
changes (Charter §4). Impact is a qualitative band derived from coverage.

The failure taxonomy and domain mapping below are **authored, static, and
human-owned**. Scout never modifies them (no autonomous self-modification).
"""
from audit_scoring import SEVERITY_RANK

# Authored failure taxonomy. Each entry: a stable failure_type, the pipeline
# domain it implicates, an inherent severity, and a structured predicate over an
# artifact assessment. Order is the canonical taxonomy order.
FAILURE_DEFS = [
    {"failure_type": "status_incomplete", "domain": "enrichment_pipeline", "severity": "high",
     "predicate": lambda a: a["status"] != "complete"},
    {"failure_type": "not_approved", "domain": "approval_workflow", "severity": "high",
     "predicate": lambda a: not a["is_approved"]},
    {"failure_type": "missing_metadata", "domain": "enrichment", "severity": "high",
     "predicate": lambda a: bool(a["missing_fields"])},
    {"failure_type": "unreviewed", "domain": "approval_workflow", "severity": "medium",
     "predicate": lambda a: not a["is_reviewed"]},
    {"failure_type": "missing_characters", "domain": "enrichment", "severity": "medium",
     "predicate": lambda a: not a["has_characters"]},
    {"failure_type": "missing_dialogue", "domain": "enrichment", "severity": "medium",
     "predicate": lambda a: not a["has_dialogue"]},
    {"failure_type": "unpaged", "domain": "ingestion", "severity": "low",
     "predicate": lambda a: a["page"] is None},
    {"failure_type": "not_locked", "domain": "approval_workflow", "severity": "low",
     "predicate": lambda a: not a["is_locked"]},
]

# Domains that reflect dataset/pipeline content quality vs. publisher process throughput.
CONTENT_DOMAINS = {"enrichment", "enrichment_pipeline", "ingestion"}
PROCESS_DOMAINS = {"approval_workflow"}

# Coverage-based impact band thresholds (authored). Impact reflects leverage —
# how widespread the failure is — not a predicted score change.
_IMPACT_HIGH_PCT = 50
_IMPACT_MEDIUM_PCT = 20

# Cap on enumerated artifact ids per failure in the JSON block (full count is always given).
_MAX_IDS = 200


def _impact_band(affected_percent):
    if affected_percent >= _IMPACT_HIGH_PCT:
        return "high"
    if affected_percent >= _IMPACT_MEDIUM_PCT:
        return "medium"
    return "low"


def build_root_cause(artifacts):
    """Aggregate artifact-level failures into the failure taxonomy (diagnostic)."""
    n = len(artifacts)
    failures = []
    for defn in FAILURE_DEFS:
        affected = [a for a in artifacts if defn["predicate"](a)]
        if not affected:
            continue
        count = len(affected)
        percent = round(100 * count / n) if n else 0
        pages = sorted({a["page"] for a in affected if isinstance(a["page"], int)})
        ids = sorted(str(a["artifact_id"]) for a in affected)
        failures.append({
            "failure_type": defn["failure_type"],
            "domain": defn["domain"],
            "severity": defn["severity"],
            "estimated_impact": _impact_band(percent),
            "affected_count": count,
            "affected_percent": percent,
            "affected_pages": pages,
            "affected_artifact_ids": ids[:_MAX_IDS],
            "affected_artifact_ids_truncated": max(0, count - _MAX_IDS),
            "explanation": f"{count} of {n} artifacts ({percent}%) exhibit '{defn['failure_type']}'.",
        })

    # Most prevalent first, then inherent severity, then stable by name.
    failures.sort(key=lambda f: (
        -f["affected_count"],
        -SEVERITY_RANK.get(f["severity"], 0),
        f["failure_type"],
    ))
    return {"artifact_count": n, "failures": failures}


def build_highest_leverage_failure(root_cause):
    """Identify the single largest content-quality failure category (diagnostic only).

    Reports the dominant failure, its scale, and a qualitative impact band — it
    does NOT recommend engineering actions or predict numeric score changes.
    Publisher-process backlog (approval/review/lock) is reported separately.
    """
    failures = root_cause["failures"]
    content = [f for f in failures if f["domain"] in CONTENT_DOMAINS]
    process = [f for f in failures if f["domain"] in PROCESS_DOMAINS]

    # Largest by coverage; ties broken by inherent severity then name.
    content_ranked = sorted(content, key=lambda f: (
        -f["affected_count"],
        -SEVERITY_RANK.get(f["severity"], 0),
        f["failure_type"],
    ))

    top = None
    if content_ranked:
        f = content_ranked[0]
        top = {
            "failure_type": f["failure_type"],
            "domain": f["domain"],
            "affected_count": f["affected_count"],
            "affected_percent": f["affected_percent"],
            "estimated_impact": f["estimated_impact"],
            "rationale": (
                f"Largest content-quality failure by coverage: affects "
                f"{f['affected_count']} of {root_cause['artifact_count']} artifacts "
                f"({f['affected_percent']}%)."
            ),
        }

    ranked = [{
        "failure_type": f["failure_type"],
        "domain": f["domain"],
        "affected_count": f["affected_count"],
        "affected_percent": f["affected_percent"],
        "estimated_impact": f["estimated_impact"],
    } for f in content_ranked]

    process_backlog = {f["failure_type"]: f["affected_count"] for f in process}

    return {
        "highest_leverage_failure": top,
        "ranked_failures": ranked,
        "process_backlog": process_backlog,
    }


def failure_summary(root_cause):
    """Compact {failure_type: affected_count} for history snapshots."""
    return {f["failure_type"]: f["affected_count"] for f in root_cause["failures"]}
