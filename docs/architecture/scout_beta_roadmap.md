# Scout Beta Roadmap

> Last verified against commit: fdf0ab8
>
> Phase definitions are **authoritative in `SCOUT_CHARTER.md` §8** (Phase 1–7). This
> document tracks execution detail and sequencing under that taxonomy. Where the two
> differ, the charter wins.

Scout is the **Dataset Intelligence Layer** for Edenseek — read-only, deterministic,
non-autonomous, serving humans and AI engineering agents. Reports use no LLM/embedding/
vision calls and are cheap to run on every audit.

## Phase 1 — Dataset Intelligence ✅ Complete

* Dataset Auditor, metadata quality scoring, weak-artifact detection
* Character analysis (recognition coverage), dialogue analysis (population coverage)
* Retrieval-readiness scoring

Result: Scout audits dataset quality. (See `REPORT_SPECIFICATION.md` §4.)

## Phase 2 — Publisher Intelligence: Review Prioritization ✅ Complete

* Artifact priority ranking (Review Priority Queue)
* Page rollup / page heat map
* Audit history persistence + trend
* `GET /audit/priority`, `GET /audit/history`

Result: Scout knows what to review next. (See `REVIEW_PRIORITIZATION.md`.)

## Phase 3 — Dataset Failure Analysis ⬅ active

Answers *why* the dataset is failing and where failures cluster, for humans and AI
engineering agents. Read-only, deterministic, **diagnostic** (not prescriptive of action).

* **Phase 3A ✅:** Root Cause Report + Highest Leverage Failure Report
* **Phase 3B ✅:** Failure Cluster Report + Retrieval Blockers Report

Adds a compact `failure_summary` to each audit-history snapshot. (See
`REPORT_SPECIFICATION.md` §6, `FAILURE_ANALYSIS.md`, and `RETRIEVAL_READINESS.md`.)

Result: Scout explains why dataset quality is low and which pipeline area is implicated.

## Phase 4 — Historical Intelligence ✅

* Metric and failure-category trends across audit snapshots (most-recent dataset)
* Since-previous-audit delta; new/resolved failures; stagnant pipeline areas
* Observational correlations (co-occurrence, never causation); confidence levels
  (insufficient/preliminary/trend)
* Historical Intelligence Report + `GET /audit/trends`

Deterministic, read-only, observational; reads only `audit_history` snapshots (no canonical
data, no schema change). **Explains change; never predicts it.** See
`HISTORICAL_INTELLIGENCE.md`.

Result: Scout reports dataset-quality trajectory over time (reads history; never
self-modifies from it).

## Phase 5 — Retrieval Readiness Intelligence

* Deeper retrieval-readiness scoring, evidence-packet analysis, coverage/gap detection

Result: Foundation for the **Cartographer Agent**.

## Phase 6 — Reader Trust Intelligence

* Hallucination detection, citation validation, reader-trust audits, refusal testing

Result: Foundation for the **Guardian Agent**.

## Phase 7 — Multi-Agent Ecosystem

* Scout (Dataset/Publisher Intelligence), Cartographer (Search), Guardian (Reader Trust),
  Critic, Strategist

Result: **Edenseek Autonomous Intelligence Platform**.

## Enabling Foundation (supports the phases above — not gating them)

Reliability/operability/persistence work that strengthens the dataset intelligence layer:

* **Stop The Bleeding ✅ (commit fdf0ab8):** path traversal fixed, OpenAI timeout/retry,
  atomic memory writes.
* **Operability:** FastAPI lifespan migration, scheduler health endpoint, test suite,
  rate limiting.
* **Persistence:** SQLite migration, memory tables, report metadata tables.
