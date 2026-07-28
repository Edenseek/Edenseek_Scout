# Scout Reports Archive & Search (Increment 5)

> A read-only archive of one issue's audit history, ordered newest-first, merging **successful
> reports** (from the rebuildable report index) with **failed/incomplete runs** (from the durable
> processed-revision ledger). All search/filtering is **server-side** over persisted metadata — the
> browser passes a query and renders; it never recomputes an audit. `scout_archive`.

## Records

Each archive record is one of:
- `record_kind: "report"` — a successful run: report/run ids, revisions, review id, both timestamps
  (`event_time`, `measurement_time`) + `certified_at`, `worst_severity`, `finding_counts`/`codes`,
  flattened `metrics` (geometry + metadata rates), versions, commits, `persisted_key`, `report_sha256`,
  and `recommendation_text` (finding titles+details). Marked `is_latest` / `is_historical`.
- `record_kind: "failed_run"` — a failed/incomplete run from the ledger: `status`, `failure_stage`,
  `error_codes`, `attempts`, `trigger`, timestamps. Failed runs are visible in the archive but excluded
  from benchmarks (Increment 3) by construction.

Records are ordered by `archived_at` (report `completed_at` / failed `updated_at`) descending. Each
report carries a `methodology_boundary` flag ({geometry, metadata}) set when its comparability key
differs from the next-newer report — so a methodology change is visible in the archive, not hidden.

## Search grammar (server-side)

`GET /audit-review/search?q=...`; tokens are ANDed:

| token | meaning |
|---|---|
| `precision<0.80`, `metadata_unchanged_rate>=0.90` | metric range (`< <= > >= =`) |
| `finding:geometry.false_panels` | report has that finding code |
| `severity:WARNING` | report has ≥1 finding of that severity |
| `publisher:<id>` `issue:<id>` `series:<id>` | identity |
| `revision:<id>` | matches approved/generated/review id |
| `report_id:` `run_id:` `commit:` `schema_version:` `algorithm_version:` `prompt_version:` | field match |
| `date_from:` `date_to:` | archived-at range |
| `kind:report` \| `kind:failed_run` | record kind |
| free text | matched against recommendation text |

Metric ranges naturally exclude failed runs (they carry no metrics). `GET /audit-review/archive`
returns the full ordered, marked archive. Both endpoints are read-only over the persisted index +
ledger; no audit logic is duplicated. (Cross-issue/platform roll-up extends this by enumerating issue
indexes — a small addition when multiple issues exist.)
