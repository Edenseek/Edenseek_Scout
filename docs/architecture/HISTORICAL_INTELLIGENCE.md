# Historical Intelligence (Phase 4)

> The deterministic model behind the Historical Intelligence Report and `GET /audit/trends`.
> Derives from `SCOUT_CHARTER.md`. **Explains change; never predicts it.** Read-only,
> deterministic, observational. It does not predict, prescribe, recommend, modify
> data/scoring, or self-modify (Charter §4). It opens **no canonical dataset** — it is pure
> over `audit_history` snapshots, so canonical data is preserved trivially.

## 1. Inputs

`edenseek_dataset.audit_history` snapshots only (Phase 2/3A):
`{timestamp, dataset_id, quality_score, scores{4}, artifact_count, weak_total_flagged, failure_summary{type:count}}`.
No new stored data — everything is a **derived view**. Percentages are computed at analysis
time so comparisons stay fair as `artifact_count` changes.

## 2. Scope (most-recent dataset)

Analysis is filtered to a single `dataset_id` (the most recent, or an explicit
`?dataset_id=`). Snapshots of other datasets are ignored.

## 3. Confidence levels

| Snapshots (of the dataset) | Confidence |
|---|---|
| < 2 | `insufficient_history` |
| 2 | `preliminary` |
| ≥ 3 | `trend` |

## 4. Trend model (whole window)

Per metric — `quality_score`, the four sub-scores (higher-is-better), and `weak_percent`
(lower-is-better) — report `first`, `last`, `change`, `series`, `consistency`
(`monotonic`/`mixed`), and `direction`:

- A change within **±1** point/percent (`STABLE_EPSILON`) is `stable`.
- Otherwise polarity-aware: higher-is-better → `improving` when it rises; lower-is-better →
  `improving` when it falls; the opposite is `worsening`.

## 5. Delta model (since previous audit)

Compares the two most recent snapshots: per-metric change, per-`failure_type` percentage
change, and new/resolved failures between them.

## 6. Failure trends and field evolution

Failure-based analysis (failure trends, new/resolved, stagnation, correlations) spans only
snapshots that **actually carry a `failure_summary`** (Phase 3A onward). A missing
`failure_summary` means "no failure data for that audit," never "zero failures" — so older
snapshots cannot create a phantom `0 → N%` trend.

## 7. Stagnant pipeline areas

Per domain (`enrichment`, `enrichment_pipeline`, `ingestion`, `approval_workflow`), the mean
failure percentage across the failure-bearing window. A domain is **stagnant** when that
mean changes within ±1 point and remains > 0.

## 8. Observed correlations (observational only)

For each consecutive interval, reductions in failure counts are mapped to inferred
publisher-action proxies (e.g. `unreviewed`↓ → `reviews_performed`, `missing_characters`↓ →
`characters_added`) and reported alongside that interval's `quality_change`. This is strict
**co-occurrence, not causation**: Scout never attributes cause, ranks "what to do," or
recommends. Every report carries the observational disclaimer. No numeric predicted score
change is ever emitted.

## 9. Guarantees

- Deterministic replay: identical history → identical output (no time/randomness in analysis).
- Read-only, no canonical access, no persisted derived data, no schema change.
- Observational and diagnostic: no predictions, prescriptions, recommendations, or self-modification.
