# D8 · Increment 2 (Series & Publisher Health rollups) — Hostile Review

**Scope reviewed:** additive pure functions `series_health` / `publisher_health` in `scout_observability.py`
(each composing the level beneath) + two additive endpoints (`/observability/health/series`,
`/observability/health/publisher`) + tests. Deterministic aggregation over the Registry; read-only; advisory.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Additive; existing behavior byte-for-byte.** `git diff main -- app.py` = two new routes only (no `-`
  lines); the certified `/observability/health` (Issue Health), `/registry`, and all existing routes are
  unchanged. `issue_health` is untouched (`series_health`/`publisher_health` are new; the shared `_envelope`
  is a new helper — `issue_health` still builds its envelope inline, byte-for-byte). Full suite **325 passed**
  (was 315).

### Deterministic aggregation only — no new intelligence (the founder's constraint)
- **No new data source, no inference.** Both functions derive **solely** from the Registry via the certified
  primitives (`assess_issue` + `roll_up`). Series = `roll_up` over its issues' healths; Publisher = `roll_up`
  over its series' healths. Pure (no wall-clock; `registry_generated_at` carried through; sorted, stable).
- **Compositional hierarchy** — `publisher_health` composes `series_health` composes `issue_health`
  (`Certified Registry → Issue → Series → Publisher`), so each level is independently explainable/testable.
- **Coherence proven** — `roll_up` is a monotone max over `attention > unknown > healthy` (associative);
  `test_coherence_publisher_equals_rollup_over_all_issues` asserts `publisher(series(issues)) ==
  roll_up(all issue healths)`. The hierarchy cannot disagree with itself.

### Ownership boundary
- **Registry-only, read-only, advisory.** No Publisher read, no write anywhere. Endpoints are `GET`,
  auth-gated (`test_observability_rollup_endpoints_require_auth` → 401), 503 on error (never 500), same
  contract as the certified projection.

### Correctness coverage
- Series: all-healthy → healthy; any attention → attention; unknown propagation (no attention); multi-series
  each rolled up; issue counts. Publisher: aggregates series; multi-publisher; issue-count rollup; the
  coherence property; tree-of-one → healthy at all three levels. Envelope shape + summary counts.

### Scope + coupling
- **Only `scout_observability.py` + `app.py` (additive) changed.** Leaf module (stdlib only, no cycle). API
  extended additively (sub-routes), preserving the certified endpoint — the agreed "refactor when a 2nd
  projection exists" done without regression. No new ADR (realizes ADR-0001 D8). Series + Publisher stayed a
  single small pure-rollup increment (no complexity blow-up → no split needed).

## Evidence
- `git diff main -- app.py`: two additive routes; no existing route changed.
- New tests: **+10** (`SeriesHealthTest` ×4, `PublisherHealthTest` ×4; endpoint ×2 incl. auth).
- Full suite (venv): **325 passed, 0 failures** (was 315).
- `py_compile` clean.

**Gate to proceed (merge Inc 2; then a separate deploy/validation increment — same as Inc 1):** founder
certification. Deploy + operator validation are separate lifecycle steps.
