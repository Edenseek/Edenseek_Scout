# Scout Beta Roadmap

> Last verified against commit: fdf0ab8
>
> Phase definitions are **authoritative in `SCOUT_CHARTER.md` §8** (Phase 1–5). This
> document tracks execution detail and sequencing under that taxonomy. Where the two
> differ, the charter wins.

## Active Phase — Phase 1: Dataset Intelligence

Scout's current active work per the charter. Read-and-advise only; deterministic where
possible (Charter §4–§5).

* Dataset Auditor
* Metadata Quality Scoring
* Weak Artifact Detection
* Character Analysis (consistency vs. reference materials)
* Dialogue Analysis (extraction completeness / OCR quality)
* Reference-Material Readiness Analysis

Inputs (read-only; **committed fixtures initially**, configurable local paths later):
`approved_dataset.json`, `approved_llm_outputs.json`, `retrieval_evidence_packets.json`,
reference materials, character sheets, scripts, creator notes.

Outputs: dataset quality reports, character analysis reports, dialogue analysis reports,
retrieval-readiness reports, weak-artifact queues (see `REPORT_SPECIFICATION.md` §4).
Audit results persist to the `edenseek_dataset` memory track (see
`PROJECT_MEMORY_SCHEMA.md` §2.3).

Result: Scout becomes the **Publisher Dataset Intelligence Agent**.

## Enabling Foundation (supports Phase 1 — not gating ahead of it)

Reliability, operability, and persistence work that strengthens Phase 1 but does **not**
block it. These were previously sequenced as standalone milestones; under the charter they
are supporting tracks for the active phase.

* **Milestone A — Stop The Bleeding ✅ Complete (commit fdf0ab8):** path traversal fixed,
  OpenAI timeout, retry handling, atomic memory writes.
* **Memory v0.4:** structured per-project memory, extraction, deduplication, `/memory`
  endpoint, dashboard panel. Provides the `edenseek_dataset` track that Phase 1 audits
  write to.
* **Operability:** FastAPI lifespan migration, scheduler health endpoint, test suite,
  rate limiting.
* **Persistence:** SQLite migration, memory tables, report metadata tables.

## Later Phases (charter taxonomy)

### Phase 2 — Publisher Intelligence: Review Prioritization (in progress)

* Artifact priority ranking (Review Priority Queue)
* Page rollup / page heat map
* Audit history persistence + trend
* `GET /audit/priority`, `GET /audit/history`

Read-only, deterministic, advisory (see `docs/architecture/REVIEW_PRIORITIZATION.md`).
Reference-material intelligence (character sheets, scripts, creator notes) follows as a
later Phase 2 increment.

Result: Scout understands the publisher review workflow and what to review next.

### Phase 3 — Retrieval Intelligence

* Retrieval-readiness scoring
* Evidence-packet analysis
* Query-coverage analysis
* Search-gap detection

Result: Foundation for the **Cartographer Agent**.

### Phase 4 — Reader Trust Intelligence

* Hallucination detection
* Citation validation
* Reader-trust audits
* Refusal testing

Result: Foundation for the **Guardian Agent**.

### Phase 5 — Multi-Agent Ecosystem

* Scout (Publisher Intelligence)
* Cartographer (Search Intelligence)
* Guardian (Reader Trust Intelligence)
* Critic
* Strategist

Result: **Edenseek Autonomous Intelligence Platform**.

## Mapping From Prior Milestone Taxonomy

The earlier A–H milestone lettering is superseded by the charter's Phase 1–5 spine. The
mapping below preserves the prior content so nothing is lost:

| Prior milestone                       | Charter phase / track                          |
|---------------------------------------|------------------------------------------------|
| A — Stop The Bleeding                  | Enabling Foundation (complete)                 |
| B — Memory v0.4                        | Enabling Foundation                            |
| C — Operability                        | Enabling Foundation                            |
| D — Persistence                        | Enabling Foundation                            |
| E — Publisher Dataset Intelligence     | **Phase 1 — Dataset Intelligence (active)**    |
| F — Search Intelligence                | Phase 3 — Retrieval Intelligence (Cartographer)|
| G — Reader Trust Intelligence          | Phase 4 — Reader Trust Intelligence (Guardian) |
| H — Multi-Agent System                 | Phase 5 — Multi-Agent Ecosystem                |
| (new — not in prior taxonomy)          | Phase 2 — Reference Intelligence               |
