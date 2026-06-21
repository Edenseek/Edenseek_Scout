# Edenseek Scout

Edenseek Scout is an always-on AI research agent developed by Edenseek Publishing.

Scout continuously monitors developments across:

* Artificial Intelligence
* Publishing
* Comics
* Digital Media
* Strategic opportunities relevant to Edenseek

The system generates autonomous intelligence reports, maintains persistent memory, and delivers research insights through a web dashboard.

## Current Status

Version: v0.3 Production Alpha (reliability hardening complete — commit fdf0ab8)

Deployment:

* Oracle Cloud VM
* FastAPI
* APScheduler
* Cloudflare DNS and HTTPS
* GitHub-based deployment workflow
* Persistent storage and memory (atomic, lock-guarded writes)

Reliability hardening is complete (path-traversal containment, OpenAI timeout/retry,
atomic memory writes). The active milestone is **Memory v0.4**. Scout is **read-and-advise
only** — it never writes code, commits, or deploys (see `SCOUT_CHARTER.md`).

Production URL:

https://scout.edenseek.com/dashboard

## Architecture

Browser
↓
Cloudflare
↓
Nginx
↓
FastAPI
↓
Scout Agent
↓
OpenAI API

## Roadmap

### v0.4 (active)

* Structured memory extraction
* Knowledge accumulation
* Memory dashboard
* Intake Reports (project continuity briefings)
* Remaining hardening: rate limiting, async generation, lifespan migration

### Future

* Active web research
* Conversational interface
* Reflection agent
* Critic agent
* Multi-agent orchestration

## Documentation

* SCOUT_CHARTER.md — governing identity and boundaries
* docs/architecture/scout_v0.3_synopsis.md
* docs/architecture/scout_status_and_tech_debt.md
* docs/architecture/scout_beta_roadmap.md
* docs/architecture/scout_future_vision.md
* docs/architecture/SCOUT_ORCHESTRATOR.md
* docs/architecture/SCOUT_SCHEDULE.md
* docs/architecture/PROJECT_MEMORY_SCHEMA.md
* docs/architecture/REPORT_SPECIFICATION.md

## Mission

Scout's long-term objective is to become Edenseek's autonomous intelligence and research system, transforming accumulated knowledge into strategic guidance for publishing, AI, and creative projects.
