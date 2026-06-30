# Edenseek Scout

Edenseek Scout is the **Dataset Intelligence Layer** for Edenseek Publishing, operating as a
**Publisher Lifecycle Audit Sidecar** — a bounded, read-only, deterministic system that
observes the permitted repository artifacts emitted by each Publisher lifecycle phase and
turns them into structured quality intelligence. Each phase emits repository artifacts; Scout
reads only the permitted artifacts for that phase, performs phase-appropriate comparisons, and
writes only Scout reports. Publisher owns creation, humans own approval, the Repository owns
storage, and Scout owns observation, comparison, diagnostics, and reporting; Scout never
modifies Publisher data, approves content, becomes the source of truth, or bypasses human
approval. Its governing identity and boundaries are defined in the sole authoritative charter,
[`SCOUT_CHARTER.md`](./SCOUT_CHARTER.md).

Scout serves **two audiences from the same deterministic outputs**:

* **Humans** (Derek, publishers) — what to review, what is wrong, is quality improving.
* **AI engineering agents** (ChatGPT, Claude Code, future Edenseek agents) — *why* the
  dataset is failing and which part of the creation/enrichment/approval/retrieval pipeline
  to improve.

Scout inspects publisher-side data artifacts and reports on their quality:

* Dataset quality and metadata completeness
* Character recognition and dialogue coverage
* Retrieval readiness
* Weak-artifact detection and review prioritization
* Dataset failure analysis (why scores are low)

Scout is **read-and-advise only** — it inspects, scores, reports, and recommends. It never
modifies canonical data, approves/rejects/locks artifacts, rewrites prompts, changes its
own scoring rules, acts as a retrieval engine, answers reader-facing questions, writes code,
or deploys. All production changes require human approval (see `SCOUT_CHARTER.md` §4).

**Cost:** reports are produced by JSON parsing, counting, and structural analysis — **no
LLM, embedding, vision, or external-service calls** — so they are cheap and safe to run on
every audit and after pipeline changes. Audit history is logged so trends can be inspected
later; Scout may read its own history but never self-modifies from it.

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
atomic memory writes). Phase 1 (Dataset Auditor) and Phase 2 (Publisher Intelligence /
review prioritization) are complete; the active phase is **Phase 3 — Dataset Failure
Analysis** (`SCOUT_CHARTER.md` §8). Scout is **read-and-advise only** and **deterministic**
— report generation makes no LLM calls (see `SCOUT_CHARTER.md` §4).

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
Scout (Dataset Intelligence Layer)
↓
deterministic reports (no LLM calls)

## Roadmap

Scout's phased roadmap is defined in [`SCOUT_CHARTER.md`](./SCOUT_CHARTER.md) §8. Phases 1
(Dataset Intelligence) and 2 (Publisher Intelligence) are complete; the active phase is
**Phase 3 — Dataset Failure Analysis** (root-cause aggregation, highest-leverage failure).
Later phases add historical intelligence, retrieval-readiness, reader-trust, and a
multi-agent ecosystem.

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
