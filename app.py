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


@app.get("/audit-review/archive")
def get_audit_review_archive(username: str = Depends(require_auth)):
    """Read-only Reports Archive (newest first): successful reports + failed runs, with latest/
    historical/failed marks and methodology boundaries. Reads persisted index + ledger only."""
    try:
        return scout_archive.build_archive()
    except (scout_report_index.ScoutReportIndexError, Exception) as e:  # noqa: BLE001
        logger.warning(f"Archive error: {e}")
        raise HTTPException(status_code=503, detail=f"Archive unavailable: {e}")


@app.get("/audit-review/search")
def get_audit_review_search(q: str = "", username: str = Depends(require_auth)):
    """Server-side search over persisted archive metadata (e.g. `precision<0.80`,
    `finding:geometry.false_panels`, `severity:WARNING`, `publisher:<id> issue:<id>`). The browser
    passes the query; all filtering happens here."""
    try:
        archive = scout_archive.build_archive()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Search error: {e}")
        raise HTTPException(status_code=503, detail=f"Search unavailable: {e}")
    return scout_archive.search_archive(archive, q)


@app.get("/intelligence/geometry")
def get_geometry_intelligence(username: str = Depends(require_auth)):
    """Read-only Geometry Intelligence projection — recurring panel failure modes + version-correlated
    improvements, consuming the persisted report index. Advisory only; mutates nothing."""
    try:
        return scout_intelligence.build_geometry_intelligence()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Geometry intelligence error: {e}")
        raise HTTPException(status_code=503, detail=f"Geometry intelligence unavailable: {e}")


@app.get("/intelligence/metadata")
def get_metadata_intelligence(username: str = Depends(require_auth)):
    """Read-only Metadata Intelligence projection — weak fields, edit classes, prompt/model/schema
    correlations, consuming the persisted index + immutable reports. Advisory only; mutates nothing."""
    try:
        return scout_intelligence.build_metadata_intelligence()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Metadata intelligence error: {e}")
        raise HTTPException(status_code=503, detail=f"Metadata intelligence unavailable: {e}")


@app.get("/reports/latest")
def get_latest_report(username: str = Depends(require_auth)):
    """The current/latest persisted immutable Scout delta report (read-only)."""
    try:
        index = scout_report_index.load_index()
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
def get_report(report_id: str, username: str = Depends(require_auth)):
    """One immutable persisted Scout delta report by report_id (read-only)."""
    try:
        index = scout_report_index.load_index()
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


@app.get("/benchmark/{level}")
def get_benchmark(level: str, username: str = Depends(require_auth)):
    """Read-only benchmark projection for a level (platform | publisher | series | issue). Reads the
    persisted, weighted projection; the browser renders it and never recomputes. Points carry counts
    + both timestamps; segments are per methodology (comparability) boundary.
    """
    keys = {"platform": "benchmark/platform.json"}
    if level not in keys:
        raise HTTPException(status_code=400,
                            detail="level must be one of: platform (publisher/series/issue: pass scope next slice)")
    try:
        projection = scout_benchmark.load_projection(keys[level])
    except scout_benchmark.ScoutBenchmarkError as e:
        logger.warning(f"Benchmark projection error: {e}")
        raise HTTPException(status_code=503, detail=f"Benchmark unavailable: {e}")
    if projection is None:
        raise HTTPException(status_code=404, detail="Benchmark projection not generated yet")
    return projection