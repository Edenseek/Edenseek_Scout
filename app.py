import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from scout import generate_report, load_memory
from scheduler import start_scheduler
from typing import Optional

from dataset_auditor import (
    run_dataset_audit,
    analyze_failures,
    analyze_clusters,
    analyze_retrieval_blockers,
    analyze_retrieval_readiness,
    analyze_trends,
    analyze_digest,
)
from audit_inputs import AuditInputError
from audit_s3_source import ScoutS3SourceError
from audit_reports import REPORT_FILES, REPORTS_ROOT
from audit_review import build_evidence_manifest, build_audit_review, AuditReviewError
import scout_report_index
import scout_benchmark
import scout_archive
import scout_intelligence
import scout_registry
import scout_observability
import scout_schema
import scout_report_publisher
from logging_config import logger

app = FastAPI(title="Edenseek Scout")


@app.exception_handler(ScoutS3SourceError)
def _approved_source_unavailable(request: Request, exc: ScoutS3SourceError):
    """The canonical Approved-Dataset S3 source is unconfigured/unreachable. Degrade gracefully
    (503) instead of a hard 500 — the legacy dataset-audit endpoints (/audit/*) only caught
    AuditInputError, so this class previously escaped as an unhandled 500. Backward-compatible:
    endpoints that already return 422/503 are unaffected."""
    logger.warning(f"Approved-Dataset source unavailable: {exc}")
    return JSONResponse(status_code=503,
                        content={"detail": f"Approved-Dataset source unavailable: {exc}"})


security = HTTPBasic()

SCOUT_USERNAME = os.getenv("SCOUT_USERNAME", "derek")
SCOUT_PASSWORD = os.getenv("SCOUT_PASSWORD")


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if SCOUT_PASSWORD is None:
        raise HTTPException(status_code=500, detail="Scout password not configured")

    username_ok = secrets.compare_digest(credentials.username, SCOUT_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, SCOUT_PASSWORD)

    if not (username_ok and password_ok):
        logger.warning("Authentication failed")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.on_event("startup")
def startup_event():
    logger.info("Edenseek Scout app starting")
    start_scheduler()
    logger.info("Edenseek Scout startup complete")


REPORTS_DIR = Path("reports")


@app.get("/")
def root():
    return {
        "name": "Edenseek Scout",
        "status": "online"
    }


@app.get("/health")
def health():
    return {
        "status": "online"
    }


@app.post("/run-scout")
def run_scout(username: str = Depends(require_auth)):
    logger.info("Manual Scout run requested")

    try:
        report_path = generate_report()
        logger.info(f"Manual Scout run completed: {report_path}")

        return {
            "status": "success",
            "report": report_path
        }

    except Exception as e:
        logger.exception(f"Manual Scout run failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Scout report generation failed"
        )

@app.get("/reports")
def list_reports(username: str = Depends(require_auth)):
    REPORTS_DIR.mkdir(exist_ok=True)

    reports = sorted(
        [file.name for file in REPORTS_DIR.glob("*.md")],
        reverse=True
    )

    return {
        "reports": reports
    }


@app.get("/report/{filename}", response_class=PlainTextResponse)
def get_report(filename: str, username: str = Depends(require_auth)):
    reports_root = REPORTS_DIR.resolve()
    report_path = (REPORTS_DIR / filename).resolve()

    if reports_root not in report_path.parents:
        logger.warning(f"Blocked path traversal attempt: {filename}")
        raise HTTPException(status_code=400, detail="Invalid report path")

    if not report_path.exists() or not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")

    return report_path.read_text(encoding="utf-8")


@app.get("/dashboard")
def dashboard(username: str = Depends(require_auth)):
    return FileResponse("static/index.html")


@app.post("/run-audit")
def run_audit(username: str = Depends(require_auth)):
    logger.info("Manual dataset audit requested")

    try:
        result = run_dataset_audit()
        logger.info(f"Manual dataset audit completed: {result['dataset_id']}")
        return {"status": "success", **result}

    except AuditInputError as e:
        logger.warning(f"Dataset audit input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")

    except Exception as e:
        logger.exception(f"Manual dataset audit failed: {e}")
        raise HTTPException(status_code=503, detail="Dataset audit failed")


@app.post("/run-delta-audit")
def run_delta_audit_endpoint(username: str = Depends(require_auth)):
    """Manually trigger the geometry/metadata DELTA audit on the current approved revision — the SAME
    canonical entry point (`audit_current_revision`) the scheduler reconciliation uses, so the founder can
    run it from the online Scout instead of the VM shell. Read-and-advise: it audits + persists an
    immutable Scout report to `edenseek-scout` and never writes Publisher data. Idempotent on run_id — a
    revision already processed under the current methodology returns ``skipped`` (a no-op success)."""
    logger.info("Manual delta audit requested")
    try:
        import scout_delta_audit
        result = scout_delta_audit.audit_current_revision(trigger="manual")
    except Exception as e:  # noqa: BLE001 — endpoint boundary; fail as 503 with a logged cause
        logger.exception(f"Manual delta audit failed: {e}")
        raise HTTPException(status_code=503, detail="Delta audit failed")
    status = result.get("status")
    if status in ("failed", "error"):
        logger.warning(f"Manual delta audit did not complete: {result}")
        raise HTTPException(status_code=503,
                            detail=f"Delta audit {status}: {result.get('error') or result.get('stage')}")
    # status is persisted | reconciled | skipped — returned verbatim so the UI can distinguish a fresh
    # run from an idempotent no-op.
    logger.info("Manual delta audit %s: run_seq=%s revision=%s",
                status, result.get("run_seq"), result.get("revision_id"))
    return result


@app.post("/run-delta-audit-all")
def run_delta_audit_all_endpoint(username: str = Depends(require_auth)):
    """Manually trigger the MULTI-ISSUE delta audit — audit EVERY published issue (Discovery-enumerated),
    not just the env-configured one (Increment 1). Read-and-advise: per-issue idempotent + ledger-guarded,
    reads only published approved surfaces, writes only `edenseek-scout`. Per-issue isolation — one issue's
    failure is recorded in the result, never aborts the run. Returns the aggregate {discovered, counts,
    results}. After the audit it refreshes the derived Registry + benchmark projections (SXI-2e) so the
    dashboard's Health and per-scope/series views reflect the new reports (non-fatal; under `rebuild`). 503
    only if the orchestrator itself blows up (a discovery/config error), not for an individual issue's failure
    (those are in `results`)."""
    logger.info("Multi-issue delta audit requested")
    try:
        import scout_delta_audit
        result = scout_delta_audit.audit_all_discovered(trigger="manual_all", rebuild=True, dataset=True)
    except Exception as e:  # noqa: BLE001 — endpoint boundary; a discovery/config failure -> 503
        logger.exception(f"Multi-issue delta audit failed: {e}")
        raise HTTPException(status_code=503, detail="Multi-issue delta audit failed")
    logger.info("Multi-issue delta audit: %s issue(s), counts=%s",
                result.get("discovered"), result.get("counts"))
    return result


@app.get("/audit/reports")
def list_audit_reports(username: str = Depends(require_auth)):
    reports = {}
    for report_type, (subdir, filename) in REPORT_FILES.items():
        path = REPORTS_ROOT / subdir / filename
        reports[report_type] = path.as_posix() if path.is_file() else None
    return {"reports": reports}


@app.get("/audit/report/{report_type}", response_class=PlainTextResponse)
def get_audit_report(report_type: str, username: str = Depends(require_auth)):
    if report_type not in REPORT_FILES:
        raise HTTPException(status_code=404, detail="Unknown report type")

    subdir, filename = REPORT_FILES[report_type]
    reports_root = REPORTS_ROOT.resolve()
    report_path = (REPORTS_ROOT / subdir / filename).resolve()

    if reports_root not in report_path.parents:
        logger.warning(f"Blocked path traversal attempt: {report_type}")
        raise HTTPException(status_code=400, detail="Invalid report path")

    if not report_path.exists() or not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not generated yet")

    return report_path.read_text(encoding="utf-8")


@app.get("/audit/priority", response_class=PlainTextResponse)
def get_audit_priority(username: str = Depends(require_auth)):
    subdir, filename = REPORT_FILES["review_priority"]
    report_path = REPORTS_ROOT / subdir / filename
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Priority queue not generated yet")
    return report_path.read_text(encoding="utf-8")


@app.get("/audit/history")
def get_audit_history(username: str = Depends(require_auth)):
    memory = load_memory()
    track = memory.get("projects", {}).get("edenseek_dataset", {})
    return {"audit_history": track.get("audit_history", [])}


@app.get("/audit/failures")
def get_audit_failures(username: str = Depends(require_auth)):
    try:
        return analyze_failures()
    except AuditInputError as e:
        logger.warning(f"Failure analysis input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")


@app.get("/audit/clusters")
def get_audit_clusters(username: str = Depends(require_auth)):
    try:
        return analyze_clusters()
    except AuditInputError as e:
        logger.warning(f"Cluster analysis input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")


@app.get("/audit/retrieval-blockers")
def get_audit_retrieval_blockers(username: str = Depends(require_auth)):
    try:
        return analyze_retrieval_blockers()
    except AuditInputError as e:
        logger.warning(f"Retrieval blocker analysis input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")


@app.get("/audit/trends")
def get_audit_trends(dataset_id: Optional[str] = None, username: str = Depends(require_auth)):
    # Historical Intelligence reads only recorded snapshots; no dataset is opened.
    return analyze_trends(dataset_id)


@app.get("/audit/retrieval-readiness")
def get_audit_retrieval_readiness(username: str = Depends(require_auth)):
    try:
        return analyze_retrieval_readiness()
    except AuditInputError as e:
        logger.warning(f"Retrieval readiness input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")


@app.get("/audit/digest")
def get_audit_digest(username: str = Depends(require_auth)):
    try:
        return analyze_digest()
    except AuditInputError as e:
        logger.warning(f"Digest input error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid audit input: {e}")


@app.get("/audit-review/evidence")
def get_audit_review_evidence(username: str = Depends(require_auth)):
    """Read-only Consumed-Evidence Manifest for the configured issue + current certified revision.

    Reports every Publisher object Scout consumed (key/status/size/sha256/version/revision/schema)
    plus permanent audit metadata + a health summary. GetObject-only; writes nothing.
    """
    try:
        return build_evidence_manifest()
    except AuditReviewError as e:
        logger.warning(f"Audit-review evidence error: {e}")
        raise HTTPException(status_code=503, detail=f"Audit-review evidence unavailable: {e}")


@app.get("/audit-review/audit")
def get_audit_review_audit(username: str = Depends(require_auth)):
    """Read-only full audit-review view: evidence manifest + live delta + Publisher/Scout state
    side by side + PASS/WARNING/FAIL/INFO findings + the delta report. Computes/persists nothing.
    """
    try:
        return build_audit_review()
    except AuditReviewError as e:
        logger.warning(f"Audit-review audit error: {e}")
        raise HTTPException(status_code=503, detail=f"Audit-review unavailable: {e}")


@app.get("/audit-review/reports")
def get_audit_review_reports(username: str = Depends(require_auth)):
    """Read-only report index: the newest-first archive of persisted Scout delta reports with the
    latest pointer + per-report searchable metadata. Reads the persisted projection only; it does
    not run or recompute audits. (Search/filter + metric graphs are the next slice.)
    """
    try:
        return scout_report_index.load_index()
    except scout_report_index.ScoutReportIndexError as e:
        logger.warning(f"Report index error: {e}")
        raise HTTPException(status_code=503, detail=f"Report index unavailable: {e}")


def _issue_context(issue_prefix: str):
    """Resolve an ``IssueContext`` for a dashboard-selected issue prefix, or ``None`` for the env
    default (unchanged single-issue behavior). A malformed prefix is a 400 (client error), not a 503;
    a config/discovery failure propagates to the caller's 503 handler. (SXI-2a multi-issue scoping.)"""
    if not issue_prefix:
        return None
    import scout_discovery
    import scout_context
    try:
        return scout_discovery.context_for_prefix(issue_prefix)
    except scout_context.IssueContextError as e:
        raise HTTPException(status_code=400, detail=f"Invalid issue_prefix: {e}")


@app.get("/issues")
def list_issues(username: str = Depends(require_auth)):
    """Enumerate discovered published issues (read-only) so the dashboard can scope the analytical
    views to a chosen issue. Each entry carries the full identity + the ``issue_prefix`` used to scope
    /audit-review/archive, /audit-review/search and /reports/*. Multi-issue (Increment 1 Discovery)."""
    try:
        import scout_discovery
        contexts = scout_discovery.discover_contexts()
    except Exception as e:  # noqa: BLE001 — a discovery/config failure -> 503
        logger.exception(f"Issue enumeration failed: {e}")
        raise HTTPException(status_code=503, detail="Issue enumeration failed")
    return {"issues": [{"issue_prefix": c.scout_prefix, **c.identity} for c in contexts]}


@app.get("/audit-review/archive")
def get_audit_review_archive(issue_prefix: str = "", username: str = Depends(require_auth)):
    """Read-only Reports Archive (newest first): successful reports + failed runs, with latest/
    historical/failed marks and methodology boundaries. Reads persisted index + ledger only.
    Optional ``issue_prefix`` scopes the archive to a chosen discovered issue; default = configured."""
    try:
        return scout_archive.build_archive(context=_issue_context(issue_prefix))
    except HTTPException:
        raise
    except (scout_report_index.ScoutReportIndexError, Exception) as e:  # noqa: BLE001
        logger.warning(f"Archive error: {e}")
        raise HTTPException(status_code=503, detail=f"Archive unavailable: {e}")


@app.get("/audit-review/search")
def get_audit_review_search(q: str = "", issue_prefix: str = "", username: str = Depends(require_auth)):
    """Server-side search over persisted archive metadata (e.g. `precision<0.80`,
    `finding:geometry.false_panels`, `severity:WARNING`, `publisher:<id> issue:<id>`). The browser
    passes the query; all filtering happens here. Optional ``issue_prefix`` scopes to a chosen issue."""
    try:
        archive = scout_archive.build_archive(context=_issue_context(issue_prefix))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Search error: {e}")
        raise HTTPException(status_code=503, detail=f"Search unavailable: {e}")
    return scout_archive.search_archive(archive, q)


@app.get("/intelligence/geometry")
def get_geometry_intelligence(level: str = "", issue_prefix: str = "",
                              username: str = Depends(require_auth)):
    """Read-only Geometry Intelligence projection — recurring panel failure modes + version-correlated
    improvements, consuming the persisted report index. Advisory only; mutates nothing. Optional ``level``
    (platform | publisher | series | issue) + ``issue_prefix`` aggregate ACROSS issues at that scope
    (SXI-2c); default = the configured single issue. A bad level/scope is a 400."""
    try:
        if level:
            return scout_intelligence.build_geometry_intelligence_scoped(level=level, issue_prefix=issue_prefix)
        return scout_intelligence.build_geometry_intelligence(context=_issue_context(issue_prefix))
    except HTTPException:
        raise
    except (ValueError, KeyError, IndexError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {e}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Geometry intelligence error: {e}")
        raise HTTPException(status_code=503, detail=f"Geometry intelligence unavailable: {e}")


@app.get("/intelligence/metadata")
def get_metadata_intelligence(level: str = "", issue_prefix: str = "",
                              username: str = Depends(require_auth)):
    """Read-only Metadata Intelligence projection — weak fields, edit classes, prompt/model/schema
    correlations, consuming the persisted index + immutable reports. Advisory only; mutates nothing.
    Optional ``level`` + ``issue_prefix`` aggregate ACROSS issues at that scope (SXI-2c); default = the
    configured single issue. A bad level/scope is a 400."""
    try:
        if level:
            return scout_intelligence.build_metadata_intelligence_scoped(level=level, issue_prefix=issue_prefix)
        return scout_intelligence.build_metadata_intelligence(context=_issue_context(issue_prefix))
    except HTTPException:
        raise
    except (ValueError, KeyError, IndexError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {e}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Metadata intelligence error: {e}")
        raise HTTPException(status_code=503, detail=f"Metadata intelligence unavailable: {e}")


@app.get("/registry")
def get_registry(username: str = Depends(require_auth)):
    """Read-only Registry: the derived, flat hierarchy-keyed projection of per-issue state
    (ADR-0001 D3/D6), as persisted at ``registry/registry.json``. Observational; mutates nothing.
    Returns an empty Registry (count 0) when none has been persisted yet."""
    try:
        return scout_registry.load_registry()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Registry error: {e}")
        raise HTTPException(status_code=503, detail=f"Registry unavailable: {e}")


@app.get("/registry/tree")
def get_registry_tree(username: str = Depends(require_auth)):
    """Read-only publisher -> title_group -> series -> issue rollup VIEW over the flat Registry
    (D6: the tree is a view, not storage). Tree-of-one today."""
    try:
        return scout_registry.tree_view(scout_registry.load_registry())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Registry tree error: {e}")
        raise HTTPException(status_code=503, detail=f"Registry tree unavailable: {e}")


@app.get("/observability/health")
def get_observability_health(username: str = Depends(require_auth)):
    """Read-only **Issue Health** projection (ADR-0001 D8): deterministic health derived SOLELY from the
    persisted Registry — per-issue health (healthy / attention / unknown + reasons) + a platform summary.
    Advisory only; mutates nothing; no Publisher access. The first of the D8 Health Projections."""
    try:
        return scout_observability.issue_health(scout_registry.load_registry())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Observability health error: {e}")
        raise HTTPException(status_code=503, detail=f"Observability health unavailable: {e}")


@app.get("/observability/health/series")
def get_observability_health_series(username: str = Depends(require_auth)):
    """Read-only **Series Health** projection (ADR-0001 D8): a deterministic aggregation of Issue Health by
    series (roll-up over each series' issues). Advisory; Registry-derived; mutates nothing."""
    try:
        return scout_observability.series_health(scout_registry.load_registry())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Series health error: {e}")
        raise HTTPException(status_code=503, detail=f"Series health unavailable: {e}")


@app.get("/observability/health/publisher")
def get_observability_health_publisher(username: str = Depends(require_auth)):
    """Read-only **Publisher Health** projection (ADR-0001 D8): a deterministic aggregation of Series Health
    by publisher. Advisory; Registry-derived; mutates nothing."""
    try:
        return scout_observability.publisher_health(scout_registry.load_registry())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Publisher health error: {e}")
        raise HTTPException(status_code=503, detail=f"Publisher health unavailable: {e}")


@app.get("/observability/health/cross-series")
def get_observability_health_cross_series(username: str = Depends(require_auth)):
    """Read-only **Cross-Series Health** projection (ADR-0001 D8): a deterministic platform-wide comparison
    of Series Health — series distribution + the actionable attention set. Advisory; Registry-derived;
    mutates nothing."""
    try:
        return scout_observability.cross_series_health(scout_registry.load_registry())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cross-series health error: {e}")
        raise HTTPException(status_code=503, detail=f"Cross-series health unavailable: {e}")


@app.get("/reports/latest")
def get_latest_report(issue_prefix: str = "", username: str = Depends(require_auth)):
    """The current/latest persisted immutable Scout delta report (read-only). Optional ``issue_prefix``
    scopes to a chosen discovered issue's latest; default = the configured issue."""
    try:
        index = scout_report_index.load_index(context=_issue_context(issue_prefix))
        latest = (index.get("latest") or {})
        key = (latest.get("persisted_key") or {}).get("history")
        if not key:
            raise HTTPException(status_code=404, detail="No persisted report yet")
        import json as _json
        return _json.loads(scout_report_publisher.read_object(
            scout_report_publisher._s3_client(os.getenv("SCOUT_REPO_S3_REGION", "us-west-2")), key))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Latest report error: {e}")
        raise HTTPException(status_code=503, detail=f"Latest report unavailable: {e}")


@app.get("/reports/{report_id}")
def get_report(report_id: str, issue_prefix: str = "", username: str = Depends(require_auth)):
    """One immutable persisted Scout delta report by report_id (read-only). Optional ``issue_prefix``
    scopes the lookup to a chosen discovered issue's index; default = the configured issue."""
    try:
        index = scout_report_index.load_index(context=_issue_context(issue_prefix))
        entry = next((e for e in index.get("entries", []) if e.get("report_id") == report_id), None)
        if entry is None:
            raise HTTPException(status_code=404, detail="Unknown report_id")
        import json as _json
        return _json.loads(scout_report_publisher.read_object(
            scout_report_publisher._s3_client(os.getenv("SCOUT_REPO_S3_REGION", "us-west-2")),
            (entry.get("persisted_key") or {}).get("history")))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Report fetch error: {e}")
        raise HTTPException(status_code=503, detail=f"Report unavailable: {e}")


@app.get("/schemas")
def list_schemas(username: str = Depends(require_auth)):
    """List the versioned machine-readable contract schemas the UI + intelligence consumers share."""
    return {"schemas": sorted(p.name.replace(".schema.json", "")
                              for p in scout_schema.SCHEMA_DIR.glob("*.schema.json"))}


@app.get("/schemas/{name}")
def get_schema(name: str, username: str = Depends(require_auth)):
    """Serve one versioned JSON Schema contract (read-only)."""
    try:
        return scout_schema.load_schema(name)
    except scout_schema.SchemaError:
        raise HTTPException(status_code=404, detail="Unknown schema")


def _benchmark_key(level: str, issue_prefix: str):
    """Resolve the persisted benchmark key for a level + scope (SXI-2c). ``platform`` needs no scope;
    ``issue``/``series``/``publisher`` derive their root from the issue_prefix via the same ownership-chain
    parse ``rebuild_all`` used to WRITE them, so a read serves exactly the object that was persisted. A
    malformed prefix is a 400."""
    if level == "platform":
        return "benchmark/platform.json"
    if level not in ("issue", "series", "publisher"):
        raise HTTPException(status_code=400, detail="level must be platform | publisher | series | issue")
    if not issue_prefix:
        raise HTTPException(status_code=400, detail=f"level '{level}' requires an issue_prefix scope")
    try:
        roots = scout_benchmark._roots(issue_prefix)
    except (KeyError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid issue_prefix (not an issue ownership chain)")
    return {"issue": f"{issue_prefix}/benchmark/benchmark.json",
            "series": f"{roots['series_root']}/benchmark/benchmark.json",
            "publisher": f"{roots['publisher_root']}/benchmark/benchmark.json"}[level]


@app.get("/benchmark/{level}")
def get_benchmark(level: str, issue_prefix: str = "", username: str = Depends(require_auth)):
    """Read-only benchmark projection for a level (platform | publisher | series | issue). Reads the
    persisted, weighted projection; the browser renders it and never recomputes. Points carry counts
    + both timestamps; segments are per methodology (comparability) boundary. Non-platform levels take an
    ``issue_prefix`` scope (the series/publisher root is derived from it). (SXI-2c: all levels served.)
    """
    key = _benchmark_key(level, issue_prefix)   # raises 400 on bad level / missing / malformed scope
    try:
        projection = scout_benchmark.load_projection(key)
    except scout_benchmark.ScoutBenchmarkError as e:
        logger.warning(f"Benchmark projection error: {e}")
        raise HTTPException(status_code=503, detail=f"Benchmark unavailable: {e}")
    if projection is None:
        raise HTTPException(status_code=404, detail="Benchmark projection not generated yet")
    return projection