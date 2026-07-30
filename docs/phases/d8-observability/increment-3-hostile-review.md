# D8 · Increment 3 (Cross-Series Health) — Hostile Review

**Scope reviewed:** additive pure `cross_series_health(registry)` in `scout_observability.py` (composing
`series_health`) + one additive endpoint `/observability/health/cross-series` + tests. Deterministic
platform-wide comparison over Series Health; read-only; advisory. Recorded `PRINCIPLES.md` P2.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Additive; existing behavior byte-for-byte.** `git diff main -- app.py` = one new route only (no `-`
  lines); the certified `/observability/health`, `/series`, `/publisher`, `/registry`, and all existing
  routes are unchanged. `issue_health` / `series_health` / `publisher_health` untouched. Full suite **330
  passed** (was 325).

### Recompute-from-below (PRINCIPLES.md P2) — the founder's invariant
- **Cross-Series is a pure function of Series Health.** `cross_series_health` composes `series_health` and
  only reshapes/filters its records (distribution + `by_health` grouping + attention set). It reaches into
  no lower layer. `test_recomputes_from_series_health` asserts `cross.summary == series.summary` and
  `attention == [non-healthy series records]` — the projection is fully recomputable from the layer beneath.
- **Deterministic, no inference.** Pure (no wall-clock; `registry_generated_at` carried through). Scope held
  to platform-wide distribution/attention only — **no per-publisher comparison, no anomaly/trend inference**.

### Ownership boundary
- Registry-only (via Series Health), read-only, advisory. No Publisher read, no write anywhere. Endpoint is
  `GET`, auth-gated (401 unauth in the endpoint test), 503 on error.

### Correctness coverage
- Tree-of-one → 1 healthy series, empty attention; mixed (healthy/attention/unknown) → correct summary,
  `by_health` grouping, and attention set = the non-healthy series (with `issue_counts`); recompute-from-below
  property; empty registry → zeros + empty groups. Endpoint serves the projection + requires auth.

### Scope + coupling
- **Only `scout_observability.py` + `app.py` (additive) changed.** Leaf module (stdlib only, no cycle). API
  extended additively (sub-route), preserving all certified endpoints. No new ADR (realizes D8). Per-publisher
  comparison deliberately deferred.

## Evidence
- `git diff main -- app.py`: one additive route; no existing route changed.
- New tests: **+5** (`CrossSeriesHealthTest` ×4; endpoint ×1 incl. auth).
- Full suite (venv): **330 passed, 0 failures** (was 325).
- `py_compile` clean.

**Gate to proceed (merge Inc 3; then a separate deploy/validation increment — same as Inc 1/2):** founder
certification.
