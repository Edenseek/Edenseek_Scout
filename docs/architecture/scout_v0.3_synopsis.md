# Edenseek Scout — Technical Synopsis (v0.3)

> Internal architecture documentation. Basis for v0.4 planning.
> **Stack:** Python · FastAPI · OpenAI (`gpt-4o-mini`) · APScheduler
> **Version:** 0.3 (per execution brief; README still reads 0.1 — see Technical Debt)

---

## 1. System Purpose

Edenseek Scout is an "always-on" AI research agent for Edenseek Publishing. It autonomously
generates concise strategic intelligence reports for Derek Uskert covering AI, publishing, and
comics-industry developments, framed around Edenseek's projects:

- **Phrasmos** — symbolic image tagging and metadata
- **Caelaris** — comic publishing project
- Long-term goal — AI-assisted comic navigation and creator tools

Reports are produced on a daily schedule and on demand, stored as Markdown, and surfaced through a
minimal web dashboard. The stated long-term direction is to evolve into a broader "Edenseek
intelligence system" that accumulates institutional knowledge over time.

---

## 2. Architecture Diagram

```
                ┌─────────────┐
   HTTP ───────▶│   app.py    │  FastAPI (endpoints, startup hook)
                └──────┬──────┘
                       │ start_scheduler()  (on startup)
                       ▼
                ┌─────────────┐
   cron 08:00 ─▶│ scheduler.py│  APScheduler BackgroundScheduler
                └──────┬──────┘
                       │ generate_report()
                       ▼
                ┌─────────────┐   OpenAI Chat Completions (gpt-4o-mini)
                │  scout.py   │◀────────────────────────────────────────▶ OpenAI API
                └──┬───────┬──┘
       reads/writes│       │writes
                   ▼       ▼
        data/memory.json   reports/YYYY-MM-DD_HH-MM-SS.md
                   ▲
                   │ REST reads
                ┌──┴──────────────┐
                │ static/index.html│  Dashboard (vanilla JS)
                └─────────────────┘
```

**Data flow:** A trigger (HTTP `POST /run-scout` or the 08:00 cron job) calls `generate_report()`.
That function loads `data/memory.json`, builds a prompt embedding the memory, a timestamp, and the
business context, calls OpenAI, writes the response to a timestamped Markdown file, increments
`report_count`, updates `last_report`, and persists memory. The dashboard reads reports back via the
REST endpoints.

---

## 3. Main Modules

| File | Responsibility |
|---|---|
| `app.py` | FastAPI app definition, startup hook that boots the scheduler, all HTTP endpoints, serves dashboard. |
| `scout.py` | Core logic: memory load/save, prompt construction, OpenAI call, report file writing. |
| `scheduler.py` | APScheduler setup; registers a daily cron job that calls `generate_report()`. |
| `static/index.html` | Minimal dashboard (vanilla JS): "Run Scout" button + report list with links. |
| `requirements.txt` | Dependencies: fastapi, uvicorn, openai==1.55.3, python-dotenv, apscheduler, requests, beautifulsoup4. |
| `.env` / `.env.example` | Holds `OPENAI_API_KEY`. |
| `reports/*.md` | Generated report artifacts. |
| `data/memory.json` | Persistent state (gitignored). |
| `archive/execution_brief_26_06_19` | Roadmap doc describing planned "Memory v0.2". |

---

## 4. FastAPI Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | Returns `{name, status:"online"}`. |
| GET | `/health` | Liveness check, `{status:"online"}`. |
| POST | `/run-scout` | Synchronously generates a report; returns `{status, report: <path>}`. |
| GET | `/reports` | Lists `reports/*.md` filenames, reverse-sorted (newest first). |
| GET | `/report/{filename}` | Returns raw Markdown as plain text; 404 if missing. |
| GET | `/dashboard` | Serves `static/index.html`. |

---

## 5. Scheduler Behavior

- A module-level `BackgroundScheduler` is created in `scheduler.py`.
- `start_scheduler()` runs once via FastAPI's `@app.on_event("startup")`.
- One registered job: `cron` trigger at `hour=8, minute=0` (server local time) calling
  `scheduled_scout()` → `generate_report()`.
- Runs in a background thread within the same process as the web server.
- No persistent job store — schedule state is recreated on each startup.

---

## 6. Memory Behavior

- **Store:** a single JSON file, `data/memory.json` (gitignored).
- **Schema:** `{report_count, themes[], opportunities[], risks[], last_report}`.
- `load_memory()` returns a default skeleton if the file is absent; `save_memory()` writes
  pretty-printed JSON and ensures the `data/` directory exists.
- **Current limitation:** only `report_count` and `last_report` are actually mutated. The
  `themes`, `opportunities`, and `risks` fields are passed *into* the prompt but are never extracted
  from generated reports or written back, so they remain empty. Populating them is the explicit
  goal of the planned "Memory v0.2."

---

## 7. Deployment Architecture

- Single-process ASGI app run via uvicorn; the scheduler lives in-process (no external worker or
  queue).
- Local filesystem is assumed durable and writable (`reports/`, `data/`, `logs/`) — i.e. a
  persistent disk, not ephemeral container storage.
- `OPENAI_API_KEY` is supplied via `.env` / environment.
- Server timezone defines the 08:00 cron firing.
- Commit `daa8a1a` ("Fix OpenAI SDK compatibility for Oracle deployment") and the pinned
  `openai==1.55.3` indicate a target of Oracle Cloud. Developed on Windows.
- No authentication, TLS, or reverse-proxy configuration is present in the repo.

---

## 8. Known Risks

- **No authentication/authorization.** `POST /run-scout` is open — anyone who can reach it can
  trigger billable OpenAI calls (cost / DoS exposure).
- **Path traversal in `/report/{filename}`.** The filename is joined directly to `REPORTS_DIR` with
  only an existence check; inputs like `../.env` could read arbitrary files — including the API key.
  Needs sanitization / containment validation.
- **Synchronous blocking endpoint.** `/run-scout` runs a multi-second OpenAI call on the request
  thread; there is no timeout or retry on the API call.
- **No error handling** around OpenAI or file I/O; a failed call propagates a 500 with no graceful
  degradation.
- **Concurrency on the memory file** — no locking; concurrent runs (manual + cron) could race on
  `data/memory.json`.
- **Scheduler durability** — in-process scheduler with no job store loses state on restart, and
  multiple workers would double-fire the job.

---

## 9. Technical Debt

- **Memory is effectively inert** — the strategic fields are never updated; the feature is
  half-wired.
- **Deprecated lifecycle hook** — `@app.on_event("startup")` is deprecated in modern FastAPI and
  should move to a lifespan handler.
- **No tests; minimal logging** — only `print` statements. `logs/` and `prompts/` directories are
  present but empty/unused.
- **Mixed indentation** in `scout.py`'s `client.chat.completions.create(...)` call (tabs vs spaces)
  is a latent style / parse fragility.
- **Version drift** — README says v0.1, the execution brief says v0.3.

---

## 10. v0.4 Roadmap

The execution brief already scopes "Memory v0.2" (structured extraction). v0.4 should combine that
feature work with security hardening.

**Core feature work (from the brief):**
1. **Structured report output** — have the model emit JSON (themes/opportunities/risks) alongside
   the narrative; consider OpenAI structured/JSON mode.
2. **Memory extraction & write-back** — parse those fields into `data/memory.json`.
3. **Deduplication** — normalize and dedupe accumulated themes/opportunities/risks.
4. **`GET /memory` endpoint** + dashboard panel showing report count, last-report time, and memory
   overview.

**Hardening / debt paydown (fold in now):**
5. **Add auth** (API key/token) on mutating + read endpoints; rate-limit `/run-scout`.
6. **Fix path traversal** in `/report/{filename}` (validate the resolved path stays within
   `reports/`).
7. **Make report generation async/background** — return a job id, run via background task; add
   timeout + retry + error handling around the OpenAI call.
8. **Migrate to FastAPI lifespan** handlers; persist APScheduler jobs (e.g. SQLAlchemy job store)
   and guard against multi-worker double-firing.
9. **Introduce real logging** and a basic test suite (endpoint smoke tests, memory round-trip).
10. **Reconcile versioning/docs** and pin remaining dependencies for reproducible Oracle deploys.

**Suggested ordering:** ship the brief's memory features (1–4) as the headline of v0.4, but land
items 5–6 in the same release — they are low-effort, high-severity security fixes.

> ⚠️ **Priority callout:** Because of the path-traversal issue (#6), if the service is exposed the
> `.env` file (real `OPENAI_API_KEY`) is currently readable over HTTP. Treat this as the top
> priority for v0.4.
