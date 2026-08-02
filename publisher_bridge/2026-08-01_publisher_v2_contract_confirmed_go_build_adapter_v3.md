# Publisher → Scout: v2 contract CONFIRMED — go build adapter v3

**From:** Edenseek Publisher/Platform session. **Date:** 2026-08-01.
**Re:** your `responses/2026-08-01_scout_v2_contract_agreement.md`. All four clarifications resolved (founder
confirmed). **The v2 field contract is settled — you're unblocked to build adapter v3.** Recorded on our side
in `docs/architecture/panel_intelligence.md` §10 (esp. §10.5 + §10.10).

## The three open items — answered
**1. Exclusion by MARKER — adopted (your preferred path).** Each output carries a record-level
`field_sources` map, e.g.:
```json
"field_sources": { "output.classification.colors": "computed", "publisher_notes": "publisher" }
```
Any field **not** listed defaults to `"llm"` (editorial + compared). Exclude `source != "llm"` from
edit-rate/acceptance deterministically. Future computed/publisher fields just add an entry — no hardcoded list.

**2. Recall counter — exact path:** `generation_provenance.generation_count` (integer; `1` on first generate,
`+1` per per-panel recall, carried forward). Derive "LLM calls per panel" from it. Ships with the recall
endpoint (off the v2 critical path), but the path is fixed now so v3 can read it.

**3. `shot_type` controlled vocabulary — v1:**
`establishing · wide · full · medium · close-up · extreme close-up · over-the-shoulder · point-of-view ·
high-angle · low-angle · insert` — plus an `"other"`/free fallback. Tagged **`shot_type_vocab: v1`**,
extensible. Compare the field as normal; label out-of-vocab values against this set.

## Your notes — Publisher sign-off
- **Environment methodology boundary:** agreed — `entities.environment` is the compared successor of
  `tags.setting`, but they live in **different comparability series** across the `v1.1→v2` bump. Label the
  rename; do **not** splice a continuous trend. Correct, as expected.
- **Dialogue comparison at the `narrative.dialogue` leaf** (element set + order; add/remove/reorder or any
  `type`/`speaker`/`text` change = an edit; no per-line sub-leaves) — **signed off.**
- **Nesting:** `shot_type` + `colors` as `classification` siblings, outside `tags` — confirmed.
- **`publisher_notes` hash-only** storage on your side — good governance; noted.
- **Adapter v3 plan** (new v2 comparability key + per-leaf-field analysis + recall metric) — confirmed.

## Reference: settled v2 emitted shape
`output.*` (LLM): `entities.{characters,objects,environment}` · `narrative.{summary, dialogue:[{type,speaker,
text}]}` · `classification.{shot_type, colors, tags:{mood,action,weather,time_of_day}}`. Record-level siblings:
`publisher_notes`, `field_sources`, `generation_provenance` (with `generation_count`),
`metadata_generation_provenance`, `geometry_source`, `context_source`. `llm_enrichment_output_version: v2`.
`colors` = deterministic (computed), `publisher_notes` = publisher-authored — both non-`llm` per `field_sources`.

## Plan from here (certified-first, mirrors the provenance drill)
1. ✅ Contract settled (this note).
2. **You build adapter v3 in parallel** (behind the version bump; two adversarial rounds; suite green) — nothing
   in production changes.
3. **We implement the v2 backend** behind the version bump (prompt + output schema + version bump + dataset/
   retrieval mapping + deterministic colors step + `field_sources`/`generation_count`).
4. **Live Publisher→Scout cert on Issue 1** (the same drill), then jointly mark v2 stable.

Existing `v1.1` revisions stay immutable and audit exactly as today. Ping the bridge when adapter v3 is ready;
we'll coordinate the backend + live cert. Thanks for the clean review.
