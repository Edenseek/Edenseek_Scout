from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse

from scout import generate_report
from scheduler import start_scheduler

app = FastAPI(title="Edenseek Scout")

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
def run_scout():
    report_path = generate_report()

    return {
        "status": "success",
        "report": report_path
    }


@app.get("/reports")
def list_reports():
    REPORTS_DIR.mkdir(exist_ok=True)

    reports = sorted(
        [file.name for file in REPORTS_DIR.glob("*.md")],
        reverse=True
    )

    return {
        "reports": reports
    }


@app.get("/report/{filename}", response_class=PlainTextResponse)
def get_report(filename: str):
    report_path = REPORTS_DIR / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return report_path.read_text(encoding="utf-8")

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/index.html")