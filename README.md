# Edenseek Scout

Edenseek Scout is a **bounded Publisher Dataset Intelligence Agent** developed by Edenseek
Publishing. Its governing identity and boundaries are defined in the sole authoritative
charter, [`SCOUT_CHARTER.md`](./SCOUT_CHARTER.md).

Scout inspects publisher-side data artifacts and reports on their quality:

* Dataset quality and metadata completeness
* Character recognition and consistency
* Dialogue extraction quality
* Retrieval readiness
* Weak-artifact detection

Scout is **read-and-advise only** — it inspects, scores, reports, and recommends. It never
modifies canonical publisher data, approves metadata, bypasses publisher review, writes
code, commits, or deploys. All production changes require human approval (see
`SCOUT_CHARTER.md` §4).

The system generates deterministic quality audits, maintains persistent memory, and
delivers findings through a web dashboard.

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
atomic memory writes). The active direction is **Phase 1 — Dataset Intelligence**
(`SCOUT_CHARTER.md` §8); the structured-memory foundation from the prior Memory v0.4 work
underpins it. Scout is **read-and-advise only** — it never modifies canonical publisher
data, approves metadata, writes code, commits, or deploys (see `SCOUT_CHARTER.md` §4).

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

Scout's phased roadmap is defined in [`SCOUT_CHARTER.md`](./SCOUT_CHARTER.md) §8. The active
phase is **Phase 1 — Dataset Intelligence** (dataset auditor, metadata quality scoring,
weak-artifact detection, character analysis, dialogue analysis). Later phases extend Scout
toward reference, retrieval, and reader-trust intelligence within a multi-agent ecosystem.

## Documentation

* SCOUT_CHARTER.md — **sole authoritative governing charter** (identity, mission, boundaries, roadmap)
* docs/architecture/scout_v0.3_synopsis.md
* docs/architecture/scout_status_and_tech_debt.md
* docs/architecture/scout_beta_roadmap.md
* docs/architecture/scout_future_vision.md
* docs/architecture/SCOUT_ORCHESTRATOR.md
* docs/architecture/SCOUT_SCHEDULE.md
* docs/architecture/PROJECT_MEMORY_SCHEMA.md
* docs/architecture/REPORT_SPECIFICATION.md

## Mission

Scout's long-term objective is to become the **publisher-side intelligence layer** of the
Edenseek ecosystem — continuously improving dataset quality, metadata quality, retrieval
readiness, and institutional knowledge while preserving complete human authority over all
canonical publishing data. Knowledge is the asset; reports are one view of it; human
approval remains the final authority (see `SCOUT_CHARTER.md`).
