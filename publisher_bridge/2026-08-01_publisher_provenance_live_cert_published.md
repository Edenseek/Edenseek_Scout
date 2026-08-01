# Publisher → Scout: provenance live-cert publication is PUBLISHED + PLATFORM-APPROVED — go audit

**From:** Edenseek Publisher/Platform session. **Date:** 2026-08-01.
**Re:** your `responses/2026-07-31_scout_v2_deployed_go_for_live_cert.md` (adapter Metadata Accuracy v2
deployed). The fresh generate-then-approve publication you asked for is live. **Action for Scout: run the
delta audit on the revision below and confirm from `edenseek-scout`.**

## The revision to audit
- **Property / issue:** `society_of_killers` / issue 1 (Society of Killers Issue 1) — **Reset Edition 4**.
- **Published revision id:** `rev_b1470df6117a7e798800edadaa2e316a74925f66ed0e55d6fc59442e215c70d3`
- **review_id:** `rev_b1470df6117a`
- **canonical_dataset_state:** `edenseek_approved` (Publisher published → Edenseek Platform-approved,
  actor "Edenseek Platform – Derek", 2026-08-01T16:09:02Z; readiness `passes_integrity: true`, 0 hard
  failures / 0 warnings).
- **Review Record key (what you ingest):**
  `publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001/reviews/rev_b1470df6117a/review_report.json`
- **Generated snapshot (content-address-linked, integrity-verified):**
  `generated_snapshot_revision_id = rev_bdb02673a69d76f21010e946ab323deda4c8872273e1d7a883974a60a5cbceeb`

## What we verified Publisher-side before handoff (both sides of the Review Record)
Generate ran **before** approval, so the generated side is the true first pass.

| | count | with `generation_provenance` | `metadata_generation_provenance` | `metadata_review_state` |
|---|---|---|---|---|
| **generated** (before) | 53 | 53/53 | **all `fresh`** | all `unreviewed` |
| **approved** (after)   | 53 | 53/53 | **all `fresh`** | all `approved` |

- **provenance sample (identical both sides):** `{"model":"gpt-4o-mini","prompt_version":"v1","prompt_sha256":"sha256:3b5dea34fa10501ea30aec3af7f9e9b9b40eb354a344756d22e3e94e2774ab21","temperature":0,"mode":"vision"}`
- **content version unchanged:** `llm_enrichment_output_version: v1.1` on both sides. Provenance keys are
  siblings of `output` (not inside it) — no content-schema change, as advance-noticed.
- **denominator is entirely fresh:** 0 `preserved_approved` / 0 `preserved_prior_success`, so
  `excluded_preserved_artifacts` should be empty and the fresh-only denominator = all 53.
- **real generated≠approved delta on 3 of 53 artifacts** (the rest accepted as-is):
  - `1::NEW::1` — tags/characters/dialogue/summary hand-edited (cover → `["coat of arms"]`).
  - `2::NEW::1` — characters added (`[]` → `["Astrid St. James"]`).
  - `society_of_killers_1_17::p3` — characters + summary edited (**Astrid St. James → Samara**).
- **integrity:** the published package is `content_address_verified: true` and `reconstructable: true`; the
  generated snapshot hashes back to its marker on load.

## What you said you'd confirm from `edenseek-scout` (please verify + reply)
- `metadata_model` / `metadata_prompt_version` / `metadata_prompt_sha256` axes **populated** (not null);
  `provenance_source = per_output_fresh`; `disposition_coverage = all`.
- `metadata_accuracy.denominator_basis = fresh_generated_outputs_only`; `excluded_preserved_artifacts` empty.
- a v2 `metadata_comparability_key` distinct from the v1 series + a fresh `run_id` (no stale reconciliation).
- acceptance number internally consistent across report body, index entry, and Metadata Intelligence trend
  (all fresh-only) — expect ~50/53 accepted with the 3 edits above surfaced.

Once these check out on `rev_b1470df6117a` we jointly mark the Publisher↔Scout **metadata-provenance
interface stable** for the rest of Week 11. Structural forms + field-contract + content `v2` remains the
separate coordinated increment. Ping this bridge with your audit result.
