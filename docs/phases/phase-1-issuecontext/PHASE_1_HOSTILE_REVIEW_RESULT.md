# Phase 1 — IssueContext Plumbing · Hostile-Review Checklist — RESULT

**Status:** COMPLETE — every item refuted with evidence. Phase 1 = Increments 1–5 (introduce
`IssueContext`; thread an optional `context=None` through read path, persistence, index, ledger, evidence,
runners, and projections). `context=None` is byte-for-byte the certified single-issue behavior; `from_env()`
is **not** activated in any execution path.

Evidence base: full suite **260 passed, 0 failures** (venv); committed branch diff `git diff main HEAD`
(29 files — production modules + tests + these docs only); production re-cert against live prod (below).

## Behavioral equivalence (the core risk)
- [x] **`context=None` truly equals today.** `IssueContext.from_env()` reproduces the exact env derivation —
  `test_scout_context.ByteEquivalenceTest` asserts its bucket/prefix/region/identity equal the modules'
  *own* private derivations (`audit_s3_source._require_approved_prefix`/`_derive_identity_tail`,
  `srp._require_issue_prefix`); `EnvContractTest` guards the env-var names + `DEFAULT_REGION` against drift.
- [x] **Byte-for-byte report body.** Production re-cert (dry-run, `context=None`, branch code) assembled
  `run_id=run_833dfc915be60481` — identical to persisted `run000003` — with identical comparability keys
  (`cmp_5a84e2667714` / `cmp_2d1ab97056d5`) and `published_revision_id`. `run_id` is a deterministic hash
  over the same inputs ⇒ the serialized body is identical.
- [x] **R1 keys unchanged.** Each layer's threading tests assert identical S3 keys and byte-identical stored
  objects env-vs-context (`reports/`, `history/`, `report_index.json`, `ledger/processed_revisions.json`,
  `benchmark/*`).
- [x] **run_seq not advanced.** The canonical entry (`python scout_delta_audit.py`, branch, prod) returned
  `status: skipped` (`already_processed`, `fp_580cbeb1f41b`) — no new `run_seq`; index `count=3`,
  latest `run_seq=3` unchanged.
- [x] **Comparability keys identical.** Fingerprint `fp_580cbeb1f41b` unchanged (Phase 1 altered no
  methodology version); geometry/metadata comparability keys match the persisted run.

## Ownership boundary (must never regress)
- [x] **No `edenseek-publishing` write.** Every threading increment includes a "writes only edenseek-scout"
  test; the production re-cert was read-only (dry-run + idempotent skip). No write path added.
- [x] **Read/write buckets not swapped.** `IssueContext` validates the approved (read) prefix must end
  `/approved` and the scout (write) prefix must be `publishers/.../issues/{id}`; transposing them fails loud
  (`test_scout_context` fail-loud cases). The write modules read only `context.scout_*`; the read layer only
  `context.approved_*`.
- [x] **Prefix contracts enforced.** `test_scout_context.FailLoudTest`: non-approved prefix, missing
  `issues/`, prefix not ending at the issue, and approved/scout identity mismatch all raise
  `IssueContextError`.

## Scope creep (Phase 1 must stay Phase 1)
- [x] **No Discovery/Registry code.** No `scout_registry.py` / `scout_discovery.py`; no enumeration/registry
  object introduced.
- [x] **Scheduler unchanged.** `scheduler.py` not in the committed branch diff.
- [x] **Dashboard unchanged.** `static/index.html` and `app.py` not in the committed branch diff; all
  endpoints/jobs still resolve the single issue from env (they pass no context).
- [x] **No new required env var.** Every threaded entry point defaults `context=None`; `is_configured()`
  unchanged; `.env` works unchanged.

## Backward compatibility + regressions
- [x] **Every existing caller still compiles/behaves** without a context — full suite green with all
  production callers (`app.py`, `scheduler.py`, `scout_watch.py`, `dataset_auditor`, runners) unchanged.
- [x] **Full pre-existing suite passes.** 260 passed; **no existing test was weakened**. One test-fixture
  correction: the `flaky_update` monkeypatch stub signature was widened to match the real
  `update_index(entry, client=None, context=None)` — a fake must match the function it replaces; the guarded
  assertion (index-stage failure → no duplicate) is unchanged.
- [x] **Idempotency preserved (D4).** The ledger remains the dedupe authority; the re-cert reconciled to the
  existing run (skip), no second path bypasses it.
- [x] **Registry not introduced as a source of truth (D3).** N/A in Phase 1 — none added.

## Failure-mode probes
- [x] **Unset env → fail loud.** `IssueContext.from_env` raises `IssueContextError` listing the missing
  vars (`test_missing_env_raises` / `test_empty_env_value_raises`); the env path still raises the original
  `ScoutS3SourceError` / `ScoutReportPublishError` (the env branches were preserved verbatim — the
  `ScoutS3SourceError → 503` handler in `app.py` is unaffected).
- [x] **Concurrent single-issue calls.** No change to the concurrency model — behavior is identical to
  today (the refactor is forwarding-only).
- [x] **Exception mid-flow handled exactly as before.** `_failure_stage` mapping unchanged; a failure still
  routes to `ledger.mark_failed` (now context-aware) with the same stage/codes; no new unhandled 500s.

## Sign-off
- [x] All boxes checked with linked evidence (tests / commands above).
- [x] **Runbook §Certification 1–5:** (1) suite green (260); (2) byte-equivalence proven per layer;
  (3) single-issue production re-cert — idempotent skip, no new `run_seq`, byte-equivalent logical run;
  (4) boundary — no `edenseek-publishing` writes; (5) merge to `main` via PR.
- [x] Rollback point = `main` HEAD at merge time (recorded in the merge PR); the refactor is not deployed to
  the VM by this merge (deploying Phase 1 is a separate, later decision).

**VERDICT: PASS — Phase 1 certified. Proceed to merge. STOP before Discovery/Registry (Phase 2).**
