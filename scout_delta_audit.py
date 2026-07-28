"""Agent runner: run the Scout Synchronization Audit and persist it + index it as one transaction.

This is **agent-side write work** (parallel to ``scout_audit.py``), not UI: it runs the deterministic
generated-vs-approved delta over the live Publisher evidence, assembles the versioned, provenance-
bearing report body, persists it to the Scout Repository (immutable history + latest-state, byte-
verified), and then updates the per-issue report index in the same transaction. The UI only ever
READS the persisted report + index; it never runs this.

Transaction semantics: the immutable report is written and verified FIRST; the index (a rebuildable
projection) is updated second. If the index update fails, the authoritative report is already
durable and the index is reconcilable with ``scout_report_index.rebuild_index``.

Read-only on the Publisher repository; writes only to ``edenseek-scout``. No LLM/vision.

Usage:
    python scout_delta_audit.py            # run + persist + index one audit, print the summary
    python scout_delta_audit.py --dry-run  # run + assemble the report body, persist nothing
Exit 0 on success, 1 on failure.
"""
import json
import sys
from collections import Counter

from logging_config import logger
import audit_review
import scout_report_publisher as srp
import scout_report_index as sri
from delta_auditor import SCOUT_DELTA_REPORT_VERSION, DELTA_ALGORITHM_VERSION
from audit_review import EVALUATION_VERSION

_SEVERITY_ORDER = ("FAIL", "WARNING", "INFO", "PASS")


def _schema_versions(delta):
    sv = (delta.get("provenance", {}) or {}).get("source_versions", {}) or {}
    return {
        "review_report": sv.get("review_report_version"),
        "platform_approval": sv.get("platform_approval_version"),
        "generated_snapshot": sv.get("generated_snapshot_version"),
    }


def _schema_version_str(sv):
    return (f"rr:{sv.get('review_report') or '-'}"
            f"|pa:{sv.get('platform_approval') or '-'}"
            f"|gs:{sv.get('generated_snapshot') or '-'}")


def build_report_body(view):
    """Assemble the versioned, provenance-bearing delta report body from an audit-review view
    (pure). Persistence assigns report_id/run_seq/completed_at/keys. Raises if the audit did not
    produce a delta (an un-adaptable contract must not be persisted as a report)."""
    delta = view.get("delta_report")
    if delta is None:
        raise ValueError("audit produced no delta report (contract not adapted); refusing to persist")

    ds = view["delta_summary"]
    g, m = ds["geometry"], ds["metadata"]
    metrics = {}
    if g.get("status") == "computed":
        metrics = {
            "precision": g.get("precision"), "recall": g.get("recall"),
            "split_rate": g.get("split_rate"), "merge_rate": g.get("merge_rate"),
            "missing_count": g.get("missing"), "spread_missing_count": g.get("spread_missing"),
            "false_count": g.get("false"),
        }

    findings = view.get("findings", [])
    counts = Counter(f["severity"] for f in findings)
    finding_counts = {s: counts.get(s, 0) for s in ("PASS", "WARNING", "FAIL", "INFO")}
    worst = next((s for s in _SEVERITY_ORDER if finding_counts.get(s)), "PASS")

    prov = delta.get("provenance", {}) or {}
    sv = _schema_versions(delta)
    ev = view["evidence"]
    return {
        # --- comparability axes (formal contract) ---
        "report_version": SCOUT_DELTA_REPORT_VERSION,
        "algorithm_version": DELTA_ALGORITHM_VERSION,
        "schema_version": _schema_version_str(sv),
        "evaluation_version": EVALUATION_VERSION,
        "schema_versions": sv,
        # --- identity + provenance ---
        "issue_identity": ev.get("issue_identity", {}),
        "applicability": delta.get("applicability"),
        "provenance": {
            "review_id": delta.get("review_id"),
            "published_revision_id": prov.get("published_revision_id"),
            "generated_snapshot_revision_id": prov.get("generated_snapshot_revision_id"),
        },
        "publisher_commit": view.get("publisher_commit") or ev.get("publisher_commit"),
        "scout_commit": view.get("scout_commit") or ev.get("scout_commit"),
        # --- measurement rollup carried on the entry for search/graph ---
        "metrics": metrics,
        "metadata_status": m.get("status"),
        "compared_artifacts": m.get("compared"),
        "finding_counts": finding_counts,
        "finding_codes": sorted({f["code"] for f in findings}),
        "worst_severity": worst,
        # --- full authoritative payload ---
        "findings": findings,
        "delta_report": delta,
        "delta_report_sha256": view.get("delta_report_sha256"),
        "evidence_summary": {
            "summary": ev.get("summary"),
            "objects": [{k: o.get(k) for k in ("role", "key", "status", "size", "sha256",
                                               "schema_version", "revision_id")}
                        for o in ev.get("objects", [])],
        },
    }


def run_and_persist(client=None, dry_run=False):
    """Run one audit, persist the report, and update the index — the full transaction.

    Returns a summary dict. ``dry_run`` assembles the report body and returns it without writing.
    Fail-loud on any error.
    """
    view = audit_review.build_audit_review(client=client)
    body = build_report_body(view)
    completed_at = view["audit_timestamp"]

    if dry_run:
        logger.info("Scout delta audit (dry-run): assembled report body; persisted nothing.")
        return {"status": "dry_run", "completed_at": completed_at, "report_body": body}

    # 1) persist the immutable report (history + latest), byte-verified.
    published = srp.publish_delta_report(body, completed_at, client=client)
    # 2) same transaction: project -> index entry, update the index (verified).
    entry = sri.build_index_entry({**published["envelope"],
                                   "report_sha256": published["report_sha256"]})
    index = sri.update_index(entry, client=client)

    logger.info("Scout delta audit persisted %s (run_seq %s); index count=%d",
                published["report_id"], published["run_seq"], index["count"])
    return {
        "status": "persisted",
        "report_id": published["report_id"],
        "run_seq": published["run_seq"],
        "keys": published["keys"],
        "report_sha256": published["report_sha256"],
        "index_count": index["count"],
        "comparability_key": entry["comparability_key"],
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv
    try:
        result = run_and_persist(dry_run=dry)
        print(json.dumps({k: v for k, v in result.items() if k != "report_body"}, indent=2))
        return 0
    except Exception as e:  # noqa: BLE001 — CLI boundary; fail-loud with a log + exit 1
        logger.exception("Scout delta audit failed: %s", e)
        return 1


if __name__ == "__main__":
    # CLI verification path: load .env so the scout-app creds + repo config are present.
    audit_review._load_dotenv()
    import os as _os
    _os.environ.pop("AWS_PROFILE", None)
    sys.exit(main())
