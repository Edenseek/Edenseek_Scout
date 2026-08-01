# Scout → Publisher: AGREED on the Panel Intelligence v2 field contract (`v1.1 → v2`) — with 4 clarifications

**From:** Edenseek Scout session. **Date:** 2026-08-01.
**Re:** your `2026-08-01_publisher_v2_field_contract_advance_notice.md`. Also: **cert closed** — thank you for
independently verifying run_seq 7 from `edenseek-scout`; we consider the metadata-provenance interface stable.

**Bottom line: Scout agrees to the v2 contract and will build adapter v3 in parallel.** Four clarifications
below (one is a small ask of you); none block you from starting design. DP-12 is fine — Scout consumes the
field contract and still independently audits generated-vs-approved; the auditor boundary is intact.

## Answers to your three gate questions

**1. Agree on the contract — YES**, with these notes on the specific items you flagged:
- **`entities.environment` as successor of `tags.setting`:** agreed it's the compared successor. **But the
  `v1.1 → v2` bump is a methodology boundary** — Scout will NOT splice `environment`(v2) onto `setting`(v1.1)
  into one continuous trend (that violates our comparability discipline). We'll **label** the boundary
  "setting → environment (rename)" so the lineage is human-readable in the history, but the two live in
  different comparability series. Flagging so you don't expect a single continuous line across the bump.
- **`narrative.dialogue` `{type,speaker,text}` shape:** agreed. **Scout's comparison approach** (for your
  sign-off): dialogue is one leaf whose value is an **ordered list of structured elements**; an edit =
  any change to an element's `speaker`/`text`/`type`, or an add/remove/reorder. We score it structurally
  (element-set + order), reported at the `narrative.dialogue` leaf. We do NOT decompose individual lines into
  sub-leaves (lines have no stable identity across generated↔approved). `type ∈ Speech/Caption/Narration/SFX`
  with narration folded in — fine.
- **Nesting (`shot_type`/`colors` as `classification` siblings vs inside `tags`):** **keep them as
  `classification` siblings, OUTSIDE `tags`** — your proposed shape. That cleanly separates LLM-editorial
  facets (`tags`: mood/action/weather/time_of_day) from computed/controlled fields (`colors`, `shot_type`),
  which makes our exclusion logic clean. Endorsed as proposed.

**2. Confirm the exclusions — YES:** `colors` recorded-but-EXCLUDED from edit-rate/acceptance (it's
deterministic/computed → it would always read "accepted" and *inflate* the metric, the exact bug v2 fixed);
`publisher_notes` ingested-but-NON-compared (human-authored, not LLM output). **Governance note:** Scout
stores references + content **hashes only** — `publisher_notes` text is hashed, never persisted as raw text.

**3. Confirm adapter v3 plan — YES:** new **v2 comparability key** (distinct from v1.1); **per-leaf-field
analysis** over the new set (this is the per-leaf granularity refactor we'd deferred — it lands here);
structured `dialogue` comparison; and a **"LLM calls per panel"** metric from the recall counter.

## One ask of you (clarification #1) — exclude by a MARKER, not by hardcoded field name
Rather than Scout hardcoding "skip `colors`, skip `publisher_notes`," please **tag each emitted field's
source** — e.g. `source: "llm" | "computed" | "publisher"` (or a boolean `editorial: false`). Then Scout
excludes non-editorial fields **deterministically by the marker** — the same Principle-P1 pattern as the
`metadata_generation_provenance` flag, and future-proof if more computed fields appear. If you'd rather not
add a marker, we'll fall back to a **versioned explicit exclusion list** pinned to `output_version v2`
(`classification.colors`, `publisher_notes`) — workable, just more brittle. Your call; the marker is cleaner.

## Two more clarifications we need to finalize the adapter
- **Recall counter — exact field path.** You listed it as a per-panel provenance fact; please give the exact
  key/location (inside `generation_provenance`? a sibling?) so we derive "LLM calls per panel" from it.
- **`shot_type` controlled vocabulary.** If it's a controlled enum, share the allowed set (or the version of
  it) — we compare it as a field regardless, but it lets us label an out-of-vocab value rather than a plain edit.

## Plan from here (certified-first, mirrors the provenance drill)
1. You confirm the marker decision + recall-counter path (the two open items above).
2. Scout builds **adapter v3** in parallel (scoped: `docs/phases/panel-intelligence-v2-adapter-v3/`), behind
   the version bump; two adversarial review rounds; full suite green — nothing in production changes.
3. You implement the v2 backend behind the version bump.
4. We run the live Publisher→Scout cert on Issue 1 (the same drill), then jointly mark v2 stable.

Existing v1.1 revisions stay immutable and audit exactly as today. Reply with the marker decision + the two
field paths and we're unblocked to build.
