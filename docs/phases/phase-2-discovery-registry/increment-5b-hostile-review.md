# Phase 2 · Increment 5b (publisher-wide Discovery) — Hostile Review

**Scope reviewed:** new module `scout_discovery.py` — a **read-only producer of `IssueContext`s** that
enumerates auditable issues in the Publisher bucket (via the `approved/published.json` marker) and builds
one context per issue with the shared bucket+region config. New tests in `tests/test_scout_discovery.py`.
Also executed **read-only against production** to validate real enumeration.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Additive, no existing module changed.** `git diff main` adds only `scout_discovery.py` + its test; no
  existing production module modified. Nothing imports `scout_discovery`, so no production code path changed.
  Full suite **295 passed** (288 prior + 7 new).

### Ownership + read-only discipline
- **Read-only enumeration.** Discovery uses `ListObjectsV2` on the Publisher bucket only — no `GetObject`,
  no `PutObject`. `test_discovery_is_read_only` asserts zero writes during enumeration. It cannot mutate
  either repository.
- **Enumerates candidates only; derives no state.** Discovery produces contexts (identity + surfaces);
  it resolves nothing. Correctness continues to be derived by the certified `scout_registry` resolve/rebuild
  pipeline. `test_discover_then_rebuild_registry` proves the separation: Discovery finds two issues, the
  **certified** `rebuild_registry` resolves each from authoritative objects (revision + verbatim state +
  audit linkage), and the **only** write is `registry/registry.json` (resolution stayed read-only).
- **Authoritative marker.** An issue is a candidate iff it has `approved/published.json` — the same
  authoritative pointer `resolve_current_revision` reads. Discovery introduces no alternative source of
  truth and never consults the stale `dataset_registry.json`.

### Robustness / failure modes
- **Malformed prefix skipped.** A discovered prefix that is not a valid issue ownership chain is logged and
  skipped (`test_malformed_prefix_is_skipped`), never fatal — `for_prefixes` validation gates every context.
- **Config fail-loud.** Missing bucket config raises `ScoutDiscoveryError` (`test_config_missing_fails_loud`);
  a transport error during listing fails loud. Empty bucket → empty list, not an error.

### Live production validation (read-only)
- Ran `discover_contexts()` against production: enumerated **1 issue** —
  `publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001` — with the
  correct identity and approved/scout surfaces. The produced `IssueContext` matches the one 5a's governed
  rebuild used. No writes (ListBucket only).

### Scope + coupling
- **Only a new module + test.** No scheduler, no autonomous execution, no write trigger; Discovery persists
  nothing.
- **No import cycle.** `scout_discovery` imports `scout_context` (leaf) + `audit_s3_source` (for the client);
  it does **not** import `scout_registry` — verified that `scout_registry`/`scout_context`/`audit_s3_source`
  do not import `scout_discovery`. Discovery produces contexts; the Registry consumes them.

## Notes
- **Enumeration policy:** Discovery finds issues with a *current published revision* (the `published.json`
  marker). Issues that exist but were never published are not candidates yet — a deliberate, documented
  choice; `resolve_entry` already tolerates unpublished issues if a broader enumeration is added later.
- **Not wired to a trigger.** Feeding `discover_contexts()` into `rebuild_registry(...)` for a publisher-wide
  materialization is proven by test but is not yet a production trigger — that (and any scheduling) is a
  later, separately-certified step.

## Evidence
- `git diff main`: only `scout_discovery.py` + `tests/test_scout_discovery.py` (+ this doc).
- New tests: **+7** (enumeration, contexts, config fail-loud, malformed-skip, read-only, feeds-rebuild
  publisher-wide tree-of-two).
- Full suite (venv): **295 passed, 0 failures** (was 288).
- Live prod: read-only enumeration of the real tree-of-one.
- `py_compile` clean.

**Gate to proceed (scheduling / a governed publisher-wide rebuild trigger — Discovery → rebuild):** founder
certification. Stop before scheduling or autonomous execution.
