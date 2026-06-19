# CLAUDE.md — Edenseek Scout AI Developer Guide

> **Read this first.**
>
> This is the primary onboarding document for Claude Code sessions and future AI agents working on Edenseek Scout.
>
> If you are new to the project, read this file first, then:
>
> 1. `docs/architecture/scout_v0.3_synopsis.md`
> 2. `docs/architecture/scout_status_and_tech_debt.md`
> 3. `docs/architecture/scout_beta_roadmap.md`
> 4. `docs/architecture/scout_future_vision.md`
>
> Last Updated: June 2026
>
> Status: Production Alpha

---

# 1. Project Overview

Edenseek Scout is an always-on AI research agent for Edenseek Publishing.

Scout continuously monitors developments in:

* Artificial Intelligence
* Publishing
* Comics
* Digital media
* Strategic opportunities relevant to Edenseek

Scout generates autonomous intelligence reports, maintains persistent memory, and presents results through a web dashboard.

Long-term vision:

> Scout evolves from a report generator into Edenseek's autonomous intelligence and research system.

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

## Priority 1 — Reliability

* Fix path traversal vulnerability
* Add OpenAI timeout handling
* Add OpenAI retry handling
* Implement atomic memory writes

## Priority 2 — Memory v0.4

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

Current high-priority issues:

## Path Traversal

Endpoint:

```text
GET /report/{filename}
```

Must be hardened before Beta.

## Memory Corruption

Current writes are not atomic.

A crash during write can corrupt memory.

## OpenAI Failure Handling

Current requests require:

* Timeouts
* Retries
* Graceful degradation

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
