# Review Prioritization (Phase 2)

> The deterministic model behind the Review Priority Queue, Page Heat Map, and Audit
> History. Derives from `SCOUT_CHARTER.md`. Read-only and advisory: Scout ranks and
> recommends; it never approves, rejects, locks, routes, or modifies datasets (Charter §4).

## 1. Inputs

All signals come from the per-artifact assessments in `audit_scoring.assess_artifact`
(pure, deterministic): `severity`, `effort`, `page`, `artifact_id`, `blocking_issues`,
`primary_weakness`, `suggested_action`.

- **severity** — max severity among an artifact's blocking issues (`critical|high|medium|low`).
- **effort** — count of distinct blocking issues (lower = closer to done = quicker win).
- **page** — integer parsed from `artifact_id` matching `^page_(\d+)_panel_\d+$`; otherwise
  `null` (colon-style ids, spreads) → bucketed as `unpaged`.

## 2. Priority ordering (Review Priority Queue)

Total order (Option B — publisher workflow efficiency):

```
severity desc  →  page asc (unpaged last)  →  effort asc  →  artifact_id asc
```

Rationale: comic review is page-bound, so within an impact band the queue keeps the
reviewer anchored to one page (minimizing context reloads), and surfaces quick wins first
*within* each page. `artifact_id` is unique, so the order is strict and independent of input
order. No randomness or timestamps participate → fully deterministic.

## 3. Estimated impact (qualitative band)

`estimated_impact` ∈ {`high`, `medium`, `low`}, mapped from severity:
`critical|high → high`, `medium → medium`, `low|info → low`.

**No numeric "expected score impact" is ever emitted.** The quality score is a derived
metric and Phase 2 lacks the evidence to predict point changes; only qualitative bands and
*measured* historical deltas are reported.

## 4. Page Heat Map

Per-page aggregation over all artifacts: `artifact_count`, `weak_count`, `by_severity`, and
`page_impact` (band from the worst severity on the page). Non-page artifacts aggregate into
an `unpaged` bucket (count surfaced as `unpaged_count`). Sort: `page_impact` band desc →
`weak_count` desc → page asc (unpaged sentinel last).

## 5. Audit History

Each audit appends a snapshot to `edenseek_dataset.audit_history` (append-only,
chronological, capped at 30; see `PROJECT_MEMORY_SCHEMA.md` §2.3). The Audit History report
shows the measured `quality_score` trend and the latest delta (`up|down|unchanged`). History
append (`scout.record_audit_history`) is separate from the idempotent latest-fields write
(`scout.update_dataset_memory`).

## 6. Guarantees

- Deterministic: identical inputs → identical ranks, heat map, and snapshot (excluding the
  recorded timestamp, which never affects ordering).
- Read-only: inputs are never mutated; outputs go only to `reports/**` and `data/memory.json`.
- Advisory: every output is a recommendation for human review; Scout takes no action.
