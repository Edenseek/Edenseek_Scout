# Edenseek Scout — Technical Synopsis (v0.3)

> Internal architecture documentation. Basis for v0.4 planning.
> **Stack:** Python · FastAPI · OpenAI (`gpt-4o-mini`) · APScheduler
> **Version:** 0.3 (README and execution brief now agree on 0.3)
> **Last verified against commit:** `fdf0ab8`

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
| `logging_config.py` | Logging setup: rotating file handler (`logs/scout.log`) + console; shared `logger`. |
| `static/index.html` | Minimal dashboard (vanilla JS): "Run Scout" button + report list with links. |
| `requirements.txt` | Dependencies: fastapi, uvicorn, openai==1.55.3, python-dotenv, apscheduler, requests, beautifulsoup4. |
| `.env` / `.env.example` | Holds `OPENAI_API_KEY`. |
| `reports/*.md` | Generated report artifacts. |
| `data/memory.json` | Persistent state (gitignored). |
| `archive/execution_brief_26_06_19` | Roadmap doc describing planned "Memory v0.2". |

---

## 4. FastAPI Endpoints

All endpoints except `/` and `/health` require HTTP Basic auth (`require_auth` in `app.py`).

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
- **HTTP Basic authentication is implemented in the app** (`app.py`, `require_auth`), gating
  `/run-scout`, `/reports`, `/report/{filename}`, and `/dashboard`. Credentials come from
  `SCOUT_USERNAME` / `SCOUT_PASSWORD`.
- **TLS and reverse proxy live in the deployment, not the repo.** `CLAUDE.md` documents the
  production chain as Cloudflare → Nginx → FastAPI (HTTPS terminated upstream); no Nginx or TLS
  config is checked into this repository. ⚠️ The presence of Nginx is asserted by `CLAUDE.md` but
  unverified here — confirm against the live VM and keep the two docs consistent.

---

## 8. Known Risks

- **Path traversal in `/report/{filename}`.** ✅ **Resolved (commit fdf0ab8).** `app.py` resolves the
  requested path and rejects any path whose resolved parent is outside `reports/`
  (`reports_root not in report_path.parents`), so an authenticated request can no longer escape
  `reports/`.
- **No rate limiting.** `POST /run-scout` is authenticated but unthrottled — an authenticated caller
  can still drive billable OpenAI calls (cost / DoS exposure). **Still open.**
- **Synchronous blocking endpoint.** `/run-scout` still runs the OpenAI call on the request thread
  (no background task); however, the call is now bounded — see timeout/retry below. **Partially open.**
- **OpenAI timeout/retry/error handling.** ✅ **Resolved (commit fdf0ab8).** `call_openai_with_retries`
  applies a 60s timeout, up to 3 attempts with exponential backoff, and logs failures; `/run-scout`
  wraps generation and returns 503 on failure rather than an unhandled 500.
- **Concurrency on the memory file** — ✅ **Resolved in-process (commit fdf0ab8).** The
  load-modify-save of `data/memory.json` is guarded by a module-level `threading.Lock`. Cross-process
  safety still depends on the future SQLite migration.
- **Scheduler durability** — in-process scheduler with no job store loses state on restart, and
  multiple workers would double-fire the job.

---

## 9. Technical Debt

- **Memory is effectively inert** — the strategic fields are never updated; the feature is
  half-wired. (Addressed by the planned Memory v0.4 — see `PROJECT_MEMORY_SCHEMA.md`.)
- **Deprecated lifecycle hook** — `@app.on_event("startup")` is deprecated in modern FastAPI and
  should move to a lifespan handler.
- **No tests** — no automated suite exists; `prompts/` directory is present but unused.

**Resolved since earlier drafts** (kept here so the record stays honest):
- ✅ **Atomic memory writes** (commit fdf0ab8) — `save_memory()` writes a temp file, `fsync`s, then
  `os.replace()`s; a crash mid-write can no longer truncate `data/memory.json`.
- ✅ **In-process memory locking** (commit fdf0ab8) — load-modify-save is guarded by a
  `threading.Lock`, preventing manual/cron races within the process.
- ✅ **OpenAI timeout & retry** (commit fdf0ab8) — `call_openai_with_retries` bounds each call (60s)
  and retries up to 3× with backoff and failure logging.
- ✅ **Path traversal fixed** (commit fdf0ab8) — `/report/{filename}` validates the resolved path
  stays within `reports/`.
- ✅ **Version drift resolved** — README and the execution brief now both read v0.3.
- ✅ File logging is implemented (`logging_config.py`, rotating handler → `logs/scout.log` + console);
  the prior "only `print` statements" note no longer applies.
- ✅ The mixed-indentation issue in `scout.py`'s `client.chat.completions.create(...)` call is fixed.

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

> ✅ **Priority callout resolved (commit fdf0ab8):** The path-traversal exposure (#6) is fixed — the
> `.env` file is no longer reachable via `/report/{filename}`. Items #1–4 (Memory v0.4) and the
> remaining hardening (#5 rate limiting, #7 async generation, #8 lifespan/job store) are now the
> active scope.

## 11. Beta Readiness Criteria

The goal of Beta is not feature completeness.

The definition of Beta is:

> "Scout can operate unattended without corrupting itself."

Before Beta, the following must be completed.

### Reliability

- [x] Path traversal vulnerability fixed (commit fdf0ab8)
- [x] OpenAI timeout and retry handling (commit fdf0ab8)
- [x] Atomic writes for memory (commit fdf0ab8) — report writes still non-atomic
- [ ] Graceful handling of OpenAI failures (bounded + 503, but no degraded-mode fallback)
- [ ] Dashboard reflects actual scheduler state

### Security

- Authentication enforced
- HTTPS enabled through Cloudflare
- Rate limiting on expensive endpoints
- Environment secrets protected

### Persistence

- Memory survives crashes
- Memory survives restarts
- Concurrent runs cannot corrupt memory

### Validation

- Basic automated test suite
- Memory round-trip tests
- Endpoint smoke tests

Beta is achieved when Scout can run continuously without operator supervision and without risk of data corruption.

## Repository Integration (Week 9)

Scout currently audits fixture datasets stored inside the repository.

Future architecture replaces fixture-only inputs with repository-backed datasets.

Target flow:

Publisher App
→ Edenseek Publishing Repository
→ Scout
→ Reader App

Scout will continue operating as a read-only intelligence layer.

Scout will never modify:

- publisher uploads
- processing artifacts
- approved datasets

Scout may only:

- inspect
- score
- audit
- classify
- report

Repository integration does not change Scout's authority boundaries.