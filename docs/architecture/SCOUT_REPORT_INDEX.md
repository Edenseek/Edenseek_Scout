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
| identity | `report_id`, `run_seq`, `completed_at`, `publisher_id`, `title_group_id`, `series_id`, `issue_id` |
| revisions | `published_revision_id` (approved), `generated_snapshot_revision_id` (generated), `review_id` |
| metrics | `precision`, `recall`, `split_rate`, `merge_rate`, `missing_count`, `spread_missing_count`, `false_count` |
| findings | `finding_counts` {PASS,WARNING,FAIL,INFO}, `finding_codes[]`, `worst_severity`, `metadata_status`, `compared_artifacts` |
| **versions** | `report_version`, `algorithm_version`, `schema_version`, `evaluation_version`, `schema_versions{}`, `comparability_key` |
| commits | `publisher_commit`, `scout_commit` |
| location | `persisted_key` {history, latest}, `report_sha256` |

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

## 4. Comparability contract (formal)

Two reports are **directly comparable** iff **all four axes** match. A change on any axis is a
**boundary**: trend graphs must segment on `comparability_key` and must not draw a continuous line
across a boundary without warning.

| axis | owns | bump when… |
|---|---|---|
| `report_version` | delta report **format** (`delta_auditor.SCOUT_DELTA_REPORT_VERSION`) | the envelope/report shape changes |
| `algorithm_version` | the delta **computation** (`delta_auditor.DELTA_ALGORITHM_VERSION`) | the IoU threshold, match/split/merge/false definitions, metadata field-equality or schema-scoping rule, or the ledger op set change |
| `schema_version` | the Publisher **input contract** consumed (composite `rr:…|pa:…|gs:…`) | the Review Record / Platform Approval / Generated PAL schema versions change |
| `evaluation_version` | the **findings/severity rules** (`audit_review.EVALUATION_VERSION`) | the PASS/WARNING/FAIL/INFO thresholds or rules change |

`comparability_key = "cmp_" + sha256("report_version=…|algorithm_version=…|schema_version=…|evaluation_version=…")[:12]`.

**Prompts / upstream models are not a Scout axis.** Scout's delta is LLM-free. Changes to the
Publisher's enrichment prompts or models surface here via `schema_version` (the enrichment output
schema) and the `generated_snapshot_revision_id` — so a graph already segments across them.

`scout_report_index.comparability_diff(a, b)` returns exactly which axes differ, so a future graph
can label a boundary ("algorithm_version changed v1→v2") rather than silently splicing.

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
