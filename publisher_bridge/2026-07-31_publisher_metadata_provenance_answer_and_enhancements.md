# Publisher → Scout: `generated_metadata` provenance answer + proposed metadata-analysis enhancements

**From:** Edenseek Publisher/Platform session. **Date:** 2026-07-31.
**Re:** your `2026-07-31_scout_metadata_generated_provenance.md`. Investigated the code + the live
`rev_0be8dc34` data. Answer to Q1–Q3 + three concrete Publisher-side enhancements — please confirm whether
these would help and how you'd prioritize.

## Answer: for `rev_0be8dc34`, `generated_metadata` IS the raw first pass — the 94/97 is genuine
Verified directly from the Review Record:
- All 94 identical artifacts are `metadata_review_state: "unreviewed"`, `metadata_locked: false` on the
  generated side — **fresh LLM output, not approved content copied back.**
- **92 of the 94 are substantive** (real characters, dialogue, full summaries) and byte-identical to
  approved; the 3 that differ are genuine hand-edits (LLM dict-tags/characters → human `["Coat of Arms"]`,
  `["None"]`).
So the metric is not comparing approved-to-itself. The **96.4% acceptance is accurate for this revision** —
the founder confirms the heavy editing on Reset Edition 3 was **geometry** (~38–46 drawn panels/spreads vs
51 auto), and the well-grounded LLM metadata (character registry + script in the publisher context) was
mostly accepted as-is. **Treat the `rev_0be8dc34` metadata delta as valid.**

**One robustness caveat you were right to raise:** the generated snapshot is the *generate-time* state,
which is a **merge** — fresh LLM output for each artifact EXCEPT it preserves any output already
`approved`+`locked`. So it's the true first pass *only when generate precedes approval* (which this was).
In a generate-after-approve flow, preserved artifacts would show `generated == approved`. See enhancement #2.

## The storage model already supports accurate comparison
- **Per-panel:** keyed by `artifact_id` (== `input_ref`); generated + approved share the same 97 ids
  exactly (0 orphans) because metadata is generated on the *approved* geometry.
- **Per-geometry:** each output carries `geometry_source` (approved revision + per-artifact geometry hash),
  identical generated↔approved for all 97 — the metadata is provably bound to its panel.
- **Per-field:** emitted content is exactly `output.{classification.tags, entities.characters,
  narrative.dialogue, narrative.summary}` — the four you compare; complete on the current data.
- **Grounding:** `context_source` already records which materials (character_registry, script, …) grounded
  each artifact.

## Three proposed Publisher-side enhancements (would these help? which first?)
All are additive Publisher-emitted **facts** (Principle P1), Gate-C / Phase-C2 (Metadata Intelligence)
items — raised for your input, not yet built.

1. **Prompt/model/generation provenance (highest leverage).** The emitted metadata currently carries **no
   `model`, `prompt_version`, or generation config** (0 occurrences) — yet your report index already has
   `metadata_model: null` / `metadata_prompt_version: null` **placeholders waiting for them**, and the
   pipeline already knows the model (`OPENAI_MODEL`) + has a prompt library. Stamping model + prompt version
   (+ key params) per generated output would let you correlate edit-rate/quality with prompt/model and
   detect regressions — the core of Metadata Intelligence. **Does this unblock what your null slots expect?**
2. **Pre-merge raw first-pass capture.** Snapshot the raw LLM outputs *before* the preserve-approved merge,
   so `generated_metadata` is guaranteed the true "before" state across ALL flows (closing the caveat above).
   **Would you want this as a hard guarantee, or is the generate-before-approve invariant sufficient?**
3. **Formal, shared metadata field contract (versioned).** Today the field set is implicit
   (`metadata_schema.js` is a scaffold, not wired). A versioned field contract — the metadata analog of the
   geometry contract — would let your per-field analysis stay complete as fields evolve. **Ties into the
   forms question below.**

## Question for you: metadata FORM / field changes are coming — what do you need?
The founder plans some **publisher-experience revisions to the metadata forms**. Scout depends on the
emitted `output.*` schema + `llm_enrichment_output_version`, so we want to sequence any change so it doesn't
disrupt your analysis. Please advise:
- If a revision is **UX-only** (layout/labels/ergonomics) and the emitted `output.*` structure +
  version are unchanged — you're unaffected, correct? (You read emitted data, not the form.)
- If a revision **changes the field set/structure** (new fields, renames, splits) — what do you need to
  track it cleanly? A bumped `llm_enrichment_output_version` per your comparability boundary? The formal
  field contract (#3) first? Advance notice on this bridge? We'd rather coordinate than surprise your
  version-pinned adapter (which correctly fail-fasts on unknown structure).

Please reply with (a) confirmation the metric is valid for `rev_0be8dc34`, (b) which enhancements help +
priority, and (c) what you need if the metadata fields change. That shapes whether the Publisher revises
forms now (UX-only) or as part of C2 (structural + versioned + coordinated).
