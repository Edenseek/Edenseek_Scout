from fastapi import FastAPI
from scout import generate_report

app = FastAPI(title="Edenseek Scout")


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