# Metadata Revision-Distance Benchmark (v1, provisional)

> Deterministic, versioned classification of how creator/publisher approval revised the automated
> metadata, per artifact and per field — using only lexical/structural measures (**no LLM**).
> Introduced in reporting Increment 1 (`delta_metadata_revision.py`). Compares Scout's canonical
> generated vs approved metadata (from the anti-corruption adapter) BEFORE any further revision.

## Governance

Scout stores **references + content hashes only** — never the raw generated/approved metadata text.
The authoritative values live in the immutable Publisher Review Record, addressable by
`(review_id, artifact_id, field)`. Every underlying measure, numerator, denominator, and hash is
preserved so the categories can be recomputed once real editorial examples are reviewed. Raw inline
values are introduced only if a future governed requirement explicitly authorizes them.

## Versioning

`METADATA_REVISION_DISTANCE_VERSION = "v1"` (**provisional**) stamps the distance definition, the
category thresholds, and the intervention weights. It is a **metadata comparability axis** — any
change is a methodology boundary, never a silent re-scoring. A future LLM-assisted semantic scorer
would be an *additional* field beside these measures (`semantic_score{model, prompt_version,
scoring_version}`), never the authoritative scorer.

## Distance + categories

Primary distance `d ∈ [0,1]` = normalized char-level Levenshtein over a canonical string rendering of
the field value (sorted-key dict / newline-joined list). Category from `d` (minor stays distinct from
a factual/complete replacement):

| category | rule (v1 provisional) | weight |
|---|---|---|
| `accepted_unchanged` | `d == 0` (identical) | 0.0 |
| `minor_wording_edit` | `0 < d ≤ 0.10` | 0.25 |
| `moderate_rewrite` | `0.10 < d ≤ 0.35` | 0.5 |
| `major_rewrite` | `0.35 < d ≤ 0.70` | 0.75 |
| `complete_replacement` | `d > 0.70` or disjoint | 1.0 |
| `added` | empty on generated, populated on approved | 0.5 |
| `removed` | populated on generated, empty on approved | 1.0 |
| `abstention` | empty on both sides (nothing to evaluate) | — (excluded) |
| `unsupported_schema` | generated/approved enrichment schema versions differ | — (excluded) |

Preserved per (artifact, field) record: `category`, `distance`, `generated_sha256`,
`approved_sha256`, `generated_empty`, `approved_empty`, and `measures{char_levenshtein,
char_levenshtein_norm, token_jaccard_distance, set_jaccard_distance, len_ratio, structural_equal,
generated_type, approved_type}`. No raw content.

## Aggregates (global + per field)

Numerators/denominators preserved, never bare percentages: `fields_generated`, `fields_approved`,
`comparable_fields`, category `counts`, `{accepted_unchanged, minor_wording_edit, moderate_rewrite,
major_rewrite, complete_replacement, added, removed}_rate` (each `{numerator, denominator, rate}`),
`unchanged_metadata_rate`, `weighted_editorial_intervention_score` (`{numerator, denominator,
score}`), `average_revision_distance`, `median_revision_distance`, `corrections_per_artifact`.

## Contract changes (Increment 1)

- **Delta report** (`delta_auditor.run_delta_audit`): new top-level `metadata_benchmark` block;
  `provenance.metadata_revision_distance_version`.
- **Report body** (`scout_delta_audit.build_report_body`): new `metadata_metrics` headline (compact
  per-report metadata rollup) carried on the index entry.
- **Index entry** (`scout_report_index.build_index_entry`): new `metadata_metrics`.
- **Comparability**: `metadata_axes` gains `metadata_revision_distance_version` — so a threshold or
  weight change becomes an explicit metadata methodology boundary in trend series.

## Live note

On the current certified revision `rev_a8c65a83a196` the generated enrichment schema (v1.1) differs
from the approved (v1), so the classifier correctly reports every field as `unsupported_schema`
(comparable_fields 0) — the same forward-only F2 fact. Real category examples begin with the
Publisher's next schema-aligned revision.
