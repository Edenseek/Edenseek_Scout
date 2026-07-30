# D8 · Increment 1 (Registry-Backed Issue Health) — Hostile Review

**Scope reviewed:** new leaf module `scout_observability.py` (a general Health Projection capability;
Issue Health as the first projection) + one additive endpoint `GET /observability/health` in `app.py` +
tests. Derives operational intelligence **solely from the Registry**; read-only; advisory.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Additive; existing behavior byte-for-byte.** `git diff main -- app.py` is one import + one new route
  inserted before `/reports/latest`; **no existing route, auth dependency, or handler changed.** The full
  suite (**315 passed**, was 301) exercises the existing surface unchanged. `scout_observability.py` and its
  test are new files; no other production module changed.

### Ownership boundary (the founder's explicit constraint)
- **No Publisher access, no writes, no new data source.** `scout_observability` imports only the standard
  library and consumes a Registry **dict**; the endpoint reads only the persisted Registry via
  `scout_registry.load_registry()` (`edenseek-scout`). It performs **no `edenseek-publishing` read and no
  write anywhere** — advisory only (Charter §4). The Publisher/Scout boundary is untouched.
- **Read-only endpoint** — `GET`, auth-gated (`test_observability_health_requires_auth` → 401), 503 on error
  (never 500; `test_observability_health_graceful`).

### General Health Projection design (per the founder's request)
- The module is framed + built as a **family** of projections, not a one-off endpoint: shared primitives
  `assess_issue` (atomic leaf rule), `roll_up` (parent-from-children — the crux primitive Series/Publisher/
  Cross-Series health will reuse), `_summary`, and a uniform envelope (`projection`/`summary`/`records`).
  Issue Health is the only concrete projection shipped; Series/Publisher/etc. are later additive increments
  that compose these primitives over the Registry `rollup`/`tree_view`. No routing over-generalization (single
  `/observability/health`, as agreed).

### Correctness / determinism
- **Pure + deterministic** — no wall-clock; `registry_generated_at` carried through from the Registry;
  records sorted by issue prefix (stable output).
- **Full rule coverage** — `healthy`; `attention` × {`audit_pending`, `audit_failed`, `not_platform_approved`,
  and a multi-reason case}; `unknown` (no revision); summary counts; the `roll_up` primitive's rules.
- **Drift guards** — `STATE_EDENSEEK_APPROVED == review_contract_adapter.STATE_EDENSEEK_APPROVED`;
  `AUDIT_AUDITED/AUDIT_FAILED == scout_registry.*` — the mirrored constants can't silently diverge.
- **Live-shape check** — the certified tree-of-one (`edenseek_approved` + `audited`) resolves to `healthy`
  (`test_certified_tree_of_one_is_healthy`), matching what the deployed `/registry` reports.

### Scope + coupling
- **Leaf module, no cycle** — `scout_observability` imports no Scout module; the endpoint composes
  `load_registry` + `issue_health`. Only `app.py` (additively) + the new module changed.
- **In-milestone** — Issue Health + shared primitives only; no Series/Publisher projections, no scheduler,
  no Registry/Discovery change, no new ADR (realizes ADR-0001 D8).

## Evidence
- `git diff main -- app.py`: import + one read-only route; no existing route changed.
- New tests: **+14** (`test_scout_observability.py` ×11 model/primitives; endpoint ×3).
- Full suite (venv): **315 passed, 0 failures** (was 301).
- `py_compile` clean.

**Gate to proceed to D8 Increment 2 (e.g. Series/Publisher Health rollups reusing `roll_up`):** founder
certification. Deploy + operator validation (plan §5) are separate lifecycle steps.
