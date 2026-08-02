# Certification Report — Adapter v3 (Panel Intelligence v2 metadata field contract)

**Track:** Week 11 · Panel Intelligence v2 · **Branch:** `week11-panel-intelligence-v2-adapter-v3`
**Date:** 2026-08-01 · **Discipline:** certified-first (build → 2 adversarial rounds → certify → deploy → live cert)
**Status:** CODE-COMPLETE · adversarially reviewed (2 rounds, all findings resolved) · offline-certified · HELD
for merge/deploy + coordinated live cert.

## 1. What changed and why
The Publisher settled the `llm_enrichment_output_version v1.1 → v2` field contract (advance-noticed + confirmed:
`publisher_bridge/2026-08-01_publisher_v2_contract_confirmed_go_build_adapter_v3.md`). Scout now consumes it
additively, with the deferred **per-leaf-field granularity** landing here. v1.1 continues to audit byte-identically.

## 2. The v2 field set (as consumed)
Compared LLM-editorial leaves (per-leaf): `entities.characters`, `entities.objects`, `entities.environment`
(successor of v1.1 `tags.setting`), `narrative.summary`, `narrative.dialogue` (list of `{type,speaker,text}`),
`classification.shot_type`, `classification.tags.{mood,action,weather,time_of_day}`.
Recorded but EXCLUDED (hash-only, never compared): `classification.colors` (computed), `publisher_notes`
(publisher-authored). Exclusion is by the Publisher record-level **`field_sources`** marker (any leaf `source
!= "llm"`), default `"llm"`; `colors` is additionally hard-excluded regardless of marker.

## 3. Scout-side changes
- **`review_contract_adapter.py`** — version-aware `_normalize_metadata` (v1.1 four fields | v2 marker-filtered
  per-leaf via `_extract_v2`/`_get_path`); `non_editorial` map (hash-only) for excluded leaves + record-level
  `publisher_notes`; `generation_count` carried (best-effort); `SUPPORTED_METADATA_VERSIONS=("v1","v1.1","v2")`;
  a fail-fast guard in `adapt_review` ONLY when both sides share an unsupported version (skew abstains).
- **`delta_metadata_revision.py`** — data-driven `_field_list` (the editorial leaves actually extracted); the
  per-artifact loop skips a leaf marker-excluded on either side (no phantom record) while skew marks the whole
  set `unsupported_schema`; structured-dialogue compared via the generic canonical rendering; acceptance gated
  on `structural_equal` (type-strict, collision-proof); `non_editorial` recorded from both sides (hash-only);
  best-effort `llm_calls_per_panel` from the recall counter; descriptive `field_set_version`.
- **No version-constant bump** (see §5). **No dashboard code change** — the editorial-burden table is
  data-driven and auto-renders the finer v2 field set; surfacing `colors`/`publisher_notes`/`llm_calls_per_panel`
  is deferred to a joint UI review.

## 4. Backward compatibility (proven)
v1.1 reviews audit **byte-identically**: `_field_list` returns the same four keys in the same order
(`sorted(FIELDS) == FIELDS`, verified), `non_editorial` empty, `llm_calls_per_panel` `None`, all metrics
identical. Confirmed live: `rev_b1470df6117a` (run007) is unaffected. Empty-metadata edge case restores the
4-field skeleton via the `or FIELDS` fallback.

## 5. Versioning / comparability (no code-version bump — deliberate)
The v1.1↔v2 boundary is carried by the evidence-dependent **`metadata_schema_version`** axis (`v1.1/v1.1` vs
`v2/v2` — dry-run confirmed), which already yields a distinct comparability key + `run_id`. The distance
DEFINITION and the fresh-only acceptance METHODOLOGY are unchanged, so `METADATA_REVISION_DISTANCE_VERSION`
and `METADATA_ACCURACY_VERSION` stay put and `static_versions()` is unchanged. Result: v1.1 content keeps its
exact numbers/keys (no spurious boundary, no needless re-run) and v2 is a clean new series.

## 6. Adversarial review (two rounds, independent)
**Round 1** found 5 edge-case findings; all fixed. **Round 2** verified every fix, found no new defect and no
v1.1 regression.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MAJOR | Mixed per-panel `field_sources` + union field list → a leaf excluded on one panel but present on another fabricated a phantom `added`/abstention record, contaminating acceptance. | The per-artifact loop skips a `(artifact,field)` pair when the leaf isn't editorial on **both** sides (schema-matched); skew still abstains over the full set. Null-but-present leaves are still compared (verified). |
| 2 | MINOR | Newline-injected structured dialogue could canonically collide → false accept. | Acceptance gated on `structural_equal` (ground truth), not `d==0`. |
| 3 | MINOR | Empty generated metadata → `per_field={}` instead of the 4-zero skeleton. | `_field_list(...) or list(FIELDS)` fallback. |
| 4 | verify | A historical `"v1"` review record would newly fail-fast. | `"v1"` added to supported (routes to v1.1 extraction, matching pre-v3 behavior). |
| 5 | NIT | An explicit `colors:"llm"` marker could pull computed colors into the compared set. | `colors` hard-excluded regardless of marker; other leaves stay marker-driven. |

**Behavior note (not a defect):** acceptance is now **type-strict** — a value differing only by type/repr
(e.g. `'5'` vs `5`) is an edit, not an accept. Arguably more correct; cannot arise in the textual metadata
schema (characters/dialogue/summary/tags carry no bare ints/bools), so it changes no v1.1/v2 numbers on real
or certified data.

## 7. Tests
Full suite **380 pass**. New: `tests/test_metadata_v2_contract.py` (16) — per-leaf field set, marker exclusion
(colors/notes recorded hash-only, no raw text), structured-dialogue edits (add/remove/reorder/speaker),
recall metric present/absent, both-sides-unsupported guard, skew-abstains, mixed-marker no-phantom, dialogue
collision, empty-metadata skeleton, `"v1"` literal, colors-marker-override, determinism.

## 8. Certification statement
Additive and backward-compatible (v1.1 byte-identical), deterministic, references+hashes only (no raw text —
verified for dialogue/notes/values), Publisher authority + Scout read-only boundary intact, v2 boundary carried
by `metadata_schema_version`. **Offline-certified.** Remaining gates: merge + deploy (backward-safe), then the
coordinated live cert against a real Publisher v2 revision (same drill as provenance).
