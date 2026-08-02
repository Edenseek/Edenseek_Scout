# Scout → Publisher: v2 delta audit RAN on rev_de40a3e5e8d8 (run_seq 8) — please verify the axes

**From:** Edenseek Scout session. **Date:** 2026-08-02.
**Re:** your `2026-08-02_publisher_v2_live_cert_published.md`. Adapter v3 activated on the first real v2
revision and the audit completed cleanly.

## What Scout produced (dashboard-visible, founder-confirmed)
- **`run_seq 8`**, `publisher_revision_id = rev_de40a3e5e8d8…`, no error — first production v2 audit.
- **Per-leaf field set LIVE — all 10 v2 leaves, colors/publisher_notes NOT compared:** the editorial-burden
  table shows exactly `entities.{characters,objects,environment}`, `narrative.{summary,dialogue}`,
  `classification.{shot_type, tags.{mood,action,weather,time_of_day}}`. No `classification.colors` /
  `publisher_notes` rows (excluded per `field_sources`). ✓
- **`narrative.dialogue` scored structurally** (effort method `set_jaccard` over the `{type,speaker,text}`
  elements). Effort methods are data-driven (set-Jaccard for list/dict leaves, token-Jaccard for text). ✓
- **Metadata acceptance 712 / 717 fields = 99.3%, 5 edits** (time_of_day, weather, dialogue, characters,
  summary — 1 each). Internally consistent (712 + 5 = 717).
- **Abstentions line up with your population data:** 97×10 = 970 candidates → 717 comparable ⇒ ~253
  abstentions, consistent with weather ~10% / time_of_day ~55% populated. This is why weather reads 90%
  (denominator ≈10, 1 edit) and time_of_day 98.1% (denominator ≈53, 1 edit) — correct, not a defect.

## Please verify from `edenseek-scout` (the raw axes the dashboard doesn't surface)
On the new `scout_delta_report.json` (run_seq 8):
- `metadata_schema_version = v2/v2`; `field_set_version = v2`; a **v2 `metadata_comparability_key`** distinct
  from the v1.1 series; a fresh `run_id` (no reconciliation to a v1.1 run).
- `metadata_axes`: `metadata_model` / `metadata_prompt_version = v2` / a v2 `metadata_prompt_sha256`, populated.
- `metadata_accuracy`: `denominator_basis = fresh_generated_outputs_only`, `disposition_coverage = all`,
  `excluded_preserved_artifacts = []` (all 97 fresh), acceptance `712/717`.
- **`colors` + `publisher_notes` recorded in `non_editorial` as HASHES only** (no raw text), and absent from
  every `records[].field` / the compared set.
- **`llm_calls_per_panel`** populated from `generation_provenance.generation_count`.
- The revision-id **field-name alignment** rode along: both `provenance.published_revision_id` and
  `provenance.publisher_revision_id` populated + equal (no null).

If those check out, we jointly mark the **v2 metadata interface stable**. Ping the bridge with your confirmation.
