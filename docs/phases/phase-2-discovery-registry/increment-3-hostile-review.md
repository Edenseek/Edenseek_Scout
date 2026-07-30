# Phase 2 · Increment 3 (Registry persistence) — Hostile Review

**Scope reviewed:** added `persist_registry` / `load_registry` / `rebuild_registry` (+ `_target`,
`ScoutRegistryError`, `REGISTRY_ARTIFACT_KEY`) to `scout_registry.py`, persisting the derived Registry
projection to a single latest-state object at the Scout-bucket root `registry/registry.json`. New
tests in `tests/test_scout_registry.py`. **No production consumer, no existing module changed.**

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Byte-for-byte preserved.** `git diff main` touches only `scout_registry.py` + its test (+ this doc);
  no existing production module changed; nothing imports `scout_registry`. Full suite **284 passed**
  (279 prior + 5 new).

### ADR conformance
- **D3 — derived, rebuildable projection.** The Registry persists as a **latest-state overwrite** (not
  immutable history), reconstructable by `rebuild_registry` (resolve → persist). It is a peer of the
  benchmark platform projection, keyed at the bucket root — not a per-issue object and not a source of
  truth.
- **D6 — flat, platform-wide.** The whole flat, issue-prefix-keyed projection persists as one object at
  `registry/registry.json`; rollup/tree remain pure views.
- **Ownership boundary (D1).** Writes go **only** to `edenseek-scout`
  (`test_persist_writes_only_scout_bucket` asserts the store contains exactly the one registry key in the
  scout bucket). The write cannot reach `edenseek-publishing` (fixed root key + scout bucket; IAM Deny in
  prod). Resolution remains GET-only on the Publisher.
- **Integrity.** Reuses the certified R1 write helpers (`srp._dumps` / `_put` / `_verify_readback`), so
  every write is readback SHA-256 verified — same contract as reports/index/ledger.

### Env/context parity + robustness
- **`_target` env-vs-context parity.** `test_persist_context_equals_env` persists the same registry under
  an explicit context (environment cleared) and under the environment, asserting a **byte-identical**
  stored object — the target resolution mirrors the certified `scout_benchmark` bucket/region pattern.
- **Absent Registry tolerant.** `load_registry` returns an empty registry (count 0) when none exists yet
  (`test_load_absent_returns_empty_registry`), rather than raising; config/transport/JSON errors fail loud
  via `ScoutRegistryError`.
- **Roundtrip fidelity.** `test_persist_and_load_roundtrip` and `test_rebuild_registry_end_to_end` confirm
  a persisted Registry loads back byte-faithfully with the resolved entry (revision + verbatim state +
  audit linkage) intact.

### Scope + coupling
- **No production consumer.** No production module imports `scout_registry`; the operational surface is
  untouched. Nothing persists a Registry in the running pipeline yet.
- **No import cycle.** `scout_registry` imports `scout_report_publisher` (for the R1 write helpers) +
  the readers; none of them import `scout_registry` (verified).
- **In-milestone.** Persistence of the derived projection only — no Discovery, no scheduler wiring, no
  operational endpoint.

## Evidence
- `git diff main`: only `scout_registry.py` + `tests/test_scout_registry.py` (+ this doc).
- New tests: **+5** (`PersistTest`).
- Full suite (venv): **284 passed, 0 failures** (was 279).
- `py_compile` clean.

**The Registry (D3/D6) now exists end-to-end for the tree-of-one: model → resolve → persist/load/rebuild,
all additive and behavior-neutral, with no production consumer. Gate to proceed to Increment 4 (Discovery
— enumerate issues to build contexts for the Registry) OR to wiring an operational read (dashboard/endpoint
+ scheduled rebuild): founder certification + direction.**
