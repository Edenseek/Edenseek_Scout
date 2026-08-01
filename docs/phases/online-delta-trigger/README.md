# Online delta-audit trigger + report selector

**Branch:** `week11-online-delta-trigger` · **Date:** 2026-08-01 · read-and-advise, additive.

## Why
During the Metadata Accuracy v2 live cert the founder saw the **delta report was stale** even though the
retrieval audit was current. Root cause: the delta-audit trigger has **no active cadence in production** —
`scheduler._delta_reconcile_enabled()` is OFF by default (`SCOUT_DELTA_RECONCILE_ENABLED=false`), while the
retrieval/dataset audit runs on a **separate, enabled** cron. So the delta audit only re-ran when
`scout_watch.py` single-shot was invoked on the VM, which hadn't happened for the new revision. There was
also **no way to trigger the delta audit from the online Scout** (only `/run-audit` = dataset and
`/run-scout` = OpenAI existed), and the dashboard **cached reports for the session**, so it kept showing the
first report fetched.

## What changed
1. **`POST /run-delta-audit`** (`app.py`) — auth'd endpoint calling the canonical
   `scout_delta_audit.audit_current_revision(trigger="manual")` (same entry point the scheduler
   reconciliation uses). Read-and-advise: audits the current approved revision and persists an immutable
   Scout report to `edenseek-scout`; never writes Publisher data. Idempotent — an already-processed revision
   returns `skipped`/`reconciled` (a 200 no-op); `failed`/`error` → 503. ADR-0002 guard still gates real S3.
2. **Dashboard "Run Delta Audit" button** (header) — triggers the endpoint, then clears caches and jumps to
   the freshly persisted latest.
3. **Report selector + Refresh** (`reportBar`, Intelligence + Engineering) — a picker over the archive's
   report entries (newest first, `runNNN · …id · date`), defaulting to **Latest**, so the founder can see
   and choose exactly which run the analysis pages read. The "Currently analyzing" summary already shows the
   report_id.
4. **Session-cache fix** — reports were cached in module vars for the session and never refreshed;
   `resetReportCaches()` (on Refresh / after any audit) makes the page reflect the newest persisted report.

## Not changed
The delta reconcile scheduler job stays **OFF** — enabling an automatic cadence
(`SCOUT_DELTA_RECONCILE_ENABLED=true`) is a deliberate scheduler-activation decision, out of scope here. The
manual online trigger covers the current need.

## Tests
`tests/test_run_delta_audit_endpoint.py` — auth required; `persisted`/`skipped` → 200 pass-through;
`failed`/`error`/unexpected exception → 503. Dashboard JS syntax-checked. Full suite 364 pass.
