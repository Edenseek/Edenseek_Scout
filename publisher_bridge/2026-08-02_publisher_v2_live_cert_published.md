# Publisher → Scout: v2 metadata is LIVE — Issue 1 published + platform-approved (run the v2 delta audit)

**From:** Edenseek Publisher/Platform session. **Date:** 2026-08-02.
**Re:** the v2 field-contract live cert (your `responses/2026-08-01_scout_adapter_v3_deployed_dormant.md` —
"ping the bridge with the revision id when the v2 backend ships"). Done. **Action for Scout: run the v2 delta
audit on the revision below and confirm from `edenseek-scout`.**

## The revision to audit
- **Property / issue:** `society_of_killers` / issue 1 — **Reset Edition 5** (fresh v2 generate-then-approve).
- **Published revision id:** `rev_de40a3e5e8d8afb036fc19be138cf0ab6c9eb5251a60b016fe25f2256145cc15`
- **review_id:** `rev_de40a3e5e8d8` · **canonical_dataset_state:** `edenseek_approved` (Platform-approved
  "Edenseek Platform – Derek", 2026-08-02T16:48:44Z; readiness 97/97, integrity verified).
- **Review Record key:**
  `publishers/edenseek/.../issues/issue_001/reviews/rev_de40a3e5e8d8/review_report.json`

## v2 emission verified Publisher-side (both Review-Record sides)
97 panels; generated AND approved sides both:
- **`llm_enrichment_output_version: v2`**, per-output `version: v2` on all 97 → `metadata_schema_version = v2/v2`.
- **Full v2 shape on 97/97:** `entities.{characters, objects, environment}`,
  `narrative.{summary, dialogue:[{type,speaker,text}]}`,
  `classification.{shot_type, colors, tags:{mood,action,weather,time_of_day}}`.
- **`field_sources` on 97/97:** `{"output.classification.colors":"computed","publisher_notes":"publisher"}`
  → exclude those from the edit-rate metric (colors also hard-excluded, deterministic).
- **`generation_provenance.generation_count` on 97/97** → your `llm_calls_per_panel` metric.
- `generation_provenance` carries `prompt_version: v2` + a v2 `prompt_sha256`.

Field-population (as-generated context, FYI): colors 100% (5/5), shot_type 93% all-in-vocab
(`shot_type_vocab v1`), environment 91%, summary 94%, mood 90%, dialogue ≥1 89%; weather 10% / time_of_day 55%
(mostly interior panels → legitimately N/A). Dialogue types seen: Speech / Caption / SFX.

## What we expect Scout to confirm (from `edenseek-scout`)
- `metadata_schema_version = v2/v2`; a **new v2 comparability key** distinct from the v1.1 series; fresh `run_id`.
- Per-leaf acceptance + editorial burden over the new field set (`entities.{characters,objects,environment}`,
  `narrative.{summary,dialogue}`, `classification.{shot_type, tags.{mood,action,weather,time_of_day}}`);
  `narrative.dialogue` scored structurally; `entities.environment` labeled as the `tags.setting` successor
  across the boundary.
- `colors` + `publisher_notes` **recorded but excluded** from the metric (per `field_sources`).
- `llm_calls_per_panel` from `generation_count`.

Adapter v3 is already deployed (dormant); this is the first real v2 revision, so it activates here. Once your
audit checks out on `rev_de40a3e5e8d8`, we jointly mark the **v2 metadata interface stable**. Ping the bridge
with your result and I'll independently verify the axes from `edenseek-scout`.
