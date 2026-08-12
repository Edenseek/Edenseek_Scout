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
import hashlib
import json
import sys
from collections import Counter

from logging_config import logger
import audit_review
import audit_s3_source
import scout_report_publisher as srp
import scout_report_index as sri
import scout_revision_ledger as ledger
from audit_review import AuditReviewError, EVALUATION_VERSION
from delta_auditor import SCOUT_DELTA_REPORT_VERSION, DELTA_ALGORITHM_VERSION
from delta_geometry import GEOMETRY_MATCH_VERSION
from delta_metadata_revision import (benchmark_headline, METADATA_REVISION_DISTANCE_VERSION,
                                     METADATA_ACCURACY_VERSION)
from delta_materials_grounding import MATERIALS_GROUNDING_VERSION
from review_contract_adapter import NORMALIZATION_VERSION

_SEVERITY_ORDER = ("FAIL", "WARNING", "INFO", "PASS")


def static_versions():
    """The static methodology versions that define the audit/comparability CONTEXT (independent of
    any single revision's evidence). Their fingerprint keys the idempotency ledger."""
    return {
        "report_version": SCOUT_DELTA_REPORT_VERSION,
        "algorithm_version": DELTA_ALGORITHM_VERSION,
        "geometry_match_version": GEOMETRY_MATCH_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "metadata_revision_distance_version": METADATA_REVISION_DISTANCE_VERSION,
        "metadata_accuracy_version": METADATA_ACCURACY_VERSION,
        "materials_grounding_version": MATERIALS_GROUNDING_VERSION,
        "evaluation_version": EVALUATION_VERSION,
    }


def _failure_stage(exc):
    """Map an exception to the pipeline stage that failed (for the ledger failure record)."""
    if isinstance(exc, AuditReviewError):
        return "evidence"
    if isinstance(exc, ValueError):
        return "assemble"            # build_report_body: no delta (contract not adapted)
    if isinstance(exc, srp.ScoutReportPublishError):
        return "persist_verify"      # write or read-back/hash verification
    if isinstance(exc, sri.ScoutReportIndexError):
        return "index"
    if isinstance(exc, ledger.ScoutRevisionLedgerError):
        return "ledger"
    return "unknown"


def _run_id(published_revision_id, generated_revision_id, comparability):
    """A deterministic LOGICAL run id: the same publication audited under the same methodology yields
    the same id, so retries are idempotent and cannot create duplicate logical runs."""
    basis = "|".join([published_revision_id or "", generated_revision_id or "",
                      comparability["geometry"], comparability["metadata"]])
    return "run_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


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
    pub_prov = ev.get("publisher_provenance", {}) or {}
    geometry_benchmark = (delta.get("geometry_delta") or {}).get("benchmark") or {}
    mb = delta.get("metadata_benchmark") or {"applicable": False}
    metadata_metrics = benchmark_headline(mb)
    # Compact metadata aggregate (counts + numerators/denominators, WITHOUT the per-field records)
    # carried on the report/entry so higher-level projections aggregate from counts, not percentages.
    # The block spreads the fresh-only `global`, so its sample-size uses the matching fresh artifact
    # count (not the all-common one) to stay internally consistent when preserved outputs exist.
    metadata_benchmark = ({"applicable": True,
                           "comparable_artifacts": mb.get("fresh_comparable_artifacts",
                                                          mb.get("comparable_artifacts")),
                           **mb["global"]} if mb.get("applicable") else {"applicable": False})
    # Dual time: event (Publisher publication) vs measurement (Scout). completed_at (measurement) is
    # stamped by the publisher; event/certified come from the evidence + Platform Approval.
    event_time = pub_prov.get("published_at")
    certified_at = ((delta.get("publisher_certified_state") or {}).get("platform_authority")
                    or {}).get("approved_at")

    body = {
        # --- comparability axes carried at top level (index projection reads these) ---
        "report_version": SCOUT_DELTA_REPORT_VERSION,
        "algorithm_version": DELTA_ALGORITHM_VERSION,
        "schema_version": _schema_version_str(sv),          # Publisher input-contract composite
        "evaluation_version": EVALUATION_VERSION,
        "schema_versions": sv,
        # --- identity + provenance (requirement 2) ---
        "issue_identity": ev.get("issue_identity", {}),
        "applicability": delta.get("applicability"),
        "provenance": {
            "review_id": delta.get("review_id"),
            "published_revision_id": prov.get("published_revision_id"),   # approved baseline (canonical key)
            # Populated alias so the delta report exposes the revision under the SAME name as the retrieval
            # report (`publisher_revision_id`) — was previously absent/null on this report type.
            "publisher_revision_id": prov.get("published_revision_id"),
            "generated_snapshot_revision_id": prov.get("generated_snapshot_revision_id"),  # generated
            "publication": {"chain_id": pub_prov.get("chain_id"),
                            "published_at": pub_prov.get("published_at"),
                            "initiating_user": pub_prov.get("initiating_user")},
            "source_versions": sv,
            "evidence_manifest_version": ev.get("manifest_version"),
            "normalization_version": prov.get("normalization_version"),
            "metadata_revision_distance_version": prov.get("metadata_revision_distance_version"),
            "geometry_detector": prov.get("geometry_detector"),
            "metadata_provenance": prov.get("metadata_provenance"),
        },
        "publisher_commit": view.get("publisher_commit") or ev.get("publisher_commit"),
        "scout_commit": view.get("scout_commit") or ev.get("scout_commit"),
        # --- dual time (event vs measurement) for time-series analysis ---
        "event_time": event_time,          # Publisher publication timestamp
        "certified_at": certified_at,      # Platform Approval certification timestamp
        # (measurement_time == completed_at, stamped at persistence)
        # --- measurement rollups carried on the entry for search/graph/benchmarks ---
        "metrics": metrics,
        "geometry_benchmark": geometry_benchmark,
        "metadata_benchmark": metadata_benchmark,
        "metadata_metrics": metadata_metrics,
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
    # Per-task comparability keys + a deterministic logical run id (for idempotency).
    body["comparability"] = sri.build_comparability(body)
    body["run_id"] = _run_id(prov.get("published_revision_id"),
                             prov.get("generated_snapshot_revision_id"), body["comparability"])
    return body


def run_and_persist(client=None, dry_run=False, context=None):
    """Run one audit, persist the report, and update the index — the full transaction.

    Returns a summary dict. ``dry_run`` assembles the report body and returns it without writing.
    Fail-loud on any error.
    """
    view = audit_review.build_audit_review(client=client, context=context)
    body = build_report_body(view)
    completed_at = view["audit_timestamp"]

    if dry_run:
        logger.info("Scout delta audit (dry-run): assembled report body; persisted nothing.")
        return {"status": "dry_run", "completed_at": completed_at, "report_body": body}

    # 1) persist the immutable report (history + latest), byte-verified. Idempotent on run_id.
    published = srp.publish_delta_report(body, completed_at, client=client, context=context)
    # 2) same transaction: project -> index entry, update the index (verified). update_index keys on
    #    run_seq, so re-running an already-persisted logical run reconciles rather than duplicates.
    entry = sri.build_index_entry({**published["envelope"],
                                   "report_sha256": published["report_sha256"]})
    index = sri.update_index(entry, client=client, context=context)

    logger.info("Scout delta audit %s %s (run_seq %s); index count=%d",
                "reconciled" if published.get("idempotent") else "persisted",
                published["report_id"], published["run_seq"], index["count"])
    return {
        "status": "reconciled" if published.get("idempotent") else "persisted",
        "report_id": published["report_id"],
        "run_id": entry["run_id"],
        "run_seq": published["run_seq"],
        "keys": published["keys"],
        "report_sha256": published["report_sha256"],
        "index_count": index["count"],
        "completed_at": completed_at,
        "published_revision_id": entry["published_revision_id"],
        "generated_snapshot_revision_id": entry["generated_snapshot_revision_id"],
        "geometry_comparability_key": entry["geometry_comparability_key"],
        "metadata_comparability_key": entry["metadata_comparability_key"],
    }


def audit_current_revision(client=None, force=False, trigger="manual", context=None):
    """THE canonical Scout delta-audit agent entry point — used by scheduled, reconciliation, and
    manual triggers alike. Idempotent and ledger-guarded.

    Flow: resolve the current certified revision → (cheap) skip if the ledger already marks it
    processed under the current methodology context → run the audit (evidence manifest + delta) →
    persist the immutable report → read it back + verify sha256 → update the latest pointer + index →
    mark the revision processed **only after all verified persistence steps succeed**. A failure at
    any stage is recorded in the ledger (with the failure stage + codes) and does NOT mark the
    revision processed. Read-only on the Publisher repository; writes only to ``edenseek-scout``.
    """
    client = client or audit_s3_source.s3_client(context.approved_region if context is not None else None)
    fingerprint = ledger.context_fingerprint(static_versions())

    # 1) detect the eligible revision (cheap: pointer read only).
    try:
        pointer = audit_s3_source.resolve_current_revision(client, context=context)
    except audit_s3_source.ScoutS3SourceError as e:
        logger.exception("Delta audit: could not resolve current revision: %s", e)
        return {"status": "error", "stage": "resolve", "error": str(e)}
    revision_id = pointer["revision_id"]

    # 2) suppress duplicates: already processed under this exact context?
    led = ledger.load_ledger(client, context=context)
    if not force and ledger.is_processed(led, revision_id, fingerprint):
        logger.info("Delta audit: revision %s already processed (fingerprint %s); skipping.",
                    revision_id, fingerprint)
        return {"status": "skipped", "revision_id": revision_id, "reason": "already_processed",
                "context_fingerprint": fingerprint}

    # 3) run + persist + verify + index (idempotent; safe to retry).
    try:
        result = run_and_persist(client=client, context=context)
    except Exception as e:  # noqa: BLE001 — recorded to the ledger with the failing stage
        stage = _failure_stage(e)
        ledger.mark_failed(revision_id, fingerprint, stage=stage, error_codes=[type(e).__name__],
                           trigger=trigger, client=client, context=context)
        logger.exception("Delta audit failed at stage=%s for revision %s: %s", stage, revision_id, e)
        return {"status": "failed", "revision_id": revision_id, "stage": stage, "error": str(e),
                "context_fingerprint": fingerprint}

    # 4) mark processed ONLY after verified persistence + index succeeded.
    ledger.mark_processed(
        revision_id, fingerprint, run_id=result["run_id"], run_seq=result["run_seq"],
        report_id=result["report_id"], completed_at=result["completed_at"],
        generated_snapshot_revision_id=result["generated_snapshot_revision_id"],
        comparability={"geometry": result["geometry_comparability_key"],
                       "metadata": result["metadata_comparability_key"]},
        trigger=trigger, client=client, context=context)
    return {"status": result["status"], "revision_id": revision_id, "run_id": result["run_id"],
            "run_seq": result["run_seq"], "report_id": result["report_id"],
            "index_count": result["index_count"], "context_fingerprint": fingerprint,
            "trigger": trigger}


def _rebuild_projections():
    """SXI-2e: after a multi-issue audit, refresh the DERIVED projections so the dashboard reflects the new
    reports (recompute-from-below): the publisher-wide Registry (drives Health) and the per-scope benchmark
    projections (drive the SXI-2c/2d per-scope + series-comparison views). Each rebuild is best-effort and
    NON-FATAL — the immutable reports are already persisted, so a rebuild failure is recorded, never fails the
    audit. Called with no client so each rebuild self-resolves its correctly-regioned client (Registry uses
    the approved region for Discovery + scout region for persist; benchmarks use the scout region)."""
    # Even the setup (imports + timestamp) is best-effort — _rebuild_projections must NEVER raise, so a
    # multi-issue audit whose reports are already persisted can never turn into a 503 over a refresh.
    try:
        import scout_registry
        import scout_benchmark
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception as e:  # noqa: BLE001 — pre-imported in every real entry path; guarded for defense-in-depth
        logger.exception("Post-audit rebuild setup failed: %s", e)
        return {"registry": f"failed: {type(e).__name__}", "benchmark": f"failed: {type(e).__name__}"}
    out = {}
    # One batch timestamp for BOTH projections so their freshness stamps agree.
    for name, fn in (("registry", lambda: scout_registry.rebuild_discovered(generated_at=ts)),
                     ("benchmark", lambda: scout_benchmark.rebuild_all(generated_at=ts))):
        try:
            fn()
            out[name] = "rebuilt"
        except Exception as e:  # noqa: BLE001 — best-effort; reports already persisted, so never fatal
            logger.exception("Post-audit %s rebuild failed: %s", name, e)
            out[name] = f"failed: {type(e).__name__}"
    logger.info("Post-audit projection rebuild: %s", out)
    return out


def audit_all_discovered(client=None, force=False, trigger="discovered", rebuild=False):
    """MULTI-ISSUE orchestrator (Increment 1) — audit EVERY published issue, not just the env-configured
    one. Enumerates issues via Discovery (read-only, published-only: keyed on ``/approved/published.json``),
    then runs the canonical ``audit_current_revision`` per discovered ``IssueContext``.

    Preserves every per-issue guarantee: each audit is idempotent + ledger-guarded (an already-processed
    revision skips), reads only that issue's approved surface, and writes only that issue's ``edenseek-scout``
    surface. Per-issue isolation — one issue's failure is recorded and never aborts the rest (mirrors the
    Registry rebuild). Deterministic order (Discovery returns sorted prefixes). Orchestration only; the
    per-issue audit is unchanged.

    ``rebuild=True`` (SXI-2e) additionally refreshes the derived Registry + benchmark projections AFTER the
    audit so the dashboard's Health and per-scope/series views reflect the new reports. Non-fatal; recorded
    under ``rebuild`` in the result. Default False preserves the certified Increment-1 behavior exactly.
    """
    import scout_discovery   # local import: keeps the module boundary one-directional
    contexts = scout_discovery.discover_contexts(client=client)
    results, counts = [], {}
    for ctx in contexts:
        try:
            r = audit_current_revision(client=client, force=force, trigger=trigger, context=ctx)
        except Exception as e:  # noqa: BLE001 — defensive: isolate a per-issue blow-up, never abort the run
            logger.exception("Multi-issue audit: unhandled error on %s: %s", ctx.scout_prefix, e)
            r = {"status": "error", "stage": "orchestrator", "error": str(e)}
        r = {**r, "issue_prefix": ctx.scout_prefix}
        results.append(r)
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1
    logger.info("Multi-issue audit: %d issue(s) discovered; status counts %s", len(contexts), counts)
    result = {"discovered": len(contexts), "counts": counts, "results": results, "trigger": trigger}
    if rebuild:
        result["rebuild"] = _rebuild_projections()
    return result


def main(argv=None):
    """Manual trigger — the same canonical agent entry point the scheduler/reconciliation use.
    ``--all`` audits every discovered issue (multi-issue); otherwise the single env-configured issue."""
    argv = argv if argv is not None else sys.argv[1:]
    try:
        if "--dry-run" in argv:
            result = run_and_persist(dry_run=True)
            print(json.dumps({k: v for k, v in result.items() if k != "report_body"}, indent=2))
        elif "--all" in argv:
            result = audit_all_discovered(force="--force" in argv, trigger="manual_all", rebuild=True)
            print(json.dumps(result, indent=2))
            return 0 if not (result["counts"].get("failed") or result["counts"].get("error")) else 1
        else:
            result = audit_current_revision(force="--force" in argv, trigger="manual")
            print(json.dumps(result, indent=2))
        return 0 if result.get("status") not in ("failed", "error") else 1
    except Exception as e:  # noqa: BLE001 — CLI boundary; fail-loud with a log + exit 1
        logger.exception("Scout delta audit failed: %s", e)
        return 1


if __name__ == "__main__":
    # CLI verification path: load .env so the scout-app creds + repo config are present.
    audit_review._load_dotenv()
    import os as _os
    # Prefer explicit access-key creds (dev .env) and only then drop an ambient AWS_PROFILE
    # so those keys win. When no access keys are present — e.g. the VM/systemd deployment
    # authenticates via a named AWS profile — keep AWS_PROFILE so boto3's default credential
    # chain can resolve it (otherwise boto3 raises NoCredentialsError).
    if _os.environ.get("AWS_ACCESS_KEY_ID"):
        _os.environ.pop("AWS_PROFILE", None)
    sys.exit(main())
