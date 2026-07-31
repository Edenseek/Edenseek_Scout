# Scout Report Index & Comparability Contract (v1)

> The durable archive + history model for persisted Scout **Synchronization Audit (delta)** reports.
> The immutable persisted reports are authoritative; the index is a **rebuildable projection** over
> them. The UI reads persisted reports/indexes only — no generation or comparison logic lives in the
> browser. Introduced Week 11 (Slice 3), building on the R1 Object-Key Contract
> (`scout_report_publisher`).

## 1. What is persisted (authoritative)

Each completed Scout delta audit is persisted by `scout_report_publisher.publish_delta_report` at the
frozen R1 keys in `edenseek-scout`, byte-verified on read-back:

- Immutable history: `{issue}/history/scout_delta_report_{run_seq}.json` (append-only; a fresh
  `run_seq` never overwrites a prior snapshot).
- Latest-state: `{issue}/reports/scout_delta_report.json` (overwritten; prior versions kept as S3
  noncurrent versions).

The persisted **report envelope** carries the comparability axes, full provenance, the raw delta
report, the findings, and an evidence summary. Historical reports are never overwritten.

## 2. The index (rebuildable projection)

`scout_report_index` maintains a per-issue index at `{issue}/reports/report_index.json`
(`report_index_version: v1`) — a **newest-first** projection of the history reports:

```jsonc
{
  "report_index_version": "v1",
  "issue_prefix": "publishers/.../issues/{issue_id}",
  "generated_at": "<latest completed_at>",
  "latest": { "report_id", "run_seq", "persisted_key" },   // the current completed report
  "count": <n>,
  "entries": [ /* newest → oldest */ ]
}
```

Each **entry** is the searchable metadata for one report:

| group | fields |
|---|---|
| identity | `report_id`, `run_id` (logical), `run_seq` (physical), `completed_at`, `publisher_id`, `title_group_id`, `series_id`, `issue_id` |
| revisions | `published_revision_id` (approved baseline), `generated_snapshot_revision_id` (generated), `review_id` |
| metrics | `precision`, `recall`, `split_rate`, `merge_rate`, `missing_count`, `spread_missing_count`, `false_count` |
| geometry benchmark | `geometry_benchmark{}` — raw counts **and** numerator/denominator pairs (see §7) |
| findings | `finding_counts` {PASS,WARNING,FAIL,INFO}, `finding_codes[]`, `worst_severity`, `metadata_status`, `compared_artifacts` |
| **versions** | `report_version`, `algorithm_version`, `schema_version`, `evaluation_version`, `normalization_version`, `schema_versions{}` |
| **comparability** | `comparability{geometry,metadata,geometry_axes,metadata_axes}`, `geometry_comparability_key`, `metadata_comparability_key` |
| commits | `publisher_commit`, `scout_commit` |
| location | `persisted_key` {history, latest}, `report_sha256` |

The persisted report envelope additionally carries full provenance (§8): publication `chain_id`/
`published_at`/`initiating_user`, `evidence_manifest_version`, `geometry_detector` (match version +
IoU threshold), `metadata_provenance` (enrichment schema versions + prompt/model identifiers when
available), and per-object evidence keys + sha256. **No secrets, credentials, or prompt bodies are
stored** — only identifiers and versions.

The index is **derived and rebuildable**: `scout_report_index.rebuild_index` scans `history/` and
reconstructs the whole index. The reports remain the source of truth; a lost or divergent index is
reconciled by rebuilding — it is never authoritative on its own.

## 3. Transaction

The agent runner (`scout_delta_audit.run_and_persist`) performs both writes as one transaction:

1. Persist the immutable report (history + latest) and **byte-verify** it.
2. Project the persisted envelope → index entry and **update + verify** the index.

The report is written and verified first. If step 2 fails, the authoritative report is already
durable and the index is reconcilable via `rebuild_index` — the projection can always be recomputed
from the immutable reports.

**Idempotency (no duplicate logical runs).** Each report carries a deterministic `run_id` =
`sha256(published_revision_id | generated_snapshot_revision_id | comparability.geometry |
comparability.metadata)`. `publish_delta_report` reads the latest object first and, if its `run_id`
already matches, returns it as a verified no-op — a retry of the same publication under the same
methodology never creates a second history snapshot or a second `run_seq`. The physical `run_seq`
still increments only for genuinely new logical runs.

## 4. Comparability contract (formal, per task family)

Geometry and metadata metrics are only comparable under the conditions that actually govern each, so
comparability is computed **per task family** — a report has both a `geometry` and a `metadata`
comparability key. Reports with an **identical** key for a task may form one continuous benchmark
series for that task's metrics. Reports with **different** keys stay visible but are separated by a
**methodology boundary** and must never be silently combined into one improvement claim.

**Geometry axes** (`geometry_comparability_key`): `task=geometry`, `metric_definition_version`
(`DELTA_ALGORITHM_VERSION`), `geometry_detector_version` (`delta_geometry.GEOMETRY_MATCH_VERSION`),
`iou_threshold`, `normalization_version` (`review_contract_adapter.NORMALIZATION_VERSION`).

**Metadata axes** (`metadata_comparability_key`): `task=metadata`, `metric_definition_version`,
`metadata_prompt_version`, `metadata_prompt_sha256`, `metadata_model`, `metadata_schema_version`
(generated/approved enrichment versions), `metadata_revision_distance_version`,
`metadata_accuracy_version`, `normalization_version`, `evaluation_version`
(`audit_review.EVALUATION_VERSION`). `metadata_prompt_sha256` is the hash of the Publisher's prompt
templates: a silent (un-versioned) prompt edit changes the sha even when the human-label
`metadata_prompt_version` is unchanged, forcing a methodology boundary instead of contaminating a series.

`comparability_key(axes) = "cmp_" + sha256(sorted "k=v" join)[:12]`. `build_comparability(body)`
returns both keys plus the axis values; `metric_series(index, task=…)` segments on the task's key and
marks `boundaries`; `comparability_diff(a_axes, b_axes)` names exactly which axes moved so a graph can
label a boundary ("iou_threshold 0.5→0.6") rather than silently splicing.

**Prompts / upstream models are captured, not ignored.** Scout's delta is LLM-free, but the metadata
it compares was produced by the Publisher's enrichment prompts/models — so those are metadata-axis
inputs (`metadata_prompt_version`, `metadata_prompt_sha256`, `metadata_model`,
`metadata_schema_version`), recorded when the Publisher emits them and otherwise `null`. As of the
metadata-provenance interface (Publisher enhancement #1), these come from the per-output
`generation_provenance` of the **fresh** generated outputs only — a preserved output keeps a *prior*
run's provenance and must not drive this run's axis. They also surface via the
`generated_snapshot_revision_id`.

## 5. Read model (server-side; UI never computes)

- `load_index()` — the newest-first index (read-only).
- `query_index(index, filters)` — pure filter over: `report_id`, issue chain, `revision`,
  `finding_code`, `severity`, `schema_version`, `commit`, `comparability_key`, `date_from`/`date_to`,
  and per-metric `<metric>_min`/`<metric>_max` ranges.
- `metric_series(index, metrics)` — per-metric series (oldest→newest) grouped into `segments` by
  `comparability_key` with `boundaries` marked, so graphs draw continuous lines only within a
  segment.

Endpoints expose these read-only (`GET /audit-review/reports` today; search + graph endpoints in the
next slice). The browser passes parameters and renders; all filtering/segmenting stays server-side.

## 6. Boundaries held

Read-only on `edenseek-publishing`; writes only to `edenseek-scout`. Scout persists and indexes its
own reports; it never mutates Publisher data, sets canonical state, or moves audit logic into the UI.

## 7. Geometry benchmark (numerators + denominators)

`geometry_benchmark` persists raw counts and explicit numerator/denominator pairs so every rate is
independently reproducible — never a bare percentage:

- counts: `true_matches`, `matched_generated`, `matched_approved`, `generated_panels_evaluated`,
  `approved_panels_evaluated`, `page_generated_panels`, `page_approved_panels`,
  `spread_generated_panels`, `spread_approved_panels`, `panel_splits`, `panel_merges`,
  `false_panels`, `missing_panels`, `missing_page_panels`, `spread_missing_panels`,
  `unchanged_geometry_panels`, `total_human_geometry_corrections`, `pages_evaluated`. (Geometry
  `v2` stratifies into page/spread sub-groups + a `strata` block; the whole-issue counts are the
  micro-averaged total.)
- rates with backing: `corrections_per_page`, `unchanged_geometry_rate`, and `ratios{precision,
  recall, segmentation_accuracy, split_rate, merge_rate, false_rate, missing_rate,
  unchanged_geometry_rate}` where each is
  `{numerator, denominator, rate}`.

## 8. Report identity + provenance (persisted envelope)

Every persisted report carries: `report_id`, `run_id`, `run_seq`, `completed_at`; the issue chain
(`publisher/title_group/series/issue`) via `issue_identity`; `provenance.publication`
(`chain_id`/`published_at`/`initiating_user`); `published_revision_id` (approved baseline),
`generated_snapshot_revision_id` (generated), `review_id`; `publisher_commit` + `scout_commit`;
`evidence_manifest_version`, `report_version`, `algorithm_version`/`evaluation_version`,
`geometry_detector` (match version + IoU), `metadata_provenance` (prompt id/version, model/provider
when available, generated/approved enrichment schema versions), `normalization_version`,
`schema_versions`; the exact `persisted_key` + `report_sha256`; and `evidence_summary.objects` with
each evidence object's key + sha256. **Secrets, credentials, and prompt bodies are never stored.**
