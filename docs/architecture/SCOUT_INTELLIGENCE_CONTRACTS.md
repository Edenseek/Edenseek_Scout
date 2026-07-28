# Scout Machine-Readable Intelligence Contracts (Increment 4)

> Geometry Intelligence and Metadata Intelligence are first-class, **read-only consumers** of the
> SAME persisted Scout contracts the dashboard uses — never HTML scrapers. Each receives only its
> domain projection plus provenance and comparability metadata, versioned by its contract. They may
> emit **advisory** recommendations but never mutate production detectors, prompts, models, schemas,
> algorithms, or Publisher-approved data; any change enters the governed approval workflow.

## Shared persisted contracts (versioned JSON Schemas in `schemas/`)

| contract | schema | endpoint |
|---|---|---|
| immutable delta report | `scout_delta_report` | `GET /reports/{report_id}`, `GET /reports/latest` |
| report index (+ search) | `report_index` | `GET /audit-review/reports`, `GET /audit-review/search` |
| benchmark projection (issue/series/publisher/platform) | `benchmark_projection` | `GET /benchmark/{level}` |
| archive | — | `GET /audit-review/archive` |
| evidence manifest | (in report / `GET /audit-review/evidence`) | — |
| Geometry Intelligence | `geometry_intelligence` | `GET /intelligence/geometry` |
| Metadata Intelligence | `metadata_intelligence` | `GET /intelligence/metadata` |

Schemas are served read-only at `GET /schemas` (list) and `GET /schemas/{name}`. A dependency-free
validator (`scout_schema`) checks documents against them; compatibility tests assert the benchmark
projection, report index, and both intelligence outputs conform — so the UI and the intelligence
systems consume identical, schema-validated contracts.

## Geometry Intelligence (`geometry_intelligence`, v1)

Consumes the report index. Domain-scoped output:
- **`segments`** — weighted metrics per comparability segment (sample sizes included; never mixed
  across a methodology boundary).
- **`recurring_failure_modes`** — per segment, summed raw counts (panel splits/merges, false,
  missing-page, spread-missing) with numerator/denominator + rate, ranked — the recurring panel
  failure modes.
- **`version_correlated_improvements`** — for each adjacent methodology segment, the axes that
  changed (`comparability_diff`) and the metric deltas + sample sizes on each side — "recall improved
  +X when the detector version changed", never a silent splice.
- **`recommendations`** — advisory (e.g. high merge-rate → under-segmentation review proposal).

## Metadata Intelligence (`metadata_intelligence`, v1)

Consumes the index + the immutable reports (for per-field detail). Domain-scoped output:
- **`weak_fields`** — per-field accepted/edit rate (numerator/denominator preserved), ranked by
  editorial rework.
- **`common_edit_classes`** — summed category distribution across comparable reports.
- **`prompt_model_schema_correlations`** — metrics grouped by (prompt version, model, metadata schema)
  with counts — correlate quality to prompt/model/schema.
- **`prompt_improvement_opportunities`** + **`recommendations`** — advisory (fields with high rework
  are prompt-refinement candidates). Only comparable (non-abstained) reports contribute.

## Governance

Every intelligence output carries a `governance` block: `advisory_only: true` and the note that
Scout changes nothing in production and that any proposed detector/prompt/model/schema/algorithm
change must enter the governed approval workflow with human authority as final. Read-only on the
Publisher repository; the intelligence layer only reads `edenseek-scout` projections.
