# Phase 2 · Increment 1 (`scout_registry.py` — Registry model) — Hostile Review

**Scope reviewed:** introduction of `scout_registry.py` (the Registry data model + pure
projection/view functions) + `tests/test_scout_registry.py`. **No I/O, no consumers, no existing
module changed** — an additive leaf, exactly like Phase 1 Increment 1 (`scout_context`).

Per ADR-0001 D7, Phase 2 builds the Registry first (seeded with the certified tree-of-one), then adds
Discovery, then points the scheduler at it. This increment is only the model.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Byte-for-byte trivially preserved.** `git diff main` touches only the two new files; no existing
  production module was modified. Nothing imports `scout_registry`, so no code path changed. Full suite
  **272 passed** (260 prior + 12 new) with every production module untouched.

### ADR conformance (the design being introduced)
- **D3 — derived projection.** The module is pure: `build_entry` / `build_registry` take supplied facts
  and produce a rebuildable, idempotent-by-key projection (`test_rebuild_is_idempotent_by_key`). It reads
  nothing and cannot consult the Publisher `dataset_registry.json`. Docstring pins the D3 invariant.
- **D6 — flat, hierarchy-keyed.** Entries are keyed by the issue ownership prefix; `rollup` and
  `tree_view` are pure VIEWS over the flat entries (`test_tree_view_is_a_view_over_flat_entries`,
  `test_rollup_by_series/publisher`). `rollup` rejects the `issue_id` leaf and unknown levels.
- **Facts vs. observations (Principle P1).** Publisher facts live in `publication`
  (`published_revision_id` / `review_id` / `state`, recorded verbatim, default `unknown`); Scout's audit
  linkage lives separately in `audit` (default `unprocessed`) — `test_audit_observation_recorded_separately`
  (and the passed audit dict is copied, not aliased).
- **Tree-of-one.** `test_tree_of_one` confirms the degenerate case is one path — the certified single
  issue — with no hierarchy over-building.

### Scope + coupling
- **Leaf module.** Imports only stdlib + `scout_context` (itself a leaf) — no import cycle; higher layers
  may later depend on the Registry.
- **No I/O / no persistence / no S3.** `resolved_at` and `generated_at` are supplied by the caller, never
  wall-clock — the projection is deterministic and testable. Persistence + resolution from authoritative
  objects are deferred to a later increment.
- **No consumers.** No production module imports it; the operational surface
  (`app.py`/`scheduler.py`/`scout_watch.py`/dashboard) is untouched.
- **In-milestone.** Registry model only — no Discovery, no scheduler wiring, no scope broadening.

## Evidence
- `git diff main`: only `scout_registry.py` + `tests/test_scout_registry.py` (additive).
- New tests: **+12** (`tests/test_scout_registry.py`).
- Full suite (venv): **272 passed, 0 failures** (was 260).
- `py_compile` clean.

**Gate to proceed to Increment 2 (seed/resolve a Registry for the certified issue from authoritative
objects + persist it as a derived, rebuildable projection):** founder certification.
