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

# Category each failure belongs to, for separated-but-visible clustering.
DOMAIN_CATEGORY = {
    "enrichment": "content",
    "enrichment_pipeline": "content",
    "ingestion": "content",
    "approval_workflow": "workflow",
}

# Failure Cluster thresholds (authored, static).
ISSUE_WIDE_THRESHOLD_PCT = 80      # overall coverage at/above which a failure is systemic
PAGE_CLUSTER_MIN_FRACTION = 0.50   # page affected-fraction at/above which it is a cluster
PAGE_CLUSTER_MIN_COUNT = 2         # minimum affected artifacts on a page to be a cluster

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


def _category(domain):
    return DOMAIN_CATEGORY.get(domain, "content")


def build_failure_clusters(artifacts):
    """Locate where failures concentrate: issue-wide, per-page, or in the unpaged bucket.

    Workflow (approval_workflow) failures remain visible and are tagged
    ``category: "workflow"`` so they are clearly separated from content failures
    rather than hidden. Pure and deterministic.
    """
    n = len(artifacts)
    page_totals = {}
    for a in artifacts:
        if isinstance(a["page"], int):
            page_totals[a["page"]] = page_totals.get(a["page"], 0) + 1

    issue_wide = []
    page_clusters = []
    unpaged_failures = []
    unpaged_total = sum(1 for a in artifacts if a["page"] is None)

    for defn in FAILURE_DEFS:
        affected = [a for a in artifacts if defn["predicate"](a)]
        count = len(affected)
        if not count:
            continue
        percent = round(100 * count / n) if n else 0
        category = _category(defn["domain"])
        base = {
            "failure_type": defn["failure_type"],
            "domain": defn["domain"],
            "category": category,
            "severity": defn["severity"],
        }

        if percent >= ISSUE_WIDE_THRESHOLD_PCT:
            issue_wide.append({**base, "affected_count": count, "affected_percent": percent,
                               "estimated_impact": _impact_band(percent)})
            continue

        # Localized page clusters (paged artifacts only).
        per_page = {}
        for a in affected:
            if isinstance(a["page"], int):
                per_page[a["page"]] = per_page.get(a["page"], 0) + 1
        for page, page_affected in per_page.items():
            page_total = page_totals.get(page, 0)
            if page_affected >= PAGE_CLUSTER_MIN_COUNT and page_total and \
                    page_affected / page_total >= PAGE_CLUSTER_MIN_FRACTION:
                conc = round(100 * page_affected / page_total)
                page_clusters.append({**base, "page": page, "affected_count": page_affected,
                                      "page_artifact_count": page_total,
                                      "concentration_percent": conc,
                                      "estimated_impact": _impact_band(conc)})

    # Unpaged bucket: failures concentrated among artifacts with no page linkage.
    unpaged_cluster = None
    if unpaged_total:
        unpaged_set = [a for a in artifacts if a["page"] is None]
        for defn in FAILURE_DEFS:
            c = sum(1 for a in unpaged_set if defn["predicate"](a))
            if c >= PAGE_CLUSTER_MIN_COUNT:
                unpaged_failures.append({
                    "failure_type": defn["failure_type"], "domain": defn["domain"],
                    "category": _category(defn["domain"]), "severity": defn["severity"],
                    "affected_count": c,
                })
        unpaged_failures.sort(key=lambda f: (-f["affected_count"],
                                             -SEVERITY_RANK.get(f["severity"], 0),
                                             f["failure_type"]))
        unpaged_cluster = {"artifact_count": unpaged_total, "failures": unpaged_failures}

    issue_wide.sort(key=lambda f: (-f["affected_count"], -SEVERITY_RANK.get(f["severity"], 0),
                                   f["failure_type"]))
    page_clusters.sort(key=lambda c: (c["page"], -c["concentration_percent"], c["failure_type"]))

    return {
        "artifact_count": n,
        "thresholds": {"issue_wide_percent": ISSUE_WIDE_THRESHOLD_PCT,
                       "page_fraction": PAGE_CLUSTER_MIN_FRACTION,
                       "min_count": PAGE_CLUSTER_MIN_COUNT},
        "issue_wide_failures": issue_wide,
        "page_clusters": page_clusters,
        "unpaged_cluster": unpaged_cluster,
    }
