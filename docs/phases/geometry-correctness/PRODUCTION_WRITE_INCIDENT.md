# Incident + RCA: test suite wrote to production

> **Status:** RESOLVED. Root cause identified; permanent safeguard landed (`scout_runtime.py`, ADR-0002);
> production active state restored + validated. One residual hardening item tracked below. 2026-07-30.

## Summary

During Increment-1 development, a full local test-suite run — on a workstation whose `.env` carried
live `edenseek-scout` credentials — **published an uncertified delta report (`run000004`, geometry
`v2`) to the production `edenseek-scout` bucket.** No Publisher (`edenseek-publishing`) data was
touched; the write was to Scout's own repo. It was caught immediately and no cleanup was attempted
without approval.

## Objects affected (all 2026-07-31T00:01Z)

| Object | Change |
|---|---|
| `…/issue_001/history/scout_delta_report_000004.json` | **created** (362 KB, geometry v2) |
| `…/issue_001/reports/report_index.json` | count 3 → **4**; `run000004` (v2) became latest |
| `…/issue_001/ledger/processed_revisions.json` | **added** `rev_0be8dc34…@fp_75f356d8b2ee` (v2), run_seq 4 |
| `…/issue_001/reports/scout_delta_report.json` (latest pointer) | overwritten to run000004 (if present) |

## Root cause (mechanism)

1. **Credentials entered the test process implicitly.** App modules load `.env` at import
   (`scout.py` → `load_dotenv()`). Importing any app module in a process that can see `.env`
   (or `~/.aws`) makes live production credentials + real bucket names active.
2. **One test drove the real audit through an unmocked path.**
   `tests/test_scout_watch.py::test_single_shot_success_exits_zero` calls `scout_watch.main([])`.
   `main()` runs **two** cycles: `check_and_audit()` (the dataset audit — the test mocks this) **and**
   `check_and_delta_audit()` (the delta agent — **not** mocked). The delta agent calls
   `scout_delta_audit.audit_current_revision(trigger="event")` with **no client**, so
   `audit_current_revision` created a **real** boto3 client (`client = client or s3_client(...)`),
   resolved the real current revision, ran the full delta, and **wrote** the report + index + ledger.
3. **It happened exactly once, and silently.** The audit is ledger-idempotent: the v2 methodology
   fingerprint was absent, so it wrote `run000004` and marked the revision processed; every later
   run sees the fingerprint and reconciles (no write). And `scout_watch.main` catches delta-cycle
   exceptions and "continues", so a *successful* write produced no failure and no visible signal.

## Why the safety boundary failed

There was **no enforced boundary** — only a convention ("inject a fake client in tests"). Any code
path that fell back to the default real client (`client=None`) would reach production whenever
credentials were ambient. Nothing at the tooling level distinguished a test/development process
from the deployed agent.

## Fix — a tooling-enforced runtime boundary (`scout_runtime.py`)

A single choke point: **every** real boto3 S3 client in the app is created by one of two factories
(`audit_s3_source._s3_client`, `scout_report_publisher._s3_client`). Both now call
`scout_runtime.guard_real_s3_client()`, which enforces `SCOUT_RUNTIME_MODE`:

- `production` — real clients allowed (the deployed VM).
- `development` (**default, deny-by-default**) — real clients refused unless `SCOUT_ALLOW_REAL_S3=1`
  is set intentionally.
- `test` — real clients **always** refused; tests inject fakes.

Defense in depth: `tests/__init__.py` forces `test` mode + bogus creds/buckets before any app
import; and because the default is deny-by-default, a test/dev process is refused **even if the
bootstrap does not run** (e.g. `unittest discover -s tests`, which imports modules top-level). The
incident path now raises `ScoutSafetyError` instead of writing. `tests/test_production_safety.py`
is the CI regression guard.

**Deployment requirement:** the Oracle VM must run with `SCOUT_RUNTIME_MODE=production` (systemd
env). This safeguard must not be deployed without that env set, or the agent would be denied its
own real client.

## Recovery

See the restore procedure (`scripts/restore_run000004.py`, dry-run first): revert `report_index.json` to
count 3 / latest `run000003`, remove the `…@fp_75f356d8b2ee` ledger entry, revert the latest delta
pointer, and remove the errant `scout_delta_report_000004.json`.

## Resolution (2026-07-30)

**Restore executed (founder-approved).** Active state reverted and verified:
- `report_index.json` → count 3, run_seqs [3,2,1], latest `run000003`.
- `processed_revisions.json` → count 2, the `…@fp_75f356d8b2ee` (v2) entry removed.
- latest pointer `reports/scout_delta_report.json` → reverted to `run000003` content.

**The errant history object could NOT be deleted — by design.** `s3:DeleteObject` on
`edenseek-scout/…/history/scout_delta_report_000004.json` returned **AccessDenied**: the
`edenseek-scout-app` identity has no delete permission. The history archive is **immutable at the
IAM layer** — Scout cannot tamper with its own record even to correct a mistake. `run000004`
therefore remains in `history/` as an orphaned, unreferenced artifact (not in the index, ledger, or
latest pointer).

**Residual hardening item (open, LOW urgency).** `scout_report_index.rebuild_index` enumerates
`history/` blindly, so a future rebuild would resurrect `run000004`. `rebuild_index` is **manual-only**
(never auto-invoked — only a supervised recovery operation), so the live risk is low. Options
considered:
- **(A)** an elevated (admin) identity deletes the object — restores true pre-incident state, but
  breaks the immutable-archive principle and needs out-of-band credentials.
- **(B) — rejected.** "Reconcile rebuild against the ledger (include only ledger-processed runs)"
  does **not** work: the ledger is keyed by `(revision, fingerprint)` and is not a complete allowlist
  — `run000001` has no ledger entry, so this would wrongly drop a legitimate report.
- **(C)** an append-only **revocation marker** (e.g. `reports/revoked_runs.json` listing errant
  `run_id`s that rebuild + queries skip) — respects immutability (records a revocation, never a
  delete) and generalizes to any future errant/superseded run. More machinery than warranted for a
  single manual-only risk.

**Decision:** track as a low-urgency follow-up. Recommended permanent fix is **(A)** at convenience
(clean, one-time), or **(C)** if the platform later wants a general revocation capability. Not
blocking the core geometry work.

**Safeguard validated** against the exact incident condition (ambient `.env` creds, default
`development` mode, no opt-in): `audit_current_revision` refuses to construct a real client
(`ScoutSafetyError`) instead of writing; the factory refuses directly; an explicit opt-in re-enables
access. Full suite green (336 tests) under both discovery styles. Principle recorded as **ADR-0002**.
