# Phase 1 — IssueContext Plumbing · Runbook

**Status:** PREPARED. **Do not execute** until `PHASE_1_ENTRY_GATE.md` is fully satisfied.
Local-development + committed-increment work only. **No production redeploy is part of Phase 1** (the
refactor is behavior-neutral; deployment of Phase 1 to the VM is a separate, later decision).

## Pre-flight (record before any change)
1. Confirm the entry gate is green (`PHASE_1_ENTRY_GATE.md`).
2. Record the **rollback point:** `git rev-parse HEAD` on `main` (the certified baseline commit).
3. Create a working branch off `main`: `phase-1-issuecontext` (never commit Phase 1 directly to `main`).
4. Capture a **baseline fingerprint** of the certified single-issue outputs for later comparison
   (read-only): current `report_index.json`, latest `scout_delta_report` `report_sha256`, latest
   `scout_report` `report_id`, ledger entry — from `edenseek-scout` (read-only; no writes).

## Execution steps (each a small, reviewed, tested commit)
1. **Add `scout_context.py`** (`IssueContext` + `from_env()` / `for_prefixes()`), with unit tests. No other
   module changed yet. Run suite.
2. **Thread `context` into the read path** (`audit_s3_source`): optional `context=None → from_env()`.
   Add the equivalence test for `resolve_current_revision` / `materialize_approved_contract`. Run suite.
3. **Thread `context` into persistence + index + ledger** (`scout_report_publisher`, `scout_report_index`,
   `scout_revision_ledger`), one module per commit, each with its equivalence test. Run suite after each.
4. **Thread `context` into the runners** (`scout_delta_audit`, `dataset_auditor`): `context=None →
   from_env()`. Add end-to-end equivalence tests. Run suite.
5. **Thread `context` into projections** (`scout_benchmark`, `scout_archive`, `scout_intelligence`).
   Run suite.
6. **Confirm `app.py`, `scheduler.py`, `scout_watch.py`, `static/index.html` are unchanged** (endpoints and
   jobs still resolve `from_env()` = single issue).

At no point does a caller become *required* to pass a context; the env default is always the fallback.

## Certification procedure (Phase 1 "done")
1. **Full test suite green**, including all new equivalence tests (explicit context ⇄ env default) and the
   pre-existing baseline (no regressions).
2. **Byte-equivalence proof:** the equivalence tests assert identical S3 keys + identical serialized bytes
   for `context=from_env()` vs the prior no-arg calls (mocked S3).
3. **Single-issue production re-cert (read-mostly):** run the canonical entry with the env-default context
   against production; verify it is **idempotent** — reconciles to the existing logical run, produces **no
   new `run_seq`**, same `report_id`/`run_id`, hash round-trip holds, index/ledger/benchmark unchanged vs
   the pre-flight fingerprint. (Because Phase 1 changes no methodology and no keys, the certified run must
   not be superseded.)
4. **Boundary check:** confirm no `PutObject` targeted `edenseek-publishing` during the re-cert (all writes
   to `edenseek-scout`; IAM Deny would catch a regression).
5. **Merge** the `phase-1-issuecontext` branch to `main` via PR only after 1–4 pass.

## Rollback procedure
- **Pre-merge:** discard the branch — `main` (the recorded rollback point) is untouched; production
  continues on the certified baseline. No production impact (Phase 1 is not deployed during development).
- **Post-merge, pre-deploy:** revert the merge commit on `main`; production is still on the prior commit
  until a deliberate redeploy.
- **If Phase 1 is ever deployed and a regression appears:** `git checkout <recorded baseline commit>` on the
  VM + `sudo systemctl restart edenseek-scout` returns to the certified single-issue behavior; the `.env`
  and IAM are unchanged, so rollback is code-only and immediate.
- **Data safety:** Phase 1 writes nothing new/irreversible — it is a behavior-neutral refactor; the
  immutable reports/index/ledger are unchanged, and any accidental extra write to `edenseek-scout` is
  versioned/recoverable.

## Guardrails (abort conditions — stop and report, do not "fix forward")
- Any equivalence test shows a **byte difference** for `context=from_env()` vs the prior call.
- The single-issue re-cert produces a **new `run_seq`** or a different `report_id`/`run_id`.
- Any write attempt to `edenseek-publishing`.
- Any need to add a **required** new env var or change production config to keep single-issue working.
- Any temptation to introduce Discovery/Registry/scheduler/dashboard behavior — that is a later phase.
