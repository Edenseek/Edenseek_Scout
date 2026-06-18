# CLAUDE.md — Edenseek Scout AI Developer Guide

> **Read this first.** This is the primary onboarding document for AI agents (Claude Code sessions)
> and developers working on Edenseek Scout. It assumes no prior context. Deeper documentation lives
> in [`docs/architecture/`](./docs/architecture/) — this file is the fast path to being productive.

---

## 1. Project Overview

Edenseek Scout is an "always-on" AI research agent for **Edenseek Publishing**. It autonomously
generates concise strategic intelligence reports for Derek Uskert covering AI, publishing, and the
comics industry, framed around Edenseek's projects:

- **Phrasmos** — symbolic image tagging and metadata.
- **Caelaris** — a comic publishing project.
- Long-term goal — AI-assisted comic navigation and creator tools.

Reports are produced on a daily schedule and on demand, stored as Markdown, and surfaced through a
minimal web dashboard. **Current version: v0.3.** (Note: `README.md` still reads v0.1 — the
execution brief and these docs are authoritative.)

The project is small and early-stage by design (three core Python modules). Treat it as a foundation
to grow, not a finished system.

---

## 2. Current Architecture

A single-process FastAPI application with three core modules. Triggers (HTTP or scheduler) call one
function, `generate_report()`, which reads memory, calls OpenAI, writes a Markdown report, and
updates memory.

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
```

**Stack:** Python · FastAPI · uvicorn · OpenAI (`gpt-4o-mini`, SDK pinned `openai==1.55.3`) ·
APScheduler · python-dotenv. (`requests` and `beautifulsoup4` are present, anticipating future
web-research capability, but are not yet used.)

Full detail: [`docs/architecture/scout_v0.3_synopsis.md`](./docs/architecture/scout_v0.3_synopsis.md).

---

## 3. Deployment Architecture

- Runs as a **single-process ASGI app via uvicorn**; the scheduler lives **in-process** (no external
  worker or queue).
- Deployed on an **Oracle Cloud VM**, kept alive by **systemd** (survives reboots).
- Source is synchronized to **GitHub**.
- Assumes a **persistent, writable local filesystem** for `reports/`, `data/`, and `logs/` — not
  ephemeral container storage.
- `OPENAI_API_KEY` is supplied via `.env` (gitignored) / environment.
- The 08:00 daily report fires on **server local time**.
- No reverse proxy, TLS, or authentication is configured in the repo yet (see §8).

---

## 4. Key Files and Responsibilities

| Path | Responsibility |
|---|---|
| `app.py` | FastAPI app, startup hook that boots the scheduler, all HTTP endpoints, serves the dashboard. |
| `scout.py` | Core logic: memory load/save, prompt construction, OpenAI call, report file writing. |
| `scheduler.py` | APScheduler setup; registers the daily cron job calling `generate_report()`. |
| `static/index.html` | Minimal dashboard (vanilla JS): "Run Scout" button + report list. |
| `requirements.txt` | Python dependencies. |
| `.env` / `.env.example` | Holds `OPENAI_API_KEY`. |
| `reports/*.md` | Generated report artifacts (timestamped). |
| `data/memory.json` | Persistent state (gitignored). |
| `archive/execution_brief_26_06_19` | Original roadmap doc ("Memory v0.2"). |
| `docs/architecture/` | Architecture, vision, and status/tech-debt documentation. |

**HTTP endpoints (in `app.py`):**

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | `{name, status:"online"}` |
| GET | `/health` | Liveness check |
| POST | `/run-scout` | Generates a report synchronously; returns its path |
| GET | `/reports` | Lists report filenames, newest first |
| GET | `/report/{filename}` | Returns raw report Markdown (404 if missing) |
| GET | `/dashboard` | Serves `static/index.html` |

**Memory model (`data/memory.json`):**
`{report_count, themes[], opportunities[], risks[], last_report}`.
⚠️ Today only `report_count` and `last_report` are actually written. `themes`, `opportunities`, and
`risks` are passed into the prompt but never extracted or persisted — wiring this up is the headline
v0.4 feature ("Memory v0.2").

---

## 5. Current Production Status

| Capability | Status |
|---|---|
| Oracle VM deployment | ✅ Complete |
| systemd persistence | ✅ Complete |
| GitHub synchronization | ✅ Complete |
| OpenAI integration | ✅ Complete |
| FastAPI app, scheduler, report storage, dashboard | ✅ Operational (v0.3) |
| Structured/accumulating memory | ⛔ Not yet (planned for v0.4) |
| Logging to file | 🔶 Planned |
| Scheduler reliability hardening | 🔶 Open |

Scout is **live and producing daily reports**. See
[`docs/architecture/scout_status_and_tech_debt.md`](./docs/architecture/scout_status_and_tech_debt.md)
for the authoritative status tracker.

---

## 6. Development Principles

1. **Knowledge is the asset.** Optimize for the quality and durability of what Scout *knows*.
   Reports are a rendering of knowledge, not the end goal.
2. **Every observation should be reusable.** Prefer structured, deduplicated, queryable outputs over
   one-off prose.
3. **Cite and date everything** as research capability grows, so conclusions stay auditable and
   stale knowledge can be retired.
4. **Degrade gracefully.** Unattended autonomy demands timeouts, retries, and error handling; a
   failed source or LLM call must never corrupt the knowledge base.
5. **Secure by default.** Scout handles credentials and runs unattended; auth, input validation, and
   least privilege are not optional.
6. **Evolve, don't rewrite.** The three-module foundation is sound — grow memory, research, and
   interfaces incrementally.
7. **Keep docs honest.** When you change behavior, update the relevant doc in `docs/architecture/`
   so "current state" and "vision" stay distinct and accurate.

---

## 7. Known Technical Debt

- **Memory is effectively inert** — strategic fields are never written back (half-wired feature).
- **Console-only output** — no file logging; `logs/scout.log` is planned.
- **In-process scheduler with no job store** — loses state on restart; would double-fire under
  multiple workers.
- **Synchronous `/run-scout`** — blocks on a multi-second OpenAI call; no timeout or retry.
- **No error handling** around OpenAI / file I/O — failures surface as raw 500s.
- **No locking on `data/memory.json`** — concurrent runs (manual + cron) can race.
- **Deprecated `@app.on_event("startup")`** — should migrate to FastAPI lifespan handlers.
- **No tests; minimal tooling** — `logs/` and `prompts/` dirs exist but are unused.
- **Mixed indentation** in `scout.py`'s `client.chat.completions.create(...)` call.
- **Version drift** — README (v0.1) vs. execution brief (v0.3).

---

## 8. Security Considerations

Scout runs unattended with a live API key, so security is a first-class concern. Current gaps,
queued for the next security review (priority order):

1. **Authentication** — `POST /run-scout` and read endpoints are open; anyone with network access
   can trigger billable OpenAI calls.
2. **Path traversal in `/report/{filename}`** — the filename is joined to `reports/` with only an
   existence check, so inputs like `../.env` could read arbitrary files, **including the
   `OPENAI_API_KEY`**. This is the highest-severity open issue: if the service is internet-exposed,
   the API key is currently readable over HTTP. Validate that the resolved path stays within
   `reports/`.
3. **HTTPS/TLS** — ensure traffic is encrypted (terminate at a reverse proxy or configure directly).
4. **Rate limiting** — bound cost and DoS exposure on `/run-scout` and other expensive endpoints.

Never commit `.env` or secrets (it is gitignored — keep it that way).

---

## 9. Current Priorities

The next milestone is **v0.4**, combining the "Memory v0.2" feature work with security hardening.

**Feature work (from the execution brief):**
1. Structured report output (model emits themes/opportunities/risks as JSON alongside the narrative).
2. Memory extraction & write-back into `data/memory.json`.
3. Deduplication of accumulated themes/opportunities/risks.
4. A `GET /memory` endpoint + dashboard panel (report count, last-report time, memory overview).

**Hardening (land in the same release):**
5. Add authentication; rate-limit `/run-scout`.
6. Fix the `/report/{filename}` path traversal.
7. Make report generation async/background with timeout + retry + error handling.
8. Migrate to FastAPI lifespan handlers; evaluate persistent APScheduler job storage.
9. Add file logging (`logs/scout.log`) and a basic test suite.
10. Reconcile version/docs.

**Suggested ordering:** ship memory features (1–4) as the v0.4 headline, but land items 5–6 in the
same release — they are low-effort, high-severity fixes.

---

## 10. Long-Term Vision

Scout is intended to evolve from a scheduled report generator into **Edenseek's autonomous
intelligence and research system** — an agent that continuously observes the world, maintains durable
institutional knowledge, and produces strategic guidance on demand.

Target capability pillars:
- **Durable memory** — a structured, deduplicated knowledge base (not a scratchpad).
- **Active research** — gather and verify external sources (hence `requests`/`beautifulsoup4`).
- **Synthesis** — connect signals across publishing, AI, comics, Phrasmos, Caelaris, and strategic
  opportunities.
- **Conversational access** — a chat interface over accumulated knowledge.
- **Autonomy & continuity** — reliable, restart-safe, event- and schedule-driven operation.

The north-star phrasing from the project's own brief: *"Scout no longer merely writes reports. Scout
begins building institutional knowledge."*

Full vision: [`docs/architecture/scout_future_vision.md`](./docs/architecture/scout_future_vision.md).

---

## Quick Orientation for a New Session

- **What exists now:** `docs/architecture/scout_v0.3_synopsis.md`
- **Where it's going:** `docs/architecture/scout_future_vision.md`
- **What's done / pending / risky:** `docs/architecture/scout_status_and_tech_debt.md`
- **Original intent:** `README.md` and `archive/execution_brief_26_06_19`
- **Run locally:** `uvicorn app:app` (needs `OPENAI_API_KEY` in `.env`); dashboard at `/dashboard`.
- **Golden rule:** Do not commit secrets, and update the docs when you change behavior.
