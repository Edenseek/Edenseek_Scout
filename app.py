import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from scout import generate_report
from scheduler import start_scheduler

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
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.on_event("startup")
def startup_event():
    start_scheduler()


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
    report_path = generate_report()

    return {
        "status": "success",
        "report": report_path
    }


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
    report_path = REPORTS_DIR / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return report_path.read_text(encoding="utf-8")


@app.get("/dashboard")
def dashboard(username: str = Depends(require_auth)):
    return FileResponse("static/index.html")