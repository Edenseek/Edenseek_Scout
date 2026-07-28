# Phase 1 — IssueContext Plumbing · Hostile-Review Checklist

**Status:** PREPARED. Adversarial checklist to run **against the Phase 1 implementation** before merge.
Assume the change is guilty of breaking the certified single-issue deployment until proven innocent.
Every item is a way Phase 1 could silently regress production; each must be explicitly refuted with
evidence (a passing test or a demonstrated read).

## Behavioral equivalence (the core risk)
- [ ] **Does `context=None` truly equal today?** Prove `from_env()` reproduces the exact prefixes/buckets
      the current code reads — no re-ordering, no defaulting to a different region/prefix.
- [ ] **Byte-for-byte report body.** The delta/dataset report serialized under a `from_env()` context is
      byte-identical to the current output (same `sort_keys`, same field order, same values) → `run_id`
      and `report_sha256` unchanged.
- [ ] **R1 keys unchanged.** `reports/{type}.json`, `history/{type}_{seq}.json`, `report_index.json`,
      `ledger/processed_revisions.json` resolve to the identical keys under the env-default context.
- [ ] **run_seq not advanced.** The single-issue re-cert reconciles (idempotent) and does **not** mint a
      new `run_seq` — confirm the ledger `run_id` matches and the latest pointer is unchanged.
- [ ] **Comparability keys identical.** Geometry/metadata `comparability_key`s do not change (Phase 1 alters
      no methodology version) — otherwise a spurious methodology boundary appears.

## Ownership boundary (must never regress)
- [ ] **No `edenseek-publishing` write.** An explicit context pointing at a wrong prefix must still route
      writes to `edenseek-scout`; a probe proves no `PutObject` to `edenseek-publishing`.
- [ ] **Read/write buckets not swapped.** `approved_*` (read) and `scout_*` (write) cannot be transposed by
      a context mis-build; validated by a guard test.
- [ ] **Prefix contracts enforced.** `approved_prefix` must end `/approved`; `scout_prefix` must end at
      `issues/{id}`; a malformed context fails fast (fail-loud), never silently writes elsewhere.

## Scope creep (Phase 1 must stay Phase 1)
- [ ] **No Discovery/Registry code** introduced (no enumeration, no registry object, no `scout_registry.py`/
      `scout_discovery.py`).
- [ ] **Scheduler unchanged.** `scheduler.py` job set + cadence identical; reconciliation still disabled by
      default.
- [ ] **Dashboard unchanged.** `static/index.html` and all `app.py` routes behave identically; endpoints
      still resolve the single issue from env.
- [ ] **No new required env var.** Existing `.env` works unchanged; any new var is optional with a
      backward-compatible default.

## Backward compatibility + regressions
- [ ] **Every existing caller still compiles/behaves** without passing a context (optional param, env
      fallback).
- [ ] **Full pre-existing suite passes** unmodified (no test had to be weakened to accommodate the refactor).
- [ ] **Idempotency preserved (D4).** The ledger remains the dedupe authority; the refactor does not create
      a second path that bypasses it.
- [ ] **Registry not introduced as a source of truth (D3).** N/A in Phase 1 — confirm none was added.

## Failure-mode probes
- [ ] Unset one env var → `from_env()` fails **loud** (clear error), never silently audits the wrong issue.
- [ ] Concurrent single-issue calls → no interleaving corrupts the index/ledger (same as today's assumption).
- [ ] A raised exception mid-refactored-flow is handled exactly as before (no new unhandled 500s; cf. the
      `ScoutS3SourceError → 503` handler already in place).

## Sign-off
- [ ] All boxes checked with linked evidence (test name or command output).
- [ ] Runbook §Certification 1–5 complete.
- [ ] Rollback point recorded; branch not yet merged (or merged with PR + green suite).
