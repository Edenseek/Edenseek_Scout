"""Dataset Auditor orchestration (Phase 1 + Phase 2).

Read-only pipeline: load inputs → deterministic scoring → prioritization +
page rollup → render reports → persist summary and append an audit-history
snapshot to the ``edenseek_dataset`` memory track. Never mutates canonical
inputs, approves metadata, or triggers itself (Charter §4).
"""
from datetime import datetime, timezone
from pathlib import Path
import os

from logging_config import logger
import audit_inputs
import audit_scoring
import audit_prioritization
import audit_failure_analysis
import audit_retrieval_blockers
import audit_retrieval_readiness
import audit_history_analysis
import audit_digest
import audit_reports
import scout

DEFAULT_INPUT_DIR = "fixtures/dataset/society_of_killers/issue_1"
REPORTS_ROOT = Path("reports")


def _resolve_input_dir(input_dir):
    return input_dir or os.getenv("SCOUT_DATASET_DIR", DEFAULT_INPUT_DIR)


def _latest_delta(history):
    if len(history) < 2:
        return None
    change = history[-1]["quality_score"] - history[-2]["quality_score"]
    direction = "up" if change > 0 else "down" if change < 0 else "unchanged"
    return {"quality_score_change": change, "direction": direction}


def _retrieval_trend(historical):
    """Extract the retrieval_readiness trend from a Historical Intelligence block."""
    if not historical or historical.get("confidence") == "insufficient_history":
        return None
    metric = next((m for m in historical.get("metrics", []) if m["name"] == "retrieval_readiness"), None)
    if not metric:
        return None
    return {"retrieval_readiness": metric["direction"], "confidence": historical.get("confidence")}


def _derive_core_blocks(result):
    """Compute the history-independent derived blocks (Phase 2/3A/3B). Returns root_cause.

    Pure; mutates ``result['blocks']`` in place. Shared by the audit run and the
    read-only digest endpoint so the pipeline is defined once.
    """
    artifacts = result["artifacts"]
    result["blocks"]["review_priority"] = audit_prioritization.prioritize(artifacts)
    result["blocks"]["page_heatmap"] = audit_prioritization.build_page_heatmap(artifacts)
    root_cause = audit_failure_analysis.build_root_cause(artifacts)
    result["blocks"]["root_cause"] = root_cause
    result["blocks"]["highest_leverage"] = audit_failure_analysis.build_highest_leverage_failure(root_cause)
    result["blocks"]["failure_clusters"] = audit_failure_analysis.build_failure_clusters(artifacts)
    result["blocks"]["retrieval_blockers"] = audit_retrieval_blockers.build_retrieval_blockers(
        artifacts, result["blocks"]["retrieval"])
    return root_cause


def run_dataset_audit(input_dir=None):
    """Run a full dataset audit and return a summary dict of the outcome."""
    input_dir = _resolve_input_dir(input_dir)
    logger.info(f"Dataset audit started: {input_dir}")

    inputs = audit_inputs.load_inputs(input_dir)
    result = audit_scoring.run_audit(inputs)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    weak = result["blocks"]["weak_artifacts"]

    # ---- Phase 2/3A/3B derived blocks ----
    root_cause = _derive_core_blocks(result)

    # ---- Phase 2: append audit-history snapshot, then build the history block ----
    snapshot = {
        "timestamp": generated_at,
        "dataset_id": result["dataset_id"],
        "quality_score": result["quality_score"],
        "scores": result["scores"],
        "artifact_count": result["artifact_count"],
        "weak_total_flagged": weak["total_flagged"],
        "failure_summary": audit_failure_analysis.failure_summary(root_cause),
    }
    history = scout.record_audit_history(snapshot)
    result["blocks"]["audit_history"] = {"history": history, "latest_delta": _latest_delta(history)}
    # ---- Phase 4: historical intelligence (most-recent dataset) ----
    result["blocks"]["historical"] = audit_history_analysis.build_historical_intelligence(history)

    # ---- Phase 5: retrieval readiness intelligence (derived synthesis) ----
    result["blocks"]["retrieval_readiness"] = audit_retrieval_readiness.build_retrieval_readiness(
        result["blocks"]["retrieval"], result["blocks"]["retrieval_blockers"],
        _retrieval_trend(result["blocks"]["historical"]), result["dataset_id"])

    # ---- Phase D1: consolidated daily digest (pure projection over the blocks above) ----
    result["blocks"]["digest"] = audit_digest.build_digest(result["blocks"])

    latest_reports = audit_reports.write_reports(result, REPORTS_ROOT, generated_at)

    summary = {
        "quality_score": result["quality_score"],
        "artifact_count": result["artifact_count"],
        "scores": result["scores"],
        "weak_artifacts_summary": {
            "total_flagged": weak["total_flagged"],
            "by_severity": weak["by_severity"],
        },
        "latest_reports": latest_reports,
        "last_audit": generated_at,
    }
    scout.update_dataset_memory(summary)

    priority = result["blocks"]["review_priority"]
    logger.info(
        f"Dataset audit complete: quality_score={result['quality_score']}, "
        f"flagged={weak['total_flagged']}/{result['artifact_count']}, "
        f"prioritized={priority['total']}"
    )
    return {
        "dataset_id": result["dataset_id"],
        "quality_score": result["quality_score"],
        "scores": result["scores"],
        "artifact_count": result["artifact_count"],
        "weak_artifacts": summary["weak_artifacts_summary"],
        "priority": {"total": priority["total"], "by_impact": priority["by_impact"]},
        "page_heatmap": {"unpaged_count": result["blocks"]["page_heatmap"]["unpaged_count"]},
        "highest_leverage_failure": result["blocks"]["highest_leverage"]["highest_leverage_failure"],
        "reports": latest_reports,
    }


def _load_and_score(input_dir):
    inputs = audit_inputs.load_inputs(_resolve_input_dir(input_dir))
    return audit_scoring.run_audit(inputs)


def analyze_failures(input_dir=None):
    """Compute failure analysis without writing reports or memory (read-only).

    Pure and deterministic; used by the agent-facing `/audit/failures` endpoint.
    """
    result = _load_and_score(input_dir)
    root_cause = audit_failure_analysis.build_root_cause(result["artifacts"])
    return {
        "dataset_id": result["dataset_id"],
        "root_cause": root_cause,
        "highest_leverage": audit_failure_analysis.build_highest_leverage_failure(root_cause),
    }


def analyze_clusters(input_dir=None):
    """Compute failure clusters without writing reports or memory (read-only)."""
    result = _load_and_score(input_dir)
    return {
        "dataset_id": result["dataset_id"],
        "failure_clusters": audit_failure_analysis.build_failure_clusters(result["artifacts"]),
    }


def analyze_retrieval_blockers(input_dir=None):
    """Compute retrieval blockers without writing reports or memory (read-only)."""
    result = _load_and_score(input_dir)
    return {
        "dataset_id": result["dataset_id"],
        "retrieval_blockers": audit_retrieval_blockers.build_retrieval_blockers(
            result["artifacts"], result["blocks"]["retrieval"]),
    }


def analyze_trends(dataset_id=None):
    """Historical Intelligence over recorded snapshots (memory-only, read-only).

    Opens no canonical dataset; pure over ``audit_history``.
    """
    track = scout.load_memory().get("projects", {}).get("edenseek_dataset", {})
    history = track.get("audit_history", [])
    return audit_history_analysis.build_historical_intelligence(history, dataset_id)


def analyze_retrieval_readiness(input_dir=None):
    """Retrieval Readiness Intelligence verdict (read-only; no retrieval performed)."""
    result = _load_and_score(input_dir)
    retrieval_block = result["blocks"]["retrieval"]
    blockers = audit_retrieval_blockers.build_retrieval_blockers(result["artifacts"], retrieval_block)
    trend = _retrieval_trend(analyze_trends())
    return {
        "dataset_id": result["dataset_id"],
        "retrieval_readiness": audit_retrieval_readiness.build_retrieval_readiness(
            retrieval_block, blockers, trend, result["dataset_id"]),
    }


def analyze_digest(input_dir=None):
    """Consolidated daily digest (read-only; writes no reports or memory).

    Re-scores the dataset and projects the derived blocks plus the recorded
    history into the digest. Does not append a new history snapshot.
    """
    result = _load_and_score(input_dir)
    _derive_core_blocks(result)
    historical = analyze_trends()  # recorded history, most-recent dataset
    result["blocks"]["historical"] = historical
    result["blocks"]["retrieval_readiness"] = audit_retrieval_readiness.build_retrieval_readiness(
        result["blocks"]["retrieval"], result["blocks"]["retrieval_blockers"],
        _retrieval_trend(historical), result["dataset_id"])
    return {"dataset_id": result["dataset_id"], "digest": audit_digest.build_digest(result["blocks"])}
