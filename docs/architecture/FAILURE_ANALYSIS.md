# Dataset Failure Analysis (Phase 3)

> The deterministic model behind the Root Cause Report and Highest Leverage Failure Report.
> Derives from `SCOUT_CHARTER.md`. Read-only, deterministic, **diagnostic** — Scout explains
> *why* the dataset is failing; it does not prescribe engineering actions, approve/reject
> anything, predict numeric score changes, or self-modify (Charter §4).

## 1. Inputs

Pure aggregation over the per-artifact assessments from `audit_scoring.assess_artifact`
(structured flags: `missing_fields`, `has_characters`, `has_dialogue`, `is_reviewed`,
`is_locked`, `is_approved`, `status`, `page`). No new inputs; no LLM/embedding/vision/network.

## 2. Failure taxonomy (authored, static, human-owned)

Scout never modifies this taxonomy (no autonomous self-modification). Phase 3A covers
artifact-level failures; retrieval blockers are Phase 3B.

| failure_type | domain | severity | condition |
|---|---|---|---|
| `status_incomplete` | enrichment_pipeline | high | `status != "complete"` |
| `not_approved` | approval_workflow | high | not in approved dataset |
| `missing_metadata` | enrichment | high | any required metadata field missing |
| `unreviewed` | approval_workflow | medium | `metadata_review_state != "reviewed"` |
| `missing_characters` | enrichment | medium | `output.entities.characters` empty |
| `missing_dialogue` | enrichment | medium | `output.narrative.dialogue` empty |
| `unpaged` | ingestion | low | no page derivable from `artifact_id` |
| `not_locked` | approval_workflow | low | `metadata_locked == false` |

**Domains** tell an AI engineering agent *which subsystem is implicated*:
`enrichment` / `enrichment_pipeline` / `ingestion` are **content** domains;
`approval_workflow` is a **process** domain (publisher throughput, reported separately).

## 3. Impact band (qualitative, coverage-based)

`estimated_impact` reflects **leverage** — how widespread a failure is — not a predicted
score change. Authored thresholds over `affected_percent`:

- `high` ≥ 50%
- `medium` ≥ 20%
- `low` otherwise

**No numeric predicted score increase is ever emitted** — only measured counts and percentages.

## 4. Root Cause Report

For each failure type with ≥1 affected artifact: `affected_count`, `affected_percent`,
`affected_pages`, a capped `affected_artifact_ids` sample (+ truncation count), inherent
`severity`, coverage-based `estimated_impact`, and a deterministic `explanation`. Sorted by
`affected_count` desc → severity desc → name.

## 5. Highest Leverage Failure Report

Identifies the single **largest content-quality failure** (by coverage; ties broken by
severity then name) — diagnostic only: it names the dominant failure, its scale, and a
qualitative impact band, with a factual rationale. It does **not** recommend engineering
actions. `ranked_failures` lists all content failures; `process_backlog` reports
approval/review/lock counts separately so workflow throughput does not mask content quality.

## 6. History

Each audit-history snapshot gains a compact `failure_summary` = `{failure_type: count}`
(see `PROJECT_MEMORY_SCHEMA.md` §2.3). This enables Phase 4 Historical Intelligence
("are recurring failures shrinking?"). Scout reads this history to report trends but never
self-modifies from it.

## 7. Guarantees

- Deterministic: identical inputs → identical taxonomy counts, ranking, and summary.
- Read-only: no input mutation; outputs only to `reports/**` and `data/memory.json`.
- Diagnostic and advisory: no actions, no approvals, no numeric predictions, no self-modification.

## 8. Failure Clusters (Phase 3B)

`build_failure_clusters(artifacts)` locates *where* the same taxonomy failures concentrate,
so an AI engineering agent can tell a **systemic** problem (fix the pipeline/prompt) from a
**localized** one (fix specific pages/artifacts). Authored thresholds:

- **Issue-wide** (systemic): overall coverage ≥ `ISSUE_WIDE_THRESHOLD_PCT` (80%).
- **Page cluster** (localized): for non-issue-wide failures, a page where the failure
  affects ≥ `PAGE_CLUSTER_MIN_FRACTION` (50%) of the page's artifacts and ≥
  `PAGE_CLUSTER_MIN_COUNT` (2) artifacts.
- **Unpaged cluster**: failures concentrated among artifacts with no page linkage
  (artifact-identity / page-mapping issues).

Every cluster carries `category` (`content` from enrichment/ingestion domains, or
`workflow` from `approval_workflow`). **Workflow failures are shown and tagged, never
hidden** — they are legitimate dataset failure patterns, kept clearly separated from
content failures (`DOMAIN_CATEGORY`). Impact is the coverage band (§3); no numeric prediction.
