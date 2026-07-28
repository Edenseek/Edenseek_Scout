# Scout Benchmark Projections (v1)

> Weighted benchmark projections across the hierarchy — issue → series → publisher → platform —
> built from the per-issue report indexes (rebuildable projections over the immutable reports).
> `scout_benchmark`, `BENCHMARK_PROJECTION_VERSION = "v1"`. Read-only over the indexes; writes only to
> `edenseek-scout`. Rebuildable and idempotent (`rebuild_all`).

## Four structural invariants

1. **Weighted from counts — never averaging percentages.** Every aggregate metric =
   `sum(numerator) / sum(denominator)` across the underlying reports. The report index entries carry
   the numerator/denominator pairs (geometry `ratios{…}`, metadata rate fields, `revision_distance_sum`
   / `comparable_fields` for the count-weighted mean distance).
2. **Sample size on every point and segment.** Each point carries `sample_sizes{reports + domain
   denominators}`; each segment carries pooled `sample_sizes`. Geometry: `generated_panels`,
   `approved_panels`, `pages`. Metadata: `comparable_fields`, `artifacts`. A metric with no counts
   fails the "no bare rate" test.
3. **Explicit methodology boundaries.** Metrics are segmented per task by `comparability_key`.
   `series(projection, task, metric, order_by)` marks each `boundary` with the axes that changed
   (`from`/`to`), and never joins two segments — a methodology change (detector/threshold/prompt/
   model/schema/normalization/evaluation) reads as a labeled boundary, not a model gain.
4. **Dual time.** Every point carries `event_time` (Publisher publication) and `measurement_time`
   (Scout), plus `certified_at`. `series(..., order_by="event_time" | "measurement_time")` orders by
   either — isolating delayed reprocessing, methodology migrations, and backfilled publications.

## Projection object

```jsonc
{ "benchmark_projection_version": "v1",
  "scope": { "level": "issue|series|publisher|platform", "publisher_id?, series_id?, issue_id?" },
  "measurement_generated_at": "...",
  "sample_sizes": { "reports", "issues", "series", "publishers" },
  "geometry": { "segments": { "<comparability_key>": { "axes", "sample_sizes",
                                 "metrics": { "<name>": { "numerator", "denominator", "rate" } } } },
                "points": [ { "run_seq", "report_id", "issue_id", "event_time", "measurement_time",
                              "certified_at", "comparability_key",
                              "metrics": { "<name>": { "value", "numerator", "denominator" } },
                              "sample_sizes" } ] },
  "metadata": { /* same shape */ } }
```

Metrics: geometry — precision, recall, split_rate, merge_rate, false_rate, missing_rate,
unchanged_geometry_rate, corrections_per_page. Metadata — accepted_unchanged / minor / moderate /
major / complete_replacement rates, corrections_per_artifact, weighted_editorial_intervention_score,
average_revision_distance. Failed/incomplete runs never enter (they live only in the ledger), so
benchmarks reflect successful runs; abstained metadata reports contribute no metadata point.

## Storage keys (`edenseek-scout`)

```
{issue}/benchmark/benchmark.json
publishers/{pub}/title_groups/{tg}/series/{series}/benchmark/benchmark.json
publishers/{pub}/benchmark/benchmark.json
benchmark/platform.json
```

## Read model

`series(projection, task, metric, order_by)` (pure) builds the ordered, segmented time series for a
chart — the browser passes `order_by` and renders; it never recomputes. `GET /benchmark/{level}`
serves a persisted projection read-only (platform now; publisher/series/issue scoping arrives with the
archive/search slice).
