# Scout Daemon & Processed-Revision Ledger (Increment 2)

> One canonical agent path for the synchronization/delta audit, shared by scheduled, reconciliation,
> and manual triggers, made idempotent by a durable processed-revision ledger. The existing
> operational **dataset** audit is unchanged. Read-only on `edenseek-publishing`; writes only to
> `edenseek-scout`.

## Canonical entry point

`scout_delta_audit.audit_current_revision(client=None, force=False, trigger=...)` is THE delta-audit
agent entry. All triggers call it:

- **event / revision-watch (primary):** `scout_watch.check_and_delta_audit()` → `audit_current_revision(trigger="event")`, run each watcher cycle alongside the unchanged dataset audit (`run_cycle`).
- **reconciliation (fallback):** `scheduler.scheduled_delta_reconcile()` → `audit_current_revision(trigger="reconciliation")`, every `SCOUT_RECONCILE_INTERVAL_MINUTES` (default 15). **Disabled by default** (`SCOUT_DELTA_RECONCILE_ENABLED=false`).
- **manual:** `python scout_delta_audit.py` → `audit_current_revision(trigger="manual")`.

## Execution flow (a successful run)

```
resolve current certified revision (pointer read, cheap)
  → ledger cheap-check: already processed under this context?  ──yes──▶ skip (no evidence read)
  → build evidence manifest + generated-vs-approved delta        (stage: evidence)
  → assemble versioned report body + run_id                      (stage: assemble)
  → persist immutable report (history + latest), byte-verified   (stage: persist_verify)
  → read back + verify SHA-256                                   (stage: persist_verify)
  → update latest pointer + report index                        (stage: index)
  → mark revision PROCESSED in the ledger  ◀── only after all verified steps succeed
```

A failure at any stage records a ledger entry (`status=failed`, `failure_stage`, `error_codes`) and
**does not** mark the revision processed. Failed/incomplete runs are recorded but excluded from the
processed set, so reconciliation retries them. Retries are safe (see idempotency).

## Ledger schema + storage key

Storage key (`edenseek-scout`): `{issue}/ledger/processed_revisions.json` (`revision_ledger_version: v1`).

```jsonc
{ "revision_ledger_version": "v1", "issue_prefix": "...", "updated_at": "...", "count": N,
  "entries": {
    "{published_revision_id}@{context_fingerprint}": {
      "revision_id", "context_fingerprint", "status",         // processed | failed
      "run_id", "run_seq", "report_id", "completed_at",
      "generated_snapshot_revision_id", "comparability": { "geometry", "metadata" },
      "failure_stage", "error_codes", "attempts", "first_seen", "updated_at", "trigger" } } }
```

## Idempotency key construction (layered)

1. **Ledger eligibility key** — `{published_revision_id}@{context_fingerprint}`, where
   `context_fingerprint = "fp_" + sha256(sorted "k=v" of the STATIC methodology versions:
   report/algorithm/geometry_match/normalization/metadata_revision_distance/evaluation)[:12]`.
   Suppresses duplicates; a methodology bump changes the fingerprint → a changed-comparability
   re-audit (not suppressed).
2. **Logical run id** — `run_id = "run_" + sha256(published_revision_id | generated_snapshot_revision_id
   | geometry_comparability_key | metadata_comparability_key)[:16]`. Identifies the logical report.
3. **Persist-level guard** — `publish_delta_report` checks the latest pointer, and on a mismatch scans
   history for `run_id`; a retry after a **partial** persist completes the existing snapshot instead of
   minting a new `run_seq`. No duplicate logical report is ever created.

## Boundaries

The dataset audit (`dataset_auditor.run_dataset_audit`, `scout_watch.check_and_audit`,
`scheduler.scheduled_audit`) is untouched. The delta agent writes only to `edenseek-scout`. Production
VM scheduling for the delta reconciliation is **not activated** in this increment.
