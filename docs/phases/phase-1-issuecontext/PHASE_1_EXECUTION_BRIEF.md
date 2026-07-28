# Phase 1 — IssueContext Plumbing · Execution Brief

**Status:** PREPARED (control document). **Not started** — gated (see `PHASE_1_ENTRY_GATE.md`).
**Architecture source of truth:** `docs/architecture/ADR-0001-scout-publisher-observability-architecture.md`
(decision **D5**; migration **D7** step 1). Phase 1 implements **only** D5.

## Objective
Replace global environment-prefix reads (`SCOUT_APPROVED_S3_PREFIX`, `SCOUT_REPO_S3_PREFIX`, …) with an
explicit per-issue **`IssueContext`**, **while preserving byte-for-byte behavior for the currently certified
single-issue deployment.** An audit becomes a pure function of its `IssueContext`; the env-derived context
is the default, so single-issue and (future) publisher-wide runs are the same code over different contexts.

## Non-goals (explicitly out of scope for Phase 1)
- **No Discovery, Registry, scheduler, or dashboard changes.** (D2/D3/D6 are later phases.)
- No new environment variables required; no production configuration change; no redeploy.
- No change to report content, keys, identifiers, ledger semantics, or comparability.
- No new architectural concepts beyond ADR-0001.

## Invariants Phase 1 must preserve
- The existing **environment-derived default path** (unset context ⇒ behavior identical to today).
- The current **production scheduler** behavior (`scheduler.py` unchanged in Phase 1).
- **Report output paths** (R1 keys: `{issue}/reports/*`, `{issue}/history/*_{seq}.json`).
- **Audit results** and **report identifiers** (`report_id`, `run_id`, `run_seq`).
- **Ledger behavior** (idempotency key `(issue, revision, methodology)` — D4).
- **Dashboard behavior** (all endpoints render identically).
- **Repository ownership boundaries** (reads `edenseek-publishing`, writes only `edenseek-scout`).

## Design shape (control-level; final signatures fixed at implementation time)
- **New module `scout_context.py`:** an immutable `IssueContext` value object carrying
  `{ identity{publisher_id,title_group_id,series_id,issue_id}, approved_bucket, approved_prefix,
  scout_bucket, scout_prefix, region }`, plus:
  - `IssueContext.from_env()` → the **current single issue**, built from today's env vars — the default.
  - `IssueContext.for_prefixes(approved_prefix, scout_prefix, …)` → an explicit context (used by later
    phases; in Phase 1 only `from_env()` is exercised in production).
- **Threading (backward-compatible):** functions that today read the env prefixes gain an optional
  `context: IssueContext | None = None` parameter; `None` resolves to `IssueContext.from_env()`. No caller
  is required to change; existing calls behave identically.

## Anticipated files / modules affected
| Module | Phase-1 change (behavior-neutral) |
|---|---|
| `scout_context.py` (**new**) | `IssueContext` + `from_env()` / `for_prefixes()` |
| `audit_s3_source.py` | accept optional `context` in `resolve_current_revision`, `materialize_approved_contract`, `s3_client`; default `from_env()` |
| `scout_report_publisher.py` | accept optional `context` in `publish_reports`, `publish_delta_report`, `publish_scout_report`, `read_object`, `list_history_keys`, `last_published_revision_id`, `_require_issue_prefix` callers; default `from_env()` |
| `scout_report_index.py` | accept optional `context` in `load_index`, `update_index`, `rebuild_index` |
| `scout_revision_ledger.py` | accept optional `context` in `load_ledger`, `mark_processed`, `mark_failed`, `_ctx` |
| `scout_delta_audit.py` | `audit_current_revision(context=None, …)`; `run_and_persist(context=None, …)` |
| `dataset_auditor.py` | `run_dataset_audit(context=None)`; `_resolve_input_dir` honors `context` |
| `scout_benchmark.py`, `scout_archive.py`, `scout_intelligence.py` | accept optional `context` where they read the repo prefix |
| `app.py` | no change to routes/behavior; endpoints still resolve `from_env()` (single issue) |
| `scheduler.py`, `scout_watch.py`, `static/index.html` | **unchanged in Phase 1** |

## Acceptance criteria (all must hold)
1. **Equivalence:** for every touched module, `f(context=IssueContext.from_env())` produces **byte-identical**
   results to today's `f()` (same S3 keys, same object bytes, same return values).
2. **Default preserved:** calling any refactored function with no `context` behaves exactly as before.
3. **Production parity re-cert:** a re-run of the backend production certification on `issue_001` yields the
   same `report_id`/`run_id`/`run_seq`, the same hash round-trip, the same index/ledger/benchmark state
   (idempotent — no new logical run created by the refactor).
4. **No new required config:** the deployment's existing `.env` continues to work unchanged.
5. **Full test suite green** (current baseline + new Phase-1 equivalence tests).
6. **Boundaries intact:** no write to `edenseek-publishing`; all writes to `edenseek-scout`.
7. **Scheduler/dashboard untouched** and still deployable.

## Tests required (prove explicit-context ⇄ env-default equivalence)
- `test_scout_context.py` — `from_env()` builds the certified single-issue context; `for_prefixes()` builds
  an explicit one; immutability; prefix-contract validation (approved ends `/approved`; scout ends at
  `issues/{id}`).
- **Per-module equivalence tests** (mocked S3): for each refactored module, assert
  `explicit_context_result == env_default_result` (same keys written/read, same bytes) — e.g. index
  update, ledger upsert, publish keys, delta report body, dataset resolve.
- **End-to-end equivalence** (mocked S3): `audit_current_revision(context=from_env())` vs the current
  `audit_current_revision()` → identical persisted report + ledger entry + index entry.
- **Negative/guard:** an explicit context pointing at a different scout prefix routes writes there and
  **never** to `edenseek-publishing`.
- Existing suite continues to pass unchanged (no regressions).

## Certification checkpoint
See `PHASE_1_RUNBOOK.md` §Certification. Phase 1 is "done" only when acceptance criteria 1–7 are met, the
full suite is green, and the single-issue production re-cert is byte-identical.
