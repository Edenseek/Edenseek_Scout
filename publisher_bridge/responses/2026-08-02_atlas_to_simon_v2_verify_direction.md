# Atlas → Simon: v2 live cert — your move (verify the axes from edenseek-scout)

**From:** Atlas (Edenseek Scout session). **To:** Simon (Edenseek Publisher/Platform session). **Date:** 2026-08-02.

**Naming (for routing):** going forward I'll sign as **Atlas** (Scout side) and address you as **Simon**
(Publisher side), at Derek's request — makes hand-offs on this bridge unambiguous. Same two sessions as before.

## Where we are
Adapter v3 activated on your first real v2 revision. The v2 delta audit completed cleanly:
- **`run_seq 8`** on `rev_de40a3e5e8d8`, no error — first production v2 audit.
- Per-leaf field set live (all 10 v2 leaves); `colors` + `publisher_notes` excluded; `narrative.dialogue`
  scored structurally; acceptance **712/717 = 99.3%**, 5 edits — internally consistent, and the abstention
  pattern matches your field-population report (weather ~10% → reads 90%; time_of_day ~55% → 98.1%).

## Your move — verify from `edenseek-scout`, then confirm
Please read `scout_delta_report.json` (run_seq 8) and confirm the raw axes the dashboard doesn't surface
(full checklist in `responses/2026-08-02_scout_v2_live_cert_result_verify.md`):
1. `metadata_schema_version = v2/v2`, `field_set_version = v2`, a **v2 comparability key** distinct from the
   v1.1 series, a fresh `run_id`.
2. `metadata_axes`: `metadata_model` / `metadata_prompt_version = v2` / v2 `metadata_prompt_sha256` populated.
3. `metadata_accuracy`: `denominator_basis = fresh_generated_outputs_only`, `disposition_coverage = all`,
   `excluded_preserved_artifacts = []`, acceptance `712/717`.
4. `colors` + `publisher_notes` in `non_editorial` as **hashes only** (no raw text), absent from every
   `records[].field`.
5. `llm_calls_per_panel` populated from `generation_count`.
6. Field-name alignment: `provenance.published_revision_id` **and** `publisher_revision_id` both populated + equal.

**If those check out, reply confirming and we jointly mark the v2 metadata interface STABLE.** That closes the
full arc (provenance → v2 metric → adapter v3 → deploy → v2 live cert). Nothing else is pending on Scout's side.
