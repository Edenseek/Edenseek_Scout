"""Deterministic, read-only scoring engine for Scout Phase 1 dataset audits.

Pure computation: no file I/O, no network, no LLM, no randomness. Identical
inputs always yield identical outputs (Charter §5). ``characters`` and
``dialogue`` are treated as opaque lists and scored on presence only, until
populated data exists (see ``docs/architecture/DATASET_INPUT_CONTRACT.md`` §5).
"""
import re

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

# Artifact ids of the form ``page_<N>_panel_<M>`` encode their page; other id
# styles (colon-style, spreads) are bucketed as "unpaged" (no silent drop).
PAGE_RE = re.compile(r"^page_(\d+)_panel_\d+$")

# Sub-score weights for the overall quality score (sum to 1.0).
WEIGHTS = {
    "metadata_completeness": 0.30,
    "character_consistency": 0.25,
    "dialogue_completeness": 0.25,
    "retrieval_readiness": 0.20,
}

REVIEWED_STATE = "reviewed"
APPROVED_STATE = "creator_approved"

# Required metadata fields checked per artifact (dotted = nested in output).
_METADATA_FIELDS = [
    "artifact_id",
    "classification.tags.action",
    "classification.tags.mood",
    "classification.tags.setting",
    "narrative.summary",
]


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def _pct(numer, denom):
    if denom == 0:
        return 0.0
    return 100.0 * numer / denom


def _max_severity(severities):
    if not severities:
        return "info"
    return max(severities, key=lambda s: SEVERITY_RANK.get(s, 0))


def _derive_page(artifact_id):
    m = PAGE_RE.match(str(artifact_id))
    return int(m.group(1)) if m else None


def _metadata_field_checks(artifact_id, output):
    tags = (output.get("classification", {}) or {}).get("tags", {}) or {}
    narrative = output.get("narrative", {}) or {}
    return {
        "artifact_id": _nonempty_str(artifact_id),
        "classification.tags.action": _nonempty_str(tags.get("action")),
        "classification.tags.mood": _nonempty_str(tags.get("mood")),
        "classification.tags.setting": _nonempty_str(tags.get("setting")),
        "narrative.summary": _nonempty_str(narrative.get("summary")),
    }


def _analyze_artifacts(outputs, approved_ids):
    """Per-artifact pass producing the raw signals every report draws from."""
    per_artifact = []
    for out in outputs:
        aid = out.get("artifact_id")
        output = out.get("output", {}) or {}
        entities = output.get("entities", {}) or {}
        narrative = output.get("narrative", {}) or {}

        checks = _metadata_field_checks(aid, output)
        missing = [k for k, ok in checks.items() if not ok]
        present = sum(1 for ok in checks.values() if ok)

        characters = entities.get("characters", []) or []
        dialogue = narrative.get("dialogue", []) or []
        summary = narrative.get("summary")
        summary_length = len(summary) if isinstance(summary, str) else 0

        per_artifact.append({
            "artifact_id": aid,
            "page": _derive_page(aid),
            "meta_present": present,
            "meta_total": len(checks),
            "missing_fields": missing,
            "summary_length": summary_length,
            "has_characters": len(characters) > 0,
            "has_dialogue": len(dialogue) > 0,
            "is_reviewed": out.get("metadata_review_state") == REVIEWED_STATE,
            "is_locked": bool(out.get("metadata_locked")),
            "is_approved": aid in approved_ids,
            "status": out.get("status"),
        })
    return per_artifact


def _score_retrieval(packets, known_ids):
    findings = []
    packet_fractions = []
    referenced_ids = set()
    for idx, pkt in enumerate(packets):
        pid = f"packet_{idx}"
        pkt_artifacts = pkt.get("artifacts", []) or []
        for a in pkt_artifacts:
            if isinstance(a, dict) and a.get("artifact_id") is not None:
                referenced_ids.add(a.get("artifact_id"))
        checks = {
            "confidence_set": pkt.get("confidence") is not None,
            "matched_fields": bool(pkt.get("matched_fields")),
            "scope": _nonempty_str(pkt.get("scope")),
            "artifacts_approved": bool(pkt_artifacts) and all(
                a.get("approval_state") == APPROVED_STATE for a in pkt_artifacts
            ),
        }
        packet_fractions.append(sum(1 for ok in checks.values() if ok) / len(checks))

        if not checks["confidence_set"]:
            findings.append({"packet_id": pid, "gap": "Evidence confidence not scored (null).",
                             "severity": "high", "recommendation": "Score retrieval confidence for this packet."})
        if not checks["matched_fields"]:
            findings.append({"packet_id": pid, "gap": "No matched_fields recorded.",
                             "severity": "high", "recommendation": "Record matched fields so evidence is traceable."})
        if not checks["scope"]:
            findings.append({"packet_id": pid, "gap": "Packet scope is empty.",
                             "severity": "medium", "recommendation": "Define the retrieval scope for this packet."})
        if not checks["artifacts_approved"]:
            findings.append({"packet_id": pid, "gap": "Referenced artifact(s) not creator-approved.",
                             "severity": "high", "recommendation": "Ensure referenced artifacts are approved before retrieval use."})

    score = round(_pct(sum(packet_fractions), len(packet_fractions))) if packet_fractions else 0
    return score, findings, referenced_ids


def _weak_reasons(pa):
    """Ordered (text, severity) reasons an artifact is weak; empty if healthy."""
    reasons = []
    if pa["status"] != "complete":
        reasons.append(("Enrichment status not complete", "high"))
    if not pa["is_approved"]:
        reasons.append(("Not in approved dataset", "high"))
    if pa["missing_fields"]:
        reasons.append(("Missing metadata: " + ", ".join(pa["missing_fields"]), "high"))
    if not pa["is_reviewed"]:
        reasons.append(("Metadata unreviewed", "medium"))
    if not pa["has_characters"]:
        reasons.append(("No characters recognized", "medium"))
    if not pa["has_dialogue"]:
        reasons.append(("No dialogue populated", "medium"))
    if not pa["is_locked"]:
        reasons.append(("Metadata not locked", "low"))
    return reasons


_ACTION_BY_WEAKNESS = {
    "Enrichment status not complete": "Complete enrichment before review.",
    "Not in approved dataset": "Route to publisher review for approval.",
    "Metadata unreviewed": "Queue for metadata review.",
    "No characters recognized": "Run character recognition / add character references.",
    "No dialogue populated": "Run dialogue extraction for this artifact.",
    "Metadata not locked": "Lock metadata once reviewed.",
}


def _suggested_action(weakness):
    if weakness.startswith("Missing metadata:"):
        return "Populate the missing metadata fields before review."
    return _ACTION_BY_WEAKNESS.get(weakness, "Review this artifact.")


def assess_artifact(pa):
    """Full per-artifact assessment shared by the weak queue and prioritization.

    Pure and deterministic. ``weak`` is True when any blocking issue exists.
    """
    reasons = _weak_reasons(pa)
    blocking = [text for text, _ in reasons]
    severity = _max_severity([s for _, s in reasons]) if reasons else None
    # Primary weakness = first reason at the max severity (stable order).
    weakness = next((text for text, s in reasons if s == severity), None) if reasons else None
    dims = [
        pa["meta_present"] / pa["meta_total"],
        1.0 if pa["has_characters"] else 0.0,
        1.0 if pa["has_dialogue"] else 0.0,
        1.0 if pa["is_reviewed"] else 0.0,
        1.0 if pa["is_approved"] else 0.0,
    ]
    return {
        "artifact_id": pa["artifact_id"],
        "page": pa["page"],
        "weak": bool(reasons),
        "severity": severity,
        "primary_weakness": weakness,
        "blocking_issues": blocking,
        "effort": len(blocking),
        "suggested_action": _suggested_action(weakness) if weakness else None,
        "score": round(_pct(sum(dims), len(dims))),
        # Raw flags (structured signals for failure analysis — Phase 3+).
        "missing_fields": pa["missing_fields"],
        "summary_length": pa["summary_length"],
        "has_characters": pa["has_characters"],
        "has_dialogue": pa["has_dialogue"],
        "is_reviewed": pa["is_reviewed"],
        "is_locked": pa["is_locked"],
        "is_approved": pa["is_approved"],
        "status": pa["status"],
    }


def _build_weak_queue(assessments):
    queue = []
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in assessments:
        if not a["weak"]:
            continue
        queue.append({
            "artifact_id": a["artifact_id"],
            "score": a["score"],
            "weakness": a["primary_weakness"],
            "severity": a["severity"],
            "suggested_action": a["suggested_action"],
        })
        if a["severity"] in by_severity:
            by_severity[a["severity"]] += 1

    queue.sort(key=lambda q: (-SEVERITY_RANK.get(q["severity"], 0), q["score"], str(q["artifact_id"])))
    return queue, by_severity


def run_audit(inputs):
    """Score a loaded input set. Pure and deterministic; returns report blocks."""
    outputs = inputs["llm_outputs"]
    approved = inputs["approved_artifacts"]
    packets = inputs["packets"]
    dataset_id = inputs["dataset_id"]
    n = len(outputs)

    approved_ids = {a.get("artifact_id") for a in approved if isinstance(a, dict)}
    per_artifact = _analyze_artifacts(outputs, approved_ids)

    meta_present = sum(pa["meta_present"] for pa in per_artifact)
    meta_total = sum(pa["meta_total"] for pa in per_artifact)
    chars_present = sum(1 for pa in per_artifact if pa["has_characters"])
    dialogue_present = sum(1 for pa in per_artifact if pa["has_dialogue"])
    reviewed = sum(1 for pa in per_artifact if pa["is_reviewed"])
    locked = sum(1 for pa in per_artifact if pa["is_locked"])
    approved_count = sum(1 for pa in per_artifact if pa["is_approved"])

    metadata_completeness = round(_pct(meta_present, meta_total))
    character_consistency = round(_pct(chars_present, n))
    dialogue_completeness = round(_pct(dialogue_present, n))
    retrieval_readiness, retrieval_findings, retrieval_referenced = _score_retrieval(packets, approved_ids)

    scores = {
        "metadata_completeness": metadata_completeness,
        "character_consistency": character_consistency,
        "dialogue_completeness": dialogue_completeness,
        "retrieval_readiness": retrieval_readiness,
    }
    quality_score = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS))

    # ---- Dataset Quality block ----
    dataset_findings = []
    for pa in per_artifact:
        for field in pa["missing_fields"]:
            dataset_findings.append({
                "artifact_id": pa["artifact_id"],
                "issue": f"Missing metadata field: {field}",
                "severity": "high",
                "recommendation": f"Populate '{field}' before review.",
            })
    if approved_count < n:
        dataset_findings.append({
            "artifact_id": None,
            "issue": f"Approval backlog: {n - approved_count} of {n} artifacts are not in the approved dataset.",
            "severity": "high",
            "recommendation": "Route unapproved artifacts to publisher review (Scout does not approve).",
        })
    if reviewed < n:
        dataset_findings.append({
            "artifact_id": None,
            "issue": f"Review backlog: {n - reviewed} of {n} artifacts are unreviewed.",
            "severity": "medium",
            "recommendation": "Queue unreviewed artifacts for metadata review.",
        })

    fields_missing = sorted({f for pa in per_artifact for f in pa["missing_fields"]})
    dataset_block = {
        "dataset": dataset_id,
        "artifact_count": n,
        "quality_score": quality_score,
        "completeness": {
            "metadata_fields_present": meta_present,
            "metadata_fields_required": meta_total,
            "fields_missing": fields_missing,
        },
        "coverage": {"approved": approved_count, "reviewed": reviewed, "locked": locked, "total": n},
        "findings": dataset_findings,
    }

    # ---- Character Analysis block (recognition coverage) ----
    character_findings = []
    if chars_present < n:
        character_findings.append({
            "issue": f"{n - chars_present} of {n} artifacts have no recognized characters.",
            "severity": "medium",
            "recommendation": "Run character recognition; populated data enables consistency scoring (Phase 2).",
        })
    character_block = {
        "consistency_score": character_consistency,
        "characters": [],  # opaque list: no populated character data to enumerate (contract §5)
        "recognition_coverage": {"artifacts_with_characters": chars_present, "artifacts_total": n},
        "reference_materials": {"available": [], "unused": []},
        "findings": character_findings,
    }

    # ---- Dialogue Analysis block (population coverage) ----
    dialogue_findings = []
    if dialogue_present < n:
        dialogue_findings.append({
            "artifact_id": None,
            "issue": f"{n - dialogue_present} of {n} artifacts have no dialogue populated.",
            "confidence": None,
            "severity": "medium",
            "recommendation": "Run dialogue extraction; populated data enables OCR/confidence scoring (Phase 2).",
        })
    dialogue_block = {
        "dialogue_completeness_score": dialogue_completeness,
        "population_coverage": {"artifacts_with_dialogue": dialogue_present, "artifacts_total": n},
        "findings": dialogue_findings,
    }

    # ---- Retrieval Readiness block ----
    retrieval_block = {
        "retrieval_readiness_score": retrieval_readiness,
        "packets_evaluated": len(packets),
        "artifacts_referenced": len(retrieval_referenced),
        "findings": retrieval_findings,
    }

    # ---- Per-artifact assessments (shared by weak queue + Phase 2) ----
    assessments = [assess_artifact(pa) for pa in per_artifact]

    # ---- Weak Artifact Queue block ----
    queue, by_severity = _build_weak_queue(assessments)
    weak_block = {
        "total_flagged": len(queue),
        "by_severity": by_severity,
        "queue": queue,
    }

    return {
        "dataset_id": dataset_id,
        "artifact_count": n,
        "scores": scores,
        "quality_score": quality_score,
        "artifacts": assessments,
        "blocks": {
            "dataset": dataset_block,
            "character": character_block,
            "dialogue": dialogue_block,
            "retrieval": retrieval_block,
            "weak_artifacts": weak_block,
        },
    }
