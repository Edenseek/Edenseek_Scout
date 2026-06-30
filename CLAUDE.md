# CLAUDE.md — Edenseek Scout AI Developer Guide

> **Read this first.**
>
> This is the primary onboarding document for Claude Code sessions and future AI agents working on Edenseek Scout.
>
> If you are new to the project, read this file first, then:
>
> 1. `SCOUT_CHARTER.md` (repo root) — the **sole authoritative governing charter** (identity, mission, boundaries, and phased roadmap; **Scout is read-and-advise only**). Where any other document conflicts with the charter, the charter wins.
> 2. `docs/architecture/scout_v0.3_synopsis.md`
> 3. `docs/architecture/scout_status_and_tech_debt.md`
> 4. `docs/architecture/scout_beta_roadmap.md`
> 5. `docs/architecture/scout_future_vision.md`
>
> Governance & specs (the v0.4 source of truth):
>
> * `docs/architecture/SCOUT_ORCHESTRATOR.md`
> * `docs/architecture/SCOUT_SCHEDULE.md`
> * `docs/architecture/PROJECT_MEMORY_SCHEMA.md`
> * `docs/architecture/REPORT_SPECIFICATION.md`
>
> Last Updated: June 2026 · Last verified against commit: fdf0ab8
>
> Status: Production Alpha (Reliability hardening complete; active milestone: Memory v0.4)

---

# 1. Project Overview

Edenseek Scout is the **Dataset Intelligence Layer** for Edenseek Publishing, operating as a
**Publisher Lifecycle Audit Sidecar** — a bounded, read-only, deterministic system
(intentionally non-autonomous: no planning, tool use, or actions). Each Publisher lifecycle
phase emits repository artifacts; Scout reads only the permitted artifacts for that phase (per
the Scout Data Access Contract), performs phase-appropriate comparisons, and writes only Scout
reports. Publisher owns creation, humans own approval, the Repository owns storage, and Scout
owns observation, comparison, diagnostics, and reporting; Scout never modifies Publisher data,
approves content, becomes the source of truth, or bypasses human approval. Its identity and
boundaries are governed by `SCOUT_CHARTER.md` (the sole authoritative charter).

Scout serves **two audiences from the same deterministic outputs**: humans (Derek,
publishers) and **AI engineering agents** (ChatGPT, Claude Code, future Edenseek agents)
that use Scout's structured intelligence to improve dataset creation, enrichment, approval,
and retrieval quality.

Scout inspects publisher-side data artifacts and reports on their quality:

* Dataset quality and metadata completeness
* Character recognition and dialogue coverage
* Retrieval readiness
* Weak-artifact detection and review prioritization
* Dataset failure analysis — *why* scores are low (Phase 3)

Scout generates **deterministic dataset-audit** reports (JSON parsing, counting, structural
analysis — **no LLM, embedding, vision, or external-service calls**); its separate
**strategic / narrative** reports are LLM-generated and do not participate in the
Publisher-workflow audit. Scout maintains persistent memory and
audit history, and presents results through a web dashboard. Reports are cheap and safe to
run on every audit. Scout is **read-and-advise only / diagnostic**: it inspects, scores,
explains, and recommends, but never modifies canonical data, approves/rejects/locks
artifacts, rewrites prompts, changes its own scoring rules, acts as a retrieval engine,
answers reader-facing questions, or self-modifies from its history (see `SCOUT_CHARTER.md`
§4).

Long-term vision:

> Scout becomes the dataset intelligence layer of the Edenseek ecosystem — explaining where
> dataset quality fails and helping humans and AI agents fix the pipeline, with human
> approval as the final authority.

---

# 2. Current Production Status

Version:

```text
v0.3 Production Alpha
```

Deployment:

```text
Oracle Cloud VM
↓
systemd
↓
FastAPI
↓
Nginx
↓
Cloudflare
↓
scout.edenseek.com
```

Production URLs:

```text
https://scout.edenseek.com/dashboard
https://scout.edenseek.com/health
```

Current Capabilities:

| Capability               | Status   |
| ------------------------ | -------- |
| Oracle VM Deployment     | ✅        |
| Cloudflare DNS           | ✅        |
| HTTPS                    | ✅        |
| Authentication           | ✅        |
| Structured Logging       | ✅        |
| Scheduler                | ✅        |
| Report Generation        | ✅        |
| Dashboard                | ✅        |
| Persistent Memory        | ⚠️ Basic |
| Knowledge Accumulation   | ❌        |
| Active Research          | ❌        |
| Conversational Interface | ❌        |

---

# 3. Architecture

Current Architecture:

```text
Browser
   ↓ HTTPS
Cloudflare
   ↓
scout.edenseek.com
   ↓
Nginx
   ↓
FastAPI
   ↓
Scout
   ↓
OpenAI API
   ↓
reports/*.md
   ↓
data/memory.json
```

The current system consists of three primary modules:

```text
app.py
scheduler.py
scout.py
```

Scout remains intentionally simple.

Do not introduce unnecessary complexity.

---

# 4. Key Files

| File                 | Purpose                           |
| -------------------- | --------------------------------- |
| `app.py`             | FastAPI application and endpoints |
| `scheduler.py`       | APScheduler jobs                  |
| `scout.py`           | Core Scout logic                  |
| `logging_config.py`  | Logging setup                     |
| `static/index.html`  | Dashboard                         |
| `reports/`           | Generated reports                 |
| `logs/scout.log`     | Runtime logs                      |
| `data/memory.json`   | Persistent memory                 |
| `.env`               | Secrets and configuration         |
| `docs/architecture/` | Architecture documentation        |

---

# 5. Development Workflow

Canonical workflow:

```text
Local Development
      ↓
GitHub
      ↓
Oracle VM
```

Deployment:

```bash
git add .
git commit -m "message"
git push

ssh oracle-vm
git pull

sudo systemctl restart edenseek-scout
```

Avoid editing production code directly on the VM.

Production changes should originate locally and flow through GitHub.

Exceptions:

* Environment variables
* Server configuration
* SSL certificates

---

# 6. Current Priorities

The next milestone is:

```text
Production Beta
```

Beta is defined as:

> Scout can operate unattended without corrupting itself.

Current priorities:

## Priority 1 — Reliability ✅ Complete (commit fdf0ab8)

* [x] Fix path traversal vulnerability
* [x] Add OpenAI timeout handling
* [x] Add OpenAI retry handling
* [x] Implement atomic memory writes

Remaining reliability follow-ups (graceful degradation, in-process memory locking is done
but cross-process safety is not, scheduler validation) are folded into Priorities 3–4.
The active milestone is now **Priority 2 — Memory v0.4**.

## Priority 2 — Memory v0.4 ⬅ active

* Structured report output
* Memory extraction
* Memory deduplication
* Memory API endpoint
* Dashboard memory viewer

## Priority 3 — Operability

* FastAPI lifespan migration
* Scheduler health endpoint
* Test suite
* Rate limiting

## Priority 4 — Persistence

* SQLite migration
* Report metadata
* Queryable memory

---

# 7. Security Notes

Scout is internet accessible.

Security is not optional.

The high-priority issues below were the Beta blockers; all three are now resolved
(commit fdf0ab8). They are kept here as a record and as guardrails for future changes.

## Path Traversal ✅ Resolved (commit fdf0ab8)

Endpoint:

```text
GET /report/{filename}
```

`app.py` resolves the requested path and rejects any path whose resolved parent escapes
`reports/`. Do not regress this when changing report-serving code.

## Memory Corruption ✅ Resolved (commit fdf0ab8)

`save_memory()` now writes a temp file, `fsync`s, then `os.replace()`s (atomic rename), and
the load-modify-save is guarded by a `threading.Lock`. A crash mid-write can no longer
corrupt memory. Cross-process safety still awaits the SQLite migration (Priority 4).

## OpenAI Failure Handling ✅ Resolved (commit fdf0ab8)

`call_openai_with_retries` applies a 60s timeout and up to 3 retries with backoff:

* [x] Timeouts
* [x] Retries
* [ ] Graceful degradation (bounded + 503 on failure; no degraded-mode fallback yet)

Never commit:

```text
.env
API keys
passwords
certificates
```

---

# 8. Development Principles

## Knowledge Is The Asset

Reports are not the product.

Knowledge is the product.

Reports are one rendering of knowledge.

---

## Evolve, Don't Rewrite

The current architecture is intentionally simple.

Prefer:

```text
small improvements
```

over:

```text
large rewrites
```

---

## Reliability Before Intelligence

Before adding:

* multi-agent systems
* advanced memory
* research automation

ensure:

* reliability
* security
* persistence

are solved first.

---

## Keep Documentation Accurate

Whenever architecture changes:

Update:

```text
scout_v0.3_synopsis.md
scout_status_and_tech_debt.md
scout_beta_roadmap.md
```

Documentation drift is considered technical debt.

---

# 9. Long-Term Vision

Scout is expected to evolve through four stages.

## Stage 1 — Production Alpha

Current state.

Characteristics:

* Single agent
* Scheduled reports
* Basic memory
* Dashboard

---

## Stage 2 — Production Beta

Characteristics:

* Reliable unattended operation
* Structured memory
* Security hardening
* Test coverage

Goal:

Trust Scout.

---

## Stage 3 — Intelligence Platform

Characteristics:

* Knowledge base
* Source tracking
* Trend detection
* Conversational interface

Goal:

Institutional knowledge.

---

## Stage 4 — Autonomous Research Organization

Characteristics:

* Research agent
* Critic agent
* Strategist agent
* Publisher agent

Goal:

Generate, critique, refine, and distribute strategic intelligence with minimal human intervention.

---

# 10. First Actions For A New Claude Session

Read:

```text
docs/architecture/scout_v0.3_synopsis.md
docs/architecture/scout_status_and_tech_debt.md
docs/architecture/scout_beta_roadmap.md
```

Then determine:

1. Current milestone
2. Highest-priority technical debt
3. Smallest safe improvement
4. Required documentation updates

Do not begin large refactors without reviewing the roadmap and architecture documents.
