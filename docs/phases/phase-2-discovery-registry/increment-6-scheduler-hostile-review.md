# Phase 2 · Increment 6 (scheduler-driven Registry rebuild) — Hostile Review

**Scope reviewed:** an **opt-in** scheduled job in `scheduler.py` — `scheduled_registry_rebuild` — that,
when enabled, runs the certified `scout_registry.rebuild_discovered` on an interval. Off by default
(`SCOUT_REGISTRY_REBUILD_ENABLED=false`). New tests in `tests/test_d2_automation.py`. **Orchestration
only — it changes no Registry or Discovery behavior.**

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Off by default → byte-for-byte scheduler.** With `SCOUT_REGISTRY_REBUILD_ENABLED` unset/false (the
  certified production config), `register_jobs` registers the **identical job set** as before — the new
  block logs "disabled" and adds no job (`test_off_by_default`). The only diff to existing behavior with the
  flag off is one extra log line + the module docstring; **no registered job or its config changed**. Full
  suite **301 passed** (297 prior + 4 new).
- **Mirrors the certified delta-reconcile job exactly** — same flag pattern (`_flag(..., "false")`), same
  interval-config pattern, same `coalesce=True` / `max_instances=1` / `replace_existing=True` /
  `misfire_grace_time`, same never-re-raise callback.

### The invariant is preserved (orchestration only)
- The job calls **only** the certified `rebuild_discovered` (Discovery → certified resolve/persist). It
  changes nothing in `scout_registry` or `scout_discovery`. `test_job_calls_certified_rebuild_discovered`
  confirms the callback invokes exactly that entry point; the pipeline (read-only Publisher, single Registry
  write, state derived from authoritative objects) is unchanged and already certified in 5c.
```
Publisher → Discovery (enumeration only) → IssueContexts → Registry rebuild → Registry
```
  The scheduler sits *above* this, invoking it on a cadence — it does not reach into any layer.

### Safety
- **Never re-raises.** `test_failure_is_caught_not_raised`: a failing rebuild is logged, the scheduler stays
  alive (same contract as every other job).
- **Idempotent + non-overlapping.** `rebuild_discovered` is a rebuildable projection; `max_instances=1` +
  `coalesce=True` prevent overlap/backlog pile-up.
- **Not activated in production.** Off by default; enabling is a deliberate deploy-time flag decision
  (`SCOUT_REGISTRY_REBUILD_ENABLED=true`, interval via `SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES`, default 60).
  This increment does not enable it on the VM. Read-only on the Publisher; the only write remains
  `registry/registry.json`.

### Scope + coupling
- **Only `scheduler.py` + one test changed.** No change to Registry, Discovery, the audit path, or the
  operational endpoints. `scheduled_registry_rebuild` lazy-imports `scout_registry` (keeps scheduler import
  light; no import cycle).

## Evidence
- `git diff main -- scheduler.py`: additive (flag helpers + one callback + one gated job block +
  docstring); no existing job's registration or behavior changed.
- New tests: **+4** (`TestRegistryRebuildJob`): off-by-default, registered-when-enabled, calls the certified
  `rebuild_discovered`, never re-raises.
- Full suite (venv): **301 passed, 0 failures** (was 297).
- `py_compile` clean.

**With this, ADR-0001 D7 is fully realized in code (IssueContext → Registry → Discovery → scheduler),
every step additive, opt-in, and orchestrating the certified pipeline. Gate to enable in production / merge
Phase 2:** founder certification + an explicit enable decision.
