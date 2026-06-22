import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from scout import generate_report
from scheduler import start_scheduler
from dataset_auditor import run_dataset_audit
from audit_inputs import AuditInputError
from audit_reports import REPORT_FILES, REPORTS_ROOT
from logging_config import logger

app = FastAPI(title="Edenseek Scout")

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