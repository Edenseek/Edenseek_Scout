# Phase 2 · Increment 5c (governed publisher-wide rebuild: Discovery → rebuild) — Hostile Review

**Scope reviewed:** `scout_registry.rebuild_discovered` + a `--discover` CLI mode — the governed
publisher-wide one-shot that runs read-only Discovery, then the certified resolve/persist pipeline over
ALL discovered issues. New tests in `tests/test_scout_discovery.py`. Also executed **live against
production**. **No scheduler, no autonomous execution.**

## Verdict: PASS

### The invariant is preserved
```
Publisher → Discovery (enumeration only) → IssueContexts → Registry rebuild → Registry
```
- `rebuild_discovered` = `scout_discovery.discover_contexts()` (read-only enumeration) → certified
  `resolve_registry` + `persist_registry`. **Discovery identifies work; the Registry derives truth** —
  Discovery contributes only the set of contexts; every entry's revision/state/audit is resolved from
  authoritative objects by the certified pipeline. `test_rebuild_discovered_publisher_wide` proves it:
  two discovered issues, both entries' truth resolved by the pipeline, and the **only** write is
  `registry/registry.json`.

### Behavioral equivalence (core risk)
- **Additive; default path byte-for-byte.** `git diff main -- scout_registry.py` adds `rebuild_discovered`
  and branches the CLI on `--discover`; the default (no-flag) CLI path still calls `rebuild_current`
  unchanged. Only `scout_registry.py` + a test changed. Full suite **297 passed** (295 prior + 2 new).
- **Certified audit path untouched.** No audit-path module changed.

### Ownership + read-only discipline
- **Read-only on the Publisher; single Scout write.** Discovery is ListBucket-only; resolution is
  GET-only; the sole write is `registry/registry.json` in `edenseek-scout` (test asserts
  `s3.puts == ["registry/registry.json"]`; the live run wrote only that key).
- **Governed one-shot.** Human-run CLI (`python scout_registry.py --discover`). It runs once and exits —
  no scheduler, no background loop, no automatic trigger.
- **Integrity.** Persist reuses the certified `srp._put`/`_verify_readback` (readback SHA-256). The CLI
  fails loud (log + exit 1).
- **Empty discovery is explicit.** No auditable issues → an empty Registry is persisted **with a logged
  warning** (`test_rebuild_discovered_empty_when_no_issues`) — no silent behavior. (Discovery enumeration
  failure is fail-loud, so "empty" means genuinely no published issues, not a swallowed error.)

### Layering / coupling
- **Registry consumes Discovery, one-directional.** `rebuild_discovered` imports `scout_discovery`
  (local import); `scout_discovery` does **not** import `scout_registry`. No import cycle. This is the
  intended evolution of the 5b separation (Discovery produces; the Registry, a higher layer, consumes).

### Live production validation
- Ran `python scout_registry.py --discover` against production: **discovered 1**, rebuilt +
  readback-verified `registry/registry.json` (count 1, `sha ec57c133…`). The resolved entry matches the
  certified baseline exactly (`rev_0be8dc34` / `edenseek_approved` / `audited` / `run_seq 3` /
  `run_833dfc915be60481` / `run000003`) and equals the single-issue rebuild from 5a — confirming the
  discover→rebuild orchestration derives identical, correct truth from real data.

### Scope
- Governed publisher-wide **one-shot** only. **No scheduler-driven execution and no autonomous execution**
  introduced — stopped here as instructed.

## Evidence
- `git diff main -- scout_registry.py`: additive (`rebuild_discovered` + CLI branch); default path unchanged.
- New tests: **+2** (`RebuildDiscoveredTest`): publisher-wide 2-issue rebuild (single Registry write),
  empty-discovery.
- Full suite (venv): **297 passed, 0 failures** (was 295).
- Live prod one-shot: discovered 1, persisted + readback-verified, entry cross-matches the certified baseline.
- `py_compile` clean.

**The full Phase-2 Discovery → Registry lifecycle is now governed and validated end-to-end against
production. Gate to proceed to scheduler-driven execution (ADR-0001 D7 step 4):** founder certification —
and a separate, explicit go-ahead, since scheduling crosses into automatic execution.
