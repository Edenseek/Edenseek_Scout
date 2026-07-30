# Phase 2 · Increment 4 (Registry operational read path) — Hostile Review

**Scope reviewed:** two additive read-only endpoints in `app.py` — `GET /registry` (the persisted flat
projection) and `GET /registry/tree` (the pure D6 rollup view) — plus endpoint tests in
`tests/test_scout_intelligence.py`. This is the **first intentional change to `app.py` since Phase 1**;
it is strictly additive (a new read surface), which is exactly the founder-directed Increment-4 step
(prove the Registry is observable before Discovery populates it).

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Existing routes byte-for-byte unchanged.** `git diff main -- app.py` is additive only: one import
  (`import scout_registry`) + two new `@app.get` handlers inserted between the intelligence endpoints and
  `/reports/latest`. No existing route, handler, auth dependency, or error handler was modified. The full
  suite (**287 passed**, was 284) exercises the existing endpoints unchanged.
- **New behavior is read-only + additive.** Both routes are `GET`, both require Basic auth
  (`Depends(require_auth)`), both only read (`load_registry` / pure `tree_view`), and both map errors to
  **503** (never 500) — matching the certified archive/intelligence endpoint contract.

### Ownership + safety
- **Read-only.** No write path; `load_registry` is GET-only and `tree_view` is pure. The endpoints cannot
  mutate either repository.
- **Graceful/empty.** With no Registry persisted yet (the production case today), `GET /registry` returns an
  **empty Registry (count 0)**, not an error — the shape is observable immediately; a populated Registry
  awaits a `rebuild_registry` (deferred; no production writer exists yet). `test_registry_graceful_without_s3`
  asserts 200-or-503, never 500.
- **Auth enforced.** `test_registry_requires_auth` confirms both routes 401 without credentials.

### ADR conformance
- `GET /registry` serves the derived flat projection (D3); `GET /registry/tree` is a pure rollup VIEW over
  the flat entries (D6: the tree is a view, not storage). `test_registry_endpoints_serve_persisted_projection`
  confirms the flat projection is served verbatim and the tree view groups under the publisher.

### Scope + coupling
- **Only `app.py` + one test file changed** this increment. No scheduler, no dashboard (`static/index.html`
  untouched — a dashboard tab is deferred and, per the standing UI note, to be reviewed together), no
  Discovery, no write/rebuild wiring.
- `app.py` now imports `scout_registry` (which imports the readers + `scout_report_publisher`); no import
  cycle (nothing imports `app`).

## Note on the Phase-1 "app.py unchanged" invariant
Phase 1's hostile review asserted `app.py` was unchanged — that was a **Phase-1 constraint** (behavior-neutral
refactor), not a permanent freeze. Phase 2 Increment 4 is the approved point at which the operational read
surface is extended, additively and read-only. Existing endpoints remain byte-for-byte identical.

## Evidence
- `git diff main -- app.py`: additive (import + 2 read-only routes); no existing route touched.
- New tests: **+3** endpoint tests (`TestEndpoints`): serves projection + tree, requires auth, graceful.
- Full suite (venv): **287 passed, 0 failures** (was 284).
- `py_compile` clean.

**Gate to proceed to Increment 5 (populate the Registry — a governed `rebuild_registry` trigger, e.g. a
manual/one-shot run against production and/or a scheduled rebuild — and/or Discovery to enumerate issues):**
founder certification + direction. Not deployed to the VM by this increment.
