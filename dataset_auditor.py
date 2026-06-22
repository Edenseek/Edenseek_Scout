"""Phase 1 Dataset Auditor orchestration.

Read-only pipeline: load inputs → deterministic scoring → render reports →
persist a summary to the ``edenseek_dataset`` memory track. Never mutates
canonical inputs, approves metadata, or triggers itself (Charter §4).
"""
from datetime import datetime, timezone
from pathlib import Path
import os

from logging_config import logger
import audit_inputs
import audit_scoring
import audit_reports
import scout

DEFAULT_INPUT_DIR = "fixtures/dataset/society_of_killers/issue_1"
REPORTS_ROOT = Path("reports")


def _resolve_input_dir(input_dir):
    return input_dir or os.getenv("SCOUT_DATASET_DIR", DEFAULT_INPUT_DIR)


def run_dataset_audit(input_dir=None):
    """Run a full dataset audit and return a summary dict of the outcome."""
    input_dir = _resolve_input_dir(input_dir)
    logger.info(f"Dataset audit started: {input_dir}")

    inputs = audit_inputs.load_inputs(input_dir)
    result = audit_scoring.run_audit(inputs)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    latest_reports = audit_reports.write_reports(result, REPORTS_ROOT, generated_at)

    weak = result["blocks"]["weak_artifacts"]
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

    logger.info(
        f"Dataset audit complete: quality_score={result['quality_score']}, "
        f"flagged={weak['total_flagged']}/{result['artifact_count']}"
    )
    return {
        "dataset_id": result["dataset_id"],
        "quality_score": result["quality_score"],
        "scores": result["scores"],
        "artifact_count": result["artifact_count"],
        "weak_artifacts": summary["weak_artifacts_summary"],
        "reports": latest_reports,
    }
